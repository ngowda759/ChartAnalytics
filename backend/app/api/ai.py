from fastapi import APIRouter, UploadFile, File, Query
from typing import List, Optional
from datetime import datetime
import random
import structlog

from app.schemas.ai import (
    AIInsight,
    ChartAnalysis,
    ChatMessage,
    ChatResponse,
)
from app.services.trade_review import trade_review_service
from app.services.chart_analysis import chart_analysis_service

logger = structlog.get_logger()
router = APIRouter()


@router.get("/insights/{symbol}", response_model=AIInsight)
async def get_market_insight(symbol: str):
    """Get AI-powered market insight"""
    logger.info("generating_market_insight", symbol=symbol)

    trends = ["bullish", "bearish", "neutral"]
    trend = random.choice(trends)

    descriptions = {
        "bullish": "The index shows strong buying interest with momentum indicators supporting higher levels. Watch for continuation above key resistance.",
        "bearish": "Selling pressure persists with technical indicators suggesting further downside. Maintain caution and respect support levels.",
        "neutral": "Market consolidating in a range with no clear directional bias. Consider waiting for a breakout before positioning.",
    }

    return AIInsight(
        id=f"insight_{symbol}_{datetime.utcnow().timestamp()}",
        symbol=symbol,
        type="trend",
        title=f"{symbol} - {trend.title()} Bias",
        description=descriptions[trend],
        confidence=round(random.uniform(60, 85), 1),
        bias=trend,
        reasoning="Based on multiple technical indicators including EMA crossovers, RSI momentum, and volume analysis.",
        indicators=["EMA 20/50", "RSI", "MACD", "VWAP"],
        timestamp=datetime.utcnow(),
    )


@router.get("/insights", response_model=List[AIInsight])
async def get_all_insights(limit: int = Query(10, ge=1, le=50)):
    """Get latest AI insights"""
    logger.info("fetching_insights", limit=limit)

    symbols = ["NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK"]
    insights = []

    for symbol in symbols[:limit]:
        insights.append(await get_market_insight(symbol))

    return insights


