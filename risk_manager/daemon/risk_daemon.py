import asyncio
import json
import os
import sys
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
import argparse
from pathlib import Path
import importlib
import sys
from pathlib import Path
import time


from project_x_py import TradingSuite, EventType

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

audit_file = log_dir / "audit.ndjson"

# Global state
suite = None
running = False
loaded_rules = {}

def log_to_audit(message):
    with open(audit_file, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "message": message
        }) + "\n")

def prompt_passcode():
    return input("Enter admin passcode: ")

def load_config():
    with open(config_path, "r") as f:
        return json.load(f)

def load_rules_from_config(config):
       rules = {}
       # Add risk_manager root to path for imports
       sys.path.insert(0, str(Path(__file__).parent.parent))
       for rule_name in config['rules']:
           if config['rules'][rule_name]['enabled']:
               try:
                   module = importlib.import_module(f'rules.{rule_name}')  # Relative import from risk_manager
                   rules[rule_name] = module
                   live_logger.info(f"Successfully loaded rule module: {rule_name}")
               except ImportError as e:
                   live_logger.error(f"Failed to load rule module: rules.{rule_name} - {e}")
                   log_to_audit(f"Failed to load rule module: {rule_name} - {e}", level="ERROR")
               except Exception as e:
                   live_logger.error(f"Error in rule module {rule_name}: {e}")
                   log_to_audit(f"Error in rule module {rule_name}: {e}", level="ERROR")
       return rules

async def event_handler(event):
    global loaded_rules, current_config
    
    # Log event
    event_data = {
        "type": str(event.type),
        "data": event.data,
        "timestamp": datetime.now().isoformat()
    }
    live_logger.info(f"Event received: {event_data}")
    log_to_audit(f"Received event: {event.type}. Data: {event.data}. In dry-run mode, no action taken.")
    
    # Single rule evaluation loop
    for name, module in loaded_rules.items():
        rule_config = current_config['rules'][name]
        result = module.check(event, rule_config)
        if result['status'] == 'BREACH':
            live_logger.warning(f'BREACH: {result["reason"]} (Rule: {name})')
            log_message = f'BREACH detected: {result["reason"]}. Action: {result["action"]}'
            if current_config['dry_run']:
                log_message += ' (dry-run: no enforcement)'
            log_to_audit(log_message, level="WARNING")

            if not current_config['dry_run']:
                enforce_start_time = time.perf_counter()
                try:
                    if result['action'] == 'flatten':
                        instrument_symbol = event.data.get('instrument', 'MNQ')
                        live_logger.info(f'Attempting to flatten position for {instrument_symbol}')
                        await suite.positions.close_position(instrument_symbol)
                        live_logger.info(f'Enforced flatten on {instrument_symbol}')
                        log_to_audit(f'Enforced: Flattened {instrument_symbol} due to {result["reason"]}.')
                except Exception as e:
                    live_logger.error(f"Enforcement failed for {instrument_symbol}: {e}")
                    log_to_audit(f"Enforcement failed for {instrument_symbol}: {e}", level="ERROR")
                finally:
                    enforce_end_time = time.perf_counter()
                    live_logger.info(f"Enforcement latency: {(enforce_end_time - enforce_start_time)*1000:.0f}ms")

async def start_daemon(args):
    global suite, running, loaded_rules, current_config
    if running:
        print("Daemon already running.")
        return
    passcode = prompt_passcode()
    if passcode != "admin123":  # Placeholder passcode in .env or hardcode for now
        print("Invalid passcode.")
        return
    current_config = load_config()
    loaded_rules = load_rules_from_config(current_config)
    if current_config["dry_run"]:
        print("Starting in dry-run mode.")
    suite = await TradingSuite.create(["MNQ"], features=[])
    account_id = int(os.getenv('PROJECT_X_ACCOUNT_ID', 12089421))
    suite.realtime.account_id = account_id
    await suite.realtime.subscribe_user_updates()
    await suite.on(EventType.ORDER_FILLED, event_handler)
    await suite.on(EventType.POSITION_UPDATED, event_handler)
    await suite.on(EventType.QUOTE_UPDATE, event_handler)
    await suite["MNQ"].data.start_realtime_feed()
    running = True
    print("Daemon started. Press Ctrl+C to stop.")
    try:
        while running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await stop_daemon(None)

async def stop_daemon(args):
    global running
    passcode = prompt_passcode()
    if passcode != "admin123":
        print("Invalid passcode.")
        return
    running = False
    await suite.realtime.unsubscribe_user_updates()
    if suite:
        await suite.disconnect()
    print("Daemon stopped.")

async def status_daemon(args):
    global loaded_rules, current_config
    try:
        current_config = load_config()
    except Exception:
        print("Failed to load configuration.")
        return
    loaded_rules = load_rules_from_config(current_config)
    print(f"Config loaded: dry_run={current_config['dry_run']}, symbols={current_config.get('symbols', [])}")
    print(f"Rules enabled in config: {list(current_config['rules'].keys())}")
    print(f"Rules successfully loaded: {list(loaded_rules.keys())}")
    if running:
        print("Daemon is running.")
    else:
        print("Daemon is not running.")

async def tail_logs(args):
    # Simple tail -f equivalent for live.log
    with open(log_dir / "live.log", "r") as f:
        f.seek(0, 2)  # End of file
        while True:
            line = f.read(1024)
            if line:
                print(line, end="")
            await asyncio.sleep(0.1)

async def dry_run_daemon(args):
    # Alias for start with dry_run=true
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
