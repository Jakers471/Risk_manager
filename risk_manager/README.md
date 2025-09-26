# Risk Manager README

## Purpose

The **Risk Manager** is a daemon process that enforces trading discipline by monitoring all broker events in real time and applying strict rule-based controls.

* Runs continuously as a **24/7 daemon** under admin control.
* Enforces **14 modular rules** (starting with *max contracts*).
* Reacts to events in **under 100ms** by flattening or cancelling orders if limits are breached.
* Provides **plain English logs and audit trails** so traders understand exactly why an order was closed.
* Rules are **configurable via JSON** and loaded dynamically.

## Integration

* Lives in its own dedicated `risk_manager/` folder.
* **Never modify the SDK** (`src/project_x_py/`).
* Uses ProjectX SDK (`TradingSuite`, `EventBus`, etc.) for authentication, events, and broker communication.
* References: Use AI_agent_1.md for detailed SDK enums, events, API calls, and payloads.

## Rules

* Each rule is its **own module** in `risk_manager/rules/`.
* Rules are **enabled/disabled + parameterized** via `risk_manager/config/risk_manager_config.json`.
* Rule contract:

  * Input: Broker event (`ORDER_FILLED`, `POSITION_UPDATE`, etc.).
  * Output: Decision (`VALID`, `BREACH`) + enforcement action (`flatten`, `cancel_orders`, etc.).

## Daemon Modes

* **Enforcement mode**: Actively cancels/closes trades on breaches.
* **Dry run mode**: Logs decisions but does not enforce.
* **Status mode**: Reports health, subscriptions, and rule states.

## CLI Commands

* `riskd start` — Start daemon (admin-only).
* `riskd stop` — Stop daemon (admin-only).
* `riskd status` — Show running status.
* `riskd tail` — Stream live logs.
* `riskd dry-run` — Run without enforcement.
* `riskd validate` — Check connectivity and event subscriptions.

## Logging

* Logs stored in `risk_manager/logs/`.
* `live.log`: Detailed technical logs (rotated at 10MB, keep 5).
* `audit.ndjson`: Plain-English event trail of every decision.
* Logs must always explain:

  * Event received.
  * Rule(s) checked.
  * Outcome.
  * Action taken.

## Security

* Start/stop and config changes are **admin-passcode protected**.
* Traders may only **observe logs**, never modify rules or stop daemon.

## Guardrails

* **Do not edit the SDK (`src/project_x_py/`)**.
* **Never use emojis**.
* Keep rules modular and config-driven.
* No monolithic files — each rule gets its own file.
* Daemon must always provide logs in human-readable language.
