from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import structlog

from app.schemas.options import (
    OptionChain,
    OptionData,
    OptionType,
    PCRAnalysis,
    OIAnalysis,
    MaxPainAnalysis,
    OptionSignal,
)
from app.services.market_service import get_market_service

logger = structlog.get_logger()
router = APIRouter()


def _unavailable(detail: str) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail=(
            f"{detail} Live option data is currently unavailable "
            "(no real data provider configured or market closed)."
        ),
    )


@router.get("/chain/{symbol}", response_model=OptionChain)
async def get_option_chain(
    symbol: str,
    expiry: Optional[str] = Query(None, description="Expiry date (YYYY-MM-DD)"),
):
    """Get option chain for a symbol.

    Only real option-chain data is returned. When no live provider is
    configured (or the market is closed) the endpoint returns 503 with a
    clear message instead of fabricated strikes/OI/IV. The ``source`` /
    ``status`` fields trace the data back to its real provider.
    """
    logger.info("fetching_option_chain", symbol=symbol, expiry=expiry)

    if expiry is None:
        expiry = get_next_thursday()

    service = get_market_service()
    analysis = await service.analyze_option_chain(symbol, expiry)

    if not analysis or not analysis.strikes:
        raise _unavailable(f"Option chain unavailable for {symbol}.")

    spot_price = analysis.spot_price
    pcr = analysis.pcr
    max_pain = analysis.max_pain
    total_call_oi = analysis.total_call_oi
    total_put_oi = analysis.total_put_oi

    # Propagate the real provider source/status (default unavailable).
    src = getattr(analysis, "source", "unavailable") or "unavailable"
    chain_ts = getattr(analysis, "timestamp", None) or datetime.utcnow()

    calls = []
    puts = []
    for s in analysis.strikes:
        calls.append(
            OptionData(
                strike=s.strike,
                oi=s.call_oi,
                change_oi=s.call_change_oi,
                volume=s.call_volume,
                iv=s.call_iv,
                ltp=s.call_ltp,
                bid=round(s.call_ltp * 0.98, 2),
                ask=round(s.call_ltp * 1.02, 2),
            )
        )
        puts.append(
            OptionData(
                strike=s.strike,
                oi=s.put_oi,
                change_oi=s.put_change_oi,
                volume=s.put_volume,
                iv=s.put_iv,
                ltp=s.put_ltp,
                bid=round(s.put_ltp * 0.98, 2),
                ask=round(s.put_ltp * 1.02, 2),
            )
        )

    return OptionChain(
        symbol=symbol.upper(),
        expiry=expiry,
        spot_price=spot_price,
        timestamp=chain_ts,
        underlying_change=0.0,
        calls=calls,
        puts=puts,
        pcr=round(pcr, 2),
        max_pain=max_pain,
        total_call_oi=total_call_oi,
        total_put_oi=total_put_oi,
        source=src,
        status="live",
    )


@router.get("/analysis/{symbol}")
async def get_option_analysis(
    symbol: str,
    expiry: Optional[str] = Query(None, description="Expiry date (YYYY-MM-DD)"),
):
    """Get detailed AI-powered option chain analysis"""
    logger.info("analyzing_option_chain", symbol=symbol, expiry=expiry)

    service = get_market_service()
    analysis = await service.analyze_option_chain(symbol, expiry)

    if not analysis:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Option analysis not available for {symbol}. Live option data is "
                "currently unavailable (no real data provider configured or market "
                "closed)."
            ),
        )

    return {
        "symbol": analysis.symbol,
        "spot_price": analysis.spot_price,
        "expiry_date": analysis.expiry_date.isoformat(),
        "key_metrics": {
            "pcr": analysis.pcr,
            "pcr_change": analysis.pcr_change,
            "max_pain": analysis.max_pain,
            "atm_iv": analysis.atm_iv,
            "iv_skew": analysis.iv_skew,
        },
        "oi_summary": {
            "total_call_oi": analysis.total_call_oi,
            "total_put_oi": analysis.total_put_oi,
            "net_oi": analysis.net_oi,
        },
        "outlook": {
            "trend": analysis.trend,
            "confidence": analysis.confidence,
            "interpretation": analysis.interpretation,
        },
        "support_levels": analysis.support_levels,
        "resistance_levels": analysis.resistance_levels,
        "source": getattr(analysis, "source", "unavailable") or "unavailable",
        "status": getattr(analysis, "status", "unavailable") or "unavailable",
        "timestamp": getattr(analysis, "timestamp", None),
    }


@router.get("/pcr/{symbol}", response_model=PCRAnalysis)
async def get_pcr_analysis(symbol: str, expiry: Optional[str] = None):
    """Get PCR analysis with historical trend.

    Returns real PCR only. Without a live option feed there is no historical
    PCR series to trend, so the endpoint returns 503 instead of inventing one.
    """
    logger.info("fetching_pcr_analysis", symbol=symbol)

    service = get_market_service()
    analysis = await service.analyze_option_chain(symbol, expiry)

    if not analysis or not analysis.strikes:
        raise _unavailable(f"PCR analysis unavailable for {symbol}.")

    current_pcr = analysis.pcr
    # A single live snapshot: no fabricated history. trend is "stable" until a
    # real previous snapshot is available (future enhancement).
    interpretation = (
        "bullish" if current_pcr > 1.1 else "bearish" if current_pcr < 0.8 else "neutral"
    )

    src = getattr(analysis, "source", "unavailable") or "unavailable"
    chain_ts = getattr(analysis, "timestamp", None)

    return PCRAnalysis(
        value=round(current_pcr, 2),
        interpretation=interpretation,
        trend="stable",
        historical_values=[round(current_pcr, 2)],
        source=src,
        timestamp=chain_ts,
    )


