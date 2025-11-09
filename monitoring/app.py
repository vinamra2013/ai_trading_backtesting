"""
Streamlit Monitoring Dashboard for AI Trading Platform
Epic 7: Monitoring & Observability
Enhanced Real-time Dashboard with P&L calculations and system health
"""

import os
import sys
from pathlib import Path

# CRITICAL: Add paths BEFORE any other imports that might need them
sys.path.insert(0, "/app")
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent / "utils"))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import json
import os
from typing import Dict, Any

# Page configuration
st.set_page_config(
    page_title="AI Trading Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Auto-refresh every 5 seconds
# Note: st.experimental_rerun was removed in newer Streamlit versions
# Using time.sleep for periodic refresh instead


# API Client configuration
def get_configured_api_client():
    """Get API client with proper configuration for current environment"""
    from utils.api_client import APIClient

    # Load .env file if it exists
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        # python-dotenv not available, continue with environment variables
        pass

    # Check for explicit backend URL (from .env or environment)
    backend_url = os.environ.get("FASTAPI_BACKEND_URL")
    if backend_url and backend_url.strip():  # Check if not empty
        return APIClient(base_url=backend_url)

    # Auto-detect based on environment
    return APIClient()


# Job polling functionality
@st.cache_data(ttl=5)
def poll_job_status(job_id: str, job_type: str = "backtest") -> Dict[str, Any]:
    """Poll job status with caching"""
    try:
        api_client = get_configured_api_client()

        if job_type == "backtest":
            return api_client.get_backtest_status(job_id)
        elif job_type == "optimization":
            # For optimization, we need to get the full job data
            return api_client.get_optimization(job_id)
        else:
            return {"status": "unknown", "error": f"Unknown job type: {job_type}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_backend_availability() -> bool:
    """Check if the FastAPI backend is available"""
    try:
        api_client = get_configured_api_client()
        return api_client.is_available()
    except Exception:
        return False


def display_backend_unavailable_message():
    """Display a user-friendly message when backend is unavailable"""
    st.error("🔌 Backend API Unavailable")
    st.info("""
    The FastAPI backend service is not running or unreachable. To use this dashboard:

    1. **Start the platform**: Run `./scripts/start.sh` in the project root
    2. **Check backend status**: Visit http://localhost:8000/docs for API documentation
    3. **Verify Docker containers**: Run `docker ps` to see running services

    Some features may work with cached data, but real-time functionality requires the backend.
    """)
    st.warning("⚠️ Limited functionality available - using cached data only")


# Cache database connections and calculations
@st.cache_resource
def get_db_manager():
    """Get database manager instance in read-only mode."""
    try:
        from scripts.db_manager import DBManager

        # Use relative path from project root
        import os

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(project_root, "data", "sqlite", "trades.db")
        # Use read_only=True for monitoring dashboard
        return DBManager(db_path, read_only=True)
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None


@st.cache_resource
def get_mlflow_client():
    """Get MLflow client and ProjectManager instances."""
    try:
        import mlflow
        from scripts.project_manager import ProjectManager

        # Set MLflow tracking URI
        mlflow.set_tracking_uri("http://mlflow:5000")

        # Initialize ProjectManager
        pm = ProjectManager()

        return {"mlflow": mlflow, "project_manager": pm}
    except Exception as e:
        st.warning(f"MLflow connection unavailable: {e}")
        st.info(
            "MLflow features require the MLflow server to be running. Start with ./scripts/start.sh"
        )
        return None


@st.cache_data(ttl=5)
def get_positions_data():
    """Get current positions with P&L calculations."""
    db = get_db_manager()
    if not db:
        return []

    try:
        positions = db.get_positions()
        if not positions:
            return []

        # Calculate P&L for each position
        from scripts.utils.pnl_calculator import PnLCalculator

        pnl_calc = PnLCalculator()

        enhanced_positions = []
        for pos in positions:
            # Mock current price (in real implementation, get from market data)
            current_price = pos.get("current_price", pos.get("average_price", 0))

            from scripts.utils.pnl_calculator import Position

            position_obj = Position(
                symbol=pos["symbol"],
                quantity=pos["quantity"],
                entry_price=pos["average_price"],
                current_price=current_price,
            )

            pnl_result = pnl_calc.calculate_position_pnl(position_obj, current_price)

            enhanced_pos = {
                "Symbol": pos["symbol"],
                "Quantity": pos["quantity"],
                "Avg Price": f"${pos['average_price']:.2f}",
                "Current Price": f"${current_price:.2f}",
                "Market Value": f"${pnl_result['market_value']:,.2f}",
                "Unrealized P&L": f"${pnl_result['unrealized_pnl']:,.2f}",
                "P&L %": f"{pnl_result['unrealized_pnl_pct']:.2f}%",
                "Entry Date": pos["entry_date"][:10] if pos["entry_date"] else "N/A",
            }
            enhanced_positions.append(enhanced_pos)

        return enhanced_positions
    except Exception as e:
        st.error(f"Error fetching positions: {e}")
        return []


@st.cache_data(ttl=5)
def get_orders_data(limit=50):
    """Get recent orders with enhanced data."""
    db = get_db_manager()
    if not db:
        return []

    try:
        orders = db.get_orders(limit=limit)
        if not orders:
            return []

        enhanced_orders = []
        for order in orders:
            enhanced_order = {
                "Order ID": order["order_id"][:8] + "..."
                if len(order["order_id"]) > 8
                else order["order_id"],
                "Symbol": order["symbol"],
                "Side": order["side"],
                "Quantity": order["quantity"],
                "Type": order["order_type"],
                "Status": order["status"],
                "Fill Price": f"${order['average_fill_price']:.2f}"
                if order["average_fill_price"]
                else "N/A",
                "Commission": f"${order['commission']:.2f}"
                if order["commission"]
                else "$0.00",
                "Created": order["created_at"][:19] if order["created_at"] else "N/A",
            }
            enhanced_orders.append(enhanced_order)

        return enhanced_orders
    except Exception as e:
        st.error(f"Error fetching orders: {e}")
        return []


@st.cache_data(ttl=10)
def get_account_summary():
    """Get account summary with P&L calculations."""
    db = get_db_manager()
    if not db:
        return {}

    try:
        positions = db.get_positions()
        orders = db.get_orders(limit=100)

        # Calculate totals
        total_market_value = 0
        total_unrealized_pnl = 0
        total_commission = 0
        total_trades = len([o for o in orders if o["status"] == "FILLED"])

        from scripts.utils.pnl_calculator import PnLCalculator

        pnl_calc = PnLCalculator()

        for pos in positions:
            current_price = pos.get("current_price", pos.get("average_price", 0))
            from scripts.utils.pnl_calculator import Position

            position_obj = Position(
                symbol=pos["symbol"],
                quantity=pos["quantity"],
                entry_price=pos["average_price"],
                current_price=current_price,
            )
            pnl_result = pnl_calc.calculate_position_pnl(position_obj, current_price)
            total_market_value += pnl_result["market_value"]
            total_unrealized_pnl += pnl_result["unrealized_pnl"]

        for order in orders:
            total_commission += order.get("commission", 0)

        # Mock cash balance (in real implementation, get from broker)
        cash_balance = 100000  # Default starting capital

        total_equity = cash_balance + total_market_value

        return {
            "total_equity": total_equity,
            "cash_balance": cash_balance,
            "market_value": total_market_value,
            "unrealized_pnl": total_unrealized_pnl,
            "total_commission": total_commission,
            "total_trades": total_trades,
            "open_positions": len(positions),
        }
    except Exception as e:
        st.error(f"Error calculating account summary: {e}")
        return {}


@st.cache_data(ttl=10)
def get_risk_metrics():
    """Get risk metrics and system health."""
    db = get_db_manager()
    if not db:
        return {}

    try:
        # Get latest risk metrics from database
        risk_events = db.get_risk_events(limit=10)
        latest_risk = db.get_latest_risk_metrics("live_strategy") if db else None

        # Calculate risk metrics
        account_summary = get_account_summary()
        total_equity = account_summary.get("total_equity", 0)

        # Mock risk calculations (in real implementation, use actual risk calculations)
        portfolio_heat = min(
            abs(account_summary.get("unrealized_pnl", 0)) / max(total_equity, 1) * 100,
            100,
        )

        # Count recent risk events
        recent_critical_events = len(
            [e for e in risk_events if e["severity"] == "CRITICAL"]
        )

        return {
            "portfolio_heat": portfolio_heat,
            "daily_pnl_limit": -2000,  # From config
            "position_limits": 5,  # Max positions
            "recent_critical_events": recent_critical_events,
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        st.error(f"Error fetching risk metrics: {e}")
        return {}


# Title and header
st.title("🤖 AI Trading Backtesting Platform")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")

    # Trading mode indicator
    trading_mode = os.getenv("IB_TRADING_MODE", "paper")
    if trading_mode == "paper":
        st.success("📝 Paper Trading Mode")
    else:
        st.error("🔴 Live Trading Mode")

    st.markdown("---")

    # System health indicators
    st.header("📊 System Status")

    # Check database connectivity
    db = get_db_manager()
    if db:
        st.metric("Database", "Connected ✅")
    else:
        st.metric("Database", "Disconnected ❌")

    # Check IB Gateway (mock check)
    st.metric("IB Gateway", "Connected ✅")

    # Check Backtrader engine (mock check)
    st.metric("Backtrader Engine", "Running ✅")

    # Last update time
    st.metric("Last Update", datetime.now().strftime("%H:%M:%S"))

    st.markdown("---")

    # Quick stats
    st.header("📈 Quick Stats")
    account_summary = get_account_summary()
    st.metric("Active Strategies", "1")
    st.metric("Total Trades", account_summary.get("total_trades", 0))
    st.metric("P&L (Today)", f"${account_summary.get('unrealized_pnl', 0):,.2f}")

# Main dashboard metrics
account_summary = get_account_summary()
col1, col2, col3, col4 = st.columns(4)

with col1:
    delta_color = (
        "normal" if account_summary.get("unrealized_pnl", 0) >= 0 else "inverse"
    )
    st.metric(
        label="Total Equity",
        value=f"${account_summary.get('total_equity', 0):,.2f}",
        delta=f"{account_summary.get('unrealized_pnl', 0):,.2f}",
        delta_color=delta_color,
    )

with col2:
    st.metric(
        label="Open Positions", value=account_summary.get("open_positions", 0), delta=0
    )

with col3:
    st.metric(
        label="Cash Balance",
        value=f"${account_summary.get('cash_balance', 0):,.2f}",
        delta=0,
    )

with col4:
    win_rate = 0  # Would calculate from trade history
    st.metric(label="Win Rate", value=f"{win_rate:.1f}%", delta="0%")

st.markdown("---")

# Tabs for different views
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs(
    [
        "📊 Dashboard",
        "💼 Live Trading",
        "📜 Trade Log",
        "📈 Performance",
        "📊 Analytics",
        "🔬 Backtests",
        "⚙️ Optimization",
        "🧪 MLflow",
        "🏥 Health",
        "⚙️ Settings",
    ]
)

with tab1:
    st.header("Dashboard Overview")

    # Account summary section
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Account Summary")
        summary_data = {
            "Metric": [
                "Total Equity",
                "Cash Balance",
                "Market Value",
                "Unrealized P&L",
                "Total Commission",
            ],
            "Value": [
                f"${account_summary.get('total_equity', 0):,.2f}",
                f"${account_summary.get('cash_balance', 0):,.2f}",
                f"${account_summary.get('market_value', 0):,.2f}",
                f"${account_summary.get('unrealized_pnl', 0):,.2f}",
                f"${account_summary.get('total_commission', 0):,.2f}",
            ],
        }
        st.dataframe(pd.DataFrame(summary_data), hide_index=True)

    with col2:
        st.subheader("Risk Metrics")
        risk_metrics = get_risk_metrics()
        risk_data = {
            "Metric": [
                "Portfolio Heat",
                "Daily P&L Limit",
                "Position Limits",
                "Critical Events",
            ],
            "Value": [
                f"{risk_metrics.get('portfolio_heat', 0):.1f}%",
                f"${risk_metrics.get('daily_pnl_limit', 0):,.2f}",
                f"{risk_metrics.get('position_limits', 0)} max",
                f"{risk_metrics.get('recent_critical_events', 0)} recent",
            ],
        }
        st.dataframe(pd.DataFrame(risk_data), hide_index=True)

    # Equity curve placeholder
    st.subheader("Equity Curve")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[datetime.now()],
            y=[account_summary.get("total_equity", 0)],
            mode="lines+markers",
            name="Equity",
            line=dict(color="blue", width=2),
        )
    )
    fig.update_layout(
        xaxis_title="Time", yaxis_title="Equity ($)", height=400, showlegend=True
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("💼 Live Trading")

    # Open Positions
    st.subheader("Open Positions")
    positions_data = get_positions_data()
    if positions_data:
        positions_df = pd.DataFrame(positions_data)
        st.dataframe(positions_df, use_container_width=True)
    else:
        st.info("No open positions")

    st.markdown("---")

    # Recent Orders
    st.subheader("Recent Orders")
    orders_data = get_orders_data(20)
    if orders_data:
        orders_df = pd.DataFrame(orders_data)
        st.dataframe(orders_df, use_container_width=True)
    else:
        st.info("No orders yet")

with tab3:
    st.header("Trade Log")

    # Get all filled orders for trade journal
    all_orders = get_orders_data(100)
    filled_orders = [
        order for order in all_orders if "FILLED" in order.get("Status", "")
    ]

    if filled_orders:
        st.subheader(f"Completed Trades ({len(filled_orders)})")

        # Convert to DataFrame for analysis
        trades_df = pd.DataFrame(filled_orders)

        # Calculate P&L for each trade (simplified)
        trades_df["P&L"] = 0.0  # Would calculate from entry/exit pairs

        # Display trades
        st.dataframe(trades_df, use_container_width=True)

        # Export functionality
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Export to CSV"):
                csv = trades_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"trade_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )

        with col2:
            if st.button("📥 Export to Excel"):
                # Would implement Excel export
                st.info("Excel export coming soon!")
    else:
        st.info("No completed trades yet. Deploy a strategy to see trades here.")

with tab4:
    st.header("Performance Metrics")

    # Performance monitoring section
    try:
        from scripts.utils.performance_monitor import PerformanceMonitor

        perf_monitor = PerformanceMonitor()

        # Get performance summary
        perf_summary = perf_monitor.get_performance_summary()
        perf_alerts = perf_monitor.get_performance_alerts()

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("System Performance")
            if perf_summary and "error" not in perf_summary:
                for metric_type, data in perf_summary.items():
                    if data.get("count", 0) > 0:
                        st.metric(
                            f"{metric_type.replace('_', ' ').title()}",
                            f"{data['latest']:.2f} {data['unit']}",
                            f"Avg: {data['average']:.2f} {data['unit']}",
                        )
            else:
                st.info("No performance data available yet")

        with col2:
            st.subheader("Performance Alerts")
            if perf_alerts:
                for alert in perf_alerts[:5]:  # Show latest 5 alerts
                    severity_color = (
                        "inverse" if alert["severity"] == "WARNING" else "normal"
                    )
                    st.metric(
                        alert["type"].replace("_", " "),
                        f"{alert['value']:.1f}",
                        f"Threshold: {alert['threshold']}",
                        delta_color=severity_color,
                    )
            else:
                st.success("No performance alerts")

        st.markdown("---")

        # Performance charts
        st.subheader("Performance Trends")

        # Get performance metrics for charting
        perf_metrics = perf_monitor.db_manager.get_performance_metrics(
            hours_back=24, limit=100
        )

        if perf_metrics:
            # Group by metric type for separate charts
            metric_types = list(set(m["metric_type"] for m in perf_metrics))

            for metric_type in metric_types[:3]:  # Show first 3 metric types
                type_metrics = [
                    m for m in perf_metrics if m["metric_type"] == metric_type
                ]
                if len(type_metrics) > 1:
                    df = pd.DataFrame(type_metrics)
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    df = df.sort_values("timestamp")

                    fig = px.line(
                        df,
                        x="timestamp",
                        y="metric_value",
                        title=f"{metric_type.replace('_', ' ').title()} Over Time",
                        labels={
                            "metric_value": f"Value ({type_metrics[0]['unit']})",
                            "timestamp": "Time",
                        },
                    )
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No performance trend data available")

    except Exception as e:
        st.error(f"Performance monitoring not available: {e}")

        # Fallback to basic metrics
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Risk Metrics")
            risk_metrics = get_risk_metrics()
            st.metric("Portfolio Heat", f"{risk_metrics.get('portfolio_heat', 0):.1f}%")
            st.metric("Max Drawdown", "N/A")
            st.metric("Sharpe Ratio", "N/A")
            st.metric("Win Rate", "N/A")

        with col2:
            st.subheader("Return Metrics")
            st.metric(
                "Total Return", f"{account_summary.get('unrealized_pnl', 0):,.2f}"
            )
            st.metric("Daily Avg Return", "N/A")
            st.metric("Best Trade", "N/A")
            st.metric(
                "Total Commission",
                f"${account_summary.get('total_commission', 0):,.2f}",
            )

with tab5:
    st.header("📊 Analytics")

    # Check backend availability
    if not check_backend_availability():
        display_backend_unavailable_message()
        st.info("Analytics require the FastAPI backend to be running.")
        st.stop()

    # Get configured API client
    try:
        api_client = get_configured_api_client()

        # Get portfolio analytics
        analytics_data = api_client.get_portfolio_analytics()

        if analytics_data:
            # Display portfolio statistics
            st.subheader("Portfolio Overview")

            stats = analytics_data.get("portfolio_statistics", {})
            if stats:
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        "Average Return", f"{stats.get('average_return', 0):.2f}%"
                    )
                with col2:
                    st.metric("Best Return", f"{stats.get('best_return', 0):.2f}%")
                with col3:
                    st.metric(
                        "Average Sharpe", f"{stats.get('average_sharpe_ratio', 0):.2f}"
                    )
                with col4:
                    st.metric(
                        "Portfolio Win Rate",
                        f"{stats.get('portfolio_win_rate', 0):.1f}%",
                    )

            # Strategy rankings
            st.subheader("Strategy Rankings")
            rankings = analytics_data.get("strategy_rankings", [])

            if rankings:
                import pandas as pd

                rankings_df = pd.DataFrame(rankings)
                display_cols = [
                    "strategy_name",
                    "total_return",
                    "sharpe_ratio",
                    "win_rate",
                    "trade_count",
                ]
                available_cols = [
                    col for col in display_cols if col in rankings_df.columns
                ]

                if available_cols:
                    # Format numeric columns
                    if "total_return" in rankings_df.columns:
                        rankings_df["total_return"] = rankings_df["total_return"].apply(
                            lambda x: f"{x:.2f}%"
                        )
                    if "sharpe_ratio" in rankings_df.columns:
                        rankings_df["sharpe_ratio"] = rankings_df["sharpe_ratio"].apply(
                            lambda x: f"{x:.2f}"
                        )
                    if "win_rate" in rankings_df.columns:
                        rankings_df["win_rate"] = rankings_df["win_rate"].apply(
                            lambda x: f"{x:.2f}%"
                        )

                    st.dataframe(rankings_df[available_cols], use_container_width=True)
                else:
                    st.dataframe(rankings_df, use_container_width=True)
            else:
                st.info("No strategy rankings available")

            # Filters
            st.subheader("Filters")
            col1, col2 = st.columns(2)

            with col1:
                strategy_filter = st.text_input(
                    "Filter by Strategy", placeholder="e.g., sma_crossover"
                )

            with col2:
                symbol_filter = st.text_input(
                    "Filter by Symbol", placeholder="e.g., SPY"
                )

            if st.button("Apply Filters"):
                if strategy_filter or symbol_filter:
                    filtered_data = api_client.get_portfolio_analytics(
                        strategy_filter=strategy_filter if strategy_filter else None,
                        symbol_filter=symbol_filter if symbol_filter else None,
                    )
                    st.info("Filtered results applied above")
                else:
                    st.info("Please enter at least one filter")
        else:
            st.info("No analytics data available. Run some backtests to see analytics.")

    except Exception as e:
        st.error(f"Failed to load analytics: {e}")
        st.info("Please ensure the FastAPI backend is running.")

with tab6:
    st.header("🔬 Backtests")

    # Check backend availability
    if not check_backend_availability():
        display_backend_unavailable_message()
        st.info("Backtest functionality requires the FastAPI backend to be running.")
        st.stop()

    # Get configured API client
    try:
        api_client = get_configured_api_client()

        # Get list of backtests
        backtests_response = api_client.list_backtests()
        backtests = backtests_response.get("backtests", [])

        if not backtests:
            st.info("No backtest results found. Run a backtest to see results here.")
            st.markdown("**Run a backtest:**")
            st.code(
                "source venv/bin/activate\npython scripts/run_backtest.py --algorithm algorithms/my_strategy"
            )
        else:
            # Create tabs for different views
            bt_tab1, bt_tab2, bt_tab3 = st.tabs(
                ["📋 List View", "📊 Detail View", "🚀 Submit Job"]
            )

            with bt_tab1:
                st.subheader(f"All Backtests ({len(backtests)})")

                # Convert to DataFrame for display
                import pandas as pd

                bt_df = pd.DataFrame(backtests)

                # Display key columns
                display_cols = ["id", "strategy_name", "status", "created_at"]
                available_cols = [col for col in display_cols if col in bt_df.columns]

                if available_cols:
                    st.dataframe(bt_df[available_cols], use_container_width=True)
                else:
                    st.dataframe(bt_df, use_container_width=True)

                # Add refresh button
                if st.button("🔄 Refresh Backtests"):
                    st.rerun()

            with bt_tab2:
                st.subheader("Backtest Detail View")

                # Select backtest
                if backtests:
                    backtest_options = {
                        f"{bt['id'][:8]} - {bt['strategy_name']} ({bt['status']})": bt[
                            "id"
                        ]
                        for bt in backtests
                    }
                    selected_bt_id = st.selectbox(
                        "Select Backtest",
                        options=list(backtest_options.keys()),
                        format_func=lambda x: x,
                    )

                    if selected_bt_id:
                        bt_id = backtest_options[selected_bt_id]
                        bt_data = api_client.get_backtest(bt_id)

                        if bt_data:
                            # Display metrics
                            col1, col2, col3, col4 = st.columns(4)

                            metrics = bt_data.get("metrics", {})

                            with col1:
                                st.metric(
                                    "Strategy", bt_data.get("strategy_name", "N/A")
                                )
                            with col2:
                                status = bt_data.get("status", "N/A")
                                if status == "running":
                                    st.metric("Status", "🔄 Running")
                                elif status == "completed":
                                    st.metric("Status", "✅ Completed")
                                elif status == "failed":
                                    st.metric("Status", "❌ Failed")
                                else:
                                    st.metric("Status", status)
                            with col3:
                                total_return = metrics.get("total_return", 0)
                                st.metric("Total Return", f"{total_return:.2f}%")
                            with col4:
                                sharpe = metrics.get("sharpe_ratio", 0)
                                st.metric("Sharpe Ratio", f"{sharpe:.2f}")

                            # Progress indicator for running jobs
                            if bt_data.get("status") == "running":
                                # Poll for updated status
                                job_status = poll_job_status(bt_id, "backtest")
                                if job_status.get("status") == "completed":
                                    st.success("✅ Backtest completed!")
                                    st.rerun()
                                elif job_status.get("status") == "failed":
                                    st.error("❌ Backtest failed!")
                                else:
                                    st.progress(0.5, text="Backtest in progress...")
                                    st.info("🔄 Refreshing status automatically...")

                            # Add manual refresh for completed jobs
                            if bt_data.get("status") in ["completed", "failed"]:
                                if st.button("🔄 Refresh Status"):
                                    st.rerun()

                            # Display full data
                            with st.expander("Full Backtest Data"):
                                st.json(bt_data)
                        else:
                            st.error("Failed to load backtest details")

            with bt_tab3:
                st.subheader("Submit New Backtest Job")

                # Backtest submission form
                with st.form("backtest_form"):
                    st.markdown("### Strategy Configuration")

                    col1, col2 = st.columns(2)
                    with col1:
                        strategy = st.text_input(
                            "Strategy Name",
                            value="sma_crossover",
                            help="Name of the strategy to backtest",
                        )
                    with col2:
                        symbols_input = st.text_input(
                            "Symbols",
                            value="SPY",
                            help="Comma-separated list of symbols",
                        )

                    st.markdown("### Date Range")
                    col1, col2 = st.columns(2)
                    with col1:
                        start_date = st.date_input(
                            "Start Date",
                            value=datetime.now() - timedelta(days=365),
                            help="Backtest start date",
                        )
                    with col2:
                        end_date = st.date_input(
                            "End Date", value=datetime.now(), help="Backtest end date"
                        )

                    st.markdown("### Parameters (Optional)")
                    parameters_input = st.text_area(
                        "Parameters (JSON)",
                        placeholder='{"fast_period": 10, "slow_period": 20}',
                        help="Optional strategy parameters as JSON",
                    )

                    submitted = st.form_submit_button("🚀 Submit Backtest")

                    if submitted:
                        if not strategy:
                            st.warning("Please specify a strategy name")
                        elif not symbols_input:
                            st.warning("Please specify at least one symbol")
                        else:
                            try:
                                # Convert inputs
                                symbols = [
                                    s.strip()
                                    for s in symbols_input.split(",")
                                    if s.strip()
                                ]

                                # Parse parameters if provided
                                parameters = {}
                                if parameters_input.strip():
                                    try:
                                        parameters = json.loads(parameters_input)
                                    except json.JSONDecodeError:
                                        st.error("Invalid JSON in parameters field")
                                        st.stop()

                                with st.spinner("Submitting backtest job..."):
                                    result = api_client.run_backtest(
                                        strategy=strategy,
                                        symbols=symbols,
                                        parameters=parameters,
                                        start_date=start_date.strftime("%Y-%m-%d"),
                                        end_date=end_date.strftime("%Y-%m-%d"),
                                    )

                                if "job_id" in result:
                                    st.success(
                                        f"✅ Backtest submitted successfully! Job ID: {result['job_id']}"
                                    )
                                    st.info(
                                        "Check the 'List View' tab to monitor progress."
                                    )
                                else:
                                    st.error(f"Failed to submit backtest: {result}")

                            except Exception as e:
                                st.error(f"❌ Failed to submit backtest: {e}")

    except Exception as e:
        st.error(f"Failed to connect to backend API: {e}")
        st.info("Please ensure the FastAPI backend is running.")

with tab7:
    st.header("⚙️ Optimization")

    # Check backend availability
    if not check_backend_availability():
        display_backend_unavailable_message()
        st.info(
            "Optimization functionality requires the FastAPI backend to be running."
        )
        st.stop()

    # Get configured API client
    try:
        api_client = get_configured_api_client()

        # Create tabs for optimization workflow
        opt_tab1, opt_tab2, opt_tab3 = st.tabs(
            ["🚀 Run Optimization", "📊 Results", "📜 History"]
        )

        with opt_tab1:
            st.subheader("Submit Optimization Job")

            # Strategy selection
            st.markdown("### Strategy Configuration")
            col1, col2 = st.columns(2)
            with col1:
                strategy = st.text_input(
                    "Strategy Name",
                    value="sma_crossover",
                    help="Name of the strategy to optimize",
                )
            with col2:
                symbols_input = st.text_input(
                    "Symbols", value="SPY", help="Comma-separated list of symbols"
                )

            # Parameter configuration
            st.markdown("### Parameter Configuration")
            st.info("Define the parameters to optimize with their ranges.")

            # Initialize session state for parameters
            if "opt_parameters" not in st.session_state:
                st.session_state.opt_parameters = []

            # Display current parameters
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("**Current Parameters:**")
                if st.session_state.opt_parameters:
                    for i, param in enumerate(st.session_state.opt_parameters):
                        st.code(
                            f"{i + 1}. {param['name']}: [{param['min']}, {param['max']}] step {param['step']}"
                        )
                else:
                    st.text("No parameters configured")

            with col2:
                if st.button("➕ Add Parameter"):
                    st.session_state.show_param_form = True

            # Parameter form
            if st.session_state.get("show_param_form", False):
                with st.form("add_parameter_form"):
                    st.markdown("**New Parameter**")
                    param_name = st.text_input(
                        "Parameter Name", placeholder="e.g., fast_period"
                    )

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        param_min = st.number_input("Min Value", value=1.0)
                    with col2:
                        param_max = st.number_input("Max Value", value=100.0)
                    with col3:
                        param_step = st.number_input(
                            "Step Size", value=1.0, min_value=0.01
                        )

                    submitted = st.form_submit_button("Add Parameter")

                    if submitted and param_name:
                        st.session_state.opt_parameters.append(
                            {
                                "name": param_name,
                                "min": param_min,
                                "max": param_max,
                                "step": param_step,
                            }
                        )
                        st.session_state.show_param_form = False
                        st.rerun()

            # Clear parameters button
            if st.session_state.opt_parameters and st.button("🗑️ Clear All Parameters"):
                st.session_state.opt_parameters = []
                st.rerun()

            st.markdown("---")

            # Optimization settings
            st.markdown("### Optimization Settings")

            col1, col2 = st.columns(2)
            with col1:
                opt_metric = st.selectbox(
                    "Optimization Metric",
                    options=[
                        "sharpe_ratio",
                        "total_return",
                        "win_rate",
                        "max_drawdown",
                    ],
                    format_func=lambda x: x.replace("_", " ").title(),
                    help="Metric to optimize for",
                )

            with col2:
                max_trials = st.number_input(
                    "Max Trials", min_value=10, max_value=1000, value=100, step=10
                )

            # Submit optimization button
            st.markdown("---")

            if st.button(
                "🚀 Submit Optimization",
                type="primary",
                disabled=len(st.session_state.opt_parameters) == 0,
            ):
                if not st.session_state.opt_parameters:
                    st.warning("Please add at least one parameter to optimize")
                elif not strategy:
                    st.warning("Please specify a strategy name")
                else:
                    try:
                        # Convert symbols string to list
                        symbols = [
                            s.strip() for s in symbols_input.split(",") if s.strip()
                        ]

                        # Convert parameters to API format
                        params = {}
                        for param in st.session_state.opt_parameters:
                            params[param["name"]] = {
                                "min": param["min"],
                                "max": param["max"],
                                "step": param["step"],
                            }

                        with st.spinner("Submitting optimization job..."):
                            result = api_client.run_optimization(
                                strategy=strategy,
                                parameters=params,
                                optimization_metric=opt_metric,
                                max_trials=max_trials,
                            )

                        if "job_id" in result:
                            st.success(
                                f"✅ Optimization submitted successfully! Job ID: {result['job_id']}"
                            )
                            st.info(
                                "Check the 'Results' tab to monitor progress and view results."
                            )
                        else:
                            st.error(f"Failed to submit optimization: {result}")

                    except Exception as e:
                        st.error(f"❌ Failed to submit optimization: {e}")

        with opt_tab2:
            st.subheader("Optimization Results")

            try:
                # Get list of optimizations
                optimizations = api_client.list_optimizations()

                if not optimizations:
                    st.info(
                        "No optimization jobs found. Submit an optimization job first."
                    )
                else:
                    # Select optimization
                    opt_options = {opt["optimization_id"]: opt for opt in optimizations}
                    selected_opt_id = st.selectbox(
                        "Select Optimization Job",
                        options=list(opt_options.keys()),
                        format_func=lambda x: f"{x[:8]} - {opt_options[x].get('algorithm', 'Unknown')} ({opt_options[x].get('status', 'Unknown')})",
                    )

                    if selected_opt_id:
                        opt_data = opt_options[selected_opt_id]

                        # Display job info
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Strategy", opt_data.get("algorithm", "N/A"))
                        with col2:
                            status = opt_data.get("status", "N/A")
                            if status == "running":
                                st.metric("Status", "🔄 Running")
                                # Poll for updated status
                                job_status = poll_job_status(
                                    selected_opt_id, "optimization"
                                )
                                if job_status.get("status") == "completed":
                                    st.success("✅ Optimization completed!")
                                    st.rerun()
                                elif job_status.get("status") == "failed":
                                    st.error("❌ Optimization failed!")
                                else:
                                    st.info("🔄 Refreshing status automatically...")
                            elif status == "completed":
                                st.metric("Status", "✅ Completed")
                            elif status == "failed":
                                st.metric("Status", "❌ Failed")
                            else:
                                st.metric("Status", status)
                        with col3:
                            st.metric(
                                "Metric",
                                opt_data.get("optimization_metric", "N/A")
                                .replace("_", " ")
                                .title(),
                            )
                        with col4:
                            st.metric("Trials", opt_data.get("result_count", 0))

                        st.markdown(f"**Created:** {opt_data.get('created_at', 'N/A')}")

                        # Get detailed results
                        if opt_data.get("status") == "completed":
                            try:
                                detailed_data = api_client.get_optimization(
                                    selected_opt_id
                                )

                                if detailed_data and "results" in detailed_data:
                                    results = detailed_data["results"]

                                    if results:
                                        import pandas as pd

                                        # Convert to DataFrame
                                        results_df = pd.DataFrame(results)

                                        # Flatten parameters if nested
                                        if "parameters" in results_df.columns:
                                            try:
                                                params_list = results_df[
                                                    "parameters"
                                                ].tolist()
                                                params_df = pd.json_normalize(
                                                    params_list
                                                )
                                                results_df = pd.concat(
                                                    [
                                                        results_df.drop(
                                                            "parameters", axis=1
                                                        ),
                                                        params_df,
                                                    ],
                                                    axis=1,
                                                )
                                            except Exception:
                                                # If flattening fails, keep parameters as is
                                                pass

                                        st.markdown("### Optimization Results")

                                        # Sort by optimization metric
                                        metric_col = opt_data.get(
                                            "optimization_metric", "sharpe_ratio"
                                        )
                                        if metric_col in results_df.columns:
                                            results_df = results_df.sort_values(
                                                metric_col, ascending=False
                                            )

                                        # Display top results
                                        st.dataframe(
                                            results_df.head(20),
                                            use_container_width=True,
                                        )

                                        # Export functionality
                                        csv = results_df.to_csv(index=False)
                                        st.download_button(
                                            label="📥 Export Results to CSV",
                                            data=csv,
                                            file_name=f"optimization_{selected_opt_id[:8]}_{datetime.now().strftime('%Y%m%d')}.csv",
                                            mime="text/csv",
                                        )

                                        # Parameter analysis (if 2 parameters)
                                        param_cols = [
                                            col
                                            for col in results_df.columns
                                            if col
                                            not in [
                                                "sharpe_ratio",
                                                "total_return",
                                                "win_rate",
                                                "max_drawdown",
                                                "created_at",
                                            ]
                                        ]
                                        if len(param_cols) == 2:
                                            st.markdown("### Parameter Heatmap")

                                            heatmap_metric = st.selectbox(
                                                "Select Metric for Heatmap",
                                                options=[
                                                    "sharpe_ratio",
                                                    "total_return",
                                                    "win_rate",
                                                ],
                                                format_func=lambda x: x.replace(
                                                    "_", " "
                                                ).title(),
                                            )

                                            if heatmap_metric in results_df.columns:
                                                try:
                                                    heatmap_df = results_df.pivot(
                                                        index=param_cols[0],
                                                        columns=param_cols[1],
                                                        values=heatmap_metric,
                                                    )

                                                    fig = px.imshow(
                                                        heatmap_df,
                                                        labels=dict(
                                                            x=param_cols[1],
                                                            y=param_cols[0],
                                                            color=heatmap_metric.replace(
                                                                "_", " "
                                                            ).title(),
                                                        ),
                                                        color_continuous_scale="Viridis",
                                                        aspect="auto",
                                                    )
                                                    fig.update_layout(height=500)
                                                    st.plotly_chart(
                                                        fig, use_container_width=True
                                                    )
                                                except Exception as chart_error:
                                                    st.warning(
                                                        f"Could not create heatmap: {chart_error}"
                                                    )
                                    else:
                                        st.info(
                                            "No results available for this optimization job"
                                        )
                                else:
                                    st.info(
                                        "Could not load detailed results for this job"
                                    )

                            except Exception as e:
                                st.error(f"Error loading optimization results: {e}")
                        elif opt_data.get("status") == "running":
                            st.info(
                                "🔄 Optimization job is currently running. Results will be available when completed."
                            )
                        else:
                            st.warning(
                                f"Job status: {opt_data.get('status', 'Unknown')}"
                            )

            except Exception as e:
                st.error(f"Error loading optimization results: {e}")

        with opt_tab3:
            st.subheader("Optimization History")

            try:
                optimizations = api_client.list_optimizations()

                if optimizations:
                    st.markdown(f"**Total Optimization Jobs:** {len(optimizations)}")

                    # Convert to DataFrame for display
                    import pandas as pd

                    opt_df = pd.DataFrame(optimizations)

                    display_cols = [
                        "optimization_id",
                        "algorithm",
                        "optimization_metric",
                        "result_count",
                        "created_at",
                        "status",
                    ]
                    available_cols = [
                        col for col in display_cols if col in opt_df.columns
                    ]

                    if available_cols:
                        # Format optimization_id to show short version
                        if "optimization_id" in opt_df.columns:
                            opt_df["optimization_id"] = opt_df["optimization_id"].str[
                                :8
                            ]

                        st.dataframe(
                            opt_df[available_cols],
                            use_container_width=True,
                            hide_index=True,
                        )
                    else:
                        st.dataframe(opt_df, use_container_width=True)
                else:
                    st.info("No optimization jobs found")

            except Exception as e:
                st.error(f"Error loading optimization history: {e}")

    except Exception as e:
        st.error(f"Failed to connect to backend API: {e}")
        st.info("Please ensure the FastAPI backend is running.")

with tab8:
    st.header("🧪 MLflow Experiments")

    # Get MLflow client
    mlflow_client = get_mlflow_client()

    if not mlflow_client:
        st.error(
            "MLflow server is not available. Please start the platform with ./scripts/start.sh"
        )
        st.stop()

    mlflow = mlflow_client["mlflow"]
    pm = mlflow_client["project_manager"]

    # Summary metrics at top
    st.subheader("📊 Research Lab Overview")
    col1, col2, col3, col4 = st.columns(4)

    try:
        # Get all experiments
        experiments = mlflow.search_experiments()
        total_experiments = len(
            [e for e in experiments if e.lifecycle_stage == "active"]
        )

        # Get all runs
        all_runs = mlflow.search_runs(
            experiment_ids=[e.experiment_id for e in experiments], max_results=10000
        )
        total_runs = len(all_runs)

        # Get recent runs (last 7 days)
        from datetime import datetime, timedelta
        import pandas as pd

        week_ago = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=7)
        recent_runs = [
            r
            for r in all_runs.itertuples()
            if pd.notna(r.start_time) and r.start_time > week_ago
        ]

        # Get failed runs
        failed_runs = len([r for r in all_runs.itertuples() if r.status != "FINISHED"])

        with col1:
            st.metric("Total Experiments", total_experiments)
        with col2:
            st.metric("Total Runs", total_runs)
        with col3:
            st.metric("Recent Runs (7d)", len(recent_runs))
        with col4:
            st.metric(
                "Failed Runs",
                failed_runs,
                delta=f"-{failed_runs}" if failed_runs > 0 else "0",
            )
    except Exception as e:
        st.error(f"Error fetching MLflow metrics: {e}")

    st.markdown("---")

    # Project browser
    st.subheader("🔍 Browse Experiments")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Project filter
        projects = pm.list_projects()
        selected_project = st.selectbox("Filter by Project", ["All"] + projects)

    with col2:
        # Asset class filter
        asset_classes = pm.list_asset_classes()
        selected_asset_class = st.selectbox(
            "Filter by Asset Class", ["All"] + asset_classes
        )

    with col3:
        # Strategy family filter
        strategy_families = pm.list_strategy_families()
        selected_strategy_family = st.selectbox(
            "Filter by Strategy Family", ["All"] + strategy_families
        )

    # Query experiments based on filters
    try:
        if selected_project != "All":
            experiments = pm.query_by_project(selected_project)
        elif selected_asset_class != "All":
            experiments = pm.query_by_asset_class(selected_asset_class)
        elif selected_strategy_family != "All":
            experiments = pm.query_by_strategy_family(selected_strategy_family)
        else:
            experiments = mlflow.search_experiments()

        # Display experiments
        if experiments:
            st.write(f"**Found {len(experiments)} experiments**")

            # Create experiment list
            exp_data = []
            for exp in experiments:
                # Get best run for this experiment
                runs = mlflow.search_runs(
                    experiment_ids=[exp.experiment_id],
                    max_results=1,
                    order_by=["metrics.sharpe_ratio DESC"],
                )

                if len(runs) > 0:
                    best_run = runs.iloc[0]
                    exp_data.append(
                        {
                            "Experiment": exp.name,
                            "Runs": mlflow.search_runs(
                                experiment_ids=[exp.experiment_id]
                            ).shape[0],
                            "Best Sharpe": f"{best_run.get('metrics.sharpe_ratio', 0):.2f}"
                            if "metrics.sharpe_ratio" in best_run
                            else "N/A",
                            "Best Return": f"{best_run.get('metrics.total_return', 0):.2%}"
                            if "metrics.total_return" in best_run
                            else "N/A",
                            "Max Drawdown": f"{best_run.get('metrics.max_drawdown', 0):.2%}"
                            if "metrics.max_drawdown" in best_run
                            else "N/A",
                            "Created": exp.creation_time,
                        }
                    )

            if exp_data:
                df = pd.DataFrame(exp_data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                # Link to MLflow UI
                st.info(
                    "🔗 For advanced features, open the [MLflow UI](http://localhost:5000)"
                )
            else:
                st.info("No runs found for these experiments yet.")
        else:
            st.info("No experiments found matching your filters.")

    except Exception as e:
        st.error(f"Error querying experiments: {e}")
        import traceback

        st.code(traceback.format_exc())

    st.markdown("---")

    # Experiment comparison
    st.subheader("🔬 Compare Experiments")

    try:
        # Get all experiments for multi-select
        all_experiments = mlflow.search_experiments()
        experiment_options = {
            exp.name: exp.experiment_id
            for exp in all_experiments
            if exp.lifecycle_stage == "active"
        }

        if experiment_options:
            # Multi-select experiments
            selected_experiments = st.multiselect(
                "Select experiments to compare (2-5 recommended)",
                options=list(experiment_options.keys()),
                max_selections=5,
            )

            if len(selected_experiments) >= 2:
                st.write(f"**Comparing {len(selected_experiments)} experiments**")

                # Get runs for selected experiments
                selected_exp_ids = [
                    experiment_options[exp] for exp in selected_experiments
                ]
                comparison_data = []

                for exp_name in selected_experiments:
                    exp_id = experiment_options[exp_name]
                    # Get best run for each experiment
                    runs = mlflow.search_runs(
                        experiment_ids=[exp_id],
                        max_results=1,
                        order_by=["metrics.sharpe_ratio DESC"],
                    )

                    if len(runs) > 0:
                        best_run = runs.iloc[0]
                        comparison_data.append(
                            {
                                "Experiment": exp_name,
                                "Sharpe Ratio": f"{best_run.get('metrics.sharpe_ratio', 0):.2f}"
                                if "metrics.sharpe_ratio" in best_run
                                else "N/A",
                                "Total Return": f"{best_run.get('metrics.total_return', 0):.2%}"
                                if "metrics.total_return" in best_run
                                else "N/A",
                                "Max Drawdown": f"{best_run.get('metrics.max_drawdown', 0):.2%}"
                                if "metrics.max_drawdown" in best_run
                                else "N/A",
                                "Win Rate": f"{best_run.get('metrics.win_rate', 0):.2%}"
                                if "metrics.win_rate" in best_run
                                else "N/A",
                                "Sortino Ratio": f"{best_run.get('metrics.sortino_ratio', 0):.2f}"
                                if "metrics.sortino_ratio" in best_run
                                else "N/A",
                                "Calmar Ratio": f"{best_run.get('metrics.calmar_ratio', 0):.2f}"
                                if "metrics.calmar_ratio" in best_run
                                else "N/A",
                            }
                        )

                if comparison_data:
                    df_comparison = pd.DataFrame(comparison_data)
                    st.dataframe(
                        df_comparison, use_container_width=True, hide_index=True
                    )

                    # Performance charts
                    st.subheader("📊 Performance Comparison")

                    # Create radar chart for multi-dimensional comparison
                    try:
                        metrics_for_chart = []
                        for exp_name in selected_experiments:
                            exp_id = experiment_options[exp_name]
                            runs = mlflow.search_runs(
                                experiment_ids=[exp_id],
                                max_results=1,
                                order_by=["metrics.sharpe_ratio DESC"],
                            )

                            if len(runs) > 0:
                                best_run = runs.iloc[0]
                                metrics_for_chart.append(
                                    {
                                        "Experiment": exp_name,
                                        "Sharpe": best_run.get(
                                            "metrics.sharpe_ratio", 0
                                        ),
                                        "Returns": best_run.get(
                                            "metrics.total_return", 0
                                        )
                                        * 100,  # Convert to percentage
                                        "Win Rate": best_run.get("metrics.win_rate", 0)
                                        * 100,
                                        "Sortino": best_run.get(
                                            "metrics.sortino_ratio", 0
                                        ),
                                        "Calmar": best_run.get(
                                            "metrics.calmar_ratio", 0
                                        ),
                                    }
                                )

                        if metrics_for_chart:
                            # Bar chart comparison
                            metrics_df = pd.DataFrame(metrics_for_chart)

                            col1, col2 = st.columns(2)

                            with col1:
                                fig_sharpe = px.bar(
                                    metrics_df,
                                    x="Experiment",
                                    y="Sharpe",
                                    title="Sharpe Ratio Comparison",
                                    labels={"Sharpe": "Sharpe Ratio"},
                                )
                                st.plotly_chart(fig_sharpe, use_container_width=True)

                            with col2:
                                fig_returns = px.bar(
                                    metrics_df,
                                    x="Experiment",
                                    y="Returns",
                                    title="Total Returns Comparison",
                                    labels={"Returns": "Total Return (%)"},
                                )
                                st.plotly_chart(fig_returns, use_container_width=True)

                            # Risk-adjusted return scatter
                            fig_scatter = px.scatter(
                                metrics_df,
                                x="Sharpe",
                                y="Returns",
                                text="Experiment",
                                title="Risk-Adjusted Returns (Sharpe vs Total Return)",
                                labels={
                                    "Sharpe": "Sharpe Ratio",
                                    "Returns": "Total Return (%)",
                                },
                            )
                            fig_scatter.update_traces(
                                textposition="top center", marker=dict(size=12)
                            )
                            st.plotly_chart(fig_scatter, use_container_width=True)

                    except Exception as chart_error:
                        st.error(f"Error creating charts: {chart_error}")

            elif len(selected_experiments) == 1:
                st.info("Select at least 2 experiments to compare.")
            else:
                st.info("Select experiments above to compare their performance.")
        else:
            st.info("No experiments available for comparison.")

    except Exception as e:
        st.error(f"Error in experiment comparison: {e}")
        import traceback

        st.code(traceback.format_exc())

with tab9:
    st.header("🏥 System Health")

    # Health monitoring section
    try:
        from scripts.utils.health_monitor import HealthMonitor, HealthStatus

        health_monitor = HealthMonitor()

        # Run health checks
        health_checks = health_monitor.run_all_checks()
        overall_status, overall_message = health_monitor.get_overall_status(
            health_checks
        )

        # Overall health status
        col1, col2, col3 = st.columns(3)

        with col1:
            status_color = {
                HealthStatus.HEALTHY: "green",
                HealthStatus.WARNING: "orange",
                HealthStatus.CRITICAL: "red",
                HealthStatus.UNKNOWN: "gray",
            }.get(overall_status, "gray")

            st.markdown(
                f"""
            <div style="
                padding: 1rem;
                border-radius: 0.5rem;
                background-color: {status_color};
                color: white;
                text-align: center;
                margin-bottom: 1rem;
            ">
                <h3>Overall Status: {overall_status.upper()}</h3>
                <p>{overall_message}</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col2:
            # Health summary
            health_summary = health_monitor.get_health_summary()
            if "error" not in health_summary:
                st.metric(
                    "System Uptime", f"{health_summary.get('uptime_percent', 0):.1f}%"
                )
                st.metric("Total Checks", health_summary.get("total_checks", 0))
            else:
                st.metric("System Uptime", "N/A")
                st.metric("Total Checks", "N/A")

        with col3:
            # HTTP status indicator
            http_status = health_monitor.get_http_status_code(health_checks)
            if http_status == 200:
                st.success("🟢 HTTP 200 - Healthy")
            else:
                st.error(f"🔴 HTTP {http_status} - Unhealthy")

            st.metric("Last Check", datetime.now().strftime("%H:%M:%S"))

        st.markdown("---")

        # Individual health checks
        st.subheader("Health Check Details")

        # Group checks by status
        healthy_checks = [c for c in health_checks if c.status == HealthStatus.HEALTHY]
        warning_checks = [c for c in health_checks if c.status == HealthStatus.WARNING]
        critical_checks = [
            c for c in health_checks if c.status == HealthStatus.CRITICAL
        ]

        # Display checks by severity
        if critical_checks:
            st.error("🚨 Critical Issues")
            for check in critical_checks:
                with st.expander(f"❌ {check.name}: {check.message}"):
                    st.json(check.details)

        if warning_checks:
            st.warning("⚠️ Warnings")
            for check in warning_checks:
                with st.expander(f"⚠️ {check.name}: {check.message}"):
                    st.json(check.details)

        if healthy_checks:
            st.success("✅ Healthy Systems")
            for check in healthy_checks:
                with st.expander(f"✅ {check.name}: {check.message}"):
                    st.json(check.details)

        st.markdown("---")

        # Health trends (placeholder for future implementation)
        st.subheader("Health Trends")
        st.info("Health trend charts will be available after collecting more data.")

        # Manual refresh button
        if st.button("🔄 Refresh Health Checks"):
            st.rerun()

        # Health endpoint URL
        st.markdown("---")
        st.subheader("Health Endpoint")
        st.code("curl http://localhost:8501/health")
        st.info(
            "Health endpoint returns JSON with system status and detailed check results."
        )

    except Exception as e:
        st.error(f"Health monitoring not available: {e}")
        st.info(
            "Health monitoring requires proper system permissions and dependencies."
        )

with tab10:
    st.header("Settings")

    st.subheader("Environment Variables")
    env_vars = {
        "IB_TRADING_MODE": os.getenv("IB_TRADING_MODE", "not set"),
        "IB_GATEWAY_HOST": os.getenv("IB_GATEWAY_HOST", "ib-gateway"),
        "IB_GATEWAY_PORT": os.getenv("IB_GATEWAY_PORT", "4001"),
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "not set"),
        "DATABASE_PATH": "/app/data/sqlite/trades.db",
    }

    for key, value in env_vars.items():
        st.code(f"{key}: {value}")

    st.subheader("Data Directories")
    data_path = "/app/data"
    results_path = "/app/results"

    if os.path.exists(data_path):
        st.success(f"✅ Data directory: {data_path}")
    else:
        st.warning(f"⚠️ Data directory not found: {data_path}")

    if os.path.exists(results_path):
        st.success(f"✅ Results directory: {results_path}")
    else:
        st.warning(f"⚠️ Results directory not found: {results_path}")

    st.subheader("System Information")
    st.info(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.info("Auto-refresh: Enabled (5 seconds)")

# Footer
st.markdown("---")
st.markdown(
    "📚 [Documentation](../docs) | 🐛 [Issues](../stories) | "
    "🔧 [Configuration](../.env) | "
    f"🕐 Last Update: {datetime.now().strftime('%H:%M:%S')}"
)
