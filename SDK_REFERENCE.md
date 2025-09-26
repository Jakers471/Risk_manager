# ProjectX SDK Reference - Enums, Events, API Calls

## 1. Enums

### EventType (from event_bus.py)
- Class: `class EventType(Enum):`
- Values:
  - `NEW_BAR`: New OHLCV bar formed (e.g., 1min close).
  - `POSITION_CLOSED`: Position fully closed.
  - `ORDER_FILLED`: Order executed/filled.
  - `ORDER_CANCELLED`: Order cancelled.
  - `ORDER_REJECTED`: Order rejected by broker.
  - `DATA_UPDATE`: General data update (e.g., bar data changed).
  - `QUOTE_UPDATE`: Bid/ask quote update.
  - `TRADE_TICK`: Individual trade tick (price/size).
  - `POSITION_UPDATE`: Position changed (size/P&L).
  - `POSITION_OPENED`: New position opened.
  - `POSITION_PNL_UPDATE`: P&L updated for position.
  - `RISK_LIMIT_WARNING`: Risk threshold hit (e.g., loss > limit).
- Import: `from project_x_py import EventType`
- Usage: Subscribe with `await suite.on(EventType.TRADE_TICK, handler)`.

### OrderSide (from types/trading.py)
- Class: `class OrderSide(IntEnum):`
- Values: `BUY = 0`, `SELL = 1`.
- Usage: `side=OrderSide.BUY` in `place_order()`.

### OrderType (from types/trading.py)
- Class: `class OrderType(Enum):`
- Values: `MARKET`, `LIMIT`, `STOP`, `STOP_LIMIT`, `BRACKET`, `OCO`.
- Usage: `order_type=OrderType.LIMIT` in `place_order()`.

### SessionType (from sessions/config.py)
- Class: `class SessionType(Enum):`
- Values: `RTH` (Regular Trading Hours), `ETH` (Extended).
- Usage: In DataManagerConfig for filtering.

### RiskStatus (from risk_manager)
- Values: `VALID`, `WARNING`, `EXCEEDED`.
- Usage: In `RiskValidationResponse.status`.

### PositionStatus (from types/protocols.py)
- Values: `OPEN`, `CLOSED`, `PENDING`.
- Usage: `position.status == PositionStatus.OPEN`.

## 2. Events

Events are emitted via EventBus. Data is dict with timestamp, type, details (e.g., {'instrument': 'MNQ', 'price': 21000}).

### Position-Related Events
- `POSITION_UPDATED`: Position change (size, P&L). Data: {'instrument': 'MNQ', 'size': 1, 'unrealized_pnl': -5.0, 'current_price': 21000}.
  - Usage: `@event_bus.on(POSITION_UPDATED)` in position_manager/tracking.py.
- `POSITION_OPENED`: New position. Data: {'instrument': 'MNQ', 'size': 1, 'avg_price': 21000}.
- `POSITION_CLOSED`: Position closed. Data: {'instrument': 'MNQ', 'pnl': 25.0, 'exit_price': 21025}.
- `POSITION_PNL_UPDATE`: P&L recalculated. Data: {'instrument': 'MNQ', 'unrealized_pnl': -5.0}.

### Quote/Trade Events (Realtime)
- `QUOTE_UPDATE`: Bid/ask update. Data: {'instrument': 'MNQ', 'bid': 21000.25, 'ask': 21000.5, 'bid_size': 100, 'ask_size': 50}.
- `TRADE_TICK`: Trade tick. Data: {'instrument': 'MNQ', 'price': 21000.5, 'size': 100, 'side': 'buy'}.
  - Alias: "market_trade": TRADE_TICK.
- `NEW_BAR`: New OHLCV bar. Data: {'instrument': 'MNQ', 'timeframe': '1min', 'open': 21000, 'high': 21005, 'low': 20995, 'close': 21002, 'volume': 500}.
- `DATA_UPDATE`: General data change. Data: {'instrument': 'MNQ', 'type': 'bar', 'data': {...}}.

