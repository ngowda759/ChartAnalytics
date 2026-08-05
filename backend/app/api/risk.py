from fastapi import APIRouter, Query
from typing import Optional
import random
import structlog

from app.schemas.risk import (
    PositionSizeRequest,
    PositionSizeResponse,
    RiskCalculation,
    DailyLimit,
)

logger = structlog.get_logger()
router = APIRouter()


@router.post("/position-size", response_model=PositionSizeResponse)
async def calculate_position_size(data: PositionSizeRequest):
    """Calculate position size based on risk parameters"""
    logger.info("calculating_position_size")
    
    # Position size formula: (Account * Risk%) / (Entry - SL)
    risk_amount = data.account_size * (data.risk_percent / 100)
    price_difference = abs(data.entry_price - data.stop_loss)
    
    if price_difference == 0:
        return PositionSizeResponse(
            quantity=0,
            risk_amount=0,
            capital_required=0,
            risk_percent=0,
        )
    
    quantity = int(risk_amount / price_difference)
    capital_required = quantity * data.entry_price
    
    return PositionSizeResponse(
        quantity=quantity,
        risk_amount=round(risk_amount, 2),
        capital_required=round(capital_required, 2),
        risk_percent=data.risk_percent,
    )


@router.get("/risk-calculation", response_model=RiskCalculation)
async def calculate_risk(
    entry_price: float = Query(...),
    stop_loss: float = Query(...),
    target: float = Query(...),
    quantity: int = Query(...),
    trade_type: str = Query("long", description="long or short"),
):
    """Calculate complete risk metrics for a trade"""
    logger.info("calculating_risk")
    
    if trade_type.lower() == "long":
        max_loss = (entry_price - stop_loss) * quantity
        max_profit = (target - entry_price) * quantity
        breakeven = entry_price
    else:
        max_loss = (stop_loss - entry_price) * quantity
        max_profit = (entry_price - target) * quantity
        breakeven = entry_price
    
    return RiskCalculation(
        position_size={
            "quantity": quantity,
            "risk_amount": round(abs(max_loss), 2),
            "capital_required": round(entry_price * quantity, 2),
            "risk_percent": round(abs(max_loss) / (entry_price * quantity) * 100, 2),
        },
        max_loss=round(max_loss, 2),
        max_profit=round(max_profit, 2),
        breakeven=round(breakeven, 2),
    )


@router.get("/daily-limit", response_model=DailyLimit)
async def get_daily_limit(user_id: str = "user_1"):
    """Get current daily loss limit status"""
    logger.info("fetching_daily_limit", user_id=user_id)
    
    max_loss = 5000
    current_loss = random.uniform(0, max_loss * 0.8)
    
    return DailyLimit(
        date=datetime.utcnow(),
        max_loss=max_loss,
        current_loss=round(current_loss, 2),
        remaining_loss=round(max_loss - current_loss, 2),
        is_limit_hit=current_loss >= max_loss,
    )


from datetime import datetime
