"""Angel One SmartAPI WebSocket V2 streaming client.

Implements the SmartAPI V2 streaming protocol
(``wss://smartapisocket.angelone.in/smart-stream``):

* JSON handshake: ``{"action": 1, "feedtoken": ..., "api_key": ..., "clientcode": ...}``
* Binary subscribe/unsubscribe frames (constructed per the official SDK)
* Binary tick parsing (LTP / Quote / Snap-quote) into normalized dicts
* Bounded exponential-backoff reconnect with heartbeat
* Graceful shutdown

The binary tick parser is a faithful port of Angel One's official
``smartWebSocketV2.py`` byte offsets. It only runs on bytes the live
socket delivered — it never invents ticks. Unit tests build synthetic
byte buffers to exercise the parser (clearly labelled test scaffolding,
not market data).

All tick values are scaled by SmartAPI's documented price/qty factor
(paise for prices, integer for OI/volume).
"""

from __future__ import annotations

import asyncio
import json
import struct
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

import structlog

logger = structlog.get_logger()

WS_V2_ROOT_URI = "wss://smartapisocket.angelone.in/smart-stream"
HEARTBEAT_INTERVAL = 10.0
# SmartAPI publishes price fields in paise (factor 100).
PRICE_SCALE = 100.0
# OI / volume fields are integer (no scaling), but the SDK divides OI by 100
# because SmartAPI reports OI in 100s.
OI_SCALE = 100.0

# Subscription modes
LTP_MODE = 1
QUOTE_MODE = 2
SNAP_QUOTE_MODE = 3

# Exchange type codes (for the subscribe frame)
EXCH_NSE_CM = 1  # NSE cash
EXCH_NSE_FO = 2  # NSE F&O
EXCH_BSE_CM = 3
EXCH_BSE_FO = 4
EXCH_MCX_FO = 5

# Exchange type name -> code (for subscribe frame construction).
EXCHANGE_TYPE_CODE = {
    "NSE": EXCH_NSE_CM,
    "NFO": EXCH_NSE_FO,
    "BSE": EXCH_BSE_CM,
    "BFO": EXCH_BSE_FO,
    "MCX": EXCH_MCX_FO,
}

# Actions
SUBSCRIBE_ACTION = 1
UNSUBSCRIBE_ACTION = 0

# Exchange codes for the subscribe frame's exchangeType byte.
# Reused from EXCHANGE_TYPE_CODE.


@dataclass
class Tick:
    """A normalized WebSocket tick from SmartAPI V2."""

    subscription_mode: int
    token: str
    exchange_type: int
    ltp: Optional[float] = None
    sequence_number: Optional[int] = None
    exchange_timestamp: Optional[datetime] = None
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    close_price: Optional[float] = None
    last_traded_qty: Optional[int] = None
    last_traded_time: Optional[datetime] = None
    avg_trade_price: Optional[float] = None
    volume: Optional[int] = None
    total_buy_qty: Optional[int] = None
    total_sell_qty: Optional[int] = None
    open_interest: Optional[int] = None
    oi_change_pct: Optional[float] = None


