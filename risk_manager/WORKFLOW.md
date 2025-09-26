# Risk Manager AI Agent 1

## Purpose

This file guides the **AI agent** working inside the repo.
It explains:

* How to follow the six docs (`README.md`, `ARCHITECTURE.md`, `CONFIG.md`, `OPERATIONS.md`, `TEST_PLAN.md`, `GUARDRAILS.md`).
* How to structure work step by step.
* How to test and confirm functionality.
* How to stay aligned with the beginner user (me).

**Important:** I am new to coding. Keep explanations clear, avoid jargon, and always tie back to the structure in this folder.

---

## Workflow Plan

### Phase 1: Foundation

1. **Read the six docs in `risk_manager/`**.

   * `README.md` = purpose + CLI commands.
   * `ARCHITECTURE.md` = folder map + event flow.
   * `CONFIG.md` = rule config schema.
   * `OPERATIONS.md` = daemon lifecycle, logs, admin.
   * `TEST_PLAN.md` = how to validate.
   * `GUARDRAILS.md` = strict do's/don'ts.
2. **Set up daemon skeleton** in `daemon/risk_daemon.py`.

   * Must support: `start`, `stop`, `status`, `tail`, `dry-run`, `validate`.
   * Must load config from `config/risk_manager_config.json`.
   * Must attach to ProjectX EventBus.
3. Confirm daemon runs in **dry-run mode** first (no enforcement).

### Phase 2: First Rule (Max Contracts)

1. Create `rules/max_contracts.py`.

   * Implement rule contract: `check(event, config) -> Decision`.
   * Must enforce: if size > max, flatten → cancel orders.
   * Must log **plain English explanation**.
2. Update config JSON with `max_contracts` section.
3. Test in **dry-run mode** with manual orders.
4. Move to **live mode** with small practice trades.

### Phase 3: Logging & Diagnostics

1. Verify `logs/live.log` rotates at 10MB, keeps 5 files.
2. Verify `logs/audit.ndjson` logs every decision in plain English.
3. Add timing benchmark to confirm **<100ms** enforcement latency.

### Phase 4: Expand Rules

1. Add each new rule as its own file in `rules/`.
2. Always update `CONFIG.md` and `risk_manager_config.json` with new parameters.
3. Run **dry-run tests** before live testing.
4. Only move to live trades when dry-run is stable.

### Phase 5: Maintenance

1. Never edit SDK code in `src/project_x_py/`.
2. Only touch `risk_manager/` folder.
3. If updates break something, roll back to last working config + rule set.
4. Keep `AI_agent_1.md` updated with progress (date, changes, results).

---

## Testing Checklist

For every new change:

* ✅ Does daemon start/stop with admin passcode?
* ✅ Does config load without errors?
* ✅ Are logs written in both `live.log` and `audit.ndjson`?
* ✅ Does dry-run show detection without enforcement?
* ✅ Do live small trades trigger enforcement correctly?
* ✅ Is latency logged under 100ms?

---

## Staying on Track

* Always reference `GUARDRAILS.md` before coding.
* Always check `CONFIG.md` when adding/updating rules.
* Always use `TEST_PLAN.md` before moving to live testing.
* Always update this file (`AI_agent_1.md`) with progress notes.

---

## Notes for AI

* I am a beginner. Keep code clean, modular, and easy to follow.
* Always explain what was added/changed in simple language.
* Never dump massive code files; keep modules small and focused.
* No emojis. Ever.
