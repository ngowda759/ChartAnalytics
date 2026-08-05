"""Telegram Alert Service - Send trading alerts to users."""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import structlog

logger = structlog.get_logger()


class AlertType(str, Enum):
    EMA_CROSS = "ema_cross"
    VWAP_CROSS = "vwap_cross"
    BREAKOUT = "breakout"
    OI_SPIKE = "oi_spike"
    PCR_SHIFT = "pcr_shift"
    VOLUME_SPIKE = "volume_spike"
    PRICE_ALERT = "price_alert"
    RSI_SIGNAL = "rsi_signal"


@dataclass
class Alert:
    id: str
    user_id: str
    type: AlertType
    symbol: str
    condition: str
    value: float
    is_active: bool = True
    last_triggered: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AlertNotification:
    id: str
    type: AlertType
    symbol: str
    title: str
    message: str
    timestamp: datetime
    priority: str = "normal"  # "low", "normal", "high", "urgent"


@dataclass
class TelegramConfig:
    bot_token: str = ""
    chat_id: str = ""
    enabled: bool = False


class TelegramAlertService:
    """Service for managing and sending trading alerts via Telegram."""

    def __init__(self):
        self.logger = structlog.get_logger()
        self._alerts: Dict[str, List[Alert]] = {}
        self._notifications: List[AlertNotification] = []
        self._config = TelegramConfig()

    def configure(self, bot_token: str = "", chat_id: str = "", enabled: bool = False):
        """Configure Telegram settings."""
        self._config = TelegramConfig(
            bot_token=bot_token,
            chat_id=chat_id,
            enabled=enabled,
        )
        self.logger.info("telegram_configured", enabled=enabled)

    def create_alert(
        self,
        user_id: str,
        alert_type: AlertType,
        symbol: str,
        condition: str,
        value: float,
    ) -> Alert:
        """Create a new alert."""
        alert_id = f"alert_{user_id}_{symbol}_{alert_type.value}_{datetime.utcnow().timestamp()}"
        
        alert = Alert(
            id=alert_id,
            user_id=user_id,
            type=alert_type,
            symbol=symbol,
            condition=condition,
            value=value,
        )
        
        if user_id not in self._alerts:
            self._alerts[user_id] = []
        self._alerts[user_id].append(alert)
        
        self.logger.info("alert_created", alert_id=alert_id, user_id=user_id)
        return alert

    def get_alerts(self, user_id: str, active_only: bool = False) -> List[Alert]:
        """Get alerts for a user."""
        alerts = self._alerts.get(user_id, [])
        if active_only:
            alerts = [a for a in alerts if a.is_active]
        return alerts

    def update_alert(self, alert_id: str, updates: Dict[str, Any]) -> Optional[Alert]:
        """Update an alert."""
        for user_id, alerts in self._alerts.items():
            for alert in alerts:
                if alert.id == alert_id:
                    if "is_active" in updates:
                        alert.is_active = updates["is_active"]
                    if "value" in updates:
                        alert.value = updates["value"]
                    self.logger.info("alert_updated", alert_id=alert_id)
                    return alert
        return None

    def delete_alert(self, alert_id: str) -> bool:
        """Delete an alert."""
        for user_id, alerts in list(self._alerts.items()):
            self._alerts[user_id] = [a for a in alerts if a.id != alert_id]
        return True

    def check_and_trigger_alerts(
        self,
        symbol: str,
        current_price: float,
        ema_20: float,
        ema_50: float,
        vwap: float,
        rsi: float,
        volume: int,
        avg_volume: int,
        pcr: float,
        call_oi_change: float,
        put_oi_change: float,
    ) -> List[AlertNotification]:
        """Check alerts and trigger any that match current conditions."""
        notifications = []

        for user_id, alerts in self._alerts.items():
            for alert in alerts:
                if not alert.is_active or alert.symbol != symbol:
                    continue

                triggered = False
                notification = None

                if alert.type == AlertType.EMA_CROSS:
                    if alert.condition == "bullish" and ema_20 > ema_50:
                        triggered = True
                        notification = self._create_ema_notification(symbol, "bullish", ema_20, ema_50)
                    elif alert.condition == "bearish" and ema_20 < ema_50:
                        triggered = True
                        notification = self._create_ema_notification(symbol, "bearish", ema_20, ema_50)

                elif alert.type == AlertType.VWAP_CROSS:
                    if alert.condition == "above" and current_price > vwap:
                        triggered = True
                        notification = self._create_vwap_notification(symbol, "above", current_price, vwap)
                    elif alert.condition == "below" and current_price < vwap:
                        triggered = True
                        notification = self._create_vwap_notification(symbol, "below", current_price, vwap)

                elif alert.type == AlertType.PRICE_ALERT:
                    if alert.condition == "above" and current_price >= alert.value:
                        triggered = True
                        notification = self._create_price_notification(symbol, "above", current_price, alert.value)
                    elif alert.condition == "below" and current_price <= alert.value:
                        triggered = True
                        notification = self._create_price_notification(symbol, "below", current_price, alert.value)

                elif alert.type == AlertType.VOLUME_SPIKE:
                    vol_ratio = volume / avg_volume if avg_volume > 0 else 0
                    if vol_ratio >= alert.value:
                        triggered = True
                        notification = self._create_volume_notification(symbol, vol_ratio)

                elif alert.type == AlertType.PCR_SHIFT:
                    if abs(pcr - alert.value) < 0.1:
                        triggered = True
                        notification = self._create_pcr_notification(symbol, pcr)

                elif alert.type == AlertType.OI_SPIKE:
                    if call_oi_change >= alert.value or put_oi_change >= alert.value:
                        triggered = True
                        notification = self._create_oi_notification(symbol, call_oi_change, put_oi_change)

                elif alert.type == AlertType.RSI_SIGNAL:
                    if alert.condition == "overbought" and rsi >= alert.value:
                        triggered = True
                        notification = self._create_rsi_notification(symbol, rsi, "overbought")
                    elif alert.condition == "oversold" and rsi <= alert.value:
                        triggered = True
                        notification = self._create_rsi_notification(symbol, rsi, "oversold")

                if triggered and notification:
                    alert.last_triggered = datetime.utcnow()
                    notifications.append(notification)
                    self._send_telegram(notification)
                    self.logger.info("alert_triggered", alert_id=alert.id, symbol=symbol)

        self._notifications.extend(notifications)
        return notifications

    def _create_ema_notification(
        self, symbol: str, direction: str, ema_20: float, ema_50: float
    ) -> AlertNotification:
        """Create EMA crossover notification."""
        emoji = "🟢" if direction == "bullish" else "🔴"
        return AlertNotification(
            id=f"notif_ema_{symbol}_{datetime.utcnow().timestamp()}",
            type=AlertType.EMA_CROSS,
            symbol=symbol,
            title=f"EMA Crossover - {direction.title()}",
            message=f"{emoji} {symbol}: EMA 20 ({ema_20:.2f}) crossed {direction} EMA 50 ({ema_50:.2f})\n\nThis indicates {direction} momentum shift.",
            timestamp=datetime.utcnow(),
            priority="high" if direction == "bullish" else "normal",
        )

    def _create_vwap_notification(
        self, symbol: str, direction: str, price: float, vwap: float
    ) -> AlertNotification:
        """Create VWAP crossover notification."""
        emoji = "📈" if direction == "above" else "📉"
        return AlertNotification(
            id=f"notif_vwap_{symbol}_{datetime.utcnow().timestamp()}",
            type=AlertType.VWAP_CROSS,
            symbol=symbol,
            title=f"VWAP Cross - Price {direction.title()}",
            message=f"{emoji} {symbol}: Price ({price:.2f}) moved {direction} VWAP ({vwap:.2f})\n\nIntraday bias shifted.",
            timestamp=datetime.utcnow(),
            priority="normal",
        )

    def _create_price_notification(
        self, symbol: str, direction: str, price: float, target: float
    ) -> AlertNotification:
        """Create price alert notification."""
        return AlertNotification(
            id=f"notif_price_{symbol}_{datetime.utcnow().timestamp()}",
            type=AlertType.PRICE_ALERT,
            symbol=symbol,
            title=f"Price Alert - {direction.title()}",
            message=f"🔔 {symbol} hit {direction.upper()} your target!\n\nCurrent: ₹{price:.2f}\nTarget: ₹{target:.2f}",
            timestamp=datetime.utcnow(),
            priority="urgent",
        )

    def _create_volume_notification(self, symbol: str, vol_ratio: float) -> AlertNotification:
        """Create volume spike notification."""
        return AlertNotification(
            id=f"notif_vol_{symbol}_{datetime.utcnow().timestamp()}",
            type=AlertType.VOLUME_SPIKE,
            symbol=symbol,
            title="Volume Spike Detected",
            message=f"📊 {symbol}: Volume at {vol_ratio:.1f}x average\n\nUnusual activity - watch for breakout.",
            timestamp=datetime.utcnow(),
            priority="normal",
        )

    def _create_pcr_notification(self, symbol: str, pcr: float) -> AlertNotification:
        """Create PCR shift notification."""
        bias = "Bullish" if pcr > 1 else "Bearish" if pcr < 1 else "Neutral"
        return AlertNotification(
            id=f"notif_pcr_{symbol}_{datetime.utcnow().timestamp()}",
            type=AlertType.PCR_SHIFT,
            symbol=symbol,
            title=f"PCR Shift - {bias} Bias",
            message=f"📈 {symbol}: PCR at {pcr:.2f}\n\nMarket sentiment: {bias}\nPut writing increasing at strikes.",
            timestamp=datetime.utcnow(),
            priority="normal",
        )

    def _create_oi_notification(
        self, symbol: str, call_oi: float, put_oi: float
    ) -> AlertNotification:
        """Create OI spike notification."""
        return AlertNotification(
            id=f"notif_oi_{symbol}_{datetime.utcnow().timestamp()}",
            type=AlertType.OI_SPIKE,
            symbol=symbol,
            title="OI Build-up Alert",
            message=f"📉 {symbol}: OI Change\n\nCall OI: {call_oi:.1f}%\nPut OI: {put_oi:.1f}%\n\nSmart money positioning detected.",
            timestamp=datetime.utcnow(),
            priority="high",
        )

    def _create_rsi_notification(
        self, symbol: str, rsi: float, zone: str
    ) -> AlertNotification:
        """Create RSI signal notification."""
        emoji = "🔥" if zone == "overbought" else "💪"
        return AlertNotification(
            id=f"notif_rsi_{symbol}_{datetime.utcnow().timestamp()}",
            type=AlertType.RSI_SIGNAL,
            symbol=symbol,
            title=f"RSI {zone.title()}",
            message=f"{emoji} {symbol}: RSI at {rsi:.1f}\n\n{zone.title()} zone - potential reversal",
            timestamp=datetime.utcnow(),
            priority="normal",
        )

    async def _send_telegram(self, notification: AlertNotification):
        """Send notification via Telegram."""
        if not self._config.enabled or not self._config.bot_token:
            self.logger.info("telegram_disabled", notification_id=notification.id)
            return

        import httpx
        
        url = f"https://api.telegram.org/bot{self._config.bot_token}/sendMessage"
        payload = {
            "chat_id": self._config.chat_id,
            "text": f"*{notification.title}*\n\n{notification.message}",
            "parse_mode": "Markdown",
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10)
                if response.status_code == 200:
                    self.logger.info("telegram_sent", notification_id=notification.id)
                else:
                    self.logger.error("telegram_failed", status=response.status_code)
        except Exception as e:
            self.logger.error("telegram_error", error=str(e))

    def get_notifications(self, user_id: str = "", limit: int = 50) -> List[AlertNotification]:
        """Get recent notifications."""
        return self._notifications[-limit:]


# Singleton instance
telegram_alerts = TelegramAlertService()
