#!/usr/bin/env python3
"""
Alert Manager Utility - Alert and notification system for live trading.

US-5.3: Risk Management - Alert system for risk events
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum
import yaml

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Alert severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class EventType(str, Enum):
    """Alert event types."""
    EMERGENCY_STOP = "emergency_stop"
    LOSS_LIMIT_BREACH = "loss_limit_breach"
    POSITION_LIMIT_BREACH = "position_limit_breach"
    CONNECTION_LOST = "connection_lost"
    ORDER_FAILED = "order_failed"
    RECONCILIATION_MISMATCH = "reconciliation_mismatch"
    RISK_THRESHOLD = "risk_threshold"
    SYSTEM_ERROR = "system_error"


class AlertManager:
    """
    Alert manager for trading system notifications.

    Supports multiple alert channels (logging, email, Slack) with
    severity-based routing and event-type categorization.
    """

    # Critical events that always trigger alerts
    CRITICAL_EVENTS = {
        EventType.EMERGENCY_STOP,
        EventType.LOSS_LIMIT_BREACH,
        EventType.CONNECTION_LOST,
        EventType.RECONCILIATION_MISMATCH
    }

    def __init__(self, config_path: str = "config/risk_config.yaml"):
        """
        Initialize AlertManager with configuration.

        Args:
            config_path: Path to risk configuration file

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            ValueError: If configuration is invalid
        """
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        self._load_config()
        self._initialize_channels()
        self._alert_history: List[Dict[str, Any]] = []
        logger.info("AlertManager initialized")

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            self.config = config.get('alerts', {})

            # Load event type configurations
            self.event_configs = {}
            for event_name, event_config in self.config.get('event_types', {}).items():
                try:
                    event_type = EventType(event_name)
                    self.event_configs[event_type] = event_config
                except ValueError:
                    logger.warning(f"Unknown event type in config: {event_name}")

            logger.debug(f"Loaded alert config: {self.config}")

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ValueError(f"Invalid configuration file: {e}")

    def _initialize_channels(self) -> None:
        """Initialize alert channels based on configuration."""
        self.channels = self.config.get('channels', {})

        # Logging channel (always enabled as fallback)
        self.logging_enabled = self.channels.get('logging', {}).get('enabled', True)
        self.logging_level = self.channels.get('logging', {}).get('level', 'INFO')

        # Email channel (future implementation)
        self.email_enabled = self.channels.get('email', {}).get('enabled', False)
        self.email_recipients = self.channels.get('email', {}).get('recipients', [])

        # Slack channel (future implementation)
        self.slack_enabled = self.channels.get('slack', {}).get('enabled', False)
        self.slack_webhook = self.channels.get('slack', {}).get('webhook_url', '')

        logger.info(f"Alert channels: logging={self.logging_enabled}, "
                   f"email={self.email_enabled}, slack={self.slack_enabled}")

    def send_alert(
        self,
        message: str,
        severity: Severity,
        event_type: EventType,
        **kwargs
    ) -> bool:
        """
        Send alert through configured channels.

        Args:
            message: Alert message
            severity: Alert severity (INFO, WARNING, CRITICAL)
            event_type: Type of event triggering the alert
            **kwargs: Additional context data

        Returns:
            True if alert sent successfully, False otherwise
        """
        try:
            # Create alert record
            alert_record = {
                'timestamp': datetime.now().isoformat(),
                'message': message,
                'severity': severity.value,
                'event_type': event_type.value,
                'context': kwargs
            }

            # Store in history
            self._alert_history.append(alert_record)

            # Route to appropriate channels
            success = True

            # Always log
            if self.logging_enabled:
                self.log_alert(message, severity, event_type, **kwargs)

            # Send to additional channels for critical events
            if self.is_critical_event(event_type) or severity == Severity.CRITICAL:
                if self.email_enabled:
                    success &= self._send_email_alert(alert_record)
                if self.slack_enabled:
                    success &= self._send_slack_alert(alert_record)

            return success

        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            # Still log even if other channels fail
            logger.critical(f"ALERT FAILED: {message} [{severity.value}]")
            return False

    def log_alert(
        self,
        message: str,
        severity: Severity,
        event_type: Optional[EventType] = None,
        **kwargs
    ) -> None:
        """
        Log alert to system logger.

        Args:
            message: Alert message
            severity: Alert severity
            event_type: Type of event (optional)
            **kwargs: Additional context data
        """
        # Format message with context
        log_message = f"[{event_type.value if event_type else 'ALERT'}] {message}"

        if kwargs:
            context_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
            log_message = f"{log_message} | Context: {context_str}"

        # Log at appropriate level
        if severity == Severity.CRITICAL:
            logger.critical(log_message)
        elif severity == Severity.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)

    def is_critical_event(self, event_type: EventType) -> bool:
        """
        Check if event type is critical.

        Args:
            event_type: Event type to check

        Returns:
            True if event is critical, False otherwise
        """
        return event_type in self.CRITICAL_EVENTS

    def get_alert_history(
        self,
        severity: Optional[Severity] = None,
        event_type: Optional[EventType] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get alert history with optional filtering.

        Args:
            severity: Filter by severity level
            event_type: Filter by event type
            limit: Maximum number of alerts to return

        Returns:
            List of alert records
        """
        filtered = self._alert_history

        # Filter by severity
        if severity is not None:
            filtered = [a for a in filtered if a['severity'] == severity.value]

        # Filter by event type
        if event_type is not None:
            filtered = [a for a in filtered if a['event_type'] == event_type.value]

        # Apply limit
        if limit is not None:
            filtered = filtered[-limit:]

        return filtered

    def get_critical_alerts(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get recent critical alerts.

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of critical alert records
        """
        return self.get_alert_history(severity=Severity.CRITICAL, limit=limit)

    def clear_history(self) -> None:
        """Clear alert history."""
        self._alert_history.clear()
        logger.info("Alert history cleared")

    def _send_email_alert(self, alert_record: Dict[str, Any]) -> bool:
        """
        Send email alert (future implementation).

        Args:
            alert_record: Alert record to send

        Returns:
            True if successful, False otherwise
        """
        # Placeholder for future email implementation
        logger.debug(f"Email alert not implemented: {alert_record['message']}")
        return True

    def _send_slack_alert(self, alert_record: Dict[str, Any]) -> bool:
        """
        Send Slack alert (future implementation).

        Args:
            alert_record: Alert record to send

        Returns:
            True if successful, False otherwise
        """
        # Placeholder for future Slack implementation
        logger.debug(f"Slack alert not implemented: {alert_record['message']}")
        return True

    def alert_emergency_stop(self, reason: str, **kwargs) -> None:
        """
        Send emergency stop alert.

        Args:
            reason: Reason for emergency stop
            **kwargs: Additional context
        """
        self.send_alert(
            message=f"Emergency stop triggered: {reason}",
            severity=Severity.CRITICAL,
            event_type=EventType.EMERGENCY_STOP,
            reason=reason,
            **kwargs
        )

    def alert_loss_limit_breach(
        self,
        loss_amount: float,
        limit: float,
        **kwargs
    ) -> None:
        """
        Send loss limit breach alert.

        Args:
            loss_amount: Current loss amount
            limit: Loss limit that was breached
            **kwargs: Additional context
        """
        self.send_alert(
            message=f"Loss limit breached: ${loss_amount:,.2f} exceeds limit of ${limit:,.2f}",
            severity=Severity.CRITICAL,
            event_type=EventType.LOSS_LIMIT_BREACH,
            loss_amount=loss_amount,
            limit=limit,
            **kwargs
        )

    def alert_position_limit_breach(
        self,
        symbol: str,
        position_value: float,
        limit: float,
        **kwargs
    ) -> None:
        """
        Send position limit breach alert.

        Args:
            symbol: Symbol that breached limit
            position_value: Current position value
            limit: Position limit
            **kwargs: Additional context
        """
        self.send_alert(
            message=f"Position limit breached for {symbol}: "
                   f"${position_value:,.2f} exceeds limit of ${limit:,.2f}",
            severity=Severity.WARNING,
            event_type=EventType.POSITION_LIMIT_BREACH,
            symbol=symbol,
            position_value=position_value,
            limit=limit,
            **kwargs
        )

    def alert_connection_lost(self, connection_type: str, **kwargs) -> None:
        """
        Send connection lost alert.

        Args:
            connection_type: Type of connection lost (broker, data feed, etc.)
            **kwargs: Additional context
        """
        self.send_alert(
            message=f"Connection lost: {connection_type}",
            severity=Severity.CRITICAL,
            event_type=EventType.CONNECTION_LOST,
            connection_type=connection_type,
            **kwargs
        )

    def alert_order_failed(
        self,
        symbol: str,
        order_type: str,
        quantity: int,
        reason: str,
        **kwargs
    ) -> None:
        """
        Send order failed alert.

        Args:
            symbol: Symbol for failed order
            order_type: Type of order (market, limit, etc.)
            quantity: Order quantity
            reason: Failure reason
            **kwargs: Additional context
        """
        self.send_alert(
            message=f"Order failed: {order_type} {quantity} {symbol} - {reason}",
            severity=Severity.WARNING,
            event_type=EventType.ORDER_FAILED,
            symbol=symbol,
            order_type=order_type,
            quantity=quantity,
            reason=reason,
            **kwargs
        )

    def alert_reconciliation_mismatch(
        self,
        symbol: str,
        system_quantity: int,
        broker_quantity: int,
        **kwargs
    ) -> None:
        """
        Send reconciliation mismatch alert.

        Args:
            symbol: Symbol with mismatch
            system_quantity: Quantity in system
            broker_quantity: Quantity at broker
            **kwargs: Additional context
        """
        self.send_alert(
            message=f"Position mismatch for {symbol}: "
                   f"System={system_quantity}, Broker={broker_quantity}",
            severity=Severity.CRITICAL,
            event_type=EventType.RECONCILIATION_MISMATCH,
            symbol=symbol,
            system_quantity=system_quantity,
            broker_quantity=broker_quantity,
            **kwargs
        )

    def alert_system_error(self, error_message: str, **kwargs) -> None:
        """
        Send system error alert.

        Args:
            error_message: Error description
            **kwargs: Additional context
        """
        self.send_alert(
            message=f"System error: {error_message}",
            severity=Severity.WARNING,
            event_type=EventType.SYSTEM_ERROR,
            error=error_message,
            **kwargs
        )
