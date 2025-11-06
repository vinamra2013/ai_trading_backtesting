#!/usr/bin/env python3
"""
Unit Tests for Correlation Analyzer - Epic 21: US-21.2 - Correlation Analysis Engine
Tests for correlation matrix calculation and strategy filtering functionality.
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
from correlation_analyzer import CorrelationAnalyzer


class TestCorrelationAnalyzer(unittest.TestCase):
    """Test cases for CorrelationAnalyzer class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create sample strategy rankings data
        self.sample_rankings = pd.DataFrame({
            'strategy': ['SMA_Crossover', 'RSI_Momentum', 'Bollinger_Reversal', 'MACD_Crossover'],
            'symbol': ['SPY', 'QQQ', 'SPY', 'QQQ'],
            'composite_score': [85, 90, 75, 80],
            'sharpe_ratio': [1.5, 2.1, 0.8, 1.9],
            'max_drawdown': [-0.15, -0.12, -0.25, -0.18]
        })

        # Create sample returns data for correlation calculation
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        np.random.seed(42)  # For reproducible results

        # Create correlated return series
        base_returns = np.random.normal(0.001, 0.02, 100)

        self.sample_returns = pd.DataFrame({
            'SMA_Crossover_SPY': base_returns + np.random.normal(0, 0.005, 100),
            'RSI_Momentum_QQQ': base_returns * 0.8 + np.random.normal(0, 0.005, 100),  # Highly correlated
            'Bollinger_Reversal_SPY': base_returns * -0.6 + np.random.normal(0, 0.005, 100),  # Moderately correlated
            'MACD_Crossover_QQQ': np.random.normal(0.001, 0.02, 100)  # Uncorrelated
        }, index=dates)

    def test_initialization(self):
        """Test CorrelationAnalyzer initialization."""
        analyzer = CorrelationAnalyzer(threshold=0.7, method='pearson')

        self.assertIsInstance(analyzer, CorrelationAnalyzer)
        self.assertEqual(analyzer.threshold, 0.7)
        self.assertEqual(analyzer.method, 'pearson')
        self.assertEqual(analyzer.min_periods, 30)

    def test_calculate_correlation_matrix(self):
        """Test correlation matrix calculation."""
        analyzer = CorrelationAnalyzer()

        corr_matrix = analyzer.calculate_correlation_matrix(self.sample_rankings)

        # Check that correlation matrix is created
        self.assertIsInstance(corr_matrix, pd.DataFrame)
        self.assertEqual(corr_matrix.shape, (4, 4))  # 4 strategies
        self.assertTrue(all(corr_matrix.index == corr_matrix.columns))

        # Check that diagonal is 1 (perfect correlation with self)
        np.testing.assert_array_almost_equal(np.diag(corr_matrix), 1.0)

        # Check that matrix is symmetric
        self.assertTrue(np.allclose(corr_matrix, corr_matrix.T))

    def test_correlation_matrix_with_returns_data(self):
        """Test correlation matrix calculation with actual returns data."""
        analyzer = CorrelationAnalyzer()

        # Mock the method to use our sample returns
        with patch.object(analyzer, '_get_strategy_returns', return_value=self.sample_returns):
            corr_matrix = analyzer.calculate_correlation_matrix(self.sample_rankings)

            self.assertIsInstance(corr_matrix, pd.DataFrame)
            self.assertEqual(corr_matrix.shape, (4, 4))

            # Check correlations are within valid range
            self.assertTrue(corr_matrix.min().min() >= -1)
            self.assertTrue(corr_matrix.max().max() <= 1)

    def test_different_correlation_methods(self):
        """Test different correlation methods."""
        methods = ['pearson', 'spearman', 'kendall']

        for method in methods:
            with self.subTest(method=method):
                analyzer = CorrelationAnalyzer(method=method)

                with patch.object(analyzer, '_get_strategy_returns', return_value=self.sample_returns):
                    corr_matrix = analyzer.calculate_correlation_matrix(self.sample_rankings)

                    self.assertIsInstance(corr_matrix, pd.DataFrame)
                    self.assertEqual(corr_matrix.shape, (4, 4))

    def test_invalid_correlation_method(self):
        """Test error handling for invalid correlation method."""
        with self.assertRaises(ValueError):
            CorrelationAnalyzer(method='invalid_method')

    def test_filter_correlated_strategies(self):
        """Test filtering of correlated strategies."""
        analyzer = CorrelationAnalyzer(threshold=0.5)  # Lower threshold for testing

        # Create a correlation matrix with known correlations
        corr_matrix = pd.DataFrame({
            'A': [1.0, 0.8, 0.3, 0.1],
            'B': [0.8, 1.0, 0.2, 0.4],
            'C': [0.3, 0.2, 1.0, 0.9],
            'D': [0.1, 0.4, 0.9, 1.0]
        }, index=['A', 'B', 'C', 'D'])

        # Mock the correlation matrix calculation
        with patch.object(analyzer, 'calculate_correlation_matrix', return_value=corr_matrix):
            filtered_df = analyzer.filter_correlated_strategies(self.sample_rankings)

            # Should filter out highly correlated strategies
            self.assertIsInstance(filtered_df, pd.DataFrame)
            self.assertTrue(len(filtered_df) <= len(self.sample_rankings))

    def test_greedy_selection_algorithm(self):
        """Test the greedy selection algorithm for diversity."""
        analyzer = CorrelationAnalyzer()

        # Create test data with known correlations
        test_strategies = ['High_Return', 'Correlated_A', 'Correlated_B', 'Uncorrelated']
        test_corr = pd.DataFrame({
            'High_Return': [1.0, 0.9, 0.8, 0.1],
            'Correlated_A': [0.9, 1.0, 0.85, 0.2],
            'Correlated_B': [0.8, 0.85, 1.0, 0.3],
            'Uncorrelated': [0.1, 0.2, 0.3, 1.0]
        }, index=test_strategies)

        rankings_with_scores = self.sample_rankings.copy()
        rankings_with_scores['composite_score'] = [95, 90, 85, 80]  # High_Return gets highest score

        selected = analyzer._greedy_diversity_selection(test_strategies, test_corr, max_select=2)

        # Should select High_Return (highest score) and Uncorrelated (most diverse)
        self.assertIn('High_Return', selected)
        self.assertIn('Uncorrelated', selected)
        self.assertEqual(len(selected), 2)

    def test_get_correlation_summary(self):
        """Test correlation summary generation."""
        analyzer = CorrelationAnalyzer(threshold=0.7)

        # Create test correlation matrix
        corr_matrix = pd.DataFrame({
            'A': [1.0, 0.8, 0.2],
            'B': [0.8, 1.0, 0.3],
            'C': [0.2, 0.3, 1.0]
        }, index=['A', 'B', 'C'])

        summary = analyzer.get_correlation_summary(corr_matrix)

        self.assertIn('num_strategies', summary)
        self.assertIn('correlation_method', summary)
        self.assertIn('avg_correlation', summary)
        self.assertIn('highly_correlated_pairs', summary)

        self.assertEqual(summary['num_strategies'], 3)
        self.assertEqual(summary['correlation_method'], 'pearson')
        self.assertEqual(summary['threshold'], 0.7)

    def test_empty_correlation_matrix_handling(self):
        """Test handling of empty correlation matrices."""
        analyzer = CorrelationAnalyzer()

        empty_matrix = pd.DataFrame()
        summary = analyzer.get_correlation_summary(empty_matrix)

        self.assertEqual(summary, {})

    def test_export_correlation_matrix(self):
        """Test correlation matrix export functionality."""
        analyzer = CorrelationAnalyzer()

        # Create test correlation matrix
        corr_matrix = pd.DataFrame({
            'A': [1.0, 0.5],
            'B': [0.5, 1.0]
        }, index=['A', 'B'])

        # Test CSV export
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            output_path = analyzer.export_correlation_matrix(corr_matrix, temp_file.name, 'csv')

            self.assertTrue(os.path.exists(output_path))

            # Verify content
            exported_df = pd.read_csv(output_path, index_col=0)
            pd.testing.assert_frame_equal(corr_matrix, exported_df, check_dtype=False)

            os.unlink(output_path)

    def test_find_correlation_clusters(self):
        """Test correlation cluster identification."""
        analyzer = CorrelationAnalyzer(cluster_threshold=0.7)

        # Create test correlation matrix with clear clusters
        corr_matrix = pd.DataFrame({
            'A': [1.0, 0.9, 0.1, 0.2],
            'B': [0.9, 1.0, 0.1, 0.2],
            'C': [0.1, 0.1, 1.0, 0.8],
            'D': [0.2, 0.2, 0.8, 1.0]
        }, index=['A', 'B', 'C', 'D'])

        clusters = analyzer.find_correlation_clusters(corr_matrix)

        # Should find 2 clusters: [A, B] and [C, D]
        self.assertIsInstance(clusters, list)
        self.assertTrue(len(clusters) >= 1)

        # Check that clusters contain the expected groupings
        cluster_strategies = [strategy for cluster in clusters for strategy in cluster]
        self.assertEqual(set(cluster_strategies), {'A', 'B', 'C', 'D'})

    def test_get_diversification_score(self):
        """Test diversification score calculation."""
        analyzer = CorrelationAnalyzer()

        # Create test correlation matrix
        corr_matrix = pd.DataFrame({
            'A': [1.0, 0.5, 0.8],
            'B': [0.5, 1.0, 0.3],
            'C': [0.8, 0.3, 1.0]
        }, index=['A', 'B', 'C'])

        selected_strategies = ['A', 'B', 'C']
        score = analyzer.get_diversification_score(selected_strategies, corr_matrix)

        # Score should be between 0 and 1
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

        # Test with single strategy (should return 0)
        single_score = analyzer.get_diversification_score(['A'], corr_matrix)
        self.assertEqual(single_score, 0.0)

        # Test with empty selection
        empty_score = analyzer.get_diversification_score([], corr_matrix)
        self.assertEqual(empty_score, 0.0)

    def test_plot_correlation_heatmap(self):
        """Test correlation heatmap generation."""
        analyzer = CorrelationAnalyzer()

        # Create test correlation matrix
        corr_matrix = pd.DataFrame({
            'A': [1.0, 0.5],
            'B': [0.5, 1.0]
        }, index=['A', 'B'])

        # Test heatmap generation without saving
        result = analyzer.plot_correlation_heatmap(corr_matrix)
        self.assertIsNone(result)  # Should return None when not saving

        # Test heatmap generation with save path
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            result = analyzer.plot_correlation_heatmap(corr_matrix, save_path=temp_file.name)
            self.assertEqual(result, temp_file.name)
            self.assertTrue(os.path.exists(temp_file.name))
            os.unlink(temp_file.name)

    def test_empty_data_handling(self):
        """Test handling of empty input data."""
        analyzer = CorrelationAnalyzer()

        # Test with empty rankings
        empty_rankings = pd.DataFrame()
        corr_matrix = analyzer.calculate_correlation_matrix(empty_rankings)
        self.assertTrue(corr_matrix.empty)

        # Test diversification score with empty correlation matrix
        score = analyzer.get_diversification_score(['A'], pd.DataFrame())
        self.assertEqual(score, 0.0)


if __name__ == '__main__':
    unittest.main()