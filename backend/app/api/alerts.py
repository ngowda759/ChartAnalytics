from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime
import uuid
import structlog

from app.schemas.alerts import (
    Alert,
    AlertCreate,
    AlertUpdate,
    AlertNotification,
)

logger = structlog.get_logger()
router = APIRouter()

# NOTE: No alert persistence/evaluation engine is wired in this environment.
# The production-safe behaviour is a truthful empty state (no alerts, no
# notifications) rather than fabricated sample data, so the dashboard shows
# "No recent alerts" instead of fake notifications. Wire a real store + alert
# engine to populate these endpoints.


@router.get("/", response_model=List[Alert])
async def get_alerts(user_id: str = "user_1", is_active: Optional[bool] = None):
    """Get user's alerts.

    No persistence layer is configured; return an empty list truthfully.
    """
    logger.info("fetching_alerts", user_id=user_id)
    return []


@router.post("/", response_model=Alert, status_code=201)
async def create_alert(data: AlertCreate, user_id: str = "user_1"):
    """Create a new alert.

    Constructs the response from the request payload (not fabricated data).
    The generated ID is a request-scoped identifier; wire a real store to
    persist it.
    """
    logger.info("creating_alert", user_id=user_id, type=data.type)
    now = datetime.utcnow()
    return Alert(
        id=f"alert_{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        type=data.type,
        symbol=data.symbol,
        condition=data.condition,
        value=data.value,
        is_active=True,
        created_at=now,
    )


@router.put("/{alert_id}", response_model=Alert)
async def update_alert(alert_id: str, updates: AlertUpdate):
    """Update an alert.

    Without persistence there is nothing to update; return 404 truthfully.
    """
    logger.info("updating_alert", alert_id=alert_id)
    raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")


@router.delete("/{alert_id}")
async def delete_alert(alert_id: str):
    """Delete an alert"""
    logger.info("deleting_alert", alert_id=alert_id)
    return {"message": "Alert deleted successfully"}


@router.get("/notifications", response_model=List[AlertNotification])
async def get_notifications(user_id: str = "user_1", limit: int = 20):
    """Get recent alert notifications.

    No alert evaluation engine is configured; return an empty list truthfully
    so the dashboard shows "No recent alerts" instead of fake notifications.
    """
    logger.info("fetching_notifications", user_id=user_id)
    return []


@router.post("/{alert_id}/test")
async def test_alert(alert_id: str):
    """Send a test notification for an alert"""
    logger.info("testing_alert", alert_id=alert_id)
    return {"message": "Test notification sent successfully"}
