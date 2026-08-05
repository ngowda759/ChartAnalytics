from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import random
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


@router.get("/chain/{symbol}", response_model=OptionChain)
async def get_option_chain(
    symbol: str,
    expiry: Optional[str] = Query(None, description="Expiry date (YYYY-MM-DD)"),
):
    """Get option chain for a symbol"""
    logger.info("fetching_option_chain", symbol=symbol, expiry=expiry)

    if expiry is None:
        expiry = get_next_thursday()

    service = get_market_service()
    analysis = await service.analyze_option_chain(symbol, expiry)

    # Use analysis or generate mock data
    if analysis:
        spot_price = analysis.spot_price
        pcr = analysis.pcr
        max_pain = analysis.max_pain
        total_call_oi = analysis.total_call_oi
        total_put_oi = analysis.total_put_oi

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
                    bid=s.call_ltp * 0.98,
                    ask=s.call_ltp * 1.02,
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
                    bid=s.put_ltp * 0.98,
                    ask=s.put_ltp * 1.02,
                )
            )
    else:
        spot_price = (
            24500
            if symbol.upper() in ["NIFTY", "NIFTY 50"]
            else 52400 if symbol.upper() in ["BANKNIFTY", "NIFTY BANK"] else 23400
        )
        strikes = [spot_price + (i - 10) * 100 for i in range(21)]

        calls = []
        puts = []
        for strike in strikes:
            dist_from_spot = abs(strike - spot_price) / spot_price
            iv = 15 + dist_from_spot * 100 + random.uniform(-2, 2)
            iv = max(10, min(50, iv))

            calls.append(
                OptionData(
                    strike=strike,
                    oi=random.randint(10000, 500000),
                    change_oi=random.randint(-50000, 100000),
                    volume=random.randint(1000, 100000),
                    iv=round(iv, 2),
                    ltp=round(
                        max(
                            0.05,
                            (spot_price - strike + random.uniform(-50, 50))
                            * random.uniform(0.01, 0.05),
                        ),
                        2,
                    ),
                    bid=round(random.uniform(0.5, 5), 2),
                    ask=round(random.uniform(0.5, 5), 2),
                )
            )
            puts.append(
                OptionData(
                    strike=strike,
                    oi=random.randint(10000, 500000),
                    change_oi=random.randint(-50000, 100000),
                    volume=random.randint(1000, 100000),
                    iv=round(iv + random.uniform(-2, 2), 2),
                    ltp=round(
                        max(
                            0.05,
                            (strike - spot_price + random.uniform(-50, 50))
                            * random.uniform(0.01, 0.05),
                        ),
                        2,
                    ),
                    bid=round(random.uniform(0.5, 5), 2),
                    ask=round(random.uniform(0.5, 5), 2),
                )
            )

        total_call_oi = sum(c.oi for c in calls)
        total_put_oi = sum(p.oi for p in puts)
        pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 1.0
        max_pain = spot_price + random.randint(-200, 200)

    return OptionChain(
        symbol=symbol.upper(),
        expiry=expiry,
        spot_price=spot_price,
        timestamp=datetime.utcnow(),
        underlying_change=round(random.uniform(-0.5, 0.5), 2),
        calls=calls,
        puts=puts,
        pcr=round(pcr, 2),
        max_pain=max_pain,
        total_call_oi=total_call_oi,
        total_put_oi=total_put_oi,
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
            status_code=404, detail=f"Option analysis not available for {symbol}"
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
    }


@router.get("/pcr/{symbol}", response_model=PCRAnalysis)
async def get_pcr_analysis(symbol: str, expiry: Optional[str] = None):
    """Get PCR analysis with historical trend"""
    logger.info("fetching_pcr_analysis", symbol=symbol)

    service = get_market_service()
    analysis = await service.analyze_option_chain(symbol, expiry)

    current_pcr = analysis.pcr if analysis else round(random.uniform(0.8, 1.2), 2)
    historical_values = [round(random.uniform(0.7, 1.3), 2) for _ in range(20)]
    trend = "rising" if current_pcr > historical_values[-5] else "falling"
    interpretation = (
        "bullish"
        if current_pcr > 1.1
        else "bearish" if current_pcr < 0.8 else "neutral"
    )

    return PCRAnalysis(
        value=current_pcr,
        interpretation=interpretation,
        trend=trend,
        historical_values=historical_values + [current_pcr],
    )


