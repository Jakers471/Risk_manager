# ProjectX SDK File Structure

## Root Level Files
- `.cursorrules`: Cursor IDE rules for AI assistance.
- `.env`: Environment variables (API keys, auth).
- `.env.example`: Template for .env setup.
- `.gitignore`: Git ignore patterns.
- `.mcp.json`: IDE metadata/config.
- `.pre-commit-config.yaml`: Pre-commit linting hooks.
- `.python-version`: Python version (3.12).
- `.secrets.baseline`: Security scanning config.
- `AGENTS.md`: AI agents guidelines.
- `CHANGELOG.md`: Version history.
- `CLAUDE.md`: Claude AI usage rules.
- `CODE_OF_CONDUCT.md`: Community guidelines.
- `CONTRIBUTING.md`: Contribution instructions.
- `DATETIME_PARSING_ISSUE.md`: Datetime bug notes.
- `GEMINI.md`: Gemini AI rules.
- `LICENSE`: MIT license.
- `README.md`: Project overview/install/quickstart.
- `SECURITY.md`: Security policy.
- `check_quality.sh`: Code quality check script.
- `codecov.yml`: Coverage reporting config.
- `forge.yaml`: Build/deploy tool config.
- `mkdocs.yml`: Documentation build config.
- `pyproject.toml`: Project metadata/dependencies.
- `pytest.ini`: Testing config.
- `test_example.sh`: Example test runner.
- `uv.lock`: Dependency lockfile.

## .claude/
- `.claude`: Claude AI config (metadata).

## .cursor/
- (Empty: IDE-specific).

## .git/
- (Git internals: config, logs, refs – version control).

## .github/
- `workflows/ci.yml`: CI pipeline (lint/test/build).

## .venv/
- (Virtual env: site-packages, binaries – runtime deps).

## benchmarks/
- `benchmark_orderbook.py`: Orderbook performance tests.
- `benchmark_realtime.py`: Realtime feed benchmarks.
- `benchmark_statistics.py`: Stats calculation speed.
- `run_benchmarks.py`: Run all benchmarks.
- `results.json`: Benchmark outputs.

## docs/
- `README.md`: Docs setup (MkDocs guide).
- `changelog.md`: Docs version changes.
- `index.md`: Homepage.
- `getting-started/authentication.md`: Auth setup.
- `getting-started/configuration.md`: Config options.
- `getting-started/installation.md`: Install steps.
- `getting-started/quickstart.md`: Basic usage.
- `guide/indicators.md`: Technical indicators.
- `guide/orderbook.md`: Orderbook analysis.
- `guide/orders.md`: Order management.
- `guide/positions.md`: Position tracking.
- `guide/realtime.md`: Realtime data.
- `guide/risk.md`: Risk management.
- `guide/sessions.md`: Trading sessions.
- `guide/trading-suite.md`: TradingSuite guide.
- `api/client.md`: Client API reference.
- `api/data-manager.md`: Data manager API.
- `api/indicators.md`: Indicators API.
- `api/models.md`: Data models.
- `api/order-manager.md`: Order manager API.
- `api/position-manager.md`: Position manager API.
- `api/risk-manager.md`: Risk API.
- `api/statistics.md`: Stats API.
- `api/trading-suite.md`: Suite API.
- `examples/advanced.md`: Advanced examples.
- `examples/backtesting.md`: Backtesting guide.
- `examples/basic.md`: Basic examples.
- `examples/multi-instrument.md`: Multi-instrument.
- `examples/notebooks/index.md`: Jupyter notebooks.
- `examples/realtime.md`: Realtime examples.
- `development/agents.md`: AI dev guide.
- `development/architecture.md`: Architecture overview.
- `development/contributing.md`: Dev contributions.
- `development/testing.md`: Testing guide.
- `migration/breaking-changes.md`: Breaking changes.
- `migration/v3-to-v4.md`: v3-v4 migration.
- `stylesheets/extra.css`: Custom docs styling.
- (Subdirs: /examples/notebooks/ – tutorials; /indicators/ – indicator docs).

## examples/
- `00_trading_suite_demo.py`: Full suite demo.
- `01_basic_client_connection.py`: Auth/basic API.
- `02_order_management.py`: Orders (place/modify).
- `03_position_management.py`: Positions/P&L.
- `04_realtime_data.py`: Realtime feeds.
- `05_orderbook_analysis.py`: Orderbook depth.
- `06_advanced_orderbook.py`: Iceberg detection.
- `07_technical_indicators.py`: Indicators usage.
- `08_order_and_position_tracking.py`: Order/position monitoring.
- `09_get_check_available_instruments.py`: Instrument search.
- `10_unified_event_system.py`: EventBus.
- `11_simplified_data_access.py`: Data patterns.
- `12_simplified_multi_timeframe.py`: Multi-timeframe.
- `13_enhanced_models.py`: Model examples.
- `15_order_lifecycle_tracking.py`: Order lifecycle.
- `15_risk_management.py`: Risk validation.
- `16_managed_trades.py`: Managed trades.
- `16_join_orders.py`: Order joining.
- `26_multi_instrument_trading.py`: Multi-instrument.
- (Subdirs: /sessions/ – session examples).

## scripts/
- `serve-docs.sh`: MkDocs serve.
- `deploy-docs.sh`: Deploy to GitHub Pages.
- `check_quality.sh`: Lint/test checks.
- `setup-dev.sh`: Dev env setup.
- `generate-coverage.sh`: Coverage reports.

## src/project_x_py/
- `__init__.py`: Package init/exports.
- `cli.py`: CLI commands (setup/config).
- `client.py`: Core client (auth/API).
- `trading_suite.py`: TradingSuite (create/managers).
- `event_bus.py`: Event system (on/emit).
- `order_manager/__init__.py`: Order init.
- `order_manager/core.py`: Order placement/cancel.
- `order_manager/order_types.py`: Order types.
- `order_manager/tracking.py`: Order events/tracking.
- `position_manager/__init__.py`: Position init.
- `position_manager/core.py`: Position get/close.
- `position_manager/tracking.py`: Position sync/events.
- `realtime_data_manager/__init__.py`: Realtime data init.
- `realtime_data_manager/core.py`: Feed start/stop/callbacks.
- `realtime_data_manager/callbacks.py`: Event handlers.
- `realtime/__init__.py`: Realtime client init.
- `realtime/core.py`: WebSocket/SignalR.
- `realtime/connection_management.py`: Hub connections.
- `realtime/subscriptions.py`: Subscribe/unsubscribe.
- `risk_manager/__init__.py`: Risk init.
- `risk_manager/core.py`: Risk validation/sizing.
- `risk_manager/managed_trade.py`: Managed trades/brackets.
- `statistics/__init__.py`: Stats aggregator.
- `statistics/bounded_statistics.py`: Memory-limited stats.
- `indicators/__init__.py`: Indicators export.
- `indicators/rsi.py`: RSI calc.
- (Subdirs: /types/ – models/enums; /utils/ – helpers (error, locks); /indicators/*.py – TA-Lib impls).

## tests/
- `test_client.py`: Client tests.
- `test_orders.py`: Order tests.
- `test_positions.py`: Position tests.
- `test_realtime.py`: Realtime tests.
- `test_indicators.py`: Indicator tests.
- `conftest.py`: Pytest fixtures.
- (Subdirs: /test_order_manager/, /test_realtime/ – unit/integration tests).

This structure provides a complete SDK for ProjectX trading: core code in src/, docs in docs/, examples in examples/, tests for validation. Key capabilities: async API calls for orders/positions/quotes, realtime WebSocket events, risk management, technical indicators, and diagnostics for robust broker communication.
