# Risk Manager Architecture

## Folder Structure

```
risk_manager/
├── README.md             # Purpose, CLI commands, guardrails
├── ARCHITECTURE.md       # This document
├── CONFIG.md             # Config schema and examples
├── OPERATIONS.md         # Running the daemon, admin-only notes
├── TEST_PLAN.md          # Testing strategy
├── GUARDRAILS.md         # Rules for AI (no emojis, no SDK edits, modularity)
│
├── config/
│   └── risk_manager_config.json   # All rule parameters
│
├── logs/
│   ├── live.log          # Technical logs (rotated at 10MB, keep 5)
│   └── audit.ndjson      # Plain-English decision trail
│
├── rules/                # Independent risk rules
│   └── max_contracts.py  # First rule implementation
│
└── daemon/
    └── risk_daemon.py    # Main daemon runner
```

## Event Flow

1. **Broker event arrives** (via ProjectX SDK EventBus).
   Example: `ORDER_FILLED`, `POSITION_UPDATE`, `ORDER_CANCELLED`.
2. **Risk Manager Daemon receives event**.

   * Parses event.
   * Sends to Rule Engine.
3. **Rule Engine evaluates enabled rules**.

   * Each rule module exposes a `check(event, config)` function.
   * Returns decision (`VALID` | `BREACH`).
4. **If breach detected** → Enforcement.

   * Action = `flatten`, `cancel_orders`, or both (per config).
   * Triggered via ProjectX SDK API (fast executor).
5. **Logging/Audit trail**.

   * `live.log`: Technical info (event payloads, timing).
   * `audit.ndjson`: Plain English explanation (e.g., *“Breached max contracts: 5 > 4. Position flattened.”*).

## Rule Plug-In Contract

Each rule is a self-contained Python module inside `rules/`.
It must implement:

* **Function**: `check(event, config) -> Decision`
* **Inputs**:

  * `event`: Broker event dict.
  * `config`: Rule parameters (from JSON).
* **Outputs**:

  * `{ "status": "VALID" | "BREACH", "reason": str, "action": "flatten" | "reduce" | "cancel_orders" }`

The daemon aggregates these results:

* If **all VALID** → do nothing.
* If **any BREACH** → enforce immediately.

## Config Loading

* All parameters stored in `config/risk_manager_config.json`.
* Daemon loads at startup and refreshes on restart.
* Rules must **check if enabled** in config before executing.

## Enforcement Priority

For max-contracts rule (v1):

1. **Flatten position immediately**.
2. **Cancel all remaining open orders** for that symbol.
3. Log the full sequence in both log files.

## Performance Targets

* Event → enforcement API call in **<100ms**.
* Use event-driven hooks only (no polling).
* Retry logic: 2–3 retries on failure before escalating.
