#!/usr/bin/env python3
"""
Regime Analyzer - Epic 17: US-17.7
Simplified regime detection and regime-aware performance analysis for trading strategies.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RegimeAnalyzer:
    """
    Simplified regime analyzer for market condition detection.
    """

    def __init__(self, sma_period: int = 200, volatility_window: int = 30):
        self.sma_period = sma_period
        self.volatility_window = volatility_window
        logger.info(
            f"RegimeAnalyzer initialized with SMA: {sma_period}, Volatility window: {volatility_window}"
        )

    def detect_regimes(
        self, price_data: pd.Series, volatility_data: Optional[pd.Series] = None
    ) -> pd.DataFrame:
        """Detect market regimes using price and volatility data."""
        try:
            # Ensure proper Series format
            if not isinstance(price_data, pd.Series):
                price_data = pd.Series(price_data)

            if price_data.index.dtype != "datetime64[ns]":
                price_data.index = pd.to_datetime(price_data.index)

            regimes = pd.DataFrame(index=price_data.index)

            # Calculate 200-day SMA and regime
            sma = price_data.rolling(window=self.sma_period).mean()
            regimes["price_regime"] = np.where(price_data > sma, "BULL", "BEAR")

            # Calculate volatility regime
            if volatility_data is not None:
                if not isinstance(volatility_data, pd.Series):
                    volatility_data = pd.Series(volatility_data)
                vol_threshold = volatility_data.rolling(252).mean()
                volatility_regime = np.where(
                    volatility_data > vol_threshold, "HIGH_VOL", "LOW_VOL"
                )
            else:
                # Calculate rolling volatility
                daily_returns = price_data.pct_change()
                rolling_vol = daily_returns.rolling(
                    window=self.volatility_window
                ).std() * np.sqrt(252)
                vol_threshold = rolling_vol.rolling(252).median()

                volatility_regime = np.where(
                    rolling_vol > vol_threshold, "HIGH_VOL", "LOW_VOL"
                )

            regimes["volatility_regime"] = volatility_regime

            # Combine regimes
            regimes["combined_regime"] = (
                regimes["price_regime"] + "_" + regimes["volatility_regime"]
            )

            logger.info(
                f"Detected regimes: {regimes['combined_regime'].value_counts().to_dict()}"
            )

            return regimes

        except Exception as e:
            logger.error(f"Error detecting regimes: {e}")
            return pd.DataFrame()

    def calculate_regime_metrics(
        self, returns: pd.Series, regimes: pd.DataFrame
    ) -> Dict:
        """Calculate performance metrics by regime."""
        try:
            # Handle duplicate indices by grouping and taking the last value
            if returns.index.duplicated().any():
                logger.warning(
                    f"Returns series has {returns.index.duplicated().sum()} duplicate indices, using last value"
                )
                returns = returns.groupby(returns.index).last()

            if regimes.index.duplicated().any():
                logger.warning(
                    f"Regimes DataFrame has {regimes.index.duplicated().sum()} duplicate indices, using last value"
                )
                regimes = regimes.groupby(regimes.index).last()

            # Align returns with regimes using merge to avoid index issues
            returns_df = returns.to_frame(name="returns")
            regimes_df = regimes[["combined_regime"]].copy()
            aligned_data = returns_df.join(regimes_df, how="inner")

            if len(aligned_data) == 0:
                logger.warning("No aligned data for regime metrics calculation")
                return {}

            regime_metrics = {}

            # Calculate metrics for each regime
            for regime in aligned_data["combined_regime"].unique():
                regime_mask = aligned_data["combined_regime"] == regime
                regime_returns = aligned_data.loc[regime_mask, "returns"]

                if len(regime_returns) == 0:
                    continue

                # Ensure regime_returns is a pandas Series
                if not isinstance(regime_returns, pd.Series):
                    regime_returns = pd.Series(regime_returns)

                regime_key = regime.lower().replace("_", "_")

                # Basic metrics
                regime_metrics[f"{regime_key}_count"] = len(regime_returns)
                regime_metrics[f"{regime_key}_return"] = regime_returns.sum()
                regime_metrics[f"{regime_key}_annual_return"] = (
                    regime_returns.mean() * 252
                )
                regime_metrics[f"{regime_key}_volatility"] = (
                    regime_returns.std() * np.sqrt(252)
                )

                # Risk-adjusted metrics
                if regime_returns.std() != 0:
                    regime_metrics[f"{regime_key}_sharpe"] = (
                        regime_returns.mean()
                        * 252
                        / (regime_returns.std() * np.sqrt(252))
                    )
                else:
                    regime_metrics[f"{regime_key}_sharpe"] = 0

                # Drawdown metrics
                cumulative = (1 + regime_returns).cumprod()
                running_max = cumulative.expanding().max()
                drawdown = (cumulative - running_max) / running_max

                regime_metrics[f"{regime_key}_max_drawdown"] = abs(drawdown.min())
                regime_metrics[f"{regime_key}_win_rate"] = (regime_returns > 0).mean()

            logger.info(f"Calculated regime metrics for {len(regime_metrics)} metrics")
            return regime_metrics

        except Exception as e:
            logger.error(f"Error calculating regime metrics: {e}")
            return {}

    def get_regime_performance_summary(
        self, returns: pd.Series, regimes: pd.DataFrame
    ) -> str:
        """Get a human-readable summary of regime performance."""
        try:
            regime_metrics = self.calculate_regime_metrics(returns, regimes)

            if not regime_metrics:
                return "No regime metrics available"

            summary_lines = ["Regime Performance Analysis:"]
            summary_lines.append("-" * 40)

            # Get unique regimes
            regime_keys = [
                k
                for k in regime_metrics.keys()
                if "_return" in k and not "annual_" in k
            ]

            for key in regime_keys:
                regime_name = key.replace("_return", "").upper()

                return_val = regime_metrics.get(key, 0)
                count = regime_metrics.get(f"{key.replace('_return', '')}_count", 0)
                sharpe = regime_metrics.get(f"{key.replace('_return', '')}_sharpe", 0)
                win_rate = regime_metrics.get(
                    f"{key.replace('_return', '')}_win_rate", 0
                )

                summary_lines.append(f"\n{regime_name}:")
                summary_lines.append(f"  Return: {return_val:.2%}")
                summary_lines.append(f"  Observations: {count}")
                summary_lines.append(f"  Sharpe Ratio: {sharpe:.2f}")
                summary_lines.append(f"  Win Rate: {win_rate:.2%}")

            return "\n".join(summary_lines)

        except Exception as e:
            logger.error(f"Error generating regime summary: {e}")
            return f"Error generating summary: {e}"
