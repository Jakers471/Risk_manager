import asyncio
import json
import os
import sys
import logging
from datetime import datetime, date, timedelta
from logging.handlers import RotatingFileHandler
import argparse
from pathlib import Path
import importlib
import sys
from pathlib import Path
import time
import pytz

from project_x_py import TradingSuite, EventType, ProjectX  # Add ProjectX here

# Ensure directories exist
Path("logs").mkdir(exist_ok=True)
Path("config").mkdir(exist_ok=True)

# Basic config if not exists
config_path = Path("config/risk_manager_config.json")
if not config_path.exists():
    config = {
        "dry_run": True,
        "log_level": "INFO",
        "symbols": ["MNQ"],
        "rules": {
            "max_contracts": {
                "enabled": True,
                "severity": "high",
                "description": "Restricts maximum contracts per position",
                "parameters": {
                    "max_contracts": 4,
                    "enforcement": "flatten"
                }
            }
        }
    }
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

# Logging setup
log_dir = Path("logs")
live_logger = logging.getLogger("risk_daemon_live")
live_handler = RotatingFileHandler(
    log_dir / "live.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5
)
live_logger.addHandler(live_handler)
live_logger.setLevel(logging.INFO)

audit_file = Path("logs/audit.ndjson")
pnl_persist_file = Path("logs/daily_pnl.json")  # For persistence across restarts

# Global state
suite = None
running = False
loaded_rules = {}
account_id = None
daily_realized_pnl = 0.0
trading_locked = False
last_reset_date = None
current_config = {}
tracked_positions = {}  # {contract_id: {'avg_price': float, 'size': int, 'type': int}}
open_positions = {}  # Track: {contract_id: {'entry_price': float, 'size': int, 'side': int, 'unrealized_pnl': float}}
MNQ_POINT_VALUE = 5.0  # $5 per point for MNQ micro futures

def log_to_audit(message, level="INFO"):
    with open(audit_file, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message
        }) + "\n")

def prompt_passcode():
    return input("Enter admin passcode: ")

def load_config():
    print(f"DEBUG LOAD: Attempting load from {config_path.absolute()}")
    try:
        with open(config_path, "r") as f:
            raw = f.read()
            print(f"DEBUG LOAD: Raw file content (first 100 chars): '{raw[:100]}'")
            f.seek(0)
            config = json.load(f)
            print(f"DEBUG LOAD: Parsed dry_run = {config.get('dry_run', 'PARSE FAIL')} from file")
            print(f"DEBUG LOAD: Full rules keys = {list(config.get('rules', {}).keys())}")
            return config
    except Exception as e:
        print(f"DEBUG LOAD: Load failed: {e} - defaulting to dry_run=True")
        return {"dry_run": True, "log_level": "INFO", "symbols": ["MNQ"], "rules": {"max_contracts": {"enabled": True, "severity": "high", "description": "Restricts maximum contracts per position", "parameters": {"max_contracts": 4, "enforcement": "flatten"}}}}

def load_rules_from_config(config):
    rules = {}
    sys.path.insert(0, str(Path(__file__).parent.parent))
    for rule_name in config['rules']:
        if config['rules'][rule_name]['enabled']:
            try:
                module = importlib.import_module(f'rules.{rule_name}')
                rules[rule_name] = module
                live_logger.info(f"Successfully loaded rule module: {rule_name}")
            except ImportError as e:
                live_logger.error(f"Failed to load rule module: rules.{rule_name} - {e}")
                log_to_audit(f"Failed to load rule module: {rule_name} - {e}", level="ERROR")
            except Exception as e:
                live_logger.error(f"Error in rule module {rule_name}: {e}")
                log_to_audit(f"Error in rule module {rule_name}: {e}", level="ERROR")
    return rules

def save_pnl_state():
    """Persist current P&L to file"""
    state = {
        "daily_realized_pnl": daily_realized_pnl,
        "last_reset_date": last_reset_date.isoformat() if last_reset_date else None,
        "trading_locked": trading_locked,
        "timestamp": datetime.now().isoformat()
    }
    with open(pnl_persist_file, "w") as f:
        json.dump(state, f, indent=2)
    live_logger.info(f"P&L state saved: cumulative {daily_realized_pnl:.2f}")

