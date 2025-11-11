#!/usr/bin/env python3
"""
Market Hours Utility - US market hours and trading day calculations.

US-5.1: Live Trading Engine - Market hours handling
"""

import logging
from datetime import datetime, date, time, timedelta
from typing import Optional
from pathlib import Path
import yaml
import pytz
from dateutil.easter import easter

logger = logging.getLogger(__name__)


class MarketHours:
    """
    Market hours utility for US equity markets.

    Handles timezone-aware calculations for market hours, pre-market,
    after-hours, and US market holidays.
    """

    def __init__(self, config_path: str = "config/live_trading_config.yaml"):
        """
        Initialize MarketHours with configuration.

        Args:
            config_path: Path to live trading configuration file

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            ValueError: If configuration is invalid
        """
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        self._load_config()
        self._initialize_timezone()
        logger.info(f"MarketHours initialized with timezone: {self.timezone}")

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            trading_hours = config.get('trading_hours', {})

            # Parse timezone
            self.timezone_str = trading_hours.get('timezone', 'America/New_York')

            # Parse regular trading hours
            self.market_open_str = trading_hours.get('market_open', '09:30')
            self.market_close_str = trading_hours.get('market_close', '16:00')

            # Parse extended hours
            self.pre_market_start_str = trading_hours.get('pre_market_start', '04:00')
            self.after_hours_end_str = trading_hours.get('after_hours_end', '20:00')

            logger.debug(f"Loaded config: {trading_hours}")

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ValueError(f"Invalid configuration file: {e}")

    def _initialize_timezone(self) -> None:
        """Initialize timezone and parse time values."""
        try:
            self.timezone = pytz.timezone(self.timezone_str)

            # Parse times
            self.market_open_time = self._parse_time(self.market_open_str)
            self.market_close_time = self._parse_time(self.market_close_str)
            self.pre_market_start_time = self._parse_time(self.pre_market_start_str)
            self.after_hours_end_time = self._parse_time(self.after_hours_end_str)

        except Exception as e:
            logger.error(f"Failed to initialize timezone: {e}")
            raise ValueError(f"Invalid timezone or time format: {e}")

    @staticmethod
    def _parse_time(time_str: str) -> time:
        """
        Parse time string in HH:MM or HH:MM:SS format.

        Args:
            time_str: Time string to parse

        Returns:
            time object
        """
        try:
            if len(time_str) == 5:  # HH:MM
                return datetime.strptime(time_str, "%H:%M").time()
            else:  # HH:MM:SS
                return datetime.strptime(time_str, "%H:%M:%S").time()
        except ValueError as e:
            raise ValueError(f"Invalid time format '{time_str}': {e}")

    def is_trading_day(self, check_date: Optional[date] = None) -> bool:
        """
        Check if a given date is a trading day (Mon-Fri, not a holiday).

        Args:
            check_date: Date to check (defaults to today)

        Returns:
            True if trading day, False otherwise
        """
        if check_date is None:
            check_date = datetime.now(self.timezone).date()

        # Check if weekend
        if check_date.weekday() >= 5:  # Saturday=5, Sunday=6
            return False

        # Check if holiday
        if self._is_market_holiday(check_date):
            return False

        return True

    def _is_market_holiday(self, check_date: date) -> bool:
        """
        Check if date is a US market holiday.

        Args:
            check_date: Date to check

        Returns:
            True if market holiday, False otherwise
        """
        year = check_date.year

        # Fixed holidays
        holidays = [
            date(year, 1, 1),   # New Year's Day
            date(year, 7, 4),   # Independence Day
            date(year, 12, 25), # Christmas
        ]

        # MLK Day: 3rd Monday in January
        holidays.append(self._nth_weekday(year, 1, 0, 3))

        # Presidents Day: 3rd Monday in February
        holidays.append(self._nth_weekday(year, 2, 0, 3))

        # Good Friday: 2 days before Easter
        easter_date = easter(year)
        holidays.append(easter_date - timedelta(days=2))

        # Memorial Day: Last Monday in May
        holidays.append(self._last_weekday(year, 5, 0))

        # Labor Day: 1st Monday in September
        holidays.append(self._nth_weekday(year, 9, 0, 1))

        # Thanksgiving: 4th Thursday in November
        holidays.append(self._nth_weekday(year, 11, 3, 4))

        # Adjust holidays that fall on weekends
        adjusted_holidays = []
        for holiday in holidays:
            if holiday.weekday() == 5:  # Saturday
                adjusted_holidays.append(holiday - timedelta(days=1))  # Friday
            elif holiday.weekday() == 6:  # Sunday
                adjusted_holidays.append(holiday + timedelta(days=1))  # Monday
            else:
                adjusted_holidays.append(holiday)

        return check_date in adjusted_holidays

    @staticmethod
    def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
        """
        Find the nth occurrence of a weekday in a month.

        Args:
            year: Year
            month: Month (1-12)
            weekday: Weekday (0=Monday, 6=Sunday)
            n: Occurrence number (1=first, 2=second, etc.)

        Returns:
            Date of the nth weekday
        """
        first_day = date(year, month, 1)
        first_weekday = first_day.weekday()

        # Calculate days until the first occurrence of the target weekday
        days_until = (weekday - first_weekday) % 7
        first_occurrence = first_day + timedelta(days=days_until)

        # Add weeks to get to the nth occurrence
        return first_occurrence + timedelta(weeks=n - 1)

    @staticmethod
    def _last_weekday(year: int, month: int, weekday: int) -> date:
        """
        Find the last occurrence of a weekday in a month.

        Args:
            year: Year
            month: Month (1-12)
            weekday: Weekday (0=Monday, 6=Sunday)

        Returns:
            Date of the last weekday
        """
        # Start from the last day of the month
        if month == 12:
            last_day = date(year, 12, 31)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        # Work backwards to find the last occurrence of the weekday
        while last_day.weekday() != weekday:
            last_day -= timedelta(days=1)

        return last_day

    def is_trading_hours(self, check_datetime: Optional[datetime] = None) -> bool:
        """
        Check if currently within regular trading hours (9:30 AM - 4:00 PM ET).

        Args:
            check_datetime: Datetime to check (defaults to now)

        Returns:
            True if within trading hours, False otherwise
        """
        if check_datetime is None:
            check_datetime = datetime.now(self.timezone)
        elif check_datetime.tzinfo is None:
            check_datetime = self.timezone.localize(check_datetime)
        else:
            check_datetime = check_datetime.astimezone(self.timezone)

        # Check if trading day
        if not self.is_trading_day(check_datetime.date()):
            return False

        # Check time range
        current_time = check_datetime.time()
        return self.market_open_time <= current_time < self.market_close_time

    def is_pre_market(self, check_datetime: Optional[datetime] = None) -> bool:
        """
        Check if currently in pre-market hours (4:00 AM - 9:30 AM ET).

        Args:
            check_datetime: Datetime to check (defaults to now)

        Returns:
            True if pre-market, False otherwise
        """
        if check_datetime is None:
            check_datetime = datetime.now(self.timezone)
        elif check_datetime.tzinfo is None:
            check_datetime = self.timezone.localize(check_datetime)
        else:
            check_datetime = check_datetime.astimezone(self.timezone)

        # Check if trading day
        if not self.is_trading_day(check_datetime.date()):
            return False

        # Check time range
        current_time = check_datetime.time()
        return self.pre_market_start_time <= current_time < self.market_open_time

    def is_after_hours(self, check_datetime: Optional[datetime] = None) -> bool:
        """
        Check if currently in after-hours (4:00 PM - 8:00 PM ET).

        Args:
            check_datetime: Datetime to check (defaults to now)

        Returns:
            True if after-hours, False otherwise
        """
        if check_datetime is None:
            check_datetime = datetime.now(self.timezone)
        elif check_datetime.tzinfo is None:
            check_datetime = self.timezone.localize(check_datetime)
        else:
            check_datetime = check_datetime.astimezone(self.timezone)

        # Check if trading day
        if not self.is_trading_day(check_datetime.date()):
            return False

        # Check time range
        current_time = check_datetime.time()
        return self.market_close_time <= current_time < self.after_hours_end_time

    def is_market_open(self, check_datetime: Optional[datetime] = None) -> bool:
        """
        Check if market is currently open (regular hours, pre-market, or after-hours).

        Args:
            check_datetime: Datetime to check (defaults to now)

        Returns:
            True if market is open, False otherwise
        """
        return (self.is_trading_hours(check_datetime) or
                self.is_pre_market(check_datetime) or
                self.is_after_hours(check_datetime))

    def get_market_open_time(self, check_date: Optional[date] = None) -> Optional[datetime]:
        """
        Get market open datetime for a given date.

        Args:
            check_date: Date to check (defaults to today)

        Returns:
            Timezone-aware datetime of market open, or None if not a trading day
        """
        if check_date is None:
            check_date = datetime.now(self.timezone).date()

        if not self.is_trading_day(check_date):
            return None

        # Combine date and time, then localize to timezone
        naive_datetime = datetime.combine(check_date, self.market_open_time)
        return self.timezone.localize(naive_datetime)

    def get_market_close_time(self, check_date: Optional[date] = None) -> Optional[datetime]:
        """
        Get market close datetime for a given date.

        Args:
            check_date: Date to check (defaults to today)

        Returns:
            Timezone-aware datetime of market close, or None if not a trading day
        """
        if check_date is None:
            check_date = datetime.now(self.timezone).date()

        if not self.is_trading_day(check_date):
            return None

        # Combine date and time, then localize to timezone
        naive_datetime = datetime.combine(check_date, self.market_close_time)
        return self.timezone.localize(naive_datetime)

    def seconds_until_market_open(self, from_datetime: Optional[datetime] = None) -> Optional[int]:
        """
        Calculate seconds until next market open.

        Args:
            from_datetime: Starting datetime (defaults to now)

        Returns:
            Seconds until market open, or None if market is currently open
        """
        if from_datetime is None:
            from_datetime = datetime.now(self.timezone)
        elif from_datetime.tzinfo is None:
            from_datetime = self.timezone.localize(from_datetime)
        else:
            from_datetime = from_datetime.astimezone(self.timezone)

        # If market is currently open, return None
        if self.is_market_open(from_datetime):
            return None

        # Find next trading day
        check_date = from_datetime.date()
        max_days = 10  # Prevent infinite loop

        for _ in range(max_days):
            # Check if today and before market open
            if self.is_trading_day(check_date):
                market_open = self.get_market_open_time(check_date)
                if from_datetime < market_open:
                    delta = market_open - from_datetime
                    return int(delta.total_seconds())

            # Move to next day
            check_date += timedelta(days=1)

        logger.warning("Could not find next market open within 10 days")
        return None

    def seconds_until_market_close(self, from_datetime: Optional[datetime] = None) -> Optional[int]:
        """
        Calculate seconds until market close.

        Args:
            from_datetime: Starting datetime (defaults to now)

        Returns:
            Seconds until market close, or None if market is closed
        """
        if from_datetime is None:
            from_datetime = datetime.now(self.timezone)
        elif from_datetime.tzinfo is None:
            from_datetime = self.timezone.localize(from_datetime)
        else:
            from_datetime = from_datetime.astimezone(self.timezone)

        # If market is not open, return None
        if not self.is_market_open(from_datetime):
            return None

        # Get today's market close
        market_close = self.get_market_close_time(from_datetime.date())
        if market_close is None:
            return None

        delta = market_close - from_datetime
        return int(delta.total_seconds())
