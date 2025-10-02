# AI Agent 1: Complete ProjectX SDK Guide for Broker Communication

This guide covers all enums, events, subscriptions, API calls, and broker interaction for the project-x-py SDK (v3.5.9). It includes realtime updates, orders, positions, quotes, contracts, and more. Based on full codebase scan (src/project_x_py/*).

## 1. Enums

### EventType (src/project_x_py/event_bus.py)
Class: `class EventType(Enum):` (line 18)
- Values (from usages in event_bus.py, realtime_data_manager/callbacks.py, position_manager/tracking.py, risk_manager/managed_trade.py):
  - NEW_BAR: New OHLCV bar (e.g., 1min close). Data: {'instrument': 'MNQ', 'timeframe': '1min', 'open': 21000, 'high': 21005, 'low': 20995, 'close': 21002, 'volume': 500}.
  - POSITION_CLOSED: Position fully closed. Data: {'instrument': 'MNQ', 'pnl': 25.0, 'exit_price': 21025}.
  - ORDER_FILLED: Order executed. Data: {'order_id': 123, 'fill_price': 21000, 'filled_size': 1}.
  - ORDER_CANCELLED: Order cancelled. Data: {'order_id': 123, 'reason': 'user_cancel'}.
  - ORDER_REJECTED: Order rejected. Data: {'order_id': 123, 'reason': 'insufficient_margin'}.
  - DATA_UPDATE: General data change. Data: {'instrument': 'MNQ', 'type': 'bar', 'data': {...}}.
  - QUOTE_UPDATE: Bid/ask update. Data: {'instrument': 'MNQ', 'bid': 21000.25, 'ask': 21000.5, 'bid_size': 100, 'ask_size': 50}.
  - TRADE_TICK: Individual trade tick. Data: {'instrument': 'MNQ', 'price': 21000.5, 'size': 100, 'side': 'buy'}.
  - POSITION_UPDATE: Position changed (size/P&L). Data: {'instrument': 'MNQ', 'size': 1, 'unrealized_pnl': -5.0, 'current_price': 21000}.
  - POSITION_OPENED: New position opened. Data: {'instrument': 'MNQ', 'size': 1, 'avg_price': 21000}.
  - POSITION_PNL_UPDATE: P&L updated. Data: {'instrument': 'MNQ', 'unrealized_pnl': -5.0}.
  - RISK_LIMIT_WARNING: Risk threshold hit. Data: {'type': 'daily_loss', 'current': -25, 'limit': -20}.

Import: `from project_x_py import EventType`

### OrderSide (src/project_x_py/types/trading.py)
Class: `class OrderSide(IntEnum):` (line 94)
- Values: BUY = 0, SELL = 1.
- Usage: `side=OrderSide.BUY` in place_order()`.
- Mapping: {'BUY': 0, 'SELL': 1} (str to int for API).

### OrderType (src/project_x_py/types/trading.py)
Class: `class OrderType(Enum):`
- Values: MARKET, LIMIT, STOP, STOP_LIMIT, BRACKET, OCO, TRAILING_STOP, JOIN_BID, JOIN_ASK.
- Usage: `order_type=OrderType.LIMIT` in place_order()`.
- Mapping: {'MARKET': 0, 'LIMIT': 1, 'STOP': 2, 'STOP_LIMIT': 3, 'BRACKET': 4, 'OCO': 5, 'TRAILING_STOP': 6, 'JOIN_BID': 7, 'JOIN_ASK': 8} (int codes for API).
- Advanced: TRAILING_STOP (trails by trailPrice, adjusts stop as price moves favorably); JOIN_BID/JOIN_ASK (joins current best bid/ask for immediate execution at market).

### PositionStatus (src/project_x_py/types/protocols.py)
- Values: OPEN, CLOSED, PENDING.
- Usage: `position.status == PositionStatus.OPEN`.
- Mapping: {'OPEN': 0, 'CLOSED': 1, 'PENDING': 2}.

### SessionType (src/project_x_py/sessions/config.py)
- Values: RTH (Regular Trading Hours), ETH (Extended).
- Usage: In DataManagerConfig for session filtering.
- Mapping: {'RTH': 0, 'ETH': 1}.

### RiskStatus (from risk_manager)
- Values: VALID, WARNING, EXCEEDED.
- Usage: In RiskValidationResponse.status.
- Mapping: {'VALID': 0, 'WARNING': 1, 'EXCEEDED': 2}.

### Additional Enums
- OrderStatus (order_manager/tracking.py): PENDING=0, FILLED=1, CANCELLED=2, REJECTED=3, EXPIRED=4. Mapping: {'PENDING': 0, 'FILLED': 1, 'CANCELLED': 2, 'REJECTED': 3, 'EXPIRED': 4}. Usage: order.status in get_order response.
- FeedStatus (realtime/core.py): CONNECTED=0, DISCONNECTED=1, SUBSCRIBED=2. Usage: realtime_client.status for connection health.
- BarType (types/market_data.py): OHLCV=0, HL2=1. Usage: In get_bars response for data type.
- QuoteType (types/market_data.py): BID=0, ASK=1, LAST=2. Usage: In quote data for price type.
- CacheStrategy (types/config_types.py): MEMORY_ONLY=0, MMAP_OVERFLOW=1. Usage: In DataManagerConfig for data storage.

## 2. Events

Events are emitted via EventBus (src/project_x_py/event_bus.py). Subscribe with `await suite.on(EventType.TRADE_TICK, handler)` or `await manager.add_callback("trade_tick", handler)`.

- Subscription: Manager-level (realtime_data_manager/core.py line 644) or suite-level (trading_suite.py line 1221).
- Data: Dict with 'timestamp', 'type', details (e.g., {'instrument': 'MNQ', 'price': 21000}).
- Start Realtime: `await mnq.data.start_realtime_feed()` (core.py line 546).
- Event Ordering/Race Conditions: Events are emitted in API order (e.g., ORDER_FILLED before POSITION_UPDATE), but async handlers may race—use locks (asyncio.Lock) in handlers for state updates. No guaranteed global order across managers; use suite-level subscriptions for coordination. For partial fills, expect multiple ORDER_FILLED before full POSITION_UPDATE.

### Position Events (position_manager/tracking.py)
- POSITION_UPDATED: Position change. Subscribe: `@event_bus.on(POSITION_UPDATED)`. Data: {'instrument': 'MNQ', 'size': 1, 'unrealized_pnl': -5.0}.
- POSITION_OPENED: New position. Data: {'instrument': 'MNQ', 'size': 1, 'avg_price': 21000}.
- POSITION_CLOSED: Closed. Data: {'instrument': 'MNQ', 'pnl': 25.0}.
- POSITION_PNL_UPDATE: P&L update. Data: {'instrument': 'MNQ', 'unrealized_pnl': -5.0}.
- PORTFOLIO_REBALANCED: Portfolio adjusted. Data: {'instruments_affected': list[str], 'total_pnl_change': float}.

### Quote/Trade Events (realtime_data_manager/callbacks.py)
- QUOTE_UPDATE: Bid/ask. Data: {'instrument': 'MNQ', 'bid': 21000.25, 'ask': 21000.5}.
- TRADE_TICK: Trade. Data: {'instrument': 'MNQ', 'price': 21000.5, 'size': 100, 'side': 'buy'}.
  - Alias: "market_trade": TRADE_TICK.
- NEW_BAR: OHLCV bar. Data: {'instrument': 'MNQ', 'timeframe': '1min', 'open': 21000, 'high': 21005, 'low': 20995, 'close': 21002, 'volume': 500}.
- DATA_UPDATE: General update. Data: {'instrument': 'MNQ', 'type': 'bar', 'data': {...}}.
- FEED_CONNECTED: WebSocket connected. Data: {'hub': str ('user'|'market'), 'latency_ms': float}.
- FEED_DISCONNECTED: Disconnected. Data: {'reason': str, 'reconnect_attempt': int}.
- SUBSCRIPTION_UPDATE: Subscription status. Data: {'contract_ids': list[str], 'status': str ('success'|'failed')} .

### Order Events (risk_manager/managed_trade.py)
- ORDER_FILLED: Filled. Data: {'order_id': 123, 'fill_price': 21000, 'filled_size': 1}.
- ORDER_CANCELLED: Cancelled. Data: {'order_id': 123, 'reason': 'user_cancel'}.
- ORDER_REJECTED: Rejected. Data: {'order_id': 123, 'reason': 'insufficient_margin'}.
- ORDER_PARTIAL_FILL: Partial fill. Data: {'order_id': 123, 'fill_price': 21000, 'filled_size': 1, 'remaining_size': 2}.
- ORDER_MODIFIED: Modified. Data: {'order_id': 123, 'old_price': 21000, 'new_price': 21010, 'status': 'modified'}.

### Risk Events
- RISK_LIMIT_WARNING: Threshold hit. Data: {'type': 'daily_loss', 'current': -25, 'limit': -20}.
- RISK_VIOLATION: Violation (hard limit). Data: {'type': 'daily_loss', 'current': -25, 'limit': -20, 'action': 'auto_close'}.

Example Subscription:
```python
async def handler(event):
    print(f"Event: {event.type} - Data: {event.data}")

suite = await TradingSuite.create(["MNQ"])
await suite.on(EventType.QUOTE_UPDATE, handler)
await suite["MNQ"].data.start_realtime_feed()
await asyncio.sleep(60)
await suite["MNQ"].data.stop_realtime_feed()
await suite.disconnect()
```

## 3. Subscriptions & Realtime Updates

### Realtime Setup (realtime_data_manager/core.py)
- `start_realtime_feed() -> bool` (line 546): Starts WebSocket. Returns True if success.
  - Usage: `await mnq.data.start_realtime_feed()`.
- `stop_realtime_feed() -> None` (line 547): Stops.
- `add_callback(event: str or EventType, handler)` (line 553): Adds callback.
  - Usage: `await mnq.data.add_callback("trade_tick", handler)`.
- `subscribe_market_data(contract_ids: list[str]) -> bool` (core.py line 667): Subscribes to market data.
  - Usage: `await realtime_client.subscribe_market_data(["CON.F.US.MNQ.Z25"])`.
- `subscribe_user_updates() -> bool` (line 666): User events (orders/positions).
- `get_realtime_validation_status() -> dict` (line 559): Subscription status.
- Time Alignment: All timestamps in UTC (via pytz). DST handled by session_type (RTH/ETH); align local time with `instrument.timezone` (e.g., 'America/New_York'). Use `data.timestamp.dt.convert_time_zone('UTC')` in Polars for alignment.
- Supported Timeframes: "1sec", "5sec", "10sec", "15sec", "30sec", "1min", "5min", "15min", "30min", "1hr", "4hr", "1day", "1week", "1month" (for bars/subscriptions).

### Broker Communication (realtime/connection_management.py)
- WebSocket Hubs:
  - User Hub: "https://rtc.topstepx.com/hubs/user" (orders, positions).
  - Market Hub: "https://rtc.topstepx.com/hubs/market" (quotes, trades).
- REST Base: "https://gateway.projectx.com/api" (auth, positions, orders).
- Contract IDs: "CON.F.US.MNQ.Z25" (e.g., for MNQ Dec 2025).
- Side Values: 0 (buy), 1 (sell) — from OrderSide.
- Auth: JWT in URL query (line 145).
- Auth/Session Refresh: `await client.authenticate()` (initial JWT, POST /auth/login with {'username': str, 'apiKey': str}; response: {'jwt': str, 'expiresIn': int (~3600s), 'accountId': int}). Check `await client.is_authenticated()` (bool). For refresh: POST /auth/refresh (headers: {'Authorization': 'Bearer {jwt}'}); `await client.refresh_token()` if expiry < 300s (from `await client.get_token_info()`: {'is_valid': bool, 'expires_in_seconds': int}). WebSocket: Attach JWT as query (?access_token=JWT). Auto-refresh in TradingSuite (every 5min, resubscribes on expiry).
- SignalR/WebSocket Protocol: Hubs use SignalR. User Hub: SubscribeAccounts([]), SubscribeOrders([account_id]), SubscribePositions([account_id]), SubscribeTrades([account_id]); UnsubscribeOrders([account_id]), etc. Market Hub: SubscribeContractQuotes([contract_id]), SubscribeContractTrades([contract_id]), SubscribeContractMarketDepth([contract_id]); UnsubscribeContractQuotes([contract_id]). Payloads: Arrays like ["SubscribeOrders", [12345]]. Auto-resubscribe on reconnect (circuit breaker after 10 failures).

Example Realtime Flow:
1. `suite = await TradingSuite.create(["MNQ"])`.
2. `await realtime_client.subscribe_market_data(["CON.F.US.MNQ.Z25"])`.
3. `await mnq.data.start_realtime_feed()`.
4. Subscribe callbacks.
5. `await asyncio.sleep(60)`.
6. `await mnq.data.stop_realtime_feed()`.
7. `await suite.disconnect()`.

## 4. API Calls

### Orders (types/protocols.py, order_manager/core.py)
- `place_order(contract_id: str, side: int, size: int, order_type: str, account_id: int | None = None) -> OrderResponse` (line 260): Place order.
  - Example: `await client.place_order("CON.F.US.MNQ.Z25", OrderSide.BUY, 1, OrderType.MARKET, account_id=12089421)`.
- `place_market_order(contract_id: str, side: int, size: int, account_id: int | None = None)` (line 256): Market order.
- `place_limit_order(contract_id: str, side: int, size: int, limit_price: float, account_id: int | None = None)` (line 214).
- `place_stop_order(contract_id: str, side: int, size: int, stop_price: float, account_id: int | None = None)` (line 207).
- `close_position(contract_id: str, account_id: int | None = None)` (line 372): Close position.
  - Example: `await client.close_position("CON.F.US.MNQ.Z25", account_id=12089421)`.
- `reduce_position(contract_id: str, reduce_by: int, account_id: int | None = None)` (line 463): Reduce size.
- `cancel_order(order_id: int, account_id: int | None = None)` (line 305).
- `get_orders(account_id: int | None = None) -> list[Order]` (line 299): All orders.
- `get_order(order_id: int, account_id: int | None = None) -> Order` (line 290).
- Error Handling: Raises ProjectXOrderError (e.g., 'invalid_price', 'insufficient_margin') with .error_code, .message. ProjectXRateLimitError: {'retry_after': int (seconds), 'remaining': int}. Retry: Use @retry_on_network_error decorator (max_attempts=3, backoff=2x). For rejects: Check response.error (e.g., 'account_not_found' if invalid account_id). Rate limits: 120 orders/min, 100 API calls/min; SDK auto-throttles. Response format: {success: bool, errorCode: int, errorMessage: str, details: dict (e.g., {'invalid_field': 'price'})}.

### Positions (types/protocols.py)
- `get_position(contract_id: str, account_id: int | None = None) -> Position` (line 455): Single position. Fields: size, avg_price, unrealized_pnl, current_price.
  - Example: `position = client.get_position("CON.F.US.MNQ.Z25", account_id=12089421)`.
- `get_all_positions(account_id: int | None = None) -> list[Position]` (line 205): All positions.
- `refresh_positions(account_id: int | None = None) -> int` (line 458): Refresh.
- Flatten/Close Logic: `close_all_positions(account_id: int | None = None, emergency: bool = False)`: Closes all (flatten portfolio). If emergency=True, force market close ignoring limits. Partial close: `reduce_position(contract_id, reduce_by: int or percentage: float)`. Confirms with {'success': bool, 'closed_size': int, 'pnl': float}.

### Quotes & Ticks (types/protocols.py)
- `get_current_price(instrument: str) -> float`: Latest price.
  - Example: `price = client.get_current_price("MNQ")`.
- `get_current_quote(instrument: str) -> Quote`: Bid/ask.
  - Example: `quote = client.get_current_quote("MNQ")`.
- `get_ticks(instrument: str, count: int) -> list[Tick]`: Historical ticks.
  - Example: `ticks = client.get_ticks("MNQ", 10)`.

### Instruments (types/protocols.py)
- `get_instrument(instrument: str) -> Instrument` (line 453): Get instrument details.
  - Fields: id (contract_id like "CON.F.US.MNQ.Z25"), name, tick_size, min_quantity.
  - Example: `instrument = client.get_instrument("MNQ")`.

### Account (types/protocols.py)
- `get_account_info(account_id: int | None = None) -> Account` (line 162): Account info. Fields: id (int), name, balance (float), simulated (bool).
- `list_accounts() -> list[Account]` (line 162): All accounts.

## 5. Broker Communication Flow

1. **Auth**: `await client.authenticate()` (JWT token).
2. **Get Instrument**: `instrument = client.get_instrument("MNQ")`; contract_id = instrument.id.
3. **Place Order**: `await client.place_market_order(contract_id, OrderSide.BUY, 1)`.
4. **Monitor Positions**: `position = client.get_position(contract_id, account_id=12089421)`.
5. **Realtime Subscription**: `await realtime_client.subscribe_market_data([contract_id])`; `await mnq.data.start_realtime_feed()`.
6. **Events**: Subscribe to EventType.QUOTE_UPDATE for quotes, TRADE_TICK for trades.
7. **Close**: `await client.close_position(contract_id, account_id=12089421)`.

### Contract IDs
- Format: "CON.F.US.MNQ.Z25" (Futures, MNQ Dec 2025).
- Get: `instrument = client.get_instrument("MNQ")`; contract_id = instrument.id.

### Side & Order Types
- Side: 0 (buy), 1 (sell).
- Types: MARKET (immediate), LIMIT (price limit), STOP (stop price), STOP_LIMIT (stop + limit), BRACKET (entry + stop/target), OCO (one cancels other).

Example Full Trade:
```python
from project_x_py import ProjectX, OrderSide, OrderType

async def trade_example():
    async with ProjectX.from_env() as client:
        await client.authenticate()
        instrument = client.get_instrument("MNQ")
        contract_id = instrument.id
        # Place buy
        response = await client.place_limit_order(contract_id, OrderSide.BUY, 1, 21000.0)
        print(f"Order: {response}")
        # Get position
        position = client.get_position(contract_id)
        print(f"P&L: ${position.unrealized_pnl:.2f}")
        # Close
        await client.close_position(contract_id)
```

## 6. Realtime Updates

### Setup
- Create suite: `suite = await TradingSuite.create(["MNQ"], features=[Features.RISK_MANAGER])`.
- Subscribe market: `await suite.client.realtime_client.subscribe_market_data([contract_id])`.
- Start feed: `await suite["MNQ"].data.start_realtime_feed()`.
- Subscribe events: `await suite.on(EventType.QUOTE_UPDATE, handler)`.
- Handler example:
```python
async def handler(event):
    data = event.data
    if event.type == EventType.QUOTE_UPDATE:
        print(f"Bid: {data['bid']}, Ask: {data['ask']}")
    elif event.type == EventType.TRADE_TICK:
        print(f"Trade: ${data['price']} x {data['size']}")
```

### Closing Positions
- `await client.close_position(contract_id, account_id=12089421)` (market close).
- Params: method="market" or "limit" (if limit, add limit_price).
- For partial: `await client.reduce_position(contract_id, reduce_by=1, account_id=12089421)`.

## 7. Detailed Payloads

### Event Payloads (from EventBus.emit() usages)
All events have common fields: {'timestamp': datetime, 'type': EventType, 'data': dict}.
- NEW_BAR: data = {'instrument': str, 'timeframe': str, 'open': float, 'high': float, 'low': float, 'close': float, 'volume': int}.
- POSITION_CLOSED: data = {'instrument': str, 'pnl': float, 'exit_price': float, 'size_closed': int, 'reason': str}.
- ORDER_FILLED: data = {'order_id': int, 'fill_price': float, 'filled_size': int, 'remaining_size': int, 'timestamp': datetime}.
- ORDER_CANCELLED: data = {'order_id': int, 'reason': str, 'timestamp': datetime}.
- ORDER_REJECTED: data = {'order_id': int, 'reason': str, 'error_code': str, 'timestamp': datetime}.
- DATA_UPDATE: data = {'instrument': str, 'type': str ('bar'|'tick'), 'data': dict (OHLCV or price/size)}.
- QUOTE_UPDATE: data = {'instrument': str, 'bid': float, 'ask': float, 'bid_size': int, 'ask_size': int, 'timestamp': datetime}.
- TRADE_TICK: data = {'instrument': str, 'price': float, 'size': int, 'side': str ('buy'|'sell'), 'timestamp': datetime}.
- POSITION_UPDATE: data = {'instrument': str, 'size': int, 'avg_price': float, 'unrealized_pnl': float, 'current_price': float, 'market_value': float, 'position_value': float, 'max_drawdown': float}.
- POSITION_OPENED: data = {'instrument': str, 'size': int, 'avg_price': float, 'open_time': datetime}.
- POSITION_PNL_UPDATE: data = {'instrument': str, 'unrealized_pnl': float, 'realized_pnl': float, 'total_pnl': float}.
- RISK_LIMIT_WARNING: data = {'type': str ('daily_loss'|'max_risk'), 'current': float, 'limit': float, 'severity': str ('warning'|'critical')}.

### API Response Payloads
- OrderResponse (from place_order, etc.): {'success': bool, 'order_id': int, 'status': str ('pending'|'filled'|'rejected'), 'message': str, 'error': str (if failed), 'timestamp': datetime}.
- Position (from get_position): {'instrument': str, 'size': int, 'avg_price': float, 'unrealized_pnl': float, 'realized_pnl': float, 'current_price': float, 'market_value': float, 'position_value': float, 'max_drawdown': float, 'status': PositionStatus, 'open_time': datetime, 'last_update': datetime}.
- Quote (from get_current_quote): {'instrument': str, 'bid': float, 'ask': float, 'bid_size': int, 'ask_size': int, 'spread': float, 'mid_price': float, 'last': float, 'timestamp': datetime}.
- Tick (from get_ticks): {'instrument': str, 'price': float, 'size': int, 'side': str ('buy'|'sell'), 'timestamp': datetime}.
- Instrument (from get_instrument): {'id': str ('CON.F.US.MNQ.Z25'), 'symbol': str ('MNQ'), 'name': str, 'exchange': str, 'currency': str, 'tick_size': float, 'min_quantity': int, 'contract_size': int, 'margin_requirement': float}.
- Account (from get_account_info): {'id': int (e.g., 12089421), 'name': str, 'balance': float, 'available_balance': float, 'margin_used': float, 'buying_power': float, 'simulated': bool, 'can_trade': bool}.
- subscribe_market_data response: {'success': bool, 'subscribed_contracts': list[str], 'error': str (if failed)}.

### Subscription Payloads
- add_callback: No return, but handler receives Event with {'type': EventType, 'data': dict (as above), 'timestamp': datetime}.
- subscribe_market_data: Returns bool (success), or raises ProjectXSubscriptionError with {'reason': str, 'contract_ids': list[str]}.

## 8. Diagnostics & Validation

### Validation Methods
- `get_stats() -> dict` (all managers): {'health_score': int (0-100), 'error_count': int, 'api_calls': int, 'success_rate': float, 'uptime': float, 'memory_usage_mb': float}.
  - Example: `stats = await suite.get_stats(); print(f"Health: {stats['health_score']}/100")`.
- `get_health_score() -> int` (0-100): Overall health.
  - Example: `score = await suite.get_health_score(); if score < 80: print("Degraded")`.
- `validate_subscriptions() -> dict`: {'active': list[str], 'failed': list[str], 'status': bool}.
  - Example: `valid = await realtime_client.validate_subscriptions(); print(valid)`.
- `get_realtime_validation_status() -> dict`: {'connected': bool, 'subscribed_contracts': int, 'latency_ms': float, 'last_heartbeat': datetime}.
  - Example: `status = await realtime_client.get_realtime_validation_status(); if not status['connected']: print("Feed down")`.
- Error Logs: Use `configure_sdk_logging(level='DEBUG')` for full traces (logs to console/file). Errors: ProjectXError with .code, .message, .details (dict, e.g., {'retry_after': 60}).
- Validation Example:
```python
async def validate_setup():
    suite = await TradingSuite.create(["MNQ"])
    # Check auth
    if not await suite.client.is_authenticated():
        await suite.client.authenticate()
    # Validate subscriptions
    status = await suite.client.realtime_client.validate_subscriptions()
    if not status['status']:
        print(f"Subscription issues: {status['failed']}")
    # Check positions
    positions = await suite.positions.get_all_positions()
    print(f"Active positions: {len(positions)}")
    # Health check
    health = await suite.get_health_score()
    print(f"System health: {health}/100")
    # Enum check example
    order = await suite.orders.get_order(123) if positions else None
    if order and order.status == 1:  # FILLED
        print("Order filled")
    # Event ordering test (with lock)
    lock = asyncio.Lock()
    async def safe_handler(event):
        async with lock:
            # Update state safely
            state[event.type] = event.data
    await suite.on(EventType.ORDER_FILLED, safe_handler)
    await suite.disconnect()

asyncio.run(validate_setup())
```
- Race Condition Check: In handlers, use `lock = asyncio.Lock(); async with lock: update_state(event.data)` to prevent concurrent modifications.

## 9. Raw API Endpoints

### REST Endpoints (from client/http.py, api routes)
- Auth: POST /auth/login (payload: {'username': str, 'password': str, 'apiKey': str (opt)}; response: {'jwt': str, 'expiresIn': int (~3600s), 'accountId': int, 'accountName': str, 'canTrade': bool, 'simulated': bool}).
- Refresh: POST /auth/refresh (headers: {'Authorization': 'Bearer {jwt}'}; response same as login).
- Orders: POST /Order/place (payload: {'accountId': int, 'contractId': str, 'type': int (OrderType, e.g., 1=LIMIT), 'side': int (0/1), 'size': int, 'limitPrice': float (opt), 'stopPrice': float (opt), 'trailPrice': float (opt for TRAILING_STOP), 'linkedOrderId': int (opt for OCO), 'customTag': str}; response: {'success': bool, 'orderId': int, 'errorCode': int, 'errorMessage': str}).
- Cancel: POST /Order/cancel (payload: {'accountId': int, 'orderId': int}; response: {'success': bool, 'errorCode': int, 'errorMessage': str}).
- Modify: POST /Order/modify (payload: {'accountId': int, 'orderId': int, 'limitPrice': float (opt), 'stopPrice': float (opt), 'size': int (opt)}; response: {'success': bool, 'errorCode': int, 'errorMessage': str}).
- Search Orders: POST /Order/searchOpen (payload: {'accountId': int, 'contractId': str (opt), 'side': int (opt)}; response: {'success': bool, 'orders': list[dict {'orderId': int, 'status': int (OrderStatus), 'size': int, 'filledSize': int, 'limitPrice': float, 'timestamp': str}], 'totalCount': int, 'errorCode': int (opt)}).
- Positions: POST /Position/searchOpen (payload: {'accountId': int}; response: {'success': bool, 'positions': list[dict {'positionId': int, 'contractId': str, 'size': int, 'averagePrice': float, 'unrealizedPnl': float}], 'errorCode': int (opt)}).
- Quotes: GET /quotes?contractIds={comma_sep_str} (response: {'success': bool, 'quotes': list[dict {'contractId': str, 'bid': float, 'ask': float, 'last': float, 'bidSize': int, 'askSize': int}], 'errorCode': int (opt)}).
- Instruments: GET /instruments/search?query={str}&limit={int} (response: {'success': bool, 'instruments': list[dict {'id': str, 'symbol': str, 'name': str, 'tickSize': float, 'minQuantity': int}], 'errorCode': int (opt)}).
- Accounts: GET /accounts (headers: Auth; response: {'success': bool, 'accounts': list[dict {'id': int, 'name': str, 'balance': float, 'simulated': bool}], 'errorCode': int (opt)}).

### WebSocket/SignalR Messages
- User Hub (/hubs/user): SubscribeAccounts([]), SubscribeOrders([account_id]), SubscribePositions([account_id]), SubscribeTrades([account_id]); UnsubscribeOrders([account_id]), etc. Payload: arrays like ["SubscribeOrders", [12345]]. Events: GatewayUserAccount (account update), GatewayUserPosition (position), GatewayUserOrder (order), GatewayUserTrade (trade).
- Market Hub (/hubs/market): SubscribeContractQuotes([contract_id]), SubscribeContractTrades([contract_id]), SubscribeContractMarketDepth([contract_id]); UnsubscribeContractQuotes([contract_id]). Payload: ["SubscribeContractQuotes", ["CON.F.US.MNQ.Z25"]]. Events: GatewayQuote (quote), GatewayTrade (trade), GatewayDepth (depth).

This covers all broker interaction. For full examples, see examples/ directory.

### Progress Log

Phase 1: Foundation - Implemented daemon skeleton in daemon/risk_daemon.py. Supports CLI: start (with passcode, dry-run logging), stop, status, tail, dry-run, validate. Loads config from config/risk_manager_config.json (created basic). Attaches to EventBus for ORDER_FILLED, POSITION_UPDATE, QUOTE_UPDATE (logs events in dry-run). Confirmed: start/stop works, config loads, subscriptions start (no errors). Logs to live.log (rotated) and audit.ndjson. Date: 2025-09-26. Changes: Skeleton CLI and event loop. Results: Tested dry-run start - events logged without enforcement.

Phase 2: First Rule (Max Contracts) - Created rules/max_contracts.py with check(event, config) function (checks POSITION_UPDATE size > max_contracts, returns BREACH with flatten action if exceeded). Updated config.json to enable max_contracts (max=4, enforcement=flatten). Updated daemon/risk_daemon.py to dynamically load enabled rules via importlib, evaluate on events (ORDER_FILLED/POSITION_UPDATE/QUOTE_UPDATE), log breaches (plain English in audit), and enforce if not dry_run (close_position on flatten). Tested in dry-run: Manual MNQ order >4 triggers BREACH log without action. Ready for live mode test with small trades. Date: 2025-09-26. Changes: Rule module, config enable, daemon rule engine. Results: Dry-run detects breach, logs correctly; no enforcement (dry-run=true).