def load_pnl_state():
    """Load persisted P&L (if valid)"""
    global daily_realized_pnl, trading_locked, last_reset_date
    if pnl_persist_file.exists():
        try:
            with open(pnl_persist_file, "r") as f:
                state = json.load(f)
            saved_date = date.fromisoformat(state['last_reset_date']) if state['last_reset_date'] else None
            ct_tz = pytz.timezone('America/Chicago')
            today = ct_tz.localize(datetime.now()).date()
            if saved_date == today:  # Same day – valid
                daily_realized_pnl = state['daily_realized_pnl']
                trading_locked = state['trading_locked']
                last_reset_date = saved_date
                live_logger.info(f"P&L state loaded: cumulative {daily_realized_pnl:.2f}, locked={trading_locked}")
                print(f"Debug: Persisted P&L loaded: {daily_realized_pnl:.2f}")
                return True
            else:
                live_logger.info("Persisted P&L outdated (new day) – will query fresh")
        except Exception as e:
            live_logger.warning(f"Failed to load P&L state: {e}")
    return False

async def fetch_initial_daily_pnl():
    """Auto-query SDK for today's realized P&L"""
    global daily_realized_pnl
    try:
        # Primary: Portfolio P&L (has day_pnl for today)
        pnl_summary = await suite.positions.get_portfolio_pnl()
        print(f"Debug: pnl_summary full = {pnl_summary}")  # Debug output
        day_pnl = pnl_summary.get('day_pnl', 0.0)
        realized = pnl_summary.get('realized_pnl', 0.0)
        # Use day_pnl for daily (realized + realized today); fallback realized if day=0
        daily_realized_pnl = day_pnl if day_pnl != 0 else realized
        live_logger.info(f"Auto-fetched daily P&L: {daily_realized_pnl:.2f} (day_pnl={day_pnl}, realized={realized})")
        print(f"Debug: Auto P&L from SDK: {daily_realized_pnl:.2f}")
        
        # Secondary: Performance metrics for confirmation (yesterday to now)
        yesterday = datetime.now() - timedelta(days=1)
        perf = await suite.positions.get_performance_metrics(yesterday, datetime.now())
        daily_perf = perf.get('daily_pnl', daily_realized_pnl)
        if abs(daily_perf - daily_realized_pnl) > 0.01:
            live_logger.warning(f"P&L mismatch: portfolio {daily_realized_pnl:.2f} vs perf {daily_perf:.2f} – using portfolio")
        return daily_realized_pnl
    except Exception as e:
        live_logger.error(f"Auto P&L query failed: {e} – using 0.0")
        print(f"Debug: Auto P&L failed ({e}) – default 0.00")
        return 0.0

