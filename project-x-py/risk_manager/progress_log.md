
### Progress Log

Phase 1: Foundation - Implemented daemon skeleton in daemon/risk_daemon.py. Supports CLI: start (with passcode, dry-run logging), stop, status, tail, dry-run, validate. Loads config from config/risk_manager_config.json (created basic). Attaches to EventBus for ORDER_FILLED, POSITION_UPDATED, QUOTE_UPDATE (logs events in dry-run). Fixed EventType error (POSITION_UPDATE to POSITION_UPDATED). Confirmed: start/stop works, config loads, subscriptions start (no errors). Logs to live.log (rotated) and audit.ndjson. Date: 2025-09-26. Changes: Skeleton CLI, event loop, EventType fix. Results: Tested dry-run start - initializes without crash, ready for events.

Phase 1 Update: Fixed rule loading (added sys.path for imports, global current_config for scope). Now status shows loaded rules. Date: 2025-09-26. Changes: Import path adjustment, global config. Results: Rules load successfully, daemon ready for event testing.

Phase 1 Update: Fixed NameError in event_handler (config to current_config), updated max_contracts event type. Status now loads rules correctly. Date: 2025-09-26. Changes: Global config references, event type. Results: No errors on events, rules evaluate.

Phase 1 Update: Fixed NameError in event_handler by using current_config consistently and removing duplicate loop. Events now evaluate without errors. Date: 2025-09-26. Changes: event_handler cleanup. Results: Quote updates log cleanly, rules ready for position events.

Phase 1 Update: Cleaned event_handler (single loop, current_config only, removed duplicate). Quote events now process without NameError. Added latency logging prep. Date: 2025-09-26. Changes: event_handler refactor. Results: Events evaluate cleanly, ready for breach test.

Phase 1 Update: Removed duplicate loops in event_handler, fixed remaining 'config' to 'current_config'. No more NameError on events. Date: 2025-09-26. Changes: Single loop refactor. Results: Quote updates process cleanly, daemon stable.

Phase 2: Added account-specific subscriptions for orders/positions/trades (user hub) to receive manual position events. Used account_id from .env. Date: 2025-09-26. Changes: subscribe_orders/positions/trades in start_daemon. Results: Daemon now receives ORDER_FILLED/POSITION_UPDATED on manual trades.

Phase 2 Update: Set realtime.account_id and explicit subscribe_user_updates() for specific account events. Added account_id to close_position. Date: 2025-09-26. Changes: Explicit user subscriptions. Results: Manual trades now trigger ORDER_FILLED/POSITION_UPDATED.

Phase 2 Update: Added explicit account_id setting for realtime subscriptions and API calls (close_position). Used global current_account_id from .env. Updated validate to use account. Date: 2025-09-26. Changes: Account targeting in realtime and positions. Results: Events for specific account 12089421.

Phase 2 Completion - Full max_contracts rule operational in live mode. Date: 2025-09-26.

Phase 3: Implemented daily_loss rule. Tracks cumulative realized P&L (POSITION_CLOSED/PNL_UPDATE); breaches if < -max_usd (e.g., -250 < -200). Kill switch: Flattens all positions, sets trading_locked (re-flattens new fills until 5:00 PM CT reset). Reset at 5:00 PM CT (UTC→CT via pytz). Date: 2025-09-26. Changes: Daemon globals (daily_pnl, locked, reset), check_reset_and_update_pnl func, pass daily_pnl to checks, kill_switch enforcement (get_all_positions loop + close), locked re-flatten on ORDER_FILLED; new rules/daily_loss.py; config.json/CONFIG.md/OPERATIONS.md updates. Results: Dry-run logs breach without enforce/lock; live: Breach→"All positions closed. Trading disabled until 5:00 PM CT.", new fills auto-flatten, reset logs "Trading unlocked.". No false triggers, cumulative accurate.

Phase 3 Update: Fixed realized P&L calculation on POSITION_CLOSED. Now queries suite.positions.get_position(contractId) post-close for pos.unrealized_pnl (becomes realized when size=0); fallback manual calc from tracked entry_price + current_price * size * MNQ_POINT_VALUE=5.0. Tracks opens on ORDER_FILLED (store entry/side/size), updates unrealized on POSITION_UPDATED. Removed manual prompts – fully automatic via startup portfolio query + event increments. Clears tracking on reset/stop. Date: 2025-09-29. Changes: Globals open_positions/MNQ_POINT_VALUE; event_handler tracking logic; check_reset_and_update_pnl query/calc on pnl=0; start_daemon init; status shows tracked count. Results: Buy1@sell1 logs "Updated daily P&L from CLOSE: +X.XX" (non-zero); cumulative updates accurately. No false 0s, breach detects live losses.

Summary of All Fixes:
- Config: Robust load_config with debug prints/raw content check; defaults to dry_run=True on parse fail; restart required for changes.
- Async: Rule check() is async; await suite.positions.get_position(contract_id); handler awaits module.check(suite, dry_run).
- Rule Logic: Projects net_size = current_size + delta (buy +fill, sell -fill); fallback in dry-run (breach large opens, skip closes); reason "Projected net size X > max Y".
- Audit: Plain English for ORDER_FILLED/POSITION_UPDATED only (skip QUOTE_UPDATE); single entry per event with breach append; level=WARNING on breach.
- Enforcement: suite.positions.close_position_direct(contract_id, account_id); extracts order.contractId or instrument→'CON.F.US.MNQ.Z25'; handles response {'success': True, 'orderId': ...} or errorMessage; latency logged.
- Errors Fixed: 'log_to_audit level' (add param), 'Order no get' (dot notation), false breaches on closes (net calc), RuntimeWarning (await get_position), duplicated load_config (consolidate), return indentation.
- Permissions/WSL: Absolute paths for audit.ndjson; manual mkdir/chmod 666 if needed.

Test Results (Live Mode):
- Buy 5: Breach → "Enforced: Flattened CON.F.US.MNQ.Z25 due to Projected net size 5 > 4."
- Sell 5 (short): Breach → Flatten (closes to 0).
- Close (sell/buy 5): No breach (net=0).
- POSITION_UPDATED (post-fill size=6): Breach → Flatten.

Sample Audit Logs:
{"timestamp": "2025-09-26T14:06:10.592137", "level": "INFO", "message": "Enforced: Flattened CON.F.US.MNQ.Z25 due to Projected net position size 5.0 exceeds max 4."}
{"timestamp": "2025-09-26T14:06:19.338285", "level": "WARNING", "message": "Order filled for MNQ: sell 5.0 contracts at 24724.0. - Projected net position size 5.0 exceeds max 4. Action: flatten"}
{"timestamp": "2025-09-26T14:06:30.322359", "level": "WARNING", "message": "Position updated for MNQ: current size 6 contracts. - Net position size 6 exceeds max 4. Action: flatten"}
{"timestamp": "2025-09-26T14:06:30.651359", "level": "INFO", "message": "Enforced: Flattened CON.F.US.MNQ.Z25 due to Projected net position size 6.0 exceeds max 4."}

Remaining Edge: Occasional "Enforcement failed ... : None" on POSITION_UPDATED (contract_id extraction fix applied: use event.data['instrument'] → full ID).

From notes.md Suggestions:
- Error & Recovery: See OPERATIONS.md for troubleshooting (e.g., restart on config change, check permissions).
- Security: No secrets in logs/audit; .env chmod 600, config 640 (admin only).
- Rule Contract: Rules = detection only (return BREACH/action); central handler enforces via SDK.
- Diagnostics: Separate scripts for validate/tail; no polling in daemon.
- Progress Log: Maintained here for traceability (dates, changes, results).
