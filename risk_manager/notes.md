daemon needs to run on : On Linux/WSL:
# Create a systemd service for risk_daemon.py so it runs as root (or a service user), starts on boot, and stays active in the background regardless of who’s logged in — no terminal required


Suggested Additions to AI_agent_1.md
	•	Add Error & Recovery section: point to OPERATIONS.md.
	•	Add Security Reminder: no secrets in logs.
	•	Add Rule Contract Reminder: rules = detection only, enforcement handled centrally.
	•	Add Diagnostics Note: keep diagnostic scripts separate from production daemon.
	•	Add Progress Log section at bottom for traceability

