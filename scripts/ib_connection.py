"""
Interactive Brokers Connection Manager (Backtrader Migration)
Epic 11: US-11.3 - IB Connection with ib_insync

Features:
- Automatic connection on startup using ib_insync
- Reconnection logic with exponential backoff (3 retries)
- Health checks every 30 seconds
- Graceful disconnection on shutdown
- Comprehensive error logging
- AsyncIO event loop management
"""

import os
import time
import logging
import asyncio
from typing import Optional
from datetime import datetime
from ib_insync import IB, util

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
    """Manages connection to Interactive Brokers Gateway/TWS using ib_insync"""

    def __init__(
        self,
        host: str = 'ib-gateway',
        port: int = None,
        client_id: int = 1,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        health_check_interval: int = 30,
        readonly: bool = False
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
            readonly: Read-only API access (default: False)
        """
        self.host = host
        self.port = port or int(os.getenv('IB_GATEWAY_PORT', '4001'))
        self.client_id = client_id
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.health_check_interval = health_check_interval
        self.readonly = readonly

        self.ib = IB()
        self.is_connected = False
        self.last_health_check = None
        self.retry_count = 0

        logger.info(
            f"IBConnectionManager initialized: {self.host}:{self.port} "
            f"(client_id={self.client_id}, readonly={self.readonly})"
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

                logger.info(f"Connection attempt {attempt + 1}/{self.max_retries}")

                # Connect using ib_insync
                self.ib.connect(
                    host=self.host,
                    port=self.port,
                    clientId=self.client_id,
                    readonly=self.readonly,
                    timeout=20
                )

                if self.ib.isConnected():
                    self.is_connected = True
                    self.retry_count = 0
                    self.last_health_check = datetime.now()

                    logger.info(
                        f"✅ Successfully connected to IB Gateway "
                        f"(serverVersion={self.ib.client.serverVersion()})"
                    )
                    return True
                else:
                    logger.warning(f"Connection attempt {attempt + 1} failed")
                    self.retry_count = attempt + 1

            except ConnectionRefusedError:
                logger.error(
                    f"Connection refused by IB Gateway at {self.host}:{self.port}. "
                    f"Is IB Gateway running?"
                )
                self.retry_count = attempt + 1

            except Exception as e:
                logger.error(
                    f"Connection error on attempt {attempt + 1}: {type(e).__name__}: {e}"
                )
                self.retry_count = attempt + 1

        logger.error(
            f"❌ Failed to connect after {self.max_retries} attempts"
        )
        self.is_connected = False
        return False

    def disconnect(self):
        """Gracefully disconnect from IB Gateway"""
        if self.is_connected and self.ib.isConnected():
            logger.info("Disconnecting from IB Gateway...")
            self.ib.disconnect()
            self.is_connected = False
            logger.info("✅ Disconnected successfully")
        else:
            logger.info("Already disconnected")

    def health_check(self) -> bool:
        """
        Perform health check on IB connection

        Returns:
            bool: True if connection is healthy
        """
        try:
            if not self.is_connected or not self.ib.isConnected():
                logger.warning("⚠️  Health check failed: Not connected")
                return False

            # Update last health check time
            self.last_health_check = datetime.now()

            # Check if we can get account summary (simple API test)
            accounts = self.ib.managedAccounts()
            if accounts:
                logger.debug(f"✅ Health check passed (accounts: {accounts})")
                return True
            else:
                logger.warning("⚠️  Health check failed: No accounts returned")
                return False

        except Exception as e:
            logger.error(f"⚠️  Health check failed: {type(e).__name__}: {e}")
            return False

    def reconnect(self) -> bool:
        """
        Attempt to reconnect after connection loss

        Returns:
            bool: True if reconnected successfully
        """
        logger.info("Attempting reconnection...")
        self.disconnect()
        time.sleep(2)  # Brief pause before reconnecting
        return self.connect()

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

    def get_connection_status(self) -> dict:
        """
        Get detailed connection status

        Returns:
            dict: Connection status information
        """
        return {
            'connected': self.is_connected and self.ib.isConnected(),
            'host': self.host,
            'port': self.port,
            'client_id': self.client_id,
            'readonly': self.readonly,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
            'retry_count': self.retry_count,
            'server_version': self.ib.client.serverVersion() if self.ib.isConnected() else None,
            'connection_time': self.ib.client.connTime if self.ib.isConnected() else None
        }


# Convenience function for simple connections
def get_ib_connection(
    host: str = 'ib-gateway',
    port: int = None,
    client_id: int = 1,
    readonly: bool = False
) -> IBConnectionManager:
    """
    Get a connected IB connection manager

    Args:
        host: IB Gateway hostname
        port: IB Gateway port
        client_id: Client identifier
        readonly: Read-only API access

    Returns:
        IBConnectionManager: Connected manager instance

    Raises:
        ConnectionError: If connection fails
    """
    manager = IBConnectionManager(
        host=host,
        port=port,
        client_id=client_id,
        readonly=readonly
    )

    if not manager.connect():
        raise ConnectionError(
            f"Failed to connect to IB Gateway at {host}:{port or 4001}"
        )

    return manager


if __name__ == '__main__':
    """Test IB connection"""
    print("Testing IB Connection Manager...")

    try:
        with IBConnectionManager() as ib_manager:
            print(f"\nConnection Status:")
            status = ib_manager.get_connection_status()
            for key, value in status.items():
                print(f"  {key}: {value}")

            print(f"\nPerforming health check...")
            healthy = ib_manager.health_check()
            print(f"Health check result: {'✅ PASS' if healthy else '❌ FAIL'}")

    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
