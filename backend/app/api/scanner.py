from fastapi import APIRouter, Query
from typing import List, Optional
from datetime import datetime
import random
import structlog

from app.schemas.scanner import (
    ScanResult,
    ScanSummary,
    ScanType,
    SignalDirection,
    ScanFilters,
    BreakoutSignal,
    EMACrossSignal,
    VolumeSignal,
    OISignal,
)

logger = structlog.get_logger()
router = APIRouter()


@router.get("/", response_model=List[ScanResult])
async def scan_market(
    scan_types: Optional[str] = Query(None, description="Comma-separated scan types"),
    min_confidence: float = Query(60.0, ge=0, le=100),
    limit: int = Query(50, ge=1, le=200),
):
    """Scan market for trading opportunities"""
    logger.info("scanning_market", scan_types=scan_types, min_confidence=min_confidence)

    if scan_types:
        types = [ScanType(t.strip()) for t in scan_types.split(",")]
    else:
        types = list(ScanType)

    symbols = [
        {"symbol": "NIFTY", "name": "NIFTY 50", "price": 24567.85},
        {"symbol": "BANKNIFTY", "name": "NIFTY Bank", "price": 52456.70},
        {"symbol": "RELIANCE", "name": "Reliance Industries", "price": 2967.50},
        {"symbol": "HDFCBANK", "name": "HDFC Bank", "price": 1689.30},
        {"symbol": "ICICIBANK", "name": "ICICI Bank", "price": 1124.75},
        {"symbol": "INFOSYS", "name": "Infosys", "price": 1834.20},
        {"symbol": "TCS", "name": "TCS", "price": 4123.45},
        {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "price": 1789.60},
        {"symbol": "SBIN", "name": "State Bank of India", "price": 823.45},
        {"symbol": "BHARTIARTL", "name": "Bharti Airtel", "price": 1456.30},
    ]

    results = []

    for sym in symbols:
        for scan_type in types:
            confidence = random.uniform(55, 95)
            if confidence < min_confidence:
                continue

            direction = random.choice(
                [
                    SignalDirection.BULLISH,
                    SignalDirection.BEARISH,
                    SignalDirection.NEUTRAL,
                ]
            )

            results.append(
                ScanResult(
                    id=f"{sym['symbol']}_{scan_type.value}_{len(results)}",
                    symbol=sym["symbol"],
                    name=sym["name"],
                    scan_type=scan_type,
                    direction=direction,
                    confidence=round(confidence, 1),
                    price=round(sym["price"] * (1 + random.uniform(-0.02, 0.02)), 2),
                    change_percent=round(random.uniform(-3, 3), 2),
                    volume_ratio=round(random.uniform(1.2, 3.5), 2),
                    details={
                        "atr": round(sym["price"] * 0.015, 2),
                        "rsi": round(random.uniform(30, 70), 2),
                        "ema_20": round(
                            sym["price"] * (1 + random.uniform(-0.02, 0.02)), 2
                        ),
                    },
                    timestamp=datetime.utcnow(),
                )
            )

    # Sort by confidence
    results.sort(key=lambda x: x.confidence, reverse=True)

    return results[:limit]


@router.get("/summary", response_model=ScanSummary)
async def get_scan_summary(
    scan_types: Optional[str] = Query(None),
):
    """Get summary of scan results"""
    logger.info("getting_scan_summary")

    results = await scan_market(scan_types=scan_types, limit=100)

    bullish = sum(1 for r in results if r.direction == SignalDirection.BULLISH)
    bearish = sum(1 for r in results if r.direction == SignalDirection.BEARISH)
    neutral = sum(1 for r in results if r.direction == SignalDirection.NEUTRAL)

    by_type = {}
    for r in results:
        by_type[r.scan_type.value] = by_type.get(r.scan_type.value, 0) + 1

    return ScanSummary(
        total_results=len(results),
        bullish_count=bullish,
        bearish_count=bearish,
        neutral_count=neutral,
        top_signals=results[:10],
        by_type=by_type,
    )


@router.get("/breakouts", response_model=List[BreakoutSignal])
async def scan_breakouts(limit: int = Query(20, ge=1, le=50)):
    """Scan for breakout opportunities"""
    logger.info("scanning_breakouts")

    symbols = [
        {"symbol": "RELIANCE", "price": 2967.50},
        {"symbol": "HDFCBANK", "price": 1689.30},
        {"symbol": "ICICIBANK", "price": 1124.75},
        {"symbol": "INFOSYS", "price": 1834.20},
        {"symbol": "TCS", "price": 4123.45},
    ]

    results = []
    for sym in symbols:
        breakout_price = sym["price"] * (1 + random.uniform(0.005, 0.02))
        current_price = sym["price"] * (1 + random.uniform(-0.01, 0.01))

        results.append(
            BreakoutSignal(
                symbol=sym["symbol"],
                type=random.choice(["resistance", "support"]),
                breakout_price=round(breakout_price, 2),
                current_price=round(current_price, 2),
                distance_percent=round(
                    ((current_price - breakout_price) / breakout_price) * 100, 2
                ),
                volume_ratio=round(random.uniform(1.5, 3.0), 2),
                atr=round(sym["price"] * 0.015, 2),
                confidence=round(random.uniform(60, 85), 1),
            )
        )

    return sorted(results, key=lambda x: x.confidence, reverse=True)[:limit]


