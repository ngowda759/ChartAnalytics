"""Angel One SmartAPI HTTP client — auth + REST helpers.

Encapsulates the SmartAPI V2 HTTP surface (login with TOTP, feed-token, LTP
quote, historical candle, option chain, scrip search) behind a small, tested
async client so :mod:`angel_one_provider` can stay focused on normalisation
and WebSocket streaming.

Endpoint reference (SmartAPI V2, official ``smartapi-python`` SDK route map):
  login          POST /rest/auth/manager/v1/login
  getFeedToken   GET  /rest/auth/angelbroking/v1/getFeedToken
  profile        GET  /rest/auth/angelbroking/v1/getProfile
  ltp            POST /rest/order/v1/getLtpQuote      (routed via /rest/market/)
  candleHistory  POST /rest/market/v1/candleHistorical
  optionChain    GET  /rest/market/v1/optionChain
  searchScrip    GET  /rest/market/v1/searchScrip

No method here fabricates data: every network/parse/credential failure is
surfaced to the caller via :class:`SmartAPIError` so the provider can return
a truthful ``unavailable`` state instead of a zeroed-out payload.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
import structlog

logger = structlog.get_logger()

SMARTAPI_BASE_URL = "https://apiconnect.angelone.in"
LOGIN_TIMEOUT = 15.0
REST_TIMEOUT = 20.0


class SmartAPIError(Exception):
    """Raised when SmartAPI returns an error or the call fails.

    Carries ``status_code`` + ``message`` so the provider can classify
    auth failures vs. rate limits vs. transient network errors.
    """

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class SmartAPIAuthError(SmartAPIError):
    """Authentication-specific failure (bad credentials / expired TOTP)."""


class SmartAPIRateLimitError(SmartAPIError):
    """429 / rate-limit response from SmartAPI."""


@dataclass
class SmartAPISession:
    """A resolved SmartAPI session."""

    jwt_token: str = ""
    refresh_token: str = ""
    feed_token: str = ""
    obtained_at: float = 0.0
    client_code: str = ""

    @property
    def is_valid(self) -> bool:
        return bool(self.jwt_token and self.feed_token)

    def age_seconds(self) -> float:
        return time.time() - self.obtained_at if self.obtained_at else 0.0


@dataclass
class SmartAPIClient:
    """Async HTTP client for the Angel One SmartAPI REST surface."""

    api_key: str = ""
    client_code: str = ""
    password: str = ""
    totp_secret: str = ""
    base_url: str = SMARTAPI_BASE_URL
    _http: Optional[httpx.AsyncClient] = None
    _session: SmartAPISession = field(default_factory=SmartAPISession)

    # -- lifecycle ---------------------------------------------------------

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-UserToken": self.api_key,
                    "X-SourceID": "WEB",
                    "X-PrivateKey": self.api_key,
                },
                timeout=REST_TIMEOUT,
            )
        return self._http

    async def close(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    @property
    def session(self) -> SmartAPISession:
        return self._session

    def is_configured(self) -> bool:
        return bool(self.api_key and self.client_code and self.password)

    # -- auth --------------------------------------------------------------

    def _generate_totp(self) -> str:
        if not self.totp_secret:
            return ""
        try:
            import pyotp
        except ImportError as exc:  # pragma: no cover - dep is optional at import
            raise SmartAPIAuthError(f"pyotp not installed: {exc}")
        return pyotp.TOTP(self.totp_secret).now()

    async def login(self) -> SmartAPISession:
        """Authenticate and populate the session (jwt + feed token).

        Raises :class:`SmartAPIAuthError` for credential/config issues and
        :class:`SmartAPIError` for transport/server errors. Never returns a
        partial session silently.
        """
        if not self.is_configured():
            raise SmartAPIAuthError(
                "Angel One not configured: set ANGEL_ONE_API_KEY, "
                "ANGEL_ONE_CLIENT_CODE and ANGEL_ONE_PASSWORD."
            )
        body = {
            "clientcode": self.client_code,
            "password": self.password,
            "totp": self._generate_totp(),
        }
        try:
            resp = await self._client().post(
                "/rest/auth/manager/v1/login", json=body, timeout=LOGIN_TIMEOUT
            )
        except httpx.HTTPError as exc:
            raise SmartAPIError(f"login transport error: {exc}") from exc
        data = self._parse(resp, op="login")
        d = data.get("data") or {}
        jwt = d.get("jwtToken") or ""
        refresh = d.get("refreshToken") or ""
        feed = d.get("feedToken") or ""
        if not jwt:
            raise SmartAPIAuthError("login succeeded but jwtToken missing")
        # Feed token is in the login payload; if absent, fetch it explicitly.
        if not feed:
            feed = await self._fetch_feed_token(jwt)
        self._session = SmartAPISession(
            jwt_token=jwt,
            refresh_token=refresh,
            feed_token=feed,
            obtained_at=time.time(),
            client_code=self.client_code,
        )
        logger.info("angel_one_login_success", client=self.client_code)
        return self._session

    async def _fetch_feed_token(self, jwt: str) -> str:
        """Fetch the feed token via the dedicated endpoint (fallback)."""
        try:
            resp = await self._client().get(
                "/rest/auth/angelbroking/v1/getFeedToken",
                headers=self._auth_headers(jwt),
                timeout=LOGIN_TIMEOUT,
            )
        except httpx.HTTPError as exc:
            raise SmartAPIError(f"feed token transport error: {exc}") from exc
        data = self._parse(resp, op="getFeedToken")
        feed = (data.get("data") or {}).get("feedToken") or ""
        if not feed:
            raise SmartAPIAuthError("feed token missing in response")
        return feed

    def _auth_headers(self, jwt_override: Optional[str] = None) -> Dict[str, str]:
        jwt = jwt_override or self._session.jwt_token
        bearer = jwt if jwt.startswith("Bearer ") else f"Bearer {jwt}"
        return {
            "Authorization": bearer,
            "X-UserToken": self.api_key,
            "X-PrivateKey": self.api_key,
        }

    async def ensure_session(self, max_age: float = 8 * 3600) -> SmartAPISession:
        """Return a valid session, logging in when missing/stale."""
        if self._session.is_valid and self._session.age_seconds() < max_age:
            return self._session
        return await self.login()

    # -- market data REST --------------------------------------------------

    async def ltp_quote(self, exchange: str, token: str) -> Dict[str, Any]:
        """Fetch the LTP/quote snapshot for one instrument."""
        sess = await self.ensure_session()
        body = {"mode": "FULL", "exchangeTokens": [{exchange: [token]}]}
        try:
            resp = await self._client().post(
                "/rest/market/v1/getLtpQuote",
                json=body,
                headers=self._auth_headers(sess.jwt_token),
            )
        except httpx.HTTPError as exc:
            raise SmartAPIError(f"ltp transport error: {exc}") from exc
        data = self._parse(resp, op="ltpQuote")
        scattered = data.get("data") or {}
        # SmartAPI nests the instrument data under the token key.
        return scattered.get(token) or scattered.get(exchange, {}).get(token) or scattered

    async def candle_history(
        self,
        exchange: str,
        token: str,
        interval: str,
        from_date: datetime,
        to_date: datetime,
    ) -> list:
        """Fetch historical candles. ``interval`` is the SmartAPI code."""
        sess = await self.ensure_session()
        body = {
            "exchange": exchange,
            "symboltoken": token,
            "interval": interval,
            "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
            "todate": to_date.strftime("%Y-%m-%d %H:%M"),
        }
        try:
            resp = await self._client().post(
                "/rest/market/v1/candleHistorical",
                json=body,
                headers=self._auth_headers(sess.jwt_token),
            )
        except httpx.HTTPError as exc:
            raise SmartAPIError(f"candle transport error: {exc}") from exc
        data = self._parse(resp, op="candleHistory")
        return data.get("data") or []

    async def option_chain(
        self, exchange: str = "NFO", token: str = "26000"
    ) -> Dict[str, Any]:
        """Fetch the full option chain for an index/stock token."""
        sess = await self.ensure_session()
        params = {"exchange": exchange, "symboltoken": token}
        try:
            resp = await self._client().get(
                "/rest/market/v1/optionChain",
                params=params,
                headers=self._auth_headers(sess.jwt_token),
            )
        except httpx.HTTPError as exc:
            raise SmartAPIError(f"option chain transport error: {exc}") from exc
        data = self._parse(resp, op="optionChain")
        return data.get("data") or {}

    async def search_scrip(self, query: str, exchange: str = "NSE") -> list:
        """Search the scrip master for a name (returns provider rows)."""
        sess = await self.ensure_session()
        params = {"exchange": exchange, "searchscrip": query}
        try:
            resp = await self._client().get(
                "/rest/market/v1/searchScrip",
                params=params,
                headers=self._auth_headers(sess.jwt_token),
            )
        except httpx.HTTPError as exc:
            raise SmartAPIError(f"searchscrip transport error: {exc}") from exc
        data = self._parse(resp, op="searchScrip")
        return data.get("data") or []

    # -- internal ----------------------------------------------------------

    def _parse(self, resp: httpx.Response, op: str) -> Dict[str, Any]:
        """Parse a SmartAPI JSON envelope and raise typed errors.

        SmartAPI returns ``{"status": true/false, "message": ..., "data": ...}``
        with HTTP 200 even on logical errors, so ``status`` is the source of
        truth. Auth errors (Token invalid/expired) are surfaced as
        :class:`SmartAPIAuthError` so the provider can re-login.
        """
        if resp.status_code == 429:
            raise SmartAPIRateLimitError("SmartAPI rate limit exceeded", 429)
        try:
            payload = resp.json()
        except ValueError as exc:
            raise SmartAPIError(
                f"{op}: non-JSON response ({resp.status_code})", resp.status_code
            ) from exc
        if not payload.get("status", False):
            msg = payload.get("message") or payload.get("error") or "unknown error"
            code = payload.get("errorCode")
            # SmartAPI auth failures: AGG-..., token invalid/expired.
            low = str(msg).lower() + " " + str(code).lower()
            if any(k in low for k in ("token", "invalid", "unauthor", "expire", "auth")):
                raise SmartAPIAuthError(f"{op}: {msg}", resp.status_code)
            raise SmartAPIError(f"{op}: {msg}", resp.status_code)
        return payload
