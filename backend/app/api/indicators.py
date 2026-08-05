from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
import structlog

from app.schemas.indicators import (
    TechnicalIndicators,
    EMAData,
    MACDData,
    RSIData,
    SupertrendData,
    BollingerBandsData,
    ATRData,
    ADXData,
    VWAPData,
    TrendDirection,
    IndicatorHistoryResponse,
    IndicatorHistory,
)
from app.services.market_service import get_market_service
from app.services.indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_macd,
    calculate_adx,
    calculate_bollinger_bands,
    calculate_atr,
    calculate_vwap,
    calculate_supertrend,
    interpret_rsi,
    get_trend_direction,
)

logger = structlog.get_logger()
router = APIRouter()


@router.get("/{symbol}", response_model=TechnicalIndicators)
async def get_indicators(symbol: str):
    """Get all technical indicators for a symbol"""
    logger.info("calculating_indicators", symbol=symbol)

    service = get_market_service()
    ohlc = await service.get_ohlc(symbol, "1d", 200)

    if not ohlc or len(ohlc) < 200:
        raise HTTPException(status_code=404, detail="Insufficient data for analysis")

    closes = [c.close for c in ohlc]
    highs = [c.high for c in ohlc]
    lows = [c.low for c in ohlc]
    volumes = [c.volume for c in ohlc]

    current_price = closes[-1]

    # EMA
    ema20_list = calculate_ema(closes, 20)
    ema50_list = calculate_ema(closes, 50)
    ema200_list = calculate_ema(closes, 200)

    ema20 = ema20_list[-1] if ema20_list and ema20_list[-1] else current_price
    ema50 = ema50_list[-1] if ema50_list and ema50_list[-1] else current_price
    ema200 = ema200_list[-1] if ema200_list and ema200_list[-1] else current_price

    ema_trend = get_trend_direction(ema20, ema50, ema200, current_price)

    # RSI
    rsi_list = calculate_rsi(closes, 14)
    rsi_value = rsi_list[-1] if rsi_list and rsi_list[-1] else 50
    rsi_signal = interpret_rsi(rsi_value)

    # MACD
    macd_line, signal_line, histogram = calculate_macd(closes)
    macd_value = macd_line[-1] if macd_line and macd_line[-1] else 0
    signal_value = signal_line[-1] if signal_line and signal_line[-1] else 0
    histogram_value = histogram[-1] if histogram and histogram[-1] else 0

    # Bollinger Bands
    bb_data = calculate_bollinger_bands(closes, 20, 2.0)
    bb = bb_data[-1] if bb_data and bb_data[-1] else None

    # VWAP
    vwap_values = calculate_vwap(highs, lows, closes, volumes)
    vwap = vwap_values[-1] if vwap_values and vwap_values[-1] else current_price

    # Supertrend
    st_data = calculate_supertrend(highs, lows, closes, 10, 3.0)
    st = st_data[-1] if st_data and st_data[-1] else None

    # ADX
    adx_data = calculate_adx(highs, lows, closes, 14)
    adx = adx_data[-1] if adx_data and adx_data[-1] else None

    # ATR
    atr_list = calculate_atr(highs, lows, closes, 14)
    atr_value = atr_list[-1] if atr_list and atr_list[-1] else 0

    return TechnicalIndicators(
        symbol=symbol,
        price=current_price,
        ema=EMAData(
            ema_20=round(ema20, 2),
            ema_50=round(ema50, 2),
            ema_200=round(ema200, 2),
            trend=TrendDirection(ema_trend),
        ),
        rsi=RSIData(
            value=round(rsi_value, 2),
            signal=rsi_signal.signal,
            overbought=rsi_value >= 70,
            oversold=rsi_value <= 30,
        ),
        macd=MACDData(
            macd=round(macd_value, 4),
            signal_line=round(signal_value, 4),
            histogram=round(histogram_value, 4),
        ),
        bollinger=(
            BollingerBandsData(
                upper=round(bb.upper, 2) if bb else current_price * 1.02,
                middle=round(bb.middle, 2) if bb else current_price,
                lower=round(bb.lower, 2) if bb else current_price * 0.98,
                bandwidth=round(bb.bandwidth, 2) if bb else 4.0,
                percent_b=round(bb.percent_b, 4) if bb else 0.5,
            )
            if bb
            else BollingerBandsData(
                upper=current_price * 1.02,
                middle=current_price,
                lower=current_price * 0.98,
                bandwidth=4.0,
                percent_b=0.5,
            )
        ),
        vwap=VWAPData(
            value=round(vwap, 2),
            position="above" if current_price > vwap else "below",
        ),
        supertrend=(
            SupertrendData(
                value=round(st.value, 2) if st else current_price,
                trend="up" if st and st.trend == "up" else "down",
                reversal=st.reversal if st else False,
            )
            if st
            else SupertrendData(value=current_price, trend="up", reversal=False)
        ),
        adx=(
            ADXData(
                adx=round(adx.adx, 2) if adx else 25,
                plus_di=round(adx.plus_di, 2) if adx else 15,
                minus_di=round(adx.minus_di, 2) if adx else 15,
                trend_strength=adx.trend_strength if adx else "moderate",
            )
            if adx
            else ADXData(adx=25, plus_di=15, minus_di=15, trend_strength="moderate")
        ),
        atr=ATRData(
            value=round(atr_value, 2),
            normalized=(
                round(atr_value / current_price * 100, 2) if current_price > 0 else 0
            ),
        ),
    )