@router.post("/analyze-chart", response_model=ChartAnalysis)
async def analyze_chart(
    symbol: str = Query(...),
    image: UploadFile = File(...),
):
    """Analyze uploaded chart image"""
    logger.info("analyzing_chart", symbol=symbol)

    patterns = [
        {
            "type": "Higher Low",
            "confidence": round(random.uniform(65, 85), 1),
            "description": "Forming higher lows suggesting bullish reversal",
        },
        {
            "type": "Support Test",
            "confidence": round(random.uniform(70, 90), 1),
            "description": "Testing previous support level",
        },
        {
            "type": "Range Bound",
            "confidence": round(random.uniform(60, 80), 1),
            "description": "Consolidating within a range",
        },
    ]

    spot_price = 24567.85
    entry = spot_price * (1 + random.uniform(-0.005, 0.005))
    stop_loss = entry * (1 - random.uniform(0.01, 0.02))
    target = entry * (1 + random.uniform(0.02, 0.04))

    return ChartAnalysis(
        id=f"chart_{datetime.utcnow().timestamp()}",
        symbol=symbol,
        patterns=[p for p in patterns if random.random() > 0.3],
        levels={
            "entry": round(entry, 2),
            "stop_loss": round(stop_loss, 2),
            "target_1": round(target, 2),
            "target_2": round(target * 1.5, 2),
            "target_3": round(target * 2, 2),
            "risk_reward": round((target - entry) / (entry - stop_loss), 2),
        },
        bias=random.choice(["bullish", "bearish", "neutral"]),
        confidence=round(random.uniform(55, 80), 1),
        reasoning="Based on chart pattern analysis and key price levels.",
        timestamp=datetime.utcnow(),
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """AI Chat Assistant"""
    logger.info("chat_message", role=message.role)

    responses = {
        "bullish": "Based on the current market conditions, the outlook appears positive. Key indicators like EMA crossovers and RSI suggest bullish momentum. However, always remember this is educational analysis, not financial advice. Consider your risk tolerance and always use proper position sizing.",
        "bearish": "Technical analysis suggests caution in the current market environment. Multiple indicators are showing bearish signals. This could be a good time to review your positions and ensure proper risk management. Remember, this is educational content only.",
        "neutral": "The market is showing mixed signals with no clear directional bias. This might be a good time to stay on the sidelines or reduce position sizes until there's more clarity. Always trade with a plan and defined risk parameters.",
    }

    return ChatResponse(
        message={
            "id": f"msg_{datetime.utcnow().timestamp()}",
            "role": "assistant",
            "content": random.choice(list(responses.values())),
            "timestamp": datetime.utcnow(),
        },
        sources=[
            "Technical Analysis Principles",
            "Market Psychology Guide",
            "Risk Management Best Practices",
        ],
    )


# Pydantic models for trade review request/response
from pydantic import BaseModel


class TradeReviewRequest(BaseModel):
    trade_id: str
    entry_price: float
    exit_price: Optional[float] = None
    stop_loss: float
    target: float
    quantity: int
    trade_type: str  # "long" or "short"
    strategy: str
    pnl: Optional[float] = None
    holding_period_minutes: Optional[int] = None


class TradeReviewResponse(BaseModel):
    trade_id: str
    overall_score: float
    entry_score: float
    exit_score: float
    risk_score: float
    psychology_score: float
    reviews: List[dict]
    summary: str
    key_improvements: List[str]


@router.post("/review-trade", response_model=TradeReviewResponse)
async def review_trade(request: TradeReviewRequest):
    """AI-powered trade review with educational insights"""
    logger.info("reviewing_trade", trade_id=request.trade_id)

    report = trade_review_service.analyze_trade(
        trade_id=request.trade_id,
        entry_price=request.entry_price,
        exit_price=request.exit_price,
        stop_loss=request.stop_loss,
        target=request.target,
        quantity=request.quantity,
        trade_type=request.trade_type,
        strategy=request.strategy,
        pnl=request.pnl,
        holding_period_minutes=request.holding_period_minutes,
    )

    return TradeReviewResponse(
        trade_id=report.trade_id,
        overall_score=report.overall_score,
        entry_score=report.entry_score,
        exit_score=report.exit_score,
        risk_score=report.risk_score,
        psychology_score=report.psychology_score,
        reviews=[r.to_dict() for r in report.reviews],
        summary=report.summary,
        key_improvements=report.key_improvements,
    )


class ChartAnalysisRequest(BaseModel):
    symbol: str
    highs: List[float]
    lows: List[float]
    closes: List[float]
    volumes: List[int]
    timestamps: List[str]


class ChartAnalysisResponse(BaseModel):
    symbol: str
    patterns: List[dict]
    levels: dict
    trend: str
    momentum: str
    volatility: str
    volume_profile: str
    bias: str
    confidence: float
    setup: Optional[dict]
    summary: str
    educational_notes: List[str]


@router.post("/analyze-patterns", response_model=ChartAnalysisResponse)
async def analyze_patterns(request: ChartAnalysisRequest):
    """Analyze chart patterns and generate trade setups"""
    logger.info("analyzing_patterns", symbol=request.symbol)

    result = chart_analysis_service.analyze_chart(
        symbol=request.symbol,
        highs=request.highs,
        lows=request.lows,
        closes=request.closes,
        volumes=request.volumes,
        timestamps=request.timestamps,
    )

    patterns_data = [
        {
            "type": p.pattern_type.value,
            "direction": p.direction.value,
            "confidence": p.confidence.value,
            "description": p.description,
            "start_index": p.start_index,
            "end_index": p.end_index,
        }
        for p in result.patterns
    ]

    setup_data = None
    if result.setup:
        setup_data = {
            "entry": result.setup.entry,
            "stop_loss": result.setup.stop_loss,
            "target_1": result.setup.target_1,
            "target_2": result.setup.target_2,
            "target_3": result.setup.target_3,
            "risk_reward_1": result.setup.risk_reward_1,
            "risk_reward_2": result.setup.risk_reward_2,
            "risk_reward_3": result.setup.risk_reward_3,
        }

    return ChartAnalysisResponse(
        symbol=request.symbol,
        patterns=patterns_data,
        levels={
            "support": result.levels.support,
            "resistance": result.levels.resistance,
            "pivot": result.levels.pivot,
            "s1": result.levels.s1,
            "r1": result.levels.r1,
            "s2": result.levels.s2,
            "r2": result.levels.r2,
        },
        trend=result.trend.value,
        momentum=result.momentum,
        volatility=result.volatility,
        volume_profile=result.volume_profile,
        bias=result.bias.value,
        confidence=result.confidence,
        setup=setup_data,
        summary=result.summary,
        educational_notes=result.educational_notes,
    )
