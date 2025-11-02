"""
Optimization Results Loader for Streamlit Dashboard
Loads and processes optimization results from JSON files
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class OptimizationLoader:
    """Load and process optimization results from JSON files."""

    def __init__(self, results_dir: str = "/app/results/optimizations"):
        """
        Initialize optimization loader.

        Args:
            results_dir: Directory containing optimization JSON files
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def list_optimizations(self) -> List[Dict[str, Any]]:
        """
        List all available optimization runs.

        Returns:
            List of optimization summary dictionaries
        """
        optimizations = []

        try:
            for json_file in self.results_dir.glob("*.json"):
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)

                    # Extract summary
                    opt_id = json_file.stem
                    summary = {
                        'optimization_id': opt_id,
                        'optimization_id_short': opt_id[:8],
                        'algorithm': data.get('algorithm', 'Unknown'),
                        'optimization_metric': data.get('optimization_metric', 'Sharpe Ratio'),
                        'parameter_count': len(data.get('parameters', {})),
                        'result_count': len(data.get('results', [])),
                        'created_at': data.get('created_at', ''),
                        'status': data.get('status', 'COMPLETED')
                    }

                    optimizations.append(summary)

                except Exception as e:
                    logger.error(f"Error loading {json_file}: {e}")
                    continue

            # Sort by date (most recent first)
            optimizations.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        except Exception as e:
            logger.error(f"Error listing optimizations: {e}")

        return optimizations

    def load_optimization(self, optimization_id: str) -> Optional[Dict[str, Any]]:
        """
        Load full optimization data by ID.

        Args:
            optimization_id: Optimization UUID or filename

        Returns:
            Full optimization data dictionary or None
        """
        json_file = self.results_dir / f"{optimization_id}.json"

        if not json_file.exists():
            logger.error(f"Optimization file not found: {json_file}")
            return None

        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            data['optimization_id'] = optimization_id
            return data

        except Exception as e:
            logger.error(f"Error loading optimization {optimization_id}: {e}")
            return None

    def get_results_dataframe(self, optimization_id: str) -> Optional[pd.DataFrame]:
        """
        Get optimization results as DataFrame.

        Args:
            optimization_id: Optimization identifier

        Returns:
            DataFrame with parameter combinations and metrics
        """
        data = self.load_optimization(optimization_id)
        if not data:
            return None

        try:
            results = data.get('results', [])
            if not results:
                return None

            df = pd.DataFrame(results)

            # Flatten parameter dictionaries into columns
            if 'parameters' in df.columns:
                params_df = pd.json_normalize(df['parameters'])
                df = pd.concat([df.drop('parameters', axis=1), params_df], axis=1)

            return df

        except Exception as e:
            logger.error(f"Error creating results DataFrame: {e}")
            return None

    def get_parameter_heatmap_data(
        self,
        optimization_id: str,
        param1: str,
        param2: str,
        metric: str
    ) -> Optional[pd.DataFrame]:
        """
        Get data for parameter heatmap.

        Args:
            optimization_id: Optimization identifier
            param1: First parameter name
            param2: Second parameter name
            metric: Metric to display

        Returns:
            Pivoted DataFrame for heatmap
        """
        df = self.get_results_dataframe(optimization_id)
        if df is None:
            return None

        try:
            # Check if parameters exist
            if param1 not in df.columns or param2 not in df.columns or metric not in df.columns:
                logger.error(f"Parameters or metric not found in results")
                return None

            # Pivot for heatmap
            heatmap_df = df.pivot(index=param1, columns=param2, values=metric)

            return heatmap_df

        except Exception as e:
            logger.error(f"Error creating heatmap data: {e}")
            return None

    def save_optimization(
        self,
        algorithm: str,
        parameters: Dict[str, Dict[str, Any]],
        optimization_metric: str,
        results: List[Dict[str, Any]]
    ) -> str:
        """
        Save optimization results to JSON file.

        Args:
            algorithm: Algorithm name
            parameters: Parameter definitions
            optimization_metric: Metric being optimized
            results: List of result dictionaries

        Returns:
            Optimization ID
        """
        import uuid
        from datetime import datetime

        optimization_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        data = {
            'optimization_id': optimization_id,
            'algorithm': algorithm,
            'parameters': parameters,
            'optimization_metric': optimization_metric,
            'results': results,
            'created_at': timestamp,
            'status': 'COMPLETED'
        }

        json_file = self.results_dir / f"{optimization_id}.json"

        try:
            with open(json_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Optimization saved: {optimization_id}")
            return optimization_id

        except Exception as e:
            logger.error(f"Error saving optimization: {e}")
            raise