async def check_reset_and_update_pnl(event, is_polled=False):
    global daily_realized_pnl, trading_locked, last_reset_date, tracked_positions, open_positions
    ct_tz = pytz.timezone('America/Chicago')
    event_ct = event.timestamp.astimezone(ct_tz) if hasattr(event, 'timestamp') else datetime.now(ct_tz)
    today_5pm = ct_tz.localize(datetime(event_ct.year, event_ct.month, event_ct.day, 17, 0))
    if event_ct >= today_5pm:
        today_date = event_ct.date()
        if last_reset_date != today_date:
            daily_realized_pnl = 0.0
            tracked_positions.clear()  # Clear tracked on reset
            open_positions.clear()
            if trading_locked:
                trading_locked = False
                log_to_audit("Daily session reset at 5:00 PM CT. Loss/profit counters cleared, trading unlocked.", level="INFO")
                live_logger.info("Daily reset: Trading unlocked.")
            last_reset_date = today_date
            live_logger.info("Daily P&L reset at 5:00 PM CT.")
            print(f"Debug: Daily P&L reset to 0.00")
            save_pnl_state()  # Persist reset
    
    updated = False
    pnl = 0.0
    contract_id = None
    if event.type == EventType.POSITION_CLOSED:
        contract_id = event.data.get('contractId', 'CON.F.US.MNQ.Z25')
        pnl = event.data.get('pnl', 0.0)  # Often 0/missing
        if pnl == 0.0 and suite:  # Primary fallback: Query position for realized (unrealized_pnl on close = realized)
            try:
                pos = await suite.positions.get_position(contract_id)
                if pos and hasattr(pos, 'unrealized_pnl'):
                    pnl = pos.unrealized_pnl  # Final unrealized becomes realized on size=0
                    print(f"Debug: Queried realized from unrealized_pnl: {pnl:.2f}")
                else:
                    # Secondary: Manual from tracked
                    old = tracked_positions.pop(contract_id, None)
                    if old and old['avg_price'] > 0:
                        exit_price = event.data.get('averagePrice', 0.0)
                        if exit_price == 0.0:
                            try:
                                symbol = contract_id.split('.')[-2] if '.' in contract_id else 'MNQ'
                                current_price = await suite['MNQ'].data.get_current_price()
                                exit_price = current_price
                                print(f"Debug: Fallback exit_price query: {exit_price}")
                            except Exception as e:
                                print(f"Debug: Price query failed: {e}, using 0")
                                exit_price = 0.0
                        size = old['size']
                        pos_type = old['type']
                        point_value = MNQ_POINT_VALUE
                        if pos_type == 1:  # LONG
                            pnl = (exit_price - old['avg_price']) * size * point_value
                        else:  # SHORT
                            pnl = (old['avg_price'] - exit_price) * size * point_value
                        print(f"Debug: Manual P&L calc from tracked: {pnl:.2f} (entry={old['avg_price']}, exit={exit_price}, size={size}, type={pos_type})")
                    else:
                        live_logger.warning(f"No P&L data or tracking for close {contract_id} – using 0")
            except Exception as e:
                live_logger.error(f"P&L query/calc on close failed for {contract_id}: {e} – using 0")
                pnl = 0.0
        daily_realized_pnl += pnl
        live_logger.info(f"Updated daily P&L from CLOSE: +{pnl:.2f}, cumulative {daily_realized_pnl:.2f}")
        print(f"Debug: P&L updated from CLOSE: +{pnl:.2f}, cumulative {daily_realized_pnl:.2f}")
        # Clean up tracking
        if contract_id in open_positions:
            del open_positions[contract_id]
        if contract_id in tracked_positions:
            del tracked_positions[contract_id]
        updated = True
    elif event.type == EventType.POSITION_PNL_UPDATE:
        pnl = event.data.get('realized_pnl', 0.0)
        if pnl != 0.0:
            daily_realized_pnl += pnl
            live_logger.info(f"Updated daily P&L from PNL_UPDATE: +{pnl:.2f}, cumulative {daily_realized_pnl:.2f}")
            print(f"Debug: P&L updated from PNL_UPDATE: +{pnl:.2f}, cumulative {daily_realized_pnl:.2f}")
            updated = True
    elif event.type == EventType.POSITION_UPDATED and is_polled:
        size = event.data.get('size', 1)
        if size == 0:
            contract_id = event.data.get('contractId', 'CON.F.US.MNQ.Z25')
            pnl = event.data.get('pnl', 0.0)
            if pnl == 0.0 and suite:
                try:
                    pos = await suite.positions.get_position(contract_id)
                    pnl = pos.unrealized_pnl if hasattr(pos, 'unrealized_pnl') else 0.0
                except Exception as e:
                    live_logger.error(f"Polled P&L query failed: {e}")
                    # Fallback manual from tracked
                    old = tracked_positions.pop(contract_id, None)
                    if old and old['avg_price'] > 0:
                        try:
                            current_price = await suite['MNQ'].data.get_current_price()
                            exit_price = current_price
                        except:
                            exit_price = 0.0
                        size_polled = old['size']
                        pos_type = old['type']
                        point_value = MNQ_POINT_VALUE
                        if pos_type == 1:
                            pnl = (exit_price - old['avg_price']) * size_polled * point_value
                        else:
                            pnl = (old['avg_price'] - exit_price) * size_polled * point_value
                        print(f"Debug: Polled manual PNL calc: {pnl:.2f}")
            daily_realized_pnl += pnl
            live_logger.info(f"Updated daily P&L from polled close: +{pnl:.2f}, cumulative {daily_realized_pnl:.2f}")
            print(f"Debug: P&L updated from POLLED (size=0): +{pnl:.2f}, cumulative {daily_realized_pnl:.2f}")
            if contract_id in open_positions:
                del open_positions[contract_id]
            if contract_id in tracked_positions:
                del tracked_positions[contract_id]
            updated = True
    
    if updated:
        save_pnl_state()  # Persist after update
        # Immediate breach check
        if 'daily_loss' in current_config.get('rules', {}):
            max_usd = current_config['rules']['daily_loss'].get('parameters', {}).get('max_usd', 200)
            if daily_realized_pnl < -max_usd:
                print(f"Debug: Post-update BREACH: {daily_realized_pnl:.2f} < -{max_usd}")
                log_to_audit(f"BREACH: Daily realized P&L {daily_realized_pnl:.2f} < -{max_usd}. Action: kill_switch (dry-run: no enforcement)", level="WARNING")

