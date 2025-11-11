#!/usr/bin/env python3
"""
Unit Tests for Strategy Ranker - Epic 21: US-21.1 - Multi-Criteria Ranking System
Tests for multi-criteria strategy ranking functionality.
"""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import tempfile
import os
from pathlib import Path

# Import the modules to test
import sys
sys.path.append('scripts')
from strategy_ranker import StrategyRanker


class TestStrategyRanker(unittest.TestCase):
    """Test cases for StrategyRanker class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create sample backtest results data
        self.sample_results = pd.DataFrame({
            'strategy': ['SMA_Crossover', 'RSI_Momentum', 'Bollinger_Reversal', 'MACD_Crossover'],
            'symbol': ['SPY', 'QQQ', 'SPY', 'QQQ'],
            'sharpe_ratio': [1.5, 2.1, 0.8, 1.9],
            'max_drawdown': [-0.15, -0.12, -0.25, -0.18],
            'win_rate': [0.55, 0.62, 0.48, 0.58],
            'total_trades': [120, 95, 85, 110],
            'profit_factor': [1.3, 1.8, 0.9, 1.5],
            'total_return': [0.45, 0.78, 0.12, 0.65],
            'volatility': [0.18, 0.15, 0.22, 0.19],
            'avg_trade': [0.0038, 0.0082, 0.0014, 0.0059]
        })

        # Create temporary config file
        self.config_data = {
            'scoring': {
                'weights': {
                    'sharpe_ratio': 40,
                    'consistency': 20,
                    'drawdown_control': 20,
                    'trade_frequency': 10,
                    'capital_efficiency': 10
                },
                'consistency': {
                    'window_days': 30,
                    'min_periods': 10
                },
                'drawdown_control': {
                    'max_drawdown_weight': 1.0
                },
                'trade_frequency': {
                    'optimal_trades_per_month': 20,
                    'frequency_weight': 1.0
                },
                'capital_efficiency': {
                    'efficiency_weight': 1.0
                }
            }
        }

        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        import yaml
        yaml.dump(self.config_data, self.temp_config)
        self.temp_config.close()

    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_config.name)

    def test_initialization(self):
        """Test StrategyRanker initialization."""
        ranker = StrategyRanker(self.temp_config.name)

        self.assertIsInstance(ranker, StrategyRanker)
        self.assertEqual(ranker.scoring_weights['sharpe_ratio'], 40)
        self.assertEqual(ranker.scoring_weights['consistency'], 20)

    @patch('strategy_ranker.RankingResultsConsolidator')
    def test_rank_strategies_with_mock_data(self, mock_consolidator):
        """Test strategy ranking with mock consolidated data."""
        # Mock the consolidator
        mock_consolidator.return_value.consolidate_to_dataframe.return_value = self.sample_results

        ranker = StrategyRanker(self.temp_config.name)
        rankings = ranker.rank_strategies()

        # Check that rankings were generated
        self.assertIsInstance(rankings, pd.DataFrame)
        self.assertFalse(rankings.empty)
        self.assertIn('composite_score', rankings.columns)
        self.assertIn('sharpe_score', rankings.columns)
        self.assertIn('rank', rankings.columns)

        # Check ranking order (higher composite score should be first)
        self.assertEqual(rankings.iloc[0]['strategy'], 'RSI_Momentum')  # Should be highest ranked

    def test_calculate_sharpe_score(self):
        """Test Sharpe ratio score calculation."""
        ranker = StrategyRanker(self.temp_config.name)

        scores = ranker._calculate_sharpe_score(self.sample_results)

        # Check that scores are normalized to 0-100
        self.assertTrue(all(0 <= score <= 100 for score in scores))

        # RSI_Momentum should have highest Sharpe score
        rsi_idx = self.sample_results[self.sample_results['strategy'] == 'RSI_Momentum'].index[0]
        self.assertEqual(scores.iloc[rsi_idx], 100.0)  # Highest Sharpe should be 100

    def test_calculate_drawdown_score(self):
        """Test drawdown control score calculation."""
        ranker = StrategyRanker(self.temp_config.name)

        scores = ranker._calculate_drawdown_score(self.sample_results)

        # Check that scores are normalized to 0-100
        self.assertTrue(all(0 <= score <= 100 for score in scores))

        # RSI_Momentum should have highest drawdown score (least drawdown)
        rsi_idx = self.sample_results[self.sample_results['strategy'] == 'RSI_Momentum'].index[0]
        self.assertEqual(scores.iloc[rsi_idx], 100.0)  # Least drawdown should be 100

    def test_calculate_frequency_score(self):
        """Test trade frequency score calculation."""
        ranker = StrategyRanker(self.temp_config.name)

        scores = ranker._calculate_frequency_score(self.sample_results)

        # Check that scores are normalized to 0-100
        self.assertTrue(all(0 <= score <= 100 for score in scores))

        # SMA_Crossover should have highest frequency score (most trades)
        sma_idx = self.sample_results[self.sample_results['strategy'] == 'SMA_Crossover'].index[0]
        self.assertEqual(scores.iloc[sma_idx], 100.0)  # Most trades should be 100

    def test_calculate_capital_efficiency_score(self):
        """Test capital efficiency score calculation."""
        ranker = StrategyRanker(self.temp_config.name)

        scores = ranker._calculate_capital_efficiency_score(self.sample_results)

        # Check that scores are normalized to 0-100
        self.assertTrue(all(0 <= score <= 100 for score in scores))

        # RSI_Momentum should have highest efficiency score (best profit factor)
        rsi_idx = self.sample_results[self.sample_results['strategy'] == 'RSI_Momentum'].index[0]
        self.assertEqual(scores.iloc[rsi_idx], 100.0)  # Best profit factor should be 100

    def test_calculate_composite_score(self):
        """Test composite score calculation."""
        ranker = StrategyRanker(self.temp_config.name)

        # Add individual scores to dataframe
        df = self.sample_results.copy()
        df['sharpe_score'] = ranker._calculate_sharpe_score(df)
        df['consistency_score'] = 75.0  # Mock consistency score
        df['drawdown_score'] = ranker._calculate_drawdown_score(df)
        df['frequency_score'] = ranker._calculate_frequency_score(df)
        df['efficiency_score'] = ranker._calculate_capital_efficiency_score(df)

        composite_scores = ranker._calculate_composite_score(df)

        # Check that composite scores are calculated correctly
        expected_weights = ranker.scoring_weights
        for idx, row in df.iterrows():
            expected = (
                row['sharpe_score'] * expected_weights['sharpe_ratio'] / 100 +
                row['consistency_score'] * expected_weights['consistency'] / 100 +
                row['drawdown_score'] * expected_weights['drawdown_control'] / 100 +
                row['frequency_score'] * expected_weights['trade_frequency'] / 100 +
                row['efficiency_score'] * expected_weights['capital_efficiency'] / 100
            )
            self.assertAlmostEqual(composite_scores.iloc[idx], expected, places=2)

    def test_get_top_strategies(self):
        """Test getting top N strategies."""
        ranker = StrategyRanker(self.temp_config.name)

        # Create mock ranked dataframe
        ranked_df = pd.DataFrame({
            'strategy': ['A', 'B', 'C', 'D'],
            'composite_score': [85, 90, 75, 80],
            'rank': [2, 1, 4, 3]
        })

        top_strategies = ranker.get_top_strategies(ranked_df, top_n=2)

        self.assertEqual(len(top_strategies), 2)
        self.assertEqual(top_strategies.iloc[0]['strategy'], 'B')  # Highest score
        self.assertEqual(top_strategies.iloc[1]['strategy'], 'A')  # Second highest

    def test_get_ranking_summary(self):
        """Test ranking summary generation."""
        ranker = StrategyRanker(self.temp_config.name)

        # Create mock ranked dataframe
        ranked_df = pd.DataFrame({
            'strategy': ['A', 'B', 'C'],
            'symbol': ['SPY', 'QQQ', 'SPY'],
            'composite_score': [85, 90, 75],
            'sharpe_ratio': [1.5, 2.0, 1.2]
        })

        summary = ranker.get_ranking_summary(ranked_df)

        self.assertIn('total_strategies_ranked', summary)
        self.assertIn('top_strategy', summary)
        self.assertIn('score_distribution', summary)
        self.assertEqual(summary['total_strategies_ranked'], 3)
        self.assertEqual(summary['top_strategy']['name'], 'B')

    def test_export_rankings(self):
        """Test ranking export functionality."""
        ranker = StrategyRanker(self.temp_config.name)

        # Create mock ranked dataframe
        ranked_df = pd.DataFrame({
            'rank': [1, 2],
            'strategy': ['A', 'B'],
            'symbol': ['SPY', 'QQQ'],
            'composite_score': [90, 85],
            'sharpe_ratio': [2.0, 1.8]
        })

        # Test CSV export
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            output_path = ranker.export_rankings(ranked_df, temp_file.name, 'csv')

            self.assertTrue(os.path.exists(output_path))

            # Verify content
            exported_df = pd.read_csv(output_path)
            self.assertEqual(len(exported_df), 2)
            self.assertIn('composite_score', exported_df.columns)

            os.unlink(output_path)

    def test_empty_results_handling(self):
        """Test handling of empty results."""
        ranker = StrategyRanker(self.temp_config.name)

        empty_df = pd.DataFrame()
        rankings = ranker.rank_strategies(results_df=empty_df)

        self.assertTrue(rankings.empty)

        # Test get_top_strategies with empty df
        top_strategies = ranker.get_top_strategies(empty_df)
        self.assertTrue(top_strategies.empty)

        # Test get_ranking_summary with empty df
        summary = ranker.get_ranking_summary(empty_df)
        self.assertEqual(summary, {})


if __name__ == '__main__':
    unittest.main()