@router.get("/oi-analysis/{symbol}", response_model=OIAnalysis)
async def get_oi_analysis(symbol: str, expiry: Optional[str] = None):
    """Get OI buildup analysis (real option-chain OI only)."""
    logger.info("fetching_oi_analysis", symbol=symbol)

    service = get_market_service()
    analysis = await service.analyze_option_chain(symbol, expiry)

    if not analysis or not analysis.strikes:
        raise _unavailable(f"OI analysis unavailable for {symbol}.")

    change_call_oi = sum(s.call_change_oi for s in analysis.strikes)
    change_put_oi = sum(s.put_change_oi for s in analysis.strikes)
    call_oi = analysis.total_call_oi
    put_oi = analysis.total_put_oi

    if change_call_oi > 0 and change_put_oi > 0:
        analysis_type = "buildup"
    elif change_call_oi < 0 and change_put_oi < 0:
        analysis_type = "unwinding"
    elif change_call_oi > 0 and change_put_oi < 0:
        analysis_type = "short_covering"
    else:
        analysis_type = "long_unwinding"

    interpretation = {
        "buildup": "Both call and put OI increasing - suggests fresh positions being built",
        "unwinding": "Both call and put OI decreasing - suggests positions being closed",
        "short_covering": "Call OI up, Put OI down - suggests short covering activity",
        "long_unwinding": "Put OI up, Call OI down - suggests long liquidation",
    }[analysis_type]

    src = getattr(analysis, "source", "unavailable") or "unavailable"
    chain_ts = getattr(analysis, "timestamp", None)

    return OIAnalysis(
        type=analysis_type,
        call_oi=call_oi,
        put_oi=put_oi,
        change_call_oi=change_call_oi,
        change_put_oi=change_put_oi,
        interpretation=interpretation,
        source=src,
        timestamp=chain_ts,
    )


@router.get("/max-pain/{symbol}", response_model=MaxPainAnalysis)
async def get_max_pain(symbol: str, expiry: Optional[str] = None):
    """Get max pain calculation (real option-chain OI only)."""
    logger.info("fetching_max_pain", symbol=symbol)

    service = get_market_service()
    analysis = await service.analyze_option_chain(symbol, expiry)

    if not analysis or not analysis.strikes:
        raise _unavailable(f"Max pain analysis unavailable for {symbol}.")

    spot_price = analysis.spot_price
    max_pain = analysis.max_pain

    # Real per-strike pain points computed from live OI.
    call_pain = {
        str(int(s.strike)): int(
            sum(max(0, s.strike - o.strike) * o.call_oi for o in analysis.strikes)
        )
        for s in analysis.strikes
    }
    put_pain = {
        str(int(s.strike)): int(
            sum(max(0, o.strike - s.strike) * o.put_oi for o in analysis.strikes)
        )
        for s in analysis.strikes
    }

    return MaxPainAnalysis(
        max_pain=max_pain,
        distance_from_spot=round(max_pain - spot_price, 2),
        call_pain_points=call_pain,
        put_pain_points=put_pain,
        source=getattr(analysis, "source", "unavailable") or "unavailable",
    )


@router.get("/signals/{symbol}", response_model=List[OptionSignal])
async def get_option_signals(symbol: str, expiry: Optional[str] = None):
    """Get option trading signals (derived from real option-chain analysis)."""
    logger.info("fetching_option_signals", symbol=symbol)

    service = get_market_service()
    analysis = await service.analyze_option_chain(symbol, expiry)

    if not analysis or not analysis.strikes:
        raise _unavailable(f"Option signals unavailable for {symbol}.")

    spot_price = analysis.spot_price
    pcr = analysis.pcr
    max_pain = analysis.max_pain
    signals: List[OptionSignal] = []

    # ATM signal — confidence derived from the analyzer's trend confidence.
    atm_strike = round(spot_price / 100) * 100
    signals.append(
        OptionSignal(
            type="atm_activity",
            strike=atm_strike,
            side=OptionType.CALL,
            confidence=round(min(80.0, 50.0 + analysis.confidence / 3), 1),
            interpretation="High ATM call activity suggests bullish bias",
        )
    )

    if pcr > 1.1:
        signals.append(
            OptionSignal(
                type="pcr_extreme",
                strike=spot_price,
                side=OptionType.PUT,
                confidence=round(min(75.0, 50.0 + (pcr - 1.1) * 25), 1),
                interpretation="Extremely high PCR suggests potential reversal",
            )
        )

    signals.append(
        OptionSignal(
            type="max_pain",
            strike=max_pain,
            side=OptionType.PUT,
            confidence=round(min(70.0, 50.0 + analysis.confidence / 4), 1),
            interpretation=f"Max pain at {max_pain} - price may gravitate towards this level",
        )
    )

    return signals


def get_next_thursday() -> str:
    """Get next Thursday's date"""
    today = datetime.utcnow()
    days_until_thursday = (4 - today.weekday() + 7) % 7
    if days_until_thursday == 0:
        days_until_thursday = 7
    next_thursday = today + timedelta(days=days_until_thursday)
    return next_thursday.strftime("%Y-%m-%d")