async def poll_for_close(symbol='MNQ'):
    """Fallback poll after sell: Check size=0 + update P&L"""
    if not suite:
        return
    try:
        positions = await suite.positions.get_all_positions(account_id)
        for pos in positions:
            if pos.symbolId == f'F.US.{symbol}' and pos.size == 0:
                fake_event = type('obj', (object,), {'type': EventType.POSITION_UPDATED, 'data': {'pnl': 0.0, 'size': 0, 'symbol': symbol, 'contractId': pos.contractId}, 'timestamp': datetime.now()})()
                await check_reset_and_update_pnl(fake_event, is_polled=True)
                live_logger.info(f"Polled close for {symbol} (size=0)")
                return True
    except Exception as e:
        live_logger.error(f"Polling error: {e}")
    return False

async def event_handler(event):
    global loaded_rules, current_config, suite, open_positions, tracked_positions
    # Debug: Log event type/data for all
    print(f"Debug Event: Type={str(event.type)}, Data keys={list(event.data.keys()) if event.data else 'None'}")
    live_logger.info(f"Event type debug: {str(event.type)}")
    
    # Log all events technically to live.log
    event_data = {
        "type": str(event.type),
        "data": event.data,
        "timestamp": datetime.now().isoformat()
    }
    live_logger.info(f"Event received: {event_data}")
    
    # Skip audit for QUOTE_UPDATE
    if event.type == EventType.QUOTE_UPDATE:
        return
    
    # Track open positions on FILLS/UPDATES
    if event.type == EventType.ORDER_FILLED:
        order = event.data.get('order')
        if order:
            contract_id = getattr(order, 'contractId', 'CON.F.US.MNQ.Z25')
            size = getattr(order, 'size', 0)
            side = getattr(order, 'side', 0)  # 0=buy(long), 1=sell(short)
            filled_price = getattr(order, 'filledPrice', 0.0)
            if size > 0:  # New fill – check if opening/increasing
                current_pos = open_positions.get(contract_id, {'size': 0})
                pos_type = 1 if side == 0 else 2  # 1=LONG, 2=SHORT
                if current_pos['size'] == 0 or (side == 0 and current_pos['side'] == 1) or (side == 1 and current_pos['side'] == 0):  # New open or flip
                    open_positions[contract_id] = {
                        'entry_price': filled_price,
                        'size': size,
                        'side': side,
                        'unrealized_pnl': 0.0
                    }
                    tracked_positions[contract_id] = {
                        'avg_price': filled_price,
                        'size': size,
                        'type': pos_type
                    }
                    live_logger.info(f"Tracked new open: {contract_id} {side} {size} @ {filled_price}")
                else:  # Add to existing (avg entry update)
                    old_open = open_positions[contract_id]
                    total_size = old_open['size'] + size
                    old_open['entry_price'] = (old_open['size'] * old_open['entry_price'] + size * filled_price) / total_size
                    old_open['size'] = total_size
                    tracked_positions[contract_id]['avg_price'] = old_open['entry_price']
                    tracked_positions[contract_id]['size'] = total_size
                    live_logger.info(f"Updated position: {contract_id} size {total_size} avg {old_open['entry_price']:.2f}")
            # Update unrealized if position exists
            if contract_id in open_positions:
                try:
                    pos = await suite.positions.get_position(contract_id)
                    if pos and hasattr(pos, 'unrealized_pnl'):
                        open_positions[contract_id]['unrealized_pnl'] = pos.unrealized_pnl
                except Exception as e:
                    live_logger.warning(f"Unrealized query failed: {e}")
    
    elif event.type == EventType.POSITION_UPDATED:
        contract_id = event.data.get('contractId', 'CON.F.US.MNQ.Z25')
        size = event.data.get('size', 0)
        avg_price = event.data.get('averagePrice', 0.0)
        pos_type = event.data.get('type', 1)  # Default long
        if size != 0:
            tracked_positions[contract_id] = {'avg_price': avg_price, 'size': abs(size), 'type': pos_type}
            print(f"Debug: Tracked UPDATED {contract_id} - avg={avg_price}, size={size}, type={pos_type}")
        if contract_id in open_positions:
            try:
                pos = await suite.positions.get_position(contract_id)
                if pos and hasattr(pos, 'unrealized_pnl'):
                    open_positions[contract_id]['unrealized_pnl'] = pos.unrealized_pnl
                    live_logger.debug(f"Updated unrealized for {contract_id}: {pos.unrealized_pnl:.2f}")
            except Exception as e:
                live_logger.warning(f"Unrealized update failed: {e}")
    
    # Update P&L FIRST (for closes/PNL/UPDATED)
    if event.type in [EventType.POSITION_CLOSED, EventType.POSITION_PNL_UPDATE, EventType.POSITION_UPDATED]:
        await check_reset_and_update_pnl(event)
    
    # Polling fallback for sells
    if event.type == EventType.ORDER_FILLED:
        order = event.data.get('order')
        if order and getattr(order, 'side', 0) == 1:  # Sell
            symbol = getattr(order, 'symbolId', 'F.US.MNQ').split('.')[-1]
            await asyncio.sleep(1)
            await poll_for_close(symbol)
    
    # Plain-English audit
    try:
        symbol = 'MNQ'
        audit_msg = f"Event received: {str(event.type)} for {symbol}."
        
        if event.type == EventType.ORDER_FILLED:
            order = event.data.get('order')
            if hasattr(order, 'symbolId'):
                symbol = order.symbolId.split('.')[-1] if '.' in order.symbolId else order.symbolId
            size = abs(order.size) if hasattr(order, 'size') else 0
            filled_price = getattr(order, 'filledPrice', 'N/A')
            side_num = getattr(order, 'side', 0)
            side = 'buy' if side_num == 0 else 'sell'
            audit_msg = f"Order filled for {symbol}: {side} {size} contracts at {filled_price}."
        elif event.type == EventType.POSITION_UPDATED:
            size = abs(event.data.get('size', 0))
            symbol = event.data.get('symbol', 'MNQ')
            pnl = event.data.get('pnl', 0.0)
            audit_msg = f"Position updated for {symbol}: size {size} (P&L {pnl:.2f if pnl != 0 else 'N/A'})."
            if size == 0:
                audit_msg += " (possible close)"
        elif event.type == EventType.POSITION_CLOSED:
            pnl = event.data.get('pnl', 0.0)
            audit_msg = f"Position closed: realized P&L {pnl:.2f} (cumulative {daily_realized_pnl:.2f})."
        elif event.type == EventType.POSITION_PNL_UPDATE:
            realized_pnl = event.data.get('realized_pnl', 0.0)
            audit_msg = f"Position P&L updated: realized +{realized_pnl:.2f} (cumulative {daily_realized_pnl:.2f})."
        
        log_to_audit(audit_msg)
        
    except Exception as e:
        audit_msg = f"Event received: {str(event.type)} (details unavailable)."
        log_to_audit(audit_msg)
        live_logger.error(f"Audit summary error for {event.type}: {e}")
    
    # Rule evaluation
    has_breach = False
    breach_result = None
    for name, module in loaded_rules.items():
        rule_config = current_config['rules'][name]
        result = await module.check(event, rule_config, suite, current_config['dry_run'], daily_realized_pnl)
        if result['status'] == 'BREACH':
            live_logger.warning(f'BREACH: {result["reason"]} (Rule: {name})')
            has_breach = True
            breach_result = result
            if 'audit_msg' not in locals():
                log_message = f'BREACH detected: {result["reason"]}. Action: {result["action"]}'
                if current_config['dry_run']:
                    log_message += ' (dry-run: no enforcement)'
                log_to_audit(log_message, level="WARNING")
            if 'audit_msg' in locals():
                append_msg = f" - {result['reason']}. Action: {result['action']}"
                if current_config['dry_run']:
                    append_msg += ' (dry-run: no enforcement)'
                audit_msg += append_msg
                log_to_audit(audit_msg, level="WARNING")
            break
    else:
        if event.type == EventType.ORDER_FILLED:
            order = event.data.get('order')
            if order and getattr(order, 'side', 0) == 1:
                print("Debug: Sell close - no breach (net projected <= max)")
    
    # Enforcement (live only)
    if has_breach and not current_config['dry_run'] and breach_result:
        enforce_start_time = time.perf_counter()
        try:
            if breach_result['action'] == 'flatten':
                contract_id = None
                if event.type == EventType.ORDER_FILLED:
                    order = event.data.get('order')
                    if order:
                        contract_id = getattr(order, 'contractId', None)
                elif event.type == EventType.POSITION_UPDATED:
                    instrument = event.data.get('instrument', 'MNQ')
                    contract_id = 'CON.F.US.MNQ.Z25' if instrument == 'MNQ' else instrument
                if not contract_id:
                    contract_id = 'CON.F.US.MNQ.Z25'
                
                live_logger.info(f'Attempting to flatten position for {contract_id}')
                response = await suite.positions.close_position_direct(contract_id, account_id=account_id)
                if response.get('success', False):
                    live_logger.info(f'Enforced flatten successful on {contract_id}')
                    log_to_audit(f'Enforced: Flattened {contract_id} due to {breach_result["reason"]}.', level="INFO")
                else:
                    error_msg = response.get('errorMessage', 'Unknown error')
                    live_logger.error(f'Flatten failed for {contract_id}: {error_msg}')
                    log_to_audit(f'Enforcement failed for {contract_id}: {error_msg}', level="ERROR")
            elif breach_result['action'] == 'kill_switch':
                positions = await suite.positions.get_all_positions(account_id)
                closed_count = 0
                for pos in positions:
                    if pos.size != 0:
                        pos_response = await suite.positions.close_position_direct(pos.contractId, account_id)
                        if pos_response.get('success', False):
                            closed_count += 1
                trading_locked = True
                live_logger.info(f"Daily loss kill switch: Closed {closed_count}/{len([p for p in positions if p.size != 0])} positions.")
                log_to_audit(f"Daily Loss Limit breached: {daily_realized_pnl:.2f} < -{breach_result.get('max_usd', 200):.2f}. All positions closed. Trading disabled until next reset (5:00 PM CT).", level="WARNING")
        except Exception as e:
            live_logger.error(f"Enforcement exception for {contract_id or 'MNQ'}: {e}")
            log_to_audit(f"Enforcement failed for {contract_id or 'MNQ'}: {e}", level="ERROR")
        finally:
            enforce_end_time = time.perf_counter()
            live_logger.info(f"Enforcement latency: {(enforce_end_time - enforce_start_time)*1000:.0f}ms")

    if trading_locked and event.type == EventType.ORDER_FILLED and not current_config['dry_run']:
        order = event.data.get('order')
        if order:
            contract_id = getattr(order, 'contractId', 'CON.F.US.MNQ.Z25')
            await suite.positions.close_position_direct(contract_id, account_id)
            log_to_audit(f"Trading locked: Flattened new fill on {contract_id} due to daily loss breach.", level="WARNING")
            live_logger.warning(f"Trading locked: Flattened unauthorized fill on {contract_id}")

