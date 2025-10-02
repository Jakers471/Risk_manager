# Risk Manager Operations

## Purpose

This document explains how the **Risk Manager Daemon** is started, stopped, and controlled.
It ensures that:

* Only **admin users** can configure or control the daemon.
* Regular traders can **observe logs only**, not change rules or stop protection.
* Logging is reliable, rotated, and always human-readable.

---

## Daemon Lifecycle

The Risk Manager runs as a **background process** on Ubuntu/WSL.

* Command-line wrapper: `riskd`
* Modes: `start`, `stop`, `status`, `tail`, `dry-run`, `validate`

### CLI Commands

* `riskd start` → Start the daemon (admin-only, passcode required).
* `riskd stop` → Stop the daemon (admin-only, passcode required).
* `riskd status` → Show if daemon is running, list active rules.
* `riskd tail` → Stream live logs to console.
* `riskd dry-run` → Start in dry-run mode (log only, no enforcement).
* `riskd validate` → Connectivity + subscription check.

---

## Admin Control

* **Daemon must be admin-passcode protected.**
* Regular users cannot:

  * Start or stop the daemon.
  * Modify rules/config.
* Regular users can:

  * Run `riskd status`.
  * Run `riskd tail` (observe logs).

Implementation note for AI:

* Protect start/stop commands with a **passcode prompt** (stored securely in `.env`).
* Passcode = only known to admin.

---

## Logging

* All logs live in:

  ```
  risk_manager/logs/
  ├── live.log        # Technical logs, rotated (10MB, keep 5 files)
  └── audit.ndjson    # Human-readable audit trail (append-only)
  ```

### Log Rotation

* `live.log` rotates at **10 MB**, keeping 5 backups.
* `audit.ndjson` never rotates (append-only).

### Human-readable audit trail

Every breach event must include a plain-English explanation:

* What event was received.
* Which rule triggered.
* What action was taken.
* Example:

  ```
  [2025-09-25 14:01:32] Breach detected: max contracts (limit=4). 
  Position opened with size=5. Action taken: flattened immediately.
  ```

---

## Config Reload

* Config (`risk_manager/config/risk_manager_config.json`) is read **on daemon startup only**.
* To change rules, **restart the daemon** (admin-only).
* No live reload.

---

## Failures & Recovery

* If daemon crashes:

  * Log reason in `live.log`.
  * Refuse restart until config is valid.
* If realtime feed disconnects (SignalR):

  * Log warning.
  * Attempt reconnect automatically.
  * Do not block trading; resume enforcement once reconnected.

---

## Security

* Secrets (API keys, JWT refresh tokens) live in **`.env` at project root**, managed by ProjectX SDK.
* Risk Manager must never duplicate or expose secrets.

---

### Daily Loss Rule Operations

**Trading Lock Mechanism:**
- On breach (cumulative realized P&L < -max_usd), all open positions are flattened via close_position_direct.
- `trading_locked` flag is set: Any new ORDER_FILLED events trigger immediate flatten of that position.
- Lock persists until 5:00 PM CT reset (automatic on next relevant event).

**Manual Unlock (Admin Only):**
- Restart daemon: `python3 risk_manager/daemon/risk_daemon.py stop` (passcode), then `start`. This clears globals but reset is time-based—wait for 5:00 PM CT or edit last_reset_date manually (not recommended).
- Check status: Tail logs for "Trading locked" messages or cumulative P&L.

**Troubleshooting:**
- Verify cumulative: Search live.log for "Updated daily P&L: ... cumulative X.XX".
- Reset issues: Ensure event timestamps are UTC; CT conversion uses pytz ('America/Chicago')—handles DST.
- No breach on positives: Rule only triggers losses < -limit; profits add to buffer.
- Test: Dry-run with simulated losses > limit → "(dry-run: no enforcement)" log.