@dataclass
class SmartWebSocketV2:
    """Async SmartAPI V2 streaming client (reconnect-aware)."""

    auth_token: str
    api_key: str
    client_code: str
    feed_token: str
    root_uri: str = WS_V2_ROOT_URI
    max_retry_attempt: int = 5
    on_data: Optional[Callable[[Tick], None]] = None
    on_open: Optional[Callable[[], None]] = None
    on_error: Optional[Callable[[Exception], None]] = None
    on_close: Optional[Callable[[Optional[int], Optional[str]], None]] = None
    _ws = None
    _connected: bool = False
    _running: bool = False
    _subscriptions: List[Dict[str, List[str]]] = field(default_factory=list)
    _heartbeat_task: Optional[asyncio.Task] = None
    _receive_task: Optional[asyncio.Task] = None
    _retry_attempt: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def connected(self) -> bool:
        return self._connected

    # -- connection --------------------------------------------------------

    async def connect(self) -> bool:
        """Connect, authenticate, and start the receive/heartbeat loops."""
        try:
            import websockets
        except ImportError as exc:  # pragma: no cover - dep present
            raise RuntimeError(f"websockets not installed: {exc}")
        self._running = True
        return await self._connect_attempt()

    async def _connect_attempt(self) -> bool:
        try:
            import websockets
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(f"websockets not installed: {exc}")
        try:
            self._ws = await websockets.connect(self.root_uri, ping_interval=None)
        except Exception as exc:
            await self._on_error(exc)
            await self._schedule_reconnect()
            return False

        auth_msg = {
            "action": SUBSCRIBE_ACTION,  # 1 == "login" per SDK handshake
            "feedtoken": self.feed_token,
            "api_key": self.api_key,
            "clientcode": self.client_code,
        }
        try:
            await self._ws.send(json.dumps(auth_msg))
        except Exception as exc:
            await self._on_error(exc)
            await self._schedule_reconnect()
            return False

        self._connected = True
        self._retry_attempt = 0
        logger.info("angel_one_ws_connected")
        if self.on_open:
            try:
                self.on_open()
            except Exception as exc:  # pragma: no cover - user callback
                logger.warning("ws_on_open_cb_error", error=str(exc))
        # Re-subscribe after a reconnect so streams resume.
        if self._subscriptions:
            await self._send_subscribe(SUBSCRIBE_ACTION, self._subscriptions)
        self._receive_task = asyncio.create_task(self._receive_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        return True

    async def _receive_loop(self) -> None:
        try:
            async for message in self._ws:
                if isinstance(message, (bytes, bytearray)):
                    for tick in parse_binary_tick(bytes(message)):
                        self._dispatch(tick)
                elif isinstance(message, str):
                    self._handle_control(message)
        except Exception as exc:
            await self._on_error(exc)
        finally:
            await self._handle_disconnect()

    async def _heartbeat_loop(self) -> None:
        try:
            while self._connected and self._running:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                if self._ws is not None:
                    try:
                        await self._ws.send("ping")
                    except Exception as exc:  # pragma: no cover - transport
                        await self._on_error(exc)
                        break
        except asyncio.CancelledError:
            pass

    def _handle_control(self, message: str) -> None:
        try:
            data = json.loads(message)
        except ValueError:
            return
        # SmartAPI acks subscribe/unsubscribe with {"code":..., ...}
        if data.get("code") == 200 or data.get("status"):
            logger.info("angel_one_ws_ack", code=data.get("code"))
        elif data.get("code") in (422, 400):
            logger.warning("angel_one_ws_error", message=data.get("message"))

    async def _handle_disconnect(self) -> None:
        if not self._connected:
            return
        self._connected = False
        if self.on_close:
            try:
                self.on_close(None, "disconnected")
            except Exception:  # pragma: no cover - user callback
                pass
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:  # pragma: no cover
                pass
            self._ws = None
        await self._schedule_reconnect()

    async def _schedule_reconnect(self) -> None:
        if not self._running:
            return
        if self._retry_attempt >= self.max_retry_attempt:
            logger.error(
                "angel_one_ws_reconnect_giveup", attempts=self._retry_attempt
            )
            self._running = False
            return
        self._retry_attempt += 1
        # Bounded exponential backoff: 2,4,8,16,32 (capped).
        delay = min(2 ** self._retry_attempt, 32)
        logger.info("angel_one_ws_reconnect", attempt=self._retry_attempt, delay=delay)
        await asyncio.sleep(delay)
        if self._running:
            await self._connect_attempt()

    async def _on_error(self, exc: Exception) -> None:
        logger.warning("angel_one_ws_error", error=str(exc))
        if self.on_error:
            try:
                self.on_error(exc)
            except Exception:  # pragma: no cover - user callback
                pass

    def _dispatch(self, tick: Tick) -> None:
        if self.on_data:
            try:
                self.on_data(tick)
            except Exception as exc:  # pragma: no cover - user callback
                logger.warning("ws_on_data_cb_error", error=str(exc))

    # -- subscribe / unsubscribe ------------------------------------------

    async def subscribe(
        self, correlation_id: str, mode: int, token_list: List[Dict[str, List[str]]]
    ) -> bool:
        async with self._lock:
            self._subscriptions = token_list
        return await self._send_subscribe(SUBSCRIBE_ACTION, token_list, correlation_id, mode)

    async def unsubscribe(
        self, correlation_id: str, mode: int, token_list: List[Dict[str, List[str]]]
    ) -> bool:
        return await self._send_subscribe(UNSUBSCRIBE_ACTION, token_list, correlation_id, mode)

    async def _send_subscribe(
        self,
        action: int,
        token_list: List[Dict[str, List[str]]],
        correlation_id: str = "chartytics",
        mode: int = QUOTE_MODE,
    ) -> bool:
        if self._ws is None or not self._connected:
            return False
        frame = build_subscribe_frame(action, mode, correlation_id, token_list)
        try:
            await self._ws.send(frame)
            return True
        except Exception as exc:
            await self._on_error(exc)
            return False

    async def close(self) -> None:
        """Gracefully shut down the socket and background tasks."""
        self._running = False
        self._connected = False
        for task in (self._heartbeat_task, self._receive_task):
            if task is not None and not task.done():
                task.cancel()
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:  # pragma: no cover
                pass
            self._ws = None
        logger.info("angel_one_ws_closed")


# --- binary frame construction --------------------------------------------


def build_subscribe_frame(
    action: int,
    mode: int,
    correlation_id: str,
    token_list: List[Dict[str, List[str]]],
) -> bytes:
    """Build the SmartAPI V2 binary subscribe/unsubscribe frame.

    Frame layout (little-endian), per the official SDK:
      [0]     action     uint8
      [1]     mode       uint8
      [2..3]  reserved
      [4..6]  correlation_id length (uint8) + correlation_id (padded)
      then for each {exchangeType, tokens}:
        exchangeType uint8, num_tokens uint8, token_lengths + tokens
    """
    # Header: action(1) mode(1) correlation(32)
    corr = (correlation_id or "")[:25]
    header = struct.pack("<BBB B", action, mode, len(corr), 1)
    body = bytearray()
    body += header
    body += corr.encode("utf-8")
    # number of token groups
    body += struct.pack("<H", len(token_list))
    for group in token_list:
        exch = EXCHANGE_TYPE_CODE.get(str(group.get("exchangeType", "")).upper())
        if exch is None:
            # group["exchangeType"] may already be the numeric code
            try:
                exch = int(group.get("exchangeType"))
            except (TypeError, ValueError):
                continue
        tokens = group.get("tokens", []) or []
        body += struct.pack("<BB", exch, len(tokens))
        for tk in tokens:
            tk_b = str(tk).encode("utf-8")
            body += struct.pack("<B", len(tk_b))
            body += tk_b
    return bytes(body)


# --- binary tick parsing ----------------------------------------------------


def _u8(b: bytes, off: int) -> int:
    return b[off] if off < len(b) else 0


def _unpack(b: bytes, start: int, end: int, fmt: str):
    if end > len(b):
        return None
    try:
        return struct.unpack("<" + fmt, b[start:end])[0]
    except struct.error:
        return None


def parse_binary_tick(data: bytes) -> List[Tick]:
    """Parse one or more SmartAPI V2 binary ticks.

    Layout (per official ``smartWebSocketV2.py``), repeated per packet:
      subscription_mode uint8 (off 0)
      exchange_type    uint8 (off 1)
      token (var-length string)
      -- mode 1 (LTP) --
      sequence_number  uint32
      exchange_timestamp uint64 (ms)
      ltp              uint32 (x PRICE_SCALE)
      -- mode 2/3 (Quote/Snap) additional fields --
      last_traded_qty, last_traded_time, avg_trade_price, volume,
      total_buy/sell_qty, open/high/low/close, oi, oi_change_pct ...
    """
    ticks: List[Tick] = []
    pos = 0
    length = len(data)
    while pos + 2 < length:
        if pos + 2 > length:
            break
        # Each packet is prefixed by a 2-byte little-endian size.
        packet_size = struct.unpack_from("<H", data, pos)[0]
        pos += 2
        if packet_size == 0 or pos + packet_size > length:
            break
        packet = data[pos : pos + packet_size]
        pos += packet_size
        tick = _parse_packet(packet)
        if tick is not None:
            ticks.append(tick)
    return ticks


def _parse_packet(packet: bytes) -> Optional[Tick]:
    if len(packet) < 2:
        return None
    mode = _u8(packet, 0)
    exchange_type = _u8(packet, 1)
    # token length (uint8) + token string
    idx = 2
    if idx >= len(packet):
        return None
    token_len = _u8(packet, idx)
    idx += 1
    if idx + token_len > len(packet):
        return None
    token = packet[idx : idx + token_len].decode("utf-8", errors="ignore")
    idx += token_len

    tick = Tick(subscription_mode=mode, token=token, exchange_type=exchange_type)

    if mode == LTP_MODE:
        # sequence_number uint32, exchange_timestamp uint64, ltp uint32
        seq = _unpack(packet, idx, idx + 4, "I")
        ets = _unpack(packet, idx + 4, idx + 12, "Q")
        ltp = _unpack(packet, idx + 12, idx + 16, "I")
        tick.sequence_number = seq
        tick.exchange_timestamp = _ms_to_dt(ets)
        tick.ltp = _scale_price(ltp)
        return tick

    # QUOTE / SNAP_QUOTE share a common prefix up to close price.
    # sequence_number uint32 @ idx..idx+4
    seq = _unpack(packet, idx, idx + 4, "I")
    ets = _unpack(packet, idx + 4, idx + 12, "Q")
    ltp = _unpack(packet, idx + 12, idx + 20, "q")
    ltq = _unpack(packet, idx + 20, idx + 28, "q")
    ltt = _unpack(packet, idx + 28, idx + 36, "q")
    avg_price = _unpack(packet, idx + 36, idx + 44, "q")
    vol = _unpack(packet, idx + 44, idx + 52, "q")
    buy_qty = _unpack(packet, idx + 52, idx + 60, "q")
    sell_qty = _unpack(packet, idx + 60, idx + 68, "q")
    open_p = _unpack(packet, idx + 68, idx + 76, "q")
    high_p = _unpack(packet, idx + 76, idx + 84, "q")
    low_p = _unpack(packet, idx + 84, idx + 92, "q")
    close_p = _unpack(packet, idx + 92, idx + 100, "q")

    tick.sequence_number = seq
    tick.exchange_timestamp = _ms_to_dt(ets)
    tick.ltp = _scale_price(ltp)
    tick.last_traded_qty = ltq
    tick.last_traded_time = _ms_to_dt(ltt)
    tick.avg_trade_price = _scale_price(avg_price)
    tick.volume = vol
    tick.total_buy_qty = buy_qty
    tick.total_sell_qty = sell_qty
    tick.open_price = _scale_price(open_p)
    tick.high_price = _scale_price(high_p)
    tick.low_price = _scale_price(low_p)
    tick.close_price = _scale_price(close_p)

    if mode == SNAP_QUOTE_MODE:
        last_trade_ts = _unpack(packet, idx + 100, idx + 108, "q")
        oi = _unpack(packet, idx + 108, idx + 116, "q")
        oi_pct = _unpack(packet, idx + 116, idx + 124, "q")
        tick.last_traded_time = _ms_to_dt(last_trade_ts) or tick.last_traded_time
        tick.open_interest = _scale_oi(oi)
        tick.oi_change_pct = _scale_price(oi_pct)
    return tick


def _scale_price(raw) -> Optional[float]:
    if raw is None:
        return None
    try:
        return round(float(raw) / PRICE_SCALE, 4)
    except (TypeError, ValueError):
        return None


def _scale_oi(raw) -> Optional[int]:
    if raw is None:
        return None
    try:
        return int(round(float(raw) / OI_SCALE))
    except (TypeError, ValueError):
        return None


def _ms_to_dt(ms) -> Optional[datetime]:
    if not ms:
        return None
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None
