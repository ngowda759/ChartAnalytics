"""System / data-provider diagnostic endpoints.

Exposes a non-secret summary of the active market-data provider so operators
can see at a glance whether the app is connected to real data. NEVER returns
API keys, tokens, secrets or passwords.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.services import market_data

router = APIRouter()


class DataProviderStatus(BaseModel):
    provider: str
    configured: bool
    connected: bool
    quote: bool
    historical_ohlcv: bool
    options: bool
    last_success: Optional[datetime] = None
    error: Optional[str] = None


@router.get("/data-provider", response_model=DataProviderStatus)
async def data_provider_status() -> DataProviderStatus:
    """Report the active market-data provider capabilities (no secrets).

    ``configured``  : the selected provider has its credentials (always true for
                      yfinance, which needs none).
    ``connected``   : a live quote/ohlc call recently succeeded.
    ``quote``/``historical_ohlcv``/``options``: capability flags.
    """
    provider = market_data.get_market_data_provider()
    configured = market_data._broker_configured(provider) if provider in ("angel_one", "kite") else True

    last_success = market_data.last_success_at()
    last_error = market_data.last_error_for("quote") or market_data.last_error_for("ohlc")

    # Capability matrix per provider.
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


@router.get("/provider-info")
async def provider_info():
    """Human-readable provider label + environment (no secrets)."""
    return {
        "provider": market_data.get_market_data_provider(),
        "display_name": market_data.provider_display_name(),
        "environment": settings.ENVIRONMENT,
        "mock_mode": market_data.is_mock_mode(),
    }
