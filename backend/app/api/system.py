"""System / data-provider diagnostic endpoints.

Exposes a non-secret summary of the active market-data provider so operators
can see at a glance whether the app is connected to real data, which provider
handles which capability (equity OHLCV vs realtime vs options/OI), and
whether Angel One is configured/connected. NEVER returns API keys, tokens,
secrets or passwords.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.services import market_data

router = APIRouter()


class ProviderCapability(BaseModel):
    configured: bool
    connected: bool
    realtime: bool = False
    historical: bool = False
    options: bool = False
    oi: bool = False


class DataProviderStatus(BaseModel):
    provider: str
    configured: bool
    connected: bool
    quote: bool
    historical_ohlcv: bool
    options: bool
    last_success: Optional[datetime] = None
    error: Optional[str] = None


class ProviderMatrix(BaseModel):
    primary_provider: str
    realtime_provider: Optional[str] = None
    options_provider: Optional[str] = None
    yfinance: ProviderCapability
    angel_one: ProviderCapability


@router.get("/data-provider", response_model=DataProviderStatus)
async def data_provider_status() -> DataProviderStatus:
    """Report the active market-data provider capabilities (no secrets).

    ``configured``  : the selected provider has its credentials (always true for
                      yfinance, which needs none).
    ``connected``   : a live quote/ohlc call recently succeeded.
    ``quote``/``historical_ohlcv``/``options``: capability flags.
    """
    provider = market_data.get_market_data_provider()
    configured = (
        market_data._broker_configured(provider)
        if provider in ("angel_one", "kite")
        else True
    )

    last_success = market_data.last_success_at()
    last_error = market_data.last_error_for("quote") or market_data.last_error_for("ohlc")

    quote_ok = provider in ("yfinance", "angel_one", "kite", "mock")
    ohlc_ok = provider in ("yfinance", "angel_one", "kite", "mock")
    options_ok = provider in ("angel_one", "kite")

    connected = last_success is not None or provider in ("yfinance", "mock")

    return DataProviderStatus(
        provider=provider,
        configured=configured,
        connected=connected,
        quote=quote_ok,
        historical_ohlcv=ohlc_ok,
        options=options_ok,
        last_success=last_success,
        error=last_error,
    )


@router.get("/provider-matrix", response_model=ProviderMatrix)
async def provider_matrix() -> ProviderMatrix:
    """Full provider capability matrix (no secrets).

    Reports which provider handles each capability:
      * primary_provider  — equity/index OHLCV (yfinance by default)
      * realtime_provider — live ticks (Angel One/Kite when configured)
      * options_provider  — option chain / OI (Angel One/Kite when configured)

    Per-provider flags are non-secret: configured (credentials present),
    connected (a live call recently succeeded), realtime/options/oi
    capability booleans.
    """
    primary = market_data.get_market_data_provider()
    realtime = market_data.get_realtime_provider()
    options = market_data.get_options_provider()
    last_success = market_data.last_success_at()

    return ProviderMatrix(
        primary_provider=primary,
        realtime_provider=realtime,
        options_provider=options,
        yfinance=ProviderCapability(
            configured=True,
            connected=last_success is not None or primary == "yfinance",
            realtime=False,
            historical=True,
            options=False,
            oi=False,
        ),
        angel_one=ProviderCapability(
            configured=market_data.angel_one_configured(),
            connected=realtime == "angel_one" or options == "angel_one",
            realtime=realtime == "angel_one",
            historical=primary == "angel_one" and market_data.angel_one_configured(),
            options=options == "angel_one",
            oi=options == "angel_one",
        ),
    )


@router.get("/provider-info")
async def provider_info():
    """Human-readable provider label + environment (no secrets)."""
    return {
        "provider": market_data.get_market_data_provider(),
        "display_name": market_data.provider_display_name(),
        "realtime_provider": market_data.get_realtime_provider(),
        "options_provider": market_data.get_options_provider(),
        "environment": settings.ENVIRONMENT,
        "mock_mode": market_data.is_mock_mode(),
    }
