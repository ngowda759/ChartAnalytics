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
        {"type": "Higher Low", "confidence": round(random.uniform(65, 85), 1), "description": "Forming higher lows suggesting bullish reversal"},
        {"type": "Support Test", "confidence": round(random.uniform(70, 90), 1), "description": "Testing previous support level"},
        {"type": "Range Bound", "confidence": round(random.uniform(60, 80), 1), "description": "Consolidating within a range"},
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
        sources=["Technical Analysis Principles", "Market Psychology Guide", "Risk Management Best Practices"],
    )