@router.get("/ema-crosses", response_model=List[EMACrossSignal])
async def scan_ema_crosses(limit: int = Query(20, ge=1, le=50)):
    """Scan for EMA crossover signals"""
    logger.info("scanning_ema_crosses")

    symbols = [
        {"symbol": "NIFTY", "price": 24567.85},
        {"symbol": "BANKNIFTY", "price": 52456.70},
        {"symbol": "RELIANCE", "price": 2967.50},
        {"symbol": "HDFCBANK", "price": 1689.30},
    ]

    results = []
    for sym in symbols:
        fast_ema = sym["price"] * (1 + random.uniform(-0.01, 0.01))
        slow_ema = sym["price"] * (1 + random.uniform(-0.02, 0.02))

        results.append(
            EMACrossSignal(
                symbol=sym["symbol"],
                cross_type=random.choice(["golden_cross", "death_cross"]),
                fast_ema=round(fast_ema, 2),
                slow_ema=round(slow_ema, 2),
                price=round(sym["price"], 2),
                distance_from_cross=round(random.uniform(-1, 1), 2),
                rsi=round(random.uniform(40, 65), 2),
                volume_ratio=round(random.uniform(1.2, 2.5), 2),
                confidence=round(random.uniform(55, 80), 1),
            )
        )

    return sorted(results, key=lambda x: x.confidence, reverse=True)[:limit]


@router.get("/volume", response_model=List[VolumeSignal])
async def scan_volume_spikes(limit: int = Query(20, ge=1, le=50)):
    """Scan for unusual volume activity"""
    logger.info("scanning_volume_spikes")

    symbols = [
        {"symbol": "RELIANCE", "price": 2967.50},
        {"symbol": "TATASTEEL", "price": 156.80},
        {"symbol": "ADANIPORTS", "price": 1289.45},
        {"symbol": "SBIN", "price": 823.45},
        {"symbol": "BHARTIARTL", "price": 1456.30},
    ]

    results = []
    for sym in symbols:
        avg_volume = random.randint(5000000, 20000000)
        current_volume = int(avg_volume * random.uniform(1.5, 4.0))

        results.append(
            VolumeSignal(
                symbol=sym["symbol"],
                type=random.choice(["spike_up", "spike_down"]),
                current_volume=current_volume,
                avg_volume=avg_volume,
                volume_ratio=round(current_volume / avg_volume, 2),
                price_change=round(random.uniform(-3, 3), 2),
                delivery_percent=round(random.uniform(50, 85), 2),
                confidence=round(random.uniform(60, 85), 1),
            )
        )

    return sorted(results, key=lambda x: x.volume_ratio, reverse=True)[:limit]


@router.get("/oi-buildup", response_model=List[OISignal])
async def scan_oi_buildup(limit: int = Query(20, ge=1, le=50)):
    """Scan for OI buildup"""
    logger.info("scanning_oi_buildup")

    symbols = [
        {"symbol": "NIFTY", "price": 24567.85},
        {"symbol": "BANKNIFTY", "price": 52456.70},
        {"symbol": "RELIANCE", "price": 2967.50},
        {"symbol": "HDFCBANK", "price": 1689.30},
    ]

    results = []
    for sym in symbols:
        change_call = random.randint(-50000, 100000)
        change_put = random.randint(-50000, 100000)

        if change_call > 0 and change_put > 0:
            oi_type = "buildup"
        elif change_call < 0 and change_put < 0:
            oi_type = "unwinding"
        else:
            oi_type = random.choice(["buildup", "unwinding"])

        results.append(
            OISignal(
                symbol=sym["symbol"],
                type=oi_type,
                change_call_oi=change_call,
                change_put_oi=change_put,
                price_change=round(random.uniform(-2, 2), 2),
                pcr=round(random.uniform(0.7, 1.3), 2),
                interpretation=(
                    "Bullish buildup" if change_call > change_put else "Bearish buildup"
                ),
                confidence=round(random.uniform(55, 80), 1),
            )
        )

    return sorted(results, key=lambda x: x.confidence, reverse=True)[:limit]
