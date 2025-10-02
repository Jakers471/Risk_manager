# Risk Manager Configuration

## Purpose

The Risk Manager is fully **config-driven**.

* All rule parameters live in **one JSON file**: `risk_manager/config/risk_manager_config.json`.
* Each rule must check config before running.
* Traders cannot edit config directly — only the **admin** can.

## Config File Path

```
risk_manager/config/risk_manager_config.json
```

## Global Fields

* `dry_run` *(bool)* — If `true`, rules only log decisions without enforcement.
* `log_level` *(str)* — `"INFO"` or `"DEBUG"`.
* `symbols` *(list[str])* — List of instruments to monitor. If empty, monitor **all**.

## Rule Schema

Each rule has its own section with:

* `enabled` *(bool)* — If `false`, rule is ignored.
* `severity` *(str)* — `"high" | "medium" | "low"` (used for logging).
* `description` *(str)* — Human-readable explanation.
* `parameters` *(object)* — Rule-specific settings.

## Example Config (Max Contracts Rule v1)

```json
{
  "dry_run": false,
  "log_level": "INFO",
  "symbols": ["MNQ", "ES"],

  "rules": {
    "max_contracts": {
      "enabled": true,
      "severity": "high",
      "description": "Restricts maximum contracts per position",
      "parameters": {
        "max_contracts": 4,
        "enforcement": "flatten" 
      }
    }
  }
}
```

### Enforcement Options

* `"flatten"` → Immediately close all positions if breach detected.
* `"reduce"` → Attempt to reduce to max allowed (if partial).
* `"cancel_orders_then_flatten"` → Cancel pending orders first, then flatten.

## Rule Expansion

Future rules follow the same pattern:

```json
"daily_loss_limit": {
  "enabled": true,
  "severity": "high",
  "description": "Stops trading after max daily loss",
  "parameters": {
    "max_loss_usd": 200,
    "reset_time": "00:01",
    "timezone": "US/Central"
  }
}
```

## Validation

The daemon must validate the config at startup:

* Check JSON is well-formed.
* Ensure required fields exist.
* Log errors and refuse to start if invalid.