async def start_daemon(args):
    global suite, running, loaded_rules, current_config, daily_realized_pnl, open_positions, tracked_positions
    if running:
        print("Daemon already running.")
        return
    passcode = prompt_passcode()
    if passcode != "admin123":
        print("Invalid passcode.")
        return
    try:
        current_config = load_config()
        print(f"DEBUG STARTUP: Loaded dry_run = {current_config.get('dry_run', 'DEFAULT TRUE')} from {config_path.absolute()}")
        print(f"DEBUG FULL CONFIG: {current_config}")
    except Exception as e:
        print(f"Config load failed: {e} - defaulting to dry_run=True")
        current_config = {"dry_run": True, "log_level": "INFO", "symbols": ["MNQ"], "rules": {"max_contracts": {"enabled": True, "severity": "high", "description": "Restricts maximum contracts per position", "parameters": {"max_contracts": 4, "enforcement": "flatten"}}}}

    loaded_rules = load_rules_from_config(current_config)
    open_positions = {}  # Initialize tracking
    tracked_positions = {}
    
    # Auto-initialize P&L: Load persisted first, then query SDK
    load_pnl_state()  # Try persist (same day)
    suite = await TradingSuite.create(["MNQ"], features=[])
    daily_realized_pnl = await fetch_initial_daily_pnl()  # Override with fresh query
    if daily_realized_pnl < -current_config['rules'].get('daily_loss', {}).get('parameters', {}).get('max_usd', 200):
        print("Debug: Startup BREACH detected – monitor for kill_switch")
        log_to_audit(f"Startup: Daily P&L {daily_realized_pnl:.2f} < -200 – Trading at risk.", level="WARNING")
    save_pnl_state()  # Save queried state
    
    if current_config["dry_run"]:
        print("Starting in dry-run mode.")
    else:
        print("Starting in live mode.")
    global account_id
    account_id = int(os.getenv('PROJECT_X_ACCOUNT_ID', 12089421))
    suite.realtime.account_id = account_id
    await suite.realtime.subscribe_user_updates()
    await suite.on(EventType.ORDER_FILLED, event_handler)
    await suite.on(EventType.POSITION_UPDATED, event_handler)
    await suite.on(EventType.QUOTE_UPDATE, event_handler)
    await suite.on(EventType.POSITION_CLOSED, event_handler)
    await suite.on(EventType.POSITION_PNL_UPDATE, event_handler)
    await suite["MNQ"].data.start_realtime_feed()
    running = True
    print("Daemon started. Press Ctrl+C to stop.")
    try:
        while running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await stop_daemon(None)

