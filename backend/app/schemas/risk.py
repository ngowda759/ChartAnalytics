from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict


class PositionSizeRequest(BaseModel):
    account_size: float = Field(..., gt=0)
    risk_percent: float = Field(..., gt=0, le=100)
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    instrument: str = "equity"  # "equity", "futures", "options"


class PositionSizeResponse(BaseModel):
    quantity: int
    risk_amount: float
    capital_required: float
    risk_percent: float


class RiskCalculation(BaseModel):
    position_size: Dict[str, float]
    max_loss: float
    max_profit: float
    breakeven: float


class DailyLimit(BaseModel):
    date: datetime
    max_loss: float
    current_loss: float
    remaining_loss: float
    is_limit_hit: bool
