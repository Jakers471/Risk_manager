# Risk Manager Test Plan

## Purpose

Testing ensures the Risk Manager works exactly as intended:

* Rules trigger instantly when breaches occur.
* No accidental enforcement on valid trades.
* Logs clearly explain every decision.

Testing is **layered**: quick checks for connectivity, dry runs for rule flow, and live trades for end-to-end validation.

---

## Testing Modes

### 1. Connectivity Validation

Command:

```
riskd validate
```

* Checks broker authentication.
* Confirms realtime subscriptions are active.
* Verifies config is valid.
* Logs result: pass/fail for each step.

### 2. Dry Run Mode

Command:

```
riskd dry-run
```

* Runs daemon with **no enforcement**, logging only.
* Simulate orders manually or via test account.
* Logs decisions in both `live.log` and `audit.ndjson`:

  * Example:

    ```
    [Dry Run] ORDER_FILLED: size=5 vs limit=4 → BREACH detected. Action (flatten) skipped.
    ```

### 3. Live Mode (Small Orders)

* Use practice account with **1–2 contract orders**.
* Place trades manually.
* Risk Manager must enforce rules in real time (<100ms).
* Observe logs:

  * Confirm enforcement (flatten/cancel).
  * Confirm plain-English explanation is written.

---

## Test Scenarios

1. **Max Contracts Rule**

   * Config: `"max_contracts": 4`.
   * Place 3-lot order → PASS (no enforcement).
   * Place 5-lot order → FAIL (immediate flatten).

2. **Partial Fill**

   * Submit 5-lot limit with max=4.
   * If partial 2-lot fill → PASS (no enforcement).
   * If full 5-lot fill → FAIL (flatten).

3. **Disabled Rule**

   * Set `"enabled": false` in config.
   * Place 10-lot order.
   * PASS = logged as unchecked, no enforcement.

4. **Dry Run**

   * With `"dry_run": true`, place 10-lot order.
   * PASS = logs show detection but no enforcement.

5. **Recovery**

   * Disconnect internet mid-trade.
   * PASS = logs show feed disconnect warning, auto-reconnect, resume enforcement.

---

## Benchmarks

* Target: <100ms from event → enforcement API call.
* Log latency in `live.log`:

  ```
  Enforcement latency: 87ms (ORDER_FILLED → close_position)
  ```

---

## Unit/Integration Tests

* Lightweight tests in `tests/`:

  * Config loader.
  * Rule engine decision function.
  * Event → action mapping.
* Run with:

  ```
  pytest -q
  ```

---

## Testing Philosophy

* **Dry runs** = fast iteration (no risk).
* **Live trades** = ultimate test (real account discipline).
* **Logs** = single source of truth.

---

