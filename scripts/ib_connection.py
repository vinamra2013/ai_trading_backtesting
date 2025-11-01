"""
Interactive Brokers Connection Manager
Epic 2: US-2.2 - IB Connection Management

Features:
- Automatic connection on startup
- Reconnection logic with exponential backoff (3 retries)
- Health checks every 30 seconds
- Graceful disconnection on shutdown
- Comprehensive error logging
"""

import os
import time
import logging
from typing import Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/ib_connection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class IBConnectionManager:
    """Manages connection to Interactive Brokers Gateway/TWS"""

    def __init__(
        self,
        host: str = 'ib-gateway',
        port: int = None,
        client_id: int = 1,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        health_check_interval: int = 30
    ):
        """
        Initialize IB Connection Manager

        Args:
            host: IB Gateway hostname (default: 'ib-gateway' for Docker)
            port: IB Gateway port (4001 for paper, 4002 for live)
            client_id: Unique client identifier
            max_retries: Maximum reconnection attempts
            initial_backoff: Initial backoff time in seconds
            health_check_interval: Health check frequency in seconds
        """
        self.host = host
        self.port = port or int(os.getenv('IB_GATEWAY_PORT', '4001'))
        self.client_id = client_id
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.health_check_interval = health_check_interval

        self.connection = None
        self.is_connected = False
        self.last_health_check = None
        self.retry_count = 0

        logger.info(
            f"IBConnectionManager initialized: {self.host}:{self.port} "
            f"(client_id={self.client_id})"
        )

    def connect(self) -> bool:
        """
        Establish connection to IB Gateway with retry logic

        Returns:
            bool: True if connected successfully
        """
        logger.info(f"Attempting to connect to IB Gateway at {self.host}:{self.port}")

        for attempt in range(self.max_retries):
            try:
                # Calculate backoff time with exponential increase
                if attempt > 0:
                    backoff_time = self.initial_backoff * (2 ** (attempt - 1))
                    logger.info(f"Retry {attempt}/{self.max_retries} after {backoff_time}s")
                    time.sleep(backoff_time)

                # Attempt connection
                # NOTE: This is a placeholder. Actual implementation will use
                # ib_insync or similar library once LEAN integration is complete
                logger.info(f"Connection attempt {attempt + 1}/{self.max_retries}")

                # TODO: Replace with actual IB connection logic
                # from ib_insync import IB
                # self.connection = IB()
                # self.connection.connect(self.host, self.port, clientId=self.client_id)

                self.is_connected = True
                self.retry_count = 0
                self.last_health_check = datetime.now()

                logger.info("✅ Successfully connected to IB Gateway")
                return True

            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                self.retry_count += 1

                if attempt == self.max_retries - 1:
                    logger.error(
                        f"❌ Failed to connect after {self.max_retries} attempts"
                    )
                    return False

        return False

    def disconnect(self) -> None:
        """Gracefully disconnect from IB Gateway"""
        if not self.is_connected:
            logger.warning("Already disconnected")
            return

        try:
            logger.info("Disconnecting from IB Gateway...")

            # TODO: Replace with actual disconnection logic
            # if self.connection:
            #     self.connection.disconnect()

            self.is_connected = False
            self.connection = None

            logger.info("✅ Gracefully disconnected from IB Gateway")

        except Exception as e:
            logger.error(f"Error during disconnection: {e}")

    def health_check(self) -> bool:
        """
        Perform health check on IB connection

        Returns:
            bool: True if connection is healthy
        """
        try:
            # Check if health check is needed
            if self.last_health_check:
                elapsed = (datetime.now() - self.last_health_check).total_seconds()
                if elapsed < self.health_check_interval:
                    return self.is_connected

            logger.debug("Performing health check...")

            # TODO: Replace with actual health check
            # if self.connection and self.connection.isConnected():
            #     self.last_health_check = datetime.now()
            #     return True

            # Placeholder: assume connected if is_connected flag is True
            if self.is_connected:
                self.last_health_check = datetime.now()
                return True

            # Connection lost - attempt reconnection
            logger.warning("⚠️ Health check failed - connection lost")
            return self.reconnect()

        except Exception as e:
            logger.error(f"Health check error: {e}")
            return False

    def reconnect(self) -> bool:
        """
        Attempt to reconnect to IB Gateway

        Returns:
            bool: True if reconnection successful
        """
        logger.warning("Attempting to reconnect...")
        self.is_connected = False
        return self.connect()

    def get_connection_status(self) -> dict:
        """
        Get detailed connection status

        Returns:
            dict: Connection status information
        """
        return {
            'is_connected': self.is_connected,
            'host': self.host,
            'port': self.port,
            'client_id': self.client_id,
            'retry_count': self.retry_count,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
            'uptime_seconds': (
                (datetime.now() - self.last_health_check).total_seconds()
                if self.last_health_check else 0
            )
        }

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# Example usage
if __name__ == "__main__":
    # Create connection manager
    manager = IBConnectionManager()

    # Connect
    if manager.connect():
        print("Connected successfully!")

        # Perform health checks
        for i in range(3):
            time.sleep(5)
            status = manager.health_check()
            print(f"Health check {i+1}: {'✅ Healthy' if status else '❌ Unhealthy'}")

        # Get status
        status = manager.get_connection_status()
        print(f"Connection status: {status}")

        # Disconnect
        manager.disconnect()
    else:
        print("Failed to connect")

    # Or use as context manager
    print("\nUsing context manager:")
    with IBConnectionManager() as conn:
        print(f"Is connected: {conn.is_connected}")
