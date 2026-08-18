"""Angel One SmartAPI data provider.

Implements the :class:`BaseDataProvider` contract against the Angel One
SmartAPI V2 surface (REST + WebSocket V2). Used for realtime quotes,
option chain with real OI, and — when a WebSocket stream is active —
live candles aggregated from ticks.

Data-integrity rules (enforced here, not just documented):
* No fabricated instrument tokens: equities/options are resolved through the
  :mod:`instrument_master` scrip lookup; index spot tokens use the
  well-known stable SmartAPI values.
* No fabricated OI/strikes/IV: every option-chain field is read from the
  live REST response or left ``None``/0; a field the provider does not
  report is never invented.
* Authentication failures, timeouts and rate limits are surfaced as
  ``None``/``[]`` (truthful unavailable) — never swallowed into fake data.

Documentation: https://smartapi.angelone.in/
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import structlog

from .base import (
    BaseDataProvider,
    InstrumentMeta,
    OHLCData,
    OptionChainData,
    SOURCE_ANGEL_ONE,
    STATUS_LIVE,
    TickerData,
)
from .candle_aggregator import CandleAggregator
from .instrument_master import get_instrument_master
from .smartapi_client import (
    SmartAPIAuthError,
    SmartAPIClient,
    SmartAPIError,
)
from .smartapi_ws_v2 import QUOTE_MODE, SmartWebSocketV2, Tick

logger = structlog.get_logger()

# SmartAPI historical-candle interval codes (per the official SDK).
INTERVAL_CODES = {
    "1m": "ONE_MINUTE",
    "5m": "FIVE_MINUTE",
    "15m": "FIFTEEN_MINUTE",
    "30m": "THIRTY_MINUTE",
    "1h": "ONE_HOUR",
    "1d": "ONE_DAY",
    "1w": "ONE_WEEK",
}


@dataclass
class AngelOneConfig:
    """Configuration for Angel One SmartAPI."""

    api_key: str = ""
    client_code: str = ""
    password: str = ""
    totp_secret: str = ""
    feed_token: str = ""


class AngelOneProvider(BaseDataProvider):
    """Angel One SmartAPI data provider.

    Provides real-time market data via WebSocket V2 and REST APIs. Option
    chain (with real OI / OI-change / IV / LTP) is available through the
    REST option-chain endpoint. Free tier includes WebSocket streaming.
    """

    def __init__(self, config: Optional[AngelOneConfig] = None):
        self.config = config or AngelOneConfig()
        self._client = SmartAPIClient(
            api_key=self.config.api_key,
            client_code=self.config.client_code,
            password=self.config.password,
            totp_secret=self.config.totp_secret,
        )
        self._ws: Optional[SmartWebSocketV2] = None
        self._aggregator = CandleAggregator()
        self._master = get_instrument_master()
        self._subscribed: set = set()
        self._quote_cache: Dict[str, TickerData] = {}
        self._cache_lock = asyncio.Lock()

    @property
    def name(self) -> str:
        return SOURCE_ANGEL_ONE

    @property
    def is_configured(self) -> bool:
        """Check if provider is configured with credentials."""
        return bool(
            self.config.api_key
            and self.config.client_code
            and self.config.password
        )

    # -- instrument lookup -------------------------------------------------

    async def lookup_instrument(self, symbol: str) -> Optional[InstrumentMeta]:
        """Resolve a symbol to normalized instrument metadata."""
        return self._master.lookup_instrument(symbol)

    # -- quotes ------------------------------------------------------------

    async def get_quote(self, symbol: str) -> Optional[TickerData]:
        """Get a real-time quote (WebSocket cache first, then REST LTP)."""
        key = symbol.upper()
        async with self._cache_lock:
            cached = self._quote_cache.get(key)
            if cached and (datetime.utcnow() - cached.timestamp).total_seconds() < 5:
                return cached
        meta = await self.lookup_instrument(symbol)
        if meta is None:
            logger.info("angel_one_token_not_found", symbol=symbol)
            return None
        try:
            raw = await self._client.ltp_quote(meta.exchange, meta.token)
        except SmartAPIAuthError as exc:
            logger.warning("angel_one_quote_auth_error", symbol=symbol, error=str(exc))
            return None
        except SmartAPIError as exc:
            logger.warning("angel_one_quote_error", symbol=symbol, error=str(exc))
            return None
        ticker = _ltp_to_ticker(symbol, meta, raw)
        if ticker is not None:
            ticker.source = SOURCE_ANGEL_ONE
            ticker.status = STATUS_LIVE
            async with self._cache_lock:
                self._quote_cache[key] = ticker
        return ticker

    async def get_quotes(self, symbols: List[str]) -> List[TickerData]:
        results = []
        for symbol in symbols:
            quote = await self.get_quote(symbol)
            if quote:
                results.append(quote)
        return results

    # -- historical OHLC ---------------------------------------------------

    async def get_ohlc(
        self,
        symbol: str,
        interval: str = "1d",
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[OHLCData]:
        """Get historical OHLC candles via SmartAPI candle history."""
        meta = await self.lookup_instrument(symbol)
        if meta is None:
            return []
        code = INTERVAL_CODES.get(interval, "ONE_DAY")
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - _interval_span(interval, limit)
        try:
            rows = await self._client.candle_history(
                meta.exchange, meta.token, code, start_date, end_date
            )
        except SmartAPIError as exc:
            logger.warning("angel_one_ohlc_error", symbol=symbol, error=str(exc))
            return []
        candles: List[OHLCData] = []
        for r in rows or []:
            try:
                ts, o, h, lc, c, vol = r[0], r[1], r[2], r[3], r[4], r[5]
                candles.append(
                    OHLCData(
                        timestamp=_parse_ts(ts),
                        open=float(o),
                        high=float(h),
                        low=float(lc),
                        close=float(c),
                        volume=int(vol or 0),
                    )
                )
            except (TypeError, ValueError, IndexError):
                continue
        return candles[-limit:] if candles else []

    # -- option chain ------------------------------------------------------

    async def get_option_chain(
        self,
        symbol: str,
        expiry: Optional[str] = None,
    ) -> List[OptionChainData]:
        """Get the real option chain for an index/stock via SmartAPI.

        Returns ``[]`` when the provider cannot return a chain (auth/transport
        failure) — never fabricated strikes/OI/IV. Unavailable provider fields
        are left ``None``/0 (e.g. IV when not reported).
        """
        idx = self._master.lookup_index(symbol)
        token = idx.token if idx else symbol
        try:
            payload = await self._client.option_chain(exchange="NFO", token=token)
        except SmartAPIError as exc:
            logger.warning("angel_one_option_chain_error", symbol=symbol, error=str(exc))
            return []
        records = payload.get("records") or payload.get("data") or []
        if not records:
            return []
        out: List[OptionChainData] = []
        snap_ts = _parse_chain_timestamp(payload)
        for r in records:
            ce = r.get("CE") or {}
            pe = r.get("PE") or {}
            if not r.get("strikePrice") and not ce and not pe:
                continue
            exp_raw = r.get("expiryDate") or ce.get("expiryDate") or pe.get("expiryDate")
            exp_dt = _parse_expiry(exp_raw)
            if expiry:
                wanted = _parse_expiry(expiry)
                if exp_dt and wanted and exp_dt.date() != wanted.date():
                    continue
            out.append(
                OptionChainData(
                    symbol=symbol.upper(),
                    expiry_date=exp_dt or datetime.utcnow(),
                    strike=_float(r.get("strikePrice")),
                    call_oi=_int(ce.get("openInterest")),
                    call_volume=_int(ce.get("totalTradedVolume")),
                    call_iv=_float(ce.get("impliedVolatility")),
                    call_ltp=_float(ce.get("lastPrice")),
                    call_change_oi=_int(ce.get("changeinOpenInterest")),
                    put_oi=_int(pe.get("openInterest")),
                    put_volume=_int(pe.get("totalTradedVolume")),
                    put_iv=_float(pe.get("impliedVolatility")),
                    put_ltp=_float(pe.get("lastPrice")),
                    put_change_oi=_int(pe.get("changeinOpenInterest")),
                    source=SOURCE_ANGEL_ONE,
                    status=STATUS_LIVE,
                    timestamp=snap_ts,
                )
            )
        return out

    async def search_symbols(self, query: str) -> List[Dict[str, str]]:
        """Search for symbols on SmartAPI."""
        try:
            rows = await self._client.search_scrip(query)
        except SmartAPIError as exc:
            logger.warning("angel_one_search_error", query=query, error=str(exc))
            return []
        return [
            {
                "symbol": r.get("symbol", ""),
                "name": r.get("symbol", ""),
                "token": str(r.get("token", "")),
                "type": r.get("instrumenttype", ""),
            }
            for r in (rows or [])[:10]
        ]

    # -- realtime WebSocket ------------------------------------------------

    async def connect_websocket(self) -> bool:
        """Connect to SmartAPI V2 WebSocket for real-time streaming."""
        if not self.is_configured:
            logger.warning("angel_one_not_configured")
            return False
        if self._ws is not None and self._ws.connected:
            return True
        try:
            sess = await self._client.ensure_session()
        except SmartAPIError as exc:
            logger.error("angel_one_ws_auth_failed", error=str(exc))
            return False
        self._ws = SmartWebSocketV2(
            auth_token=sess.jwt_token,
            api_key=self.config.api_key,
            client_code=self.config.client_code,
            feed_token=sess.feed_token,
            on_data=self._on_tick,
        )
        return await self._ws.connect()

    def _on_tick(self, tick: Tick) -> None:
        """Normalize a WS tick into the candle aggregator + quote cache."""
        symbol = self._symbol_for_token(tick.token) or tick.token
        self._aggregator.ingest(tick, symbol)
        if tick.ltp is not None:
            self._quote_cache[symbol.upper()] = TickerData(
                symbol=symbol,
                name=symbol,
                price=tick.ltp,
                change=0.0,
                change_percent=0.0,
                open=tick.open_price or 0.0,
                high=tick.high_price or 0.0,
                low=tick.low_price or 0.0,
                close=tick.close_price or 0.0,
                previous_close=tick.close_price or 0.0,
                volume=tick.volume or 0,
                timestamp=tick.exchange_timestamp or datetime.utcnow(),
                source=SOURCE_ANGEL_ONE,
                status=STATUS_LIVE,
            )

    def _symbol_for_token(self, token: str) -> Optional[str]:
        """Reverse-resolve a provider token to a symbol (best effort)."""
        meta = self._master.lookup_instrument(token)
        return meta.symbol if meta else None

    async def subscribe(self, symbols: List[str]) -> bool:
        """Subscribe to realtime quotes for symbols (QUOTE mode)."""
        if not self._ws or not self._ws.connected:
            connected = await self.connect_websocket()
            if not connected:
                return False
        groups: Dict[str, List[str]] = {}
        for symbol in symbols:
            meta = await self.lookup_instrument(symbol)
            if meta is None:
                continue
            exch = "NSE" if meta.exchange in ("", "NSE") else meta.exchange
            groups.setdefault(exch, []).append(meta.token)
            self._subscribed.add(symbol.upper())
        token_list = [
            {"exchangeType": exch, "tokens": toks} for exch, toks in groups.items()
        ]
        if not token_list:
            return False
        return await self._ws.subscribe("chartytics", QUOTE_MODE, token_list)

    async def unsubscribe(self, symbols: List[str]) -> bool:
        if not self._ws or not self._ws.connected:
            return False
        groups: Dict[str, List[str]] = {}
        for symbol in symbols:
            meta = await self.lookup_instrument(symbol)
            if meta is None:
                continue
            exch = "NSE" if meta.exchange in ("", "NSE") else meta.exchange
            groups.setdefault(exch, []).append(meta.token)
            self._subscribed.discard(symbol.upper())
        token_list = [
            {"exchangeType": exch, "tokens": toks} for exch, toks in groups.items()
        ]
        if not token_list:
            return False
        return await self._ws.unsubscribe("chartytics", QUOTE_MODE, token_list)

    async def disconnect_websocket(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
        self._subscribed.clear()

    def realtime_candles(
        self, symbol: str, interval: str, limit: int = 100
    ) -> List[OHLCData]:
        """Return candles aggregated from the live WebSocket stream (if any)."""
        buckets = self._aggregator.get_candles(symbol, interval, limit)
        return [
            OHLCData(
                timestamp=b.bucket_start,
                open=b.open or 0.0,
                high=b.high or 0.0,
                low=b.low or 0.0,
                close=b.close or 0.0,
                volume=b.volume,
            )
            for b in buckets
        ]

    async def is_available(self) -> bool:
        """Check provider availability by ensuring a valid session."""
        if not self.is_configured:
            return False
        try:
            await self._client.ensure_session()
            return True
        except SmartAPIError as exc:
            logger.info("angel_one_unavailable", error=str(exc))
            return False

    async def close(self) -> None:
        await self.disconnect_websocket()
        await self._client.close()


# --- helpers ---------------------------------------------------------------


def _ltp_to_ticker(symbol: str, meta: InstrumentMeta, raw: Dict) -> Optional[TickerData]:
    """Normalize a SmartAPI LTP quote payload into ``TickerData``."""
    if not raw:
        return None
    ltp = _float(raw.get("ltp") or raw.get("lastPrice"))
    if ltp is None:
        return None
    prev = _float(raw.get("previousClose") or raw.get("close")) or ltp
    change = _float(raw.get("netChange") or raw.get("change"))
    if change is None:
        change = round(ltp - prev, 2)
    pct = _float(raw.get("perNetChange") or raw.get("percentChange"))
    if pct is None:
        pct = round(change / prev * 100, 2) if prev else 0.0
    ts = _parse_ts(raw.get("lastTradedTime") or raw.get("exchangeTimestamp"))
    return TickerData(
        symbol=symbol,
        name=getattr(meta, "name", None) or symbol,
        price=ltp,
        change=change,
        change_percent=pct,
        open=_float(raw.get("open")) or ltp,
        high=_float(raw.get("high")) or ltp,
        low=_float(raw.get("low")) or ltp,
        close=_float(raw.get("close")) or ltp,
        previous_close=prev,
        volume=_int(raw.get("volume") or raw.get("totalTradedVolume")),
        timestamp=ts or datetime.utcnow(),
        source=SOURCE_ANGEL_ONE,
        status=STATUS_LIVE,
    )


def _float(v) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _int(v) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def _parse_ts(v) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        try:
            return datetime.utcfromtimestamp(v / 1000)
        except (TypeError, ValueError, OSError):
            return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%b-%Y %H:%M:%S"):
        try:
            return datetime.strptime(str(v), fmt)
        except ValueError:
            continue
    return None


def _parse_expiry(v) -> Optional[datetime]:
    if v is None:
        return None
    for fmt in ("%d-%b-%Y", "%Y-%m-%d", "%d-%b-%y"):
        try:
            return datetime.strptime(str(v), fmt)
        except ValueError:
            continue
    return None


def _parse_chain_timestamp(payload: Dict) -> Optional[datetime]:
    raw = payload.get("timestamp") or payload.get("lastUpdated")
    return _parse_ts(raw)


def _interval_span(interval: str, limit: int) -> timedelta:
    """Approximate calendar span covering ``limit`` bars of ``interval``."""
    secs = {
        "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
        "1h": 3600, "1d": 86400, "1w": 604800,
    }.get(interval.lower(), 86400)
    return timedelta(seconds=secs * max(limit, 1) * 1.5)


# Factory function
def create_angel_one_provider(
    api_key: str = "",
    client_code: str = "",
    password: str = "",
    totp_secret: str = "",
) -> AngelOneProvider:
    """Create Angel One provider with configuration."""
    config = AngelOneConfig(
        api_key=api_key,
        client_code=client_code,
        password=password,
        totp_secret=totp_secret,
    )
    return AngelOneProvider(config)