### Order Events
- `ORDER_FILLED`: Order filled. Data: {'order_id': 123, 'fill_price': 21000, 'filled_size': 1}.
- `ORDER_CANCELLED`: Order cancelled. Data: {'order_id': 123, 'reason': 'user_cancel'}.
- `ORDER_REJECTED`: Order rejected. Data: {'order_id': 123, 'reason': 'insufficient_margin'}.

### Risk Events
- `RISK_LIMIT_WARNING`: Threshold hit. Data: {'type': 'daily_loss', 'current': -25, 'limit': -20}.

### Subscription
- Suite-level: `await suite.on(EventType.TRADE_TICK, async def handler(event): print(event.data))`.
- Manager-level: `await mnq.data.add_callback("trade_tick", handler)`.
- Start feed: `await mnq.data.start_realtime_feed()`.
- Stop: `await mnq.data.stop_realtime_feed()`.

## 3. API Calls

### Position API (types/protocols.py)
- `get_position(contract_id: str, account_id: int | None = None) -> Position` (line 455): Single position. Fields: size, avg_price, unrealized_pnl, current_price.
  - Usage: `position = client.get_position("CON.F.US.MNQ.Z25", account_id=12078599)`.
- `get_all_positions(account_id: int | None = None) -> list[Position]` (line 205): All positions.
  - Usage: `positions = client.get_all_positions(account_id=12078599)`.
- `close_position(contract_id: str, account_id: int | None = None)` (line 372): Close.
  - Usage: `await client.close_position("CON.F.US.MNQ.Z25", account_id=12078599)`.
- `reduce_position(contract_id: str, reduce_by: int, account_id: int | None = None)` (line 463): Reduce size.
- `refresh_positions(account_id: int | None = None) -> int`: Refresh count.

### Quote/Tick API (types/protocols.py, realtime)
- `get_current_price(instrument: str) -> float`: Latest price.
  - Usage: `price = client.get_current_price("MNQ")`.
- `get_current_quote(instrument: str) -> Quote`: Bid/ask.
  - Usage: `quote = client.get_current_quote("MNQ")`.
- `get_ticks(instrument: str, count: int) -> list[Tick]`: Historical ticks.
  - Usage: `ticks = client.get_ticks("MNQ", 10)`.

### Realtime API (realtime_data_manager/core.py)
- `start_realtime_feed() -> bool` (line 546): Starts WebSocket.
  - Usage: `await mnq.data.start_realtime_feed()`.
- `stop_realtime_feed() -> None` (line 547): Stops.
- `add_callback(event: str or EventType, handler)` (line 553): Adds callback.
  - Usage: `await mnq.data.add_callback("trade_tick", handler)`.
- `subscribe_market_data(contract_ids: list[str]) -> bool` (line 667): Subscribes to market.
  - Usage: `await realtime_client.subscribe_market_data(["CON.F.US.MNQ.Z25"])` (realtime/core.py).
- `get_realtime_validation_status() -> dict` (line 559): Status.
  - Usage: `status = mnq.data.get_realtime_validation_status()`.

## 4. Realtime Flow
1. Create suite: `suite = await TradingSuite.create(["MNQ"])`.
2. Start feed: `await mnq.data.start_realtime_feed()`.
3. Subscribe: `await suite.on(EventType.QUOTE_UPDATE, handler)`.
4. Handler: `async def handler(event): data = event.data; print(data['bid'], data['ask'])`.
5. Stop: `await mnq.data.stop_realtime_feed()`.

## 5. Examples

### Subscribe to Trade Ticks
```python
from project_x_py import TradingSuite, EventType

async def on_trade_tick(event):
    data = event.data
    print(f"Trade: {data['instrument']} at ${data['price']}, size {data['size']}")

suite = await TradingSuite.create(["MNQ"])
await suite.on(EventType.TRADE_TICK, on_trade_tick)
await suite["MNQ"].data.start_realtime_feed()
await asyncio.sleep(60)
await suite["MNQ"].data.stop_realtime_feed()
await suite.disconnect()
```

### Get Position & P&L
```python
position = client.get_position("CON.F.US.MNQ.Z25", account_id=12078599)
if position:
    print(f"Size: {position.size}, Unrealized P&L: ${position.unrealized_pnl:.2f}")
```

### Full Realtime Monitoring
See examples/04_realtime_data.py for complete setup.
