from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class AlertType(str, Enum):
    EMA_CROSS = "ema_cross"
    VWAP_CROSS = "vwap_cross"
    BREAKOUT = "breakout"
    OI_SPIKE = "oi_spike"
    PCR_SHIFT = "pcr_shift"
    VOLUME_SPIKE = "volume_spike"
    PRICE_ALERT = "price_alert"


class Alert(BaseModel):
    id: str
    user_id: str
    type: AlertType
    symbol: str
    condition: str  # "above", "below", "crosses_above", "crosses_below"
    value: float
    is_active: bool
    last_triggered: Optional[datetime] = None
    created_at: datetime


class AlertCreate(BaseModel):
    type: AlertType
    symbol: str
    condition: str
    value: float


class AlertUpdate(BaseModel):
    is_active: Optional[bool] = None
    condition: Optional[str] = None
    value: Optional[float] = None


class AlertNotification(BaseModel):
    id: str
    type: AlertType
    symbol: str
    message: str
    timestamp: datetime
    is_read: bool
