from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class NotificationPreferences(BaseModel):
    email: bool = True
    telegram: bool = False
    browser: bool = True
    alerts: Dict[str, bool] = {
        "ema_cross": True,
        "vwap_cross": True,
        "breakout": True,
        "oi_spike": False,
        "pcr_shift": False,
        "volume_spike": True,
    }


class UserPreferences(BaseModel):
    theme: str = "system"
    default_index: str = "NIFTY"
    notifications: NotificationPreferences = NotificationPreferences()


class RiskProfile(BaseModel):
    max_risk_per_trade: float = 2.0  # Percentage
    max_daily_loss: float = 5.0  # Percentage
    max_weekly_loss: float = 10.0  # Percentage
    max_position_size: float = 10.0  # Percentage


class Subscription(BaseModel):
    tier: SubscriptionTier = SubscriptionTier.FREE
    expires_at: datetime


class UserBase(BaseModel):
    email: EmailStr
    name: str


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    name: Optional[str] = None
    preferences: Optional[UserPreferences] = None
    risk_profile: Optional[RiskProfile] = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole = UserRole.USER
    subscription: Subscription
    preferences: UserPreferences
    risk_profile: RiskProfile
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    sub: Optional[str] = None
    user_id: Optional[str] = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)