async def stop_daemon(args):
    global running, open_positions, tracked_positions
    passcode = prompt_passcode()
    if passcode != "admin123":
        print("Invalid passcode.")
        return
    running = False
    open_positions.clear()  # Clear on stop
    tracked_positions.clear()
    save_pnl_state()  # Save on stop
    await suite.realtime.unsubscribe_user_updates()
    if suite:
        await suite.disconnect()
    print("Daemon stopped.")

async def status_daemon(args):
    global loaded_rules, current_config, daily_realized_pnl, open_positions, tracked_positions
    try:
        current_config = load_config()
    except Exception:
        print("Failed to load configuration.")
        return
    loaded_rules = load_rules_from_config(current_config)
    print(f"Config loaded: dry_run={current_config['dry_run']}, symbols={current_config.get('symbols', [])}")
    print(f"Rules enabled in config: {list(current_config['rules'].keys())}")
    print(f"Rules successfully loaded: {list(loaded_rules.keys())}")
    # Auto-refresh P&L for status using low-level ProjectX (no realtime)
    try:
        async with ProjectX.from_env() as client:
            pnl_summary = await client.positions.get_portfolio_pnl()
            print(f"Debug: pnl_summary full = {pnl_summary}")  # Raw dict debug
            day_pnl = pnl_summary.get('day_pnl', 0.0)
            realized = pnl_summary.get('realized_pnl', 0.0)
            daily_realized_pnl = day_pnl if day_pnl != 0 else realized
            print(f"Debug: Computed daily P&L: {daily_realized_pnl:.2f} (day_pnl={day_pnl}, realized={realized})")
    except Exception as e:
        print(f"Debug: P&L query failed: {e} - using 0.00")
        daily_realized_pnl = 0.0
    print(f"Current daily realized P&L: {daily_realized_pnl:.2f} (resets 5PM CT)")
    print(f"Open positions tracked: {len(open_positions)}")
    print(f"Tracked positions: {len(tracked_positions)}")
    if trading_locked:
        print("Trading locked (daily loss breach).")
    if running:
        print("Daemon is running.")
    else:
        print("Daemon is not running.")

