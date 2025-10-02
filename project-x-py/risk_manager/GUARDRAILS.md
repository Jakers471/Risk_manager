# Risk Manager Guardrails

## Purpose

This document defines **non-negotiable rules** the coding AI must follow when working inside the `risk_manager/` folder. It ensures the Risk Manager remains stable, modular, and aligned with its purpose.

---

## Do's

* ✅ **Keep everything modular**

  * Each rule = its own file in `risk_manager/rules/`.
  * No single file should grow beyond a few hundred lines.

* ✅ **Use config-driven logic**

  * All parameters come from `risk_manager/config/risk_manager_config.json`.
  * Rules must check if `enabled` before executing.

* ✅ **Provide clear logs**

  * Technical details go to `live.log` (rotated).
  * Plain-English decisions go to `audit.ndjson`.
  * Always explain why a rule triggered.

* ✅ **Follow daemon lifecycle**

  * Daemon runs via `riskd` CLI wrapper (`start`, `stop`, `status`, `tail`, `dry-run`, `validate`).
  * Config reload only on restart.

* ✅ **Enforce admin control**

  * Start/stop requires admin passcode.
  * Regular users may only observe logs.

---

## Don'ts

* ❌ **Do not modify SDK code** (`src/project_x_py/`).
* ❌ **Do not use emojis** anywhere in code, logs, or docs.
* ❌ **Do not hard-code rule parameters**. Everything must come from config.
* ❌ **Do not collapse multiple rules into one monolithic file**.
* ❌ **Do not bypass logging** — every action must be logged.
* ❌ **Do not add complexity** beyond what is necessary for enforcement, logging, and modularity.

---

## Design Principles

* **Event-driven, not polling** → respond instantly to ProjectX EventBus events.
* **Enforcement-first** → flatten/cancel orders immediately when breach detected.
* **Plain English audit** → trader must always understand *why* a rule fired.
* **Minimal, stable core** → only add rules, never reinvent the architecture.

---

## Enforcement Priority

When in doubt, the coding AI must prioritize:

1. **Flatten position** (market).
2. **Cancel any remaining open orders**.
3. **Log both technical + plain English details**.

