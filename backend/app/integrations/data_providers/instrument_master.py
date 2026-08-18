"""Angel One instrument master / token mapping.

Resolves NSE equities, NSE indices, NFO futures and NFO options to the
provider instrument tokens required by SmartAPI REST + WebSocket calls.

Source: Angel One OpenAPI scrip master
``https://margincalculator.angelone.in/OpenAPI_File_Files/OpenAPIScripMaster.json``
(which returns ``{data: {NSE: [...], NFO: [...], ...}}``).

Design rules (data-integrity):
* No fabricated tokens. Indices use the well-known, stable SmartAPI index
  spot tokens (documented in the SmartAPI wiki). Equity/option tokens are
  resolved from the live scrip master and cached; when the master cannot be
  downloaded the lookup returns ``None`` so callers surface an unavailable
  state instead of a wrong token.
* Resolved metadata is cached in-process for ``INSTRUMENT_CACHE_TTL`` seconds
  so a single dashboard load does not refetch the master per symbol.
* Thread-safe (the master fetch is guarded by a lock so concurrent lookups
  share one download).
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

import httpx
import structlog

from .base import InstrumentMeta

logger = structlog.get_logger()

SCRIP_MASTER_URL = (
    "https://margincalculator.angelone.in/OpenAPI_File_Files/"
    "OpenAPIScripMaster.json"
)

# How long to keep the resolved instrument cache (seconds).
INSTRUMENT_CACHE_TTL = 6 * 3600  # 6h — contracts rotate daily, refresh is cheap

# Well-known SmartAPI index SPOT tokens (NSE index segment). These are stable
# and documented by Angel One; they are NOT derivative tokens.
_INDEX_TOKENS: Dict[str, str] = {
    "NIFTY": "26000",
    "NIFTY 50": "26000",
    "NIFTY50": "26000",
    "BANKNIFTY": "26001",
    "NIFTY BANK": "26001",
    "NIFTY BANK": "26001",
    "FINNIFTY": "26037",
    "NIFTY FIN SERVICE": "26037",
    "NIFTY FIN SERVICES": "26037",
    "NIFTY MIDCAP": "26023",
    "NIFTY IT": "26009",
    "INDIA VIX": "26469",
}

# Segment the spot quote endpoint expects for each index family.
_INDEX_EXCHANGE = "NSE"


class InstrumentMaster:
    """Cached resolver for Angel One instrument metadata."""

    def __init__(self, client: Optional[httpx.Client] = None):
        self._client = client
        self._owns_client = client is None
        self._lock = threading.Lock()
        self._master: Dict[str, List[dict]] = {}  # segment -> rows
        self._by_tradingsymbol: Dict[str, InstrumentMeta] = {}
        self._equity_by_symbol: Dict[str, InstrumentMeta] = {}
        self._fetched_at: float = 0.0
        self._fetch_error: Optional[str] = None

    # -- public API ---------------------------------------------------------

    def get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=30.0)
        return self._client

    def is_fresh(self) -> bool:
        return bool(self._master) and (time.time() - self._fetched_at) < INSTRUMENT_CACHE_TTL

    def lookup_index(self, symbol: str) -> Optional[InstrumentMeta]:
        """Resolve an index spot instrument (NIFTY/BANKNIFTY/FINNIFTY...)."""
        key = symbol.strip().upper()
        token = _INDEX_TOKENS.get(key)
        if not token:
            return None
        return InstrumentMeta(
            symbol=key,
            exchange=_INDEX_EXCHANGE,
            token=token,
            tradingsymbol=key,
            instrument_type="INDEX",
            name=key,
        )

    def lookup_equity(self, symbol: str) -> Optional[InstrumentMeta]:
        """Resolve an NSE equity to its SmartAPI token via the scrip master."""
        key = symbol.strip().upper()
        # Equity symbols are also valid index lookups for NIFTY/BANKNIFTY
        # families; prefer the index token when applicable.
        idx = self.lookup_index(key)
        if idx:
            return idx
        self._ensure_loaded()
        return self._equity_by_symbol.get(key)

    def lookup_option_contract(
        self,
        underlying: str,
        expiry: Optional[datetime],
        strike: float,
        option_type: str,
    ) -> Optional[InstrumentMeta]:
        """Resolve a specific NFO option contract (CE/PE) for an underlying."""
        self._ensure_loaded()
        nfo = self._master.get("NFO", [])
        ot = option_type.strip().upper()
        if ot in ("CALL", "C"):
            ot = "CE"
        elif ot in ("PUT", "P"):
            ot = "PE"
        sym_upper = underlying.strip().upper()
        for row in nfo:
            if row.get("instrumenttype") not in ("OPTIDX", "OPTSTK"):
                continue
            if row.get("symbol", "").upper() != sym_upper:
                continue
            if row.get("optiontype", "").upper() != ot:
                continue
            if _strike_of(row) != float(strike):
                continue
            row_expiry = _expiry_of(row)
            if expiry and row_expiry and row_expiry.date() != expiry.date():
                continue
            return _row_to_meta(row)
        return None

    def list_option_expiries(self, underlying: str) -> List[datetime]:
        """Distinct NFO option expiry dates for an underlying (ascending)."""
        self._ensure_loaded()
        sym_upper = underlying.strip().upper()
        nfo = self._master.get("NFO", [])
        seen: set = set()
        out: List[datetime] = []
        for row in nfo:
            if row.get("instrumenttype") not in ("OPTIDX", "OPTSTK"):
                continue
            if row.get("symbol", "").upper() != sym_upper:
                continue
            exp = _expiry_of(row)
            if exp and exp.date() not in seen:
                seen.add(exp.date())
                out.append(exp)
        out.sort()
        return out

    def lookup_instrument(self, symbol: str) -> Optional[InstrumentMeta]:
        """Generic lookup: index -> equity -> exact tradingsymbol match."""
        idx = self.lookup_index(symbol)
        if idx:
            return idx
        self._ensure_loaded()
        key = symbol.strip().upper()
        eq = self._equity_by_symbol.get(key)
        if eq:
            return eq
        return self._by_tradingsymbol.get(key)

    def last_error(self) -> Optional[str]:
        return self._fetch_error

    def clear_cache(self) -> None:
        with self._lock:
            self._master = {}
            self._by_tradingsymbol = {}
            self._equity_by_symbol = {}
            self._fetched_at = 0.0
            self._fetch_error = None

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    # -- internal -----------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if self.is_fresh():
            return
        with self._lock:
            if self.is_fresh():
                return
            self._load_master()

    def _load_master(self) -> None:
        try:
            resp = self.get_client().get(SCRIP_MASTER_URL)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            self._fetch_error = f"scrip master download failed: {exc}"
            logger.info("instrument_master_download_failed", error=str(exc))
            return

        data = payload.get("data") or payload
        if not isinstance(data, dict):
            self._fetch_error = "scrip master payload missing 'data'"
            return

        self._master = {seg: rows for seg, rows in data.items() if isinstance(rows, list)}
        self._by_tradingsymbol = {}
        self._equity_by_symbol = {}
        for row in self._master.get("NSE", []):
            meta = _row_to_meta(row)
            if not meta:
                continue
            self._by_tradingsymbol[meta.tradingsymbol.upper()] = meta
            sym = (row.get("symbol") or "").upper()
            if sym and sym not in self._equity_by_symbol:
                self._equity_by_symbol[sym] = meta
        for seg in ("NFO", "BFO", "CDS", "MCX"):
            for row in self._master.get(seg, []):
                meta = _row_to_meta(row)
                if meta:
                    self._by_tradingsymbol[meta.tradingsymbol.upper()] = meta
        self._fetched_at = time.time()
        self._fetch_error = None
        logger.info(
            "instrument_master_loaded",
            nse=len(self._equity_by_symbol),
            nfo=len(self._master.get("NFO", [])),
        )


# -- helpers ----------------------------------------------------------------


def _strike_of(row: dict) -> Optional[float]:
    try:
        return float(row.get("strike") or 0)
    except (TypeError, ValueError):
        return None


def _expiry_of(row: dict) -> Optional[datetime]:
    raw = row.get("expiry") or row.get("expiryDate")
    if not raw:
        return None
    for fmt in ("%d-%b-%Y", "%Y-%m-%d", "%d-%b-%y"):
        try:
            return datetime.strptime(str(raw), fmt)
        except ValueError:
            continue
    return None


def _row_to_meta(row: dict) -> Optional[InstrumentMeta]:
    token = str(row.get("token") or "").strip()
    tradingsymbol = str(row.get("tradingsymbol") or row.get("symbol") or "").strip()
    if not token or not tradingsymbol:
        return None
    try:
        lot = int(row.get("lotsize") or 0) or None
    except (TypeError, ValueError):
        lot = None
    return InstrumentMeta(
        symbol=str(row.get("symbol") or tradingsymbol).upper(),
        exchange=str(row.get("exch_seg") or row.get("exchange") or "").upper(),
        token=token,
        tradingsymbol=tradingsymbol.upper(),
        instrument_type=str(row.get("instrumenttype") or "").upper(),
        expiry=_expiry_of(row),
        strike=_strike_of(row),
        option_type=str(row.get("optiontype") or "").upper() or None,
        lot_size=lot,
        name=str(row.get("name") or row.get("symbol") or tradingsymbol),
    )


# Process-wide singleton so the (large) master is fetched once per process.
_master: Optional[InstrumentMaster] = None
_master_lock = threading.Lock()


def get_instrument_master() -> InstrumentMaster:
    global _master
    if _master is None:
        with _master_lock:
            if _master is None:
                _master = InstrumentMaster()
    return _master


def reset_instrument_master() -> None:
    """Test hook to drop the process-wide master + cached lookups."""
    global _master
    with _master_lock:
        if _master is not None:
            _master.clear_cache()
            _master.close()
        _master = None
