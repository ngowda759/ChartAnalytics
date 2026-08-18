"""Realtime candle aggregation from WebSocket ticks.

Builds OHLCV candles for the timeframes ChartAnalytics already uses
(1m / 5m / 15m / 1h / 1d) from the ticks the Angel One WebSocket V2
delivers. Candles are bucketed by exchange timestamps so a candle's
``open`` is the first trade of the bucket and ``close`` the last, with
``high``/``low`` tracking the extremes and ``volume`` accumulating trade
quantity — exactly the standard OHLCV aggregation.

Session-boundary handling: the bucket key is derived from the exchange
timestamp floored to the interval, so a new interval (or a new trading
day) starts a fresh bucket automatically; today's incomplete bucket is
kept separate from completed historical candles by the same timestamp
flooring, never merged.

The aggregator is pure (no network, no clock guessing): it only ingests
``Tick`` objects produced by :mod:`smartapi_ws_v2`. This makes it fully
unit-testable with synthetic ticks (clearly test scaffolding — these are
not market values).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from .smartapi_ws_v2 import Tick

# Bucket seconds per supported timeframe.
TIMEFRAME_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "1d": 86400,
}


@dataclass
class CandleBucket:
    """An in-progress OHLCV bucket for one symbol+interval."""

    symbol: str
    interval: str
    bucket_start: datetime
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: int = 0
    last_updated: Optional[datetime] = None
    closed: bool = False

    def update(self, price: float, volume: int, ts: datetime) -> None:
        if self.open is None:
            self.open = price
        self.high = price if self.high is None else max(self.high, price)
        self.low = price if self.low is None else min(self.low, price)
        self.close = price
        self.volume = self.volume + int(volume or 0)
        self.last_updated = ts


@dataclass
class CandleAggregator:
    """Per-symbol, multi-timeframe candle builder from ticks.

    ``completed`` candles older than the live bucket are retained for a
    bounded window (``MAX_COMPLETED``) so a consumer can fetch the recent
    real candles without re-hitting history. The aggregator never invents
    prices — every value comes from a real tick.
    """

    MAX_COMPLETED: int = 200
    _buckets: Dict[tuple, CandleBucket] = field(default_factory=dict)
    _completed: Dict[tuple, List[CandleBucket]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def ingest(self, tick: Tick, symbol: str) -> None:
        """Update all configured-timeframe buckets for a tick."""
        if tick.ltp is None:
            return
        ts = tick.exchange_timestamp or datetime.now(timezone.utc)
        vol = tick.last_traded_qty or 0
        with self._lock:
            for interval, secs in TIMEFRAME_SECONDS.items():
                bucket_start = _floor(ts, secs)
                key = (symbol.upper(), interval)
                bucket = self._buckets.get((key[0], key[1], bucket_start))
                if bucket is None:
                    bucket = CandleBucket(
                        symbol=symbol.upper(),
                        interval=interval,
                        bucket_start=bucket_start,
                    )
                    self._buckets[(key[0], key[1], bucket_start)] = bucket
                bucket.update(tick.ltp, vol, ts)
                # Close out any prior bucket of the same symbol/interval.
                self._close_stale(symbol.upper(), interval, bucket_start)

    def get_candles(
        self, symbol: str, interval: str, limit: int = 100
    ) -> List[CandleBucket]:
        """Return the most recent ``limit`` candles (completed + current)."""
        with self._lock:
            completed = list(self._completed.get((symbol.upper(), interval), []))
            # Active (still-open) bucket is appended last so the series is
            # ordered oldest -> newest.
            active = [
                b
                for (sym, intv, _), b in self._buckets.items()
                if sym == symbol.upper() and intv == interval
            ]
        candles = completed + active
        candles.sort(key=lambda c: c.bucket_start)
        return candles[-limit:]

    def clear(self) -> None:
        with self._lock:
            self._buckets.clear()
            self._completed.clear()

    # -- internal ----------------------------------------------------------

    def _close_stale(self, symbol: str, interval: str, current_start: datetime) -> None:
        """Mark buckets older than ``current_start`` as completed."""
        for key in list(self._buckets.keys()):
            sym, intv, start = key
            if sym != symbol or intv != interval:
                continue
            if start >= current_start:
                continue
            bucket = self._buckets.pop(key)
            bucket.closed = True
            comp = self._completed.setdefault((symbol, interval), [])
            comp.append(bucket)
            # bound memory
            if len(comp) > self.MAX_COMPLETED:
                del comp[: len(comp) - self.MAX_COMPLETED]


def _floor(ts: datetime, seconds: int) -> datetime:
    """Floor a timestamp to the interval boundary (UTC)."""
    if ts.tzinfo is not None:
        ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
    epoch = datetime(1970, 1, 1)
    delta = (ts - epoch).total_seconds()
    floored = int(delta // seconds) * seconds
    return epoch + timedelta(seconds=floored)
