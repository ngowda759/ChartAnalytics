from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime
import random
import structlog

from app.schemas.alerts import (
    Alert,
    AlertCreate,
    AlertUpdate,
    AlertNotification,
)

logger = structlog.get_logger()
router = APIRouter()


@router.get("/", response_model=List[Alert])
async def get_alerts(user_id: str = "user_1", is_active: Optional[bool] = None):
    """Get user's alerts"""
    logger.info("fetching_alerts", user_id=user_id)
    
    alerts = [
        Alert(
            id="alert_1",
            user_id=user_id,
            type="ema_cross",
            symbol="NIFTY",
            condition="crosses_above",
            value=24500,
            is_active=True,
            created_at=datetime.utcnow(),
        ),
        Alert(
            id="alert_2",
            user_id=user_id,
            type="breakout",
            symbol="BANKNIFTY",
            condition="above",
            value=53000,
            is_active=True,
            created_at=datetime.utcnow(),
        ),
        Alert(
            id="alert_3",
            user_id=user_id,
            type="pcr_shift",
            symbol="NIFTY",
            condition="above",
            value=1.2,
            is_active=False,
            created_at=datetime.utcnow(),
        ),
    ]
    
    if is_active is not None:
        alerts = [a for a in alerts if a.is_active == is_active]
    
    return alerts


@router.post("/", response_model=Alert, status_code=201)
async def create_alert(data: AlertCreate, user_id: str = "user_1"):
    """Create a new alert"""
    logger.info("creating_alert", user_id=user_id, type=data.type)
    
    return Alert(
        id=f"alert_{random.randint(1000, 9999)}",
        user_id=user_id,
        type=data.type,
        symbol=data.symbol,
        condition=data.condition,
        value=data.value,
        is_active=True,
        created_at=datetime.utcnow(),
    )


@router.put("/{alert_id}", response_model=Alert)
async def update_alert(alert_id: str, updates: AlertUpdate):
    """Update an alert"""
    logger.info("updating_alert", alert_id=alert_id)
    
    return Alert(
        id=alert_id,
        user_id="user_1",
        type="ema_cross",
        symbol="NIFTY",
        condition="crosses_above",
        value=24500,
        is_active=updates.is_active if updates.is_active is not None else True,
        created_at=datetime.utcnow(),
    )


@router.delete("/{alert_id}")
async def delete_alert(alert_id: str):
    """Delete an alert"""
    logger.info("deleting_alert", alert_id=alert_id)
    return {"message": "Alert deleted successfully"}


@router.get("/notifications", response_model=List[AlertNotification])
async def get_notifications(user_id: str = "user_1", limit: int = 20):
    """Get recent alert notifications"""
    logger.info("fetching_notifications", user_id=user_id)
    
    notifications = []
    for i in range(min(limit, 10)):
        notifications.append(
            AlertNotification(
                id=f"notif_{i + 1}",
                type=random.choice(["ema_cross", "breakout", "oi_spike", "pcr_shift"]),
                symbol=random.choice(["NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK"]),
                message=f"Alert triggered for {random.choice(['NIFTY', 'BANKNIFTY'])}",
                timestamp=datetime.utcnow(),
                is_read=random.random() > 0.3,
            )
        )
    
    return notifications


@router.post("/{alert_id}/test")
async def test_alert(alert_id: str):
    """Send a test notification for an alert"""
    logger.info("testing_alert", alert_id=alert_id)
    return {"message": "Test notification sent successfully"}