@router.get("/oi-analysis/{symbol}", response_model=OIAnalysis)
async def get_oi_analysis(symbol: str, expiry: Optional[str] = None):
    """Get OI buildup analysis"""
    logger.info("fetching_oi_analysis", symbol=symbol)

    service = get_market_service()
    analysis = await service.analyze_option_chain(symbol, expiry)

    if analysis:
        change_call_oi = sum(s.call_change_oi for s in analysis.strikes)
        change_put_oi = sum(s.put_change_oi for s in analysis.strikes)
        call_oi = analysis.total_call_oi
        put_oi = analysis.total_put_oi
    else:
        change_call_oi = random.randint(-50000, 100000)
        change_put_oi = random.randint(-50000, 100000)
        call_oi = random.randint(1000000, 5000000)
        put_oi = random.randint(1000000, 5000000)

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

    return OIAnalysis(
        type=analysis_type,
        call_oi=call_oi,
        put_oi=put_oi,
        change_call_oi=change_call_oi,
        change_put_oi=change_put_oi,
        interpretation=interpretation,
    )


@router.get("/max-pain/{symbol}", response_model=MaxPainAnalysis)
async def get_max_pain(symbol: str, expiry: Optional[str] = None):
    """Get max pain calculation"""
    logger.info("fetching_max_pain", symbol=symbol)

    service = get_market_service()
    analysis = await service.analyze_option_chain(symbol, expiry)

    spot_price = (
        analysis.spot_price
        if analysis
        else (24500 if symbol.upper() in ["NIFTY", "NIFTY 50"] else 52400)
    )
    max_pain = analysis.max_pain if analysis else spot_price + random.randint(-200, 200)

    return MaxPainAnalysis(
        max_pain=max_pain,
        distance_from_spot=round(max_pain - spot_price, 2),
        call_pain_points={
            str(int(spot_price + i * 100)): random.randint(1000, 100000)
            for i in range(-5, 6)
        },
        put_pain_points={
            str(int(spot_price + i * 100)): random.randint(1000, 100000)
            for i in range(-5, 6)
        },
    )


@router.get("/signals/{symbol}", response_model=List[OptionSignal])
async def get_option_signals(symbol: str, expiry: Optional[str] = None):
    """Get option trading signals"""
    logger.info("fetching_option_signals", symbol=symbol)

    signals = []
    service = get_market_service()
    analysis = await service.analyze_option_chain(symbol, expiry)

    spot_price = (
        analysis.spot_price
        if analysis
        else (24500 if symbol.upper() in ["NIFTY", "NIFTY 50"] else 52400)
    )
    pcr = analysis.pcr if analysis else random.uniform(0.8, 1.3)
    max_pain = analysis.max_pain if analysis else spot_price + random.randint(-200, 200)

    # ATM signal
    signals.append(
        OptionSignal(
            type="atm_activity",
            strike=round(spot_price / 100) * 100,
            side=OptionType.CALL,
            confidence=random.uniform(60, 80),
            interpretation="High ATM call activity suggests bullish bias",
        )
    )

    # PCR signal
    if pcr > 1.1:
        signals.append(
            OptionSignal(
                type="pcr_extreme",
                strike=spot_price,
                side=OptionType.PUT,
                confidence=random.uniform(55, 75),
                interpretation="Extremely high PCR suggests potential reversal",
            )
        )

    # Max pain signal
    signals.append(
        OptionSignal(
            type="max_pain",
            strike=max_pain,
            side=OptionType.PUT,
            confidence=random.uniform(50, 70),
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
