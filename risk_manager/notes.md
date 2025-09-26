daemon needs to run on : On Linux/WSL:
# Create a systemd service for risk_daemon.py so it runs as root (or a service user), starts on boot, and stays active in the background regardless of who’s logged in — no terminal required


Suggested Additions to AI_agent_1.md
	•	Add Error & Recovery section: point to OPERATIONS.md.
	•	Add Security Reminder: no secrets in logs.
	•	Add Rule Contract Reminder: rules = detection only, enforcement handled centrally.
	•	Add Diagnostics Note: keep diagnostic scripts separate from production daemon.
	•	Add Progress Log section at bottom for traceability


Enforcing User vs Admin Separation (Linux/WSL)
	•	Daemon process
	•	Runs as a systemd service under the admin account (or a dedicated riskd service user).
	•	Starts at boot, keeps running regardless of which user logs in.
	•	Regular users cannot stop or restart it.
	•	Config & secrets
	•	config/risk_manager_config.json → owned by admin, chmod 640.
	•	.env (API keys, secrets) → owned by admin, chmod 600.
	•	Only admin can edit, regular users = read-only (or no access).
	•	Logs
	•	logs/live.log and logs/audit.ndjson → readable by both admin and regular users.
	•	Permissions: chmod 644 (read-only to traders, writable only to daemon).
	•	This allows traders to observe, but not tamper.
	•	CLI commands
	•	riskd start/stop/validate → admin-only (passcode protected).
	•	riskd status/tail (and optionally riskd breaches) → allowed to all users.