@router.get("/history/{symbol}")
async def get_indicator_history(
    symbol: str,
    indicator: str = Query(
        ..., description="Indicator name (ema, rsi, macd, adx, bollinger, atr, vwap)"
    ),
    period: int = Query(20, ge=5, le=200),
):
    """Get historical values of a specific indicator"""
    logger.info("fetching_indicator_history", symbol=symbol, indicator=indicator)

    service = get_market_service()
    ohlc = await service.get_ohlc(symbol, "1d", 300)

    if not ohlc or len(ohlc) < period:
        raise HTTPException(status_code=404, detail="Insufficient data")

    closes = [c.close for c in ohlc]
    highs = [c.high for c in ohlc]
    lows = [c.low for c in ohlc]
    volumes = [c.volume for c in ohlc]

    values = []
    timestamps = [c.timestamp for c in ohlc]

    if indicator == "ema":
        ema_values = calculate_ema(closes, period)
        values = [{"value": round(v, 2) if v else None} for v in ema_values]
    elif indicator == "rsi":
        rsi_values = calculate_rsi(closes, period)
        values = [{"value": round(v, 2) if v else None} for v in rsi_values]
    elif indicator == "macd":
        macd_line, signal_line, histogram = calculate_macd(closes)
        for i in range(len(macd_line)):
            values.append(
                {
                    "macd": round(macd_line[i], 4) if macd_line[i] else None,
                    "signal": round(signal_line[i], 4) if signal_line[i] else None,
                    "histogram": round(histogram[i], 4) if histogram[i] else None,
                }
            )
    elif indicator == "bollinger":
        bb_data = calculate_bollinger_bands(closes, period, 2.0)
        values = [
            {
                "upper": round(bb.upper, 2) if bb else None,
                "middle": round(bb.middle, 2) if bb else None,
                "lower": round(bb.lower, 2) if bb else None,
            }
            for bb in bb_data
        ]
    elif indicator == "atr":
        atr_values = calculate_atr(highs, lows, closes, period)
        values = [{"value": round(v, 2) if v else None} for v in atr_values]
    elif indicator == "vwap":
        vwap_values = calculate_vwap(highs, lows, closes, volumes)
        values = [{"value": round(v, 2) if v else None} for v in vwap_values]
    elif indicator == "adx":
        adx_data = calculate_adx(highs, lows, closes, period)
        values = [
            {
                "adx": round(adx.adx, 2) if adx else None,
                "plus_di": round(adx.plus_di, 2) if adx else None,
                "minus_di": round(adx.minus_di, 2) if adx else None,
            }
            for adx in adx_data
        ]
    else:
        raise HTTPException(status_code=400, detail=f"Unknown indicator: {indicator}")

    return IndicatorHistoryResponse(
        symbol=symbol,
        indicator=indicator,
        period=period,
        values=values[: len(timestamps)],
        timestamps=timestamps,
    )


@router.get("/analysis/{symbol}")
async def get_ai_analysis(symbol: str):
    """Get AI-powered complete technical analysis"""
    logger.info("generating_ai_analysis", symbol=symbol)

    service = get_market_service()
    insight = await service.get_market_insight(symbol)

    if not insight:
        raise HTTPException(status_code=404, detail="Unable to generate analysis")

    return {
        "symbol": insight.symbol,
        "timestamp": insight.timestamp.isoformat(),
        "trend": insight.trend,
        "momentum": insight.momentum,
        "sentiment": insight.sentiment,
        "confidence": insight.confidence,
        "breakout_probability": insight.breakout_probability,
        "summary": insight.summary,
        "recommendation": insight.recommendation,
        "signals": [
            {
                "indicator": s.indicator,
                "value": s.value,
                "signal": s.signal,
                "strength": s.strength,
                "message": s.message,
            }
            for s in insight.signals
        ],
        "support_levels": [
            {"price": s.price, "strength": s.strength} for s in insight.support_levels
        ],
        "resistance_levels": [
            {"price": s.price, "strength": s.strength}
            for s in insight.resistance_levels
        ],
        "risk_factors": insight.risk_factors,
        "key_observations": insight.key_observations,
    }