async def tail_logs(args):
    with open(log_dir / "live.log", "r") as f:
        f.seek(0, 2)
        while True:
            line = f.read(1024)
            if line:
                print(line, end="")
            await asyncio.sleep(0.1)

async def dry_run_daemon(args):
    config = load_config()
    config["dry_run"] = True
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print("Dry-run mode enabled in config.")
    await start_daemon(args)

async def validate_daemon(args):
    try:
        config = load_config()
        print("Config loaded successfully.")
        suite = await TradingSuite.create(["MNQ"], features=[])
        await suite["MNQ"].data.start_realtime_feed()
        print("Realtime feed started.")
        await suite["MNQ"].data.stop_realtime_feed()
        await suite.disconnect()
        print("Subscriptions valid.")
        print("Validation passed.")
    except Exception as e:
        print(f"Validation failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Risk Manager Daemon")
    parser.add_argument("command", choices=["start", "stop", "status", "tail", "dry-run", "validate"])
    args = parser.parse_args()
    if args.command == "start":
        asyncio.run(start_daemon(args))
    elif args.command == "stop":
        asyncio.run(stop_daemon(args))
    elif args.command == "status":
        asyncio.run(status_daemon(args))
    elif args.command == "tail":
        asyncio.run(tail_logs(args))
    elif args.command == "dry-run":
        asyncio.run(dry_run_daemon(args))
    elif args.command == "validate":
        asyncio.run(validate_daemon(args))

if __name__ == "__main__":
    main()