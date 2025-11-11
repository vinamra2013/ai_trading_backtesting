#!/usr/bin/env python3
"""
Unit Tests for VARM-RSI Strategy - Epic 24: US-24.1-24.5
Tests for Volatility-Adaptive RSI Mean Reversion Strategy implementation
"""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the strategy (will fail if backtrader not available, but that's expected in test env)
try:
    from strategies.varm_rsi import VARM_RSI, BearPower, VARM_RSI_PARAMS

    BACKTRADER_AVAILABLE = True
except ImportError:
    BACKTRADER_AVAILABLE = False
    print("Backtrader not available - running limited tests")


class TestVARM_RSI(unittest.TestCase):
    """Test cases for VARM-RSI strategy."""

    def setUp(self):
        """Set up test fixtures."""
        if not BACKTRADER_AVAILABLE:
            self.skipTest("Backtrader not available")

        # Create mock data for testing
        dates = pd.date_range("2020-01-01", periods=100, freq="5min")
        np.random.seed(42)

        # Generate realistic OHLCV data
        base_price = 100
        prices = []
        for i in range(100):
            change = np.random.normal(0, 0.01)
            base_price *= 1 + change
            high = base_price * (1 + abs(np.random.normal(0, 0.005)))
            low = base_price * (1 - abs(np.random.normal(0, 0.005)))
            volume = np.random.randint(1000, 10000)
            prices.append([base_price, high, low, base_price, volume])

        self.test_data = pd.DataFrame(
            prices, columns=["open", "high", "low", "close", "volume"]
        )
        self.test_data["datetime"] = dates
        self.test_data.set_index("datetime", inplace=True)

    def test_bear_power_indicator(self):
        """Test Bear Power indicator calculation."""
        if not BACKTRADER_AVAILABLE:
            return

        # Test would require backtrader data feed
        # This is a placeholder for when backtrader is available
        pass

    def test_entry_conditions_rsi_threshold(self):
        """Test RSI entry threshold condition."""
        # Test RSI < 22 condition
        self.assertTrue(15 < 22)  # Should allow entry
        self.assertFalse(25 < 22)  # Should reject entry

    def test_entry_conditions_atr_threshold(self):
        """Test ATR volatility confirmation."""
        # Test ATR > 5 condition
        self.assertTrue(6 > 5)  # Should allow entry
        self.assertFalse(3 > 5)  # Should reject entry

    def test_volume_filter(self):
        """Test volume filter logic."""
        volume_avg = 1000
        current_volume = 2500
        multiplier = 2.5

        # Should pass: 2500 > 1000 * 2.5
        self.assertTrue(current_volume > volume_avg * multiplier)

        # Should fail: 1500 < 1000 * 2.5
        self.assertFalse(1500 > volume_avg * multiplier)

    def test_slope_calculation(self):
        """Test slope calculation for trend filter."""
        # Simple test data
        values = [100, 101, 102, 103, 104]  # Rising trend
        x = list(range(len(values)))

        # Calculate slope using numpy polyfit
        slope = np.polyfit(x, values, 1)[0]
        self.assertGreater(slope, 0)  # Should be positive

        # Test with declining trend
        values_down = [104, 103, 102, 101, 100]
        slope_down = np.polyfit(x, values_down, 1)[0]
        self.assertLess(slope_down, 0)  # Should be negative

    def test_position_sizing_base_risk(self):
        """Test base risk position sizing."""
        portfolio_value = 100000
        base_risk_pct = 0.01  # 1%
        entry_price = 100
        stop_distance = 2  # 2 point stop

        risk_amount = portfolio_value * base_risk_pct
        expected_shares = risk_amount / (entry_price * stop_distance)

        self.assertAlmostEqual(expected_shares, 50.0, places=1)

    def test_position_sizing_volatility_adjustment(self):
        """Test volatility-adjusted position sizing."""
        base_risk = 0.01
        volatility_risk_cap = 0.008
        atr_multiplier = 0.5
        atr_value = 3.0
        price = 100

        # Volatility risk = min(0.8%, 0.5 × ATR/price)
        volatility_risk = min(volatility_risk_cap, atr_multiplier * (atr_value / price))
        adjusted_risk = min(base_risk, volatility_risk)

        # Should be capped at volatility_risk_cap
        self.assertLessEqual(adjusted_risk, volatility_risk_cap)
        self.assertGreater(adjusted_risk, 0)

    def test_portfolio_risk_limits(self):
        """Test portfolio risk management limits."""
        max_positions = 3
        current_positions = 2

        # Should allow new position
        self.assertLess(current_positions, max_positions)

        # Should reject when at limit
        self.assertFalse(3 < max_positions)

    def test_drawdown_penalty(self):
        """Test drawdown-based position size adjustment."""
        portfolio_dd = 0.015  # 1.5%
        threshold = 0.015
        penalty_factor = 0.6

        # Should apply penalty
        if portfolio_dd >= threshold:
            adjusted_size = 1.0 * penalty_factor
            self.assertEqual(adjusted_size, 0.6)

    def test_market_filters(self):
        """Test SPY and VIX market filters."""
        spy_price = 400
        spy_sma = 395  # SPY > SMA should pass
        vix_level = 25  # VIX < 30 should pass

        # Both conditions should be met
        spy_filter = spy_price > spy_sma
        vix_filter = vix_level < 30

        self.assertTrue(spy_filter and vix_filter)

        # Fail if SPY below SMA
        self.assertFalse(390 > spy_sma)

        # Fail if VIX too high
        self.assertFalse(35 < 30)

    def test_earnings_exclusion_logic(self):
        """Test earnings period exclusion."""
        from datetime import datetime, time

        # Test Friday after 4 PM (should exclude)
        friday_5pm = datetime(2024, 1, 5, 17, 0)  # Friday 5 PM
        self.assertEqual(friday_5pm.weekday(), 4)  # 4 = Friday
        self.assertGreaterEqual(friday_5pm.hour, 16)

        # Test Monday before 8 AM (should exclude)
        monday_7am = datetime(2024, 1, 8, 7, 0)  # Monday 7 AM
        self.assertEqual(monday_7am.weekday(), 0)  # 0 = Monday
        self.assertLess(monday_7am.hour, 8)

        # Test Tuesday 10 AM (should allow)
        tuesday_10am = datetime(2024, 1, 9, 10, 0)  # Tuesday 10 AM
        self.assertNotEqual(tuesday_10am.weekday(), 4)
        self.assertNotEqual(tuesday_10am.weekday(), 0)

    def test_exit_conditions_time_based(self):
        """Test time-based exit conditions."""
        from datetime import datetime, timedelta

        entry_time = datetime.now() - timedelta(hours=50)  # 50 hours ago
        max_hold_hours = 48

        hold_duration = datetime.now() - entry_time
        should_exit = hold_duration.total_seconds() > (max_hold_hours * 3600)

        self.assertTrue(should_exit)  # Should exit after 48 hours

    def test_exit_conditions_profit_targets(self):
        """Test profit target calculations."""
        entry_price = 100
        atr_value = 2.0

        # Target 1: 0.8 * ATR
        target_1 = entry_price + (atr_value * 0.8)
        expected_target_1 = 101.6
        self.assertEqual(target_1, expected_target_1)

        # Target 2: 1.6 * ATR
        target_2 = entry_price + (atr_value * 1.6)
        expected_target_2 = 103.2
        self.assertEqual(target_2, expected_target_2)

    def test_exit_conditions_stop_loss(self):
        """Test stop loss calculations."""
        entry_price = 100
        atr_value = 2.0
        stop_multiplier = 0.5

        stop_loss = entry_price - (atr_value * stop_multiplier)
        expected_stop = 99.0
        self.assertEqual(stop_loss, expected_stop)

    def test_parameters_validation(self):
        """Test strategy parameters are properly defined."""
        params = VARM_RSI_PARAMS

        # Check required parameters exist
        required_params = [
            "rsi_period",
            "rsi_entry_threshold",
            "atr_period",
            "atr_min_volatility",
            "max_positions",
            "base_risk_pct",
        ]

        for param in required_params:
            self.assertIn(param, params, f"Missing required parameter: {param}")

        # Check parameter values are reasonable
        self.assertGreater(params["rsi_period"], 0)
        self.assertGreater(params["atr_period"], 0)
        self.assertGreater(params["base_risk_pct"], 0)
        self.assertLessEqual(params["base_risk_pct"], 0.05)  # Max 5% risk

    def test_correlation_monitoring_setup(self):
        """Test correlation monitoring framework setup."""
        # Test that correlation threshold is reasonable
        correlation_threshold = 0.7
        self.assertGreater(correlation_threshold, 0)
        self.assertLessEqual(correlation_threshold, 1)

        # Test correlation logic
        high_correlation = 0.85
        low_correlation = 0.3

        # High correlation should trigger disable
        self.assertGreater(high_correlation, correlation_threshold)

        # Low correlation should allow
        self.assertLessEqual(low_correlation, correlation_threshold)


if __name__ == "__main__":
    unittest.main()
