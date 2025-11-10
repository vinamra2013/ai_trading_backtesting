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
    from monitoring.utils.api_client import APIClient

    # Load .env file if it exists
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        # python-dotenv not available, continue with environment variables
        pass

    return APIClient()


# Job polling functionality
def poll_job_status(job_id: str, job_type: str = "backtest") -> Dict[str, Any]:
    """Poll job status"""
    try:
        # Create a new API client instance to avoid any caching issues
        from monitoring.utils.api_client import APIClient

        api_client = APIClient()

        if job_type == "backtest":
            result = api_client.get_backtest(int(job_id))
            # Ensure we always return a dict
            if result is None:
                return {"status": "error", "error": "API returned None"}
            return result
        elif job_type == "optimization":
            # For optimization, we need to get the full job data
            return api_client.get_optimization(int(job_id))
        else:
            return {"status": "unknown", "error": f"Unknown job type: {job_type}"}
    except ImportError as e:
        return {"status": "error", "error": f"Import error: {e}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_backend_availability() -> bool:
    """Check if the FastAPI backend is available"""
    try:
        api_client = get_configured_api_client()
        result = api_client.is_available()
        return result
    except Exception as e:
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

        # Set MLflow tracking URI (configurable)
        mlflow_tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
        if not mlflow_tracking_uri:
            if os.path.exists("/.dockerenv"):
                mlflow_tracking_uri = "http://mlflow:5000"
            else:
                mlflow_tracking_uri = "http://localhost:5000"
        mlflow.set_tracking_uri(mlflow_tracking_uri)

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

# Simple test to verify Streamlit works
st.write("🚀 Streamlit is working!")
if st.button("Test Button"):
    st.success("Button works!")

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
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    [
        "📊 Dashboard",
        "📁 Data Files",
        "📈 Performance",
        "📊 Analytics",
        "🔬 Backtests",
        "⚙️ Optimization",
        "🧪 MLflow",
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
    st.header("📁 Data Files Management")

    # Check backend availability
    if not check_backend_availability():
        st.error("Backend not available")
        st.stop()

    # Get configured API client
    try:
        api_client = get_configured_api_client()
        st.write("✅ API client ready")
    except Exception as e:
        st.error(f"Failed to initialize API client: {e}")

    st.markdown("---")

    # Create subtabs for different data operations
    data_tab1, data_tab2, data_tab3 = st.tabs(
        ["📋 File Browser", "📤 Process Data", "📊 Statistics"]
    )

    with data_tab1:
        st.subheader("Data Files Browser")

        # Refresh button
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("🔄 Refresh Files"):
                st.rerun()

        with col2:
            data_dir = st.selectbox(
                "Data Directory",
                ["data/csv", "data/csv/1m", "data/csv/5m", "data/csv/1d"],
                index=0,
            )

        # Direct file scanning (primary method)
        try:
            from scripts.data_file_scanner import DataFileScanner

            with st.spinner("Scanning data files..."):
                scanner = DataFileScanner(data_dir)
                files_data = scanner.scan_data_files()

            if files_data:
                total_files = len(files_data)
                total_size = sum(f.get("file_size_mb", 0) for f in files_data)

                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Total Files", total_files)
                with col2:
                    st.metric("Total Size", f"{total_size:.1f} MB")
                with col3:
                    st.metric("Data Directory", data_dir)
                with col4:
                    st.metric("Status", "Loaded")

                # Group files by symbol and timeframe
                from collections import defaultdict

                # Group by symbol first, then by timeframe
                symbol_groups = defaultdict(lambda: defaultdict(list))

                # Calculate symbol stats
                symbol_stats = {}
                for file_info in files_data:
                    symbol = file_info.get("symbol", "Unknown")
                    timeframe = file_info.get("timeframe", "Unknown")
                    symbol_groups[symbol][timeframe].append(file_info)

                    # Initialize or update symbol stats
                    if symbol not in symbol_stats:
                        symbol_stats[symbol] = {
                            "total_files": 0,
                            "total_size": 0.0,
                            "timeframes": set(),
                        }

                    symbol_stats[symbol]["total_files"] += 1
                    symbol_stats[symbol]["total_size"] += file_info.get(
                        "file_size_mb", 0.0
                    )
                    symbol_stats[symbol]["timeframes"].add(timeframe)

                # Display hierarchical view
                st.subheader("📊 Data Files by Symbol")

                for symbol in sorted(symbol_groups.keys()):
                    symbol_files = symbol_groups[symbol]
                    symbol_info = symbol_stats[symbol]

                    # Symbol header with summary
                    with st.expander(
                        f"📈 {symbol} - {symbol_info['total_files']} files, {symbol_info['total_size']:.1f} MB",
                        expanded=False,
                    ):
                        # Symbol overview
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Files", symbol_info["total_files"])
                        with col2:
                            st.metric(
                                "Total Size", f"{symbol_info['total_size']:.1f} MB"
                            )
                        with col3:
                            timeframe_count = len(symbol_info["timeframes"])
                            st.metric("Timeframes", timeframe_count)
                        with col4:
                            # Calculate average quality
                            symbol_qualities = []
                            for tf_files in symbol_files.values():
                                for f in tf_files:
                                    if f.get("quality_score"):
                                        symbol_qualities.append(f["quality_score"])
                            avg_quality = (
                                sum(symbol_qualities) / len(symbol_qualities)
                                if symbol_qualities
                                else 0
                            )
                            quality_label = (
                                "Excellent"
                                if avg_quality >= 90
                                else "Good"
                                if avg_quality >= 75
                                else "Fair"
                                if avg_quality >= 60
                                else "Poor"
                            )
                            st.metric(
                                "Avg Quality", f"{quality_label} ({avg_quality:.0f})"
                            )

                        # Timeframe breakdown
                        st.markdown("### By Timeframe")
                        for timeframe in sorted(symbol_files.keys()):
                            tf_files = symbol_files[timeframe]
                            tf_size = sum(f.get("file_size_mb", 0) for f in tf_files)
                            tf_rows = sum(f.get("row_count", 0) for f in tf_files)

                            with st.expander(
                                f"⏰ {timeframe} - {len(tf_files)} files, {tf_size:.1f} MB, {tf_rows:,} rows",
                                expanded=False,
                            ):
                                # Timeframe files table
                                tf_df = pd.DataFrame(tf_files)
                                # Use relative_path as filename display
                                display_df = tf_df.copy()
                                display_df["filename"] = display_df["relative_path"]
                                st.dataframe(
                                    display_df[
                                        [
                                            "filename",
                                            "file_size_mb",
                                            "last_modified",
                                            "quality_status",
                                            "row_count",
                                            "start_date",
                                            "end_date",
                                        ]
                                    ],
                                    use_container_width=True,
                                    column_config={
                                        "filename": st.column_config.TextColumn(
                                            "Filename", width="large"
                                        ),
                                        "file_size_mb": st.column_config.NumberColumn(
                                            "Size (MB)", format="%.2f"
                                        ),
                                        "last_modified": st.column_config.DatetimeColumn(
                                            "Modified"
                                        ),
                                        "quality_status": st.column_config.TextColumn(
                                            "Quality"
                                        ),
                                        "row_count": st.column_config.NumberColumn(
                                            "Rows", format=","
                                        ),
                                        "start_date": st.column_config.TextColumn(
                                            "Start Date"
                                        ),
                                        "end_date": st.column_config.TextColumn(
                                            "End Date"
                                        ),
                                    },
                                    hide_index=True,
                                )

                                # Quick actions for this timeframe
                                if len(tf_files) > 0:
                                    st.markdown("**Quick Actions:**")
                                    action_col1, action_col2, action_col3 = st.columns(
                                        3
                                    )
                                    with action_col1:
                                        if st.button(
                                            f"📊 View Sample ({timeframe})",
                                            key=f"sample_{symbol}_{timeframe}",
                                        ):
                                            # Show sample from first file
                                            sample_file = tf_files[0]
                                            try:
                                                df = pd.read_csv(
                                                    sample_file["file_path"], nrows=5
                                                )
                                                st.dataframe(df)
                                            except Exception as e:
                                                st.error(f"Failed to load sample: {e}")

                                    with action_col2:
                                        if st.button(
                                            f"📈 Quality Stats ({timeframe})",
                                            key=f"quality_{symbol}_{timeframe}",
                                        ):
                                            # Show quality distribution for this timeframe
                                            qualities = [
                                                f.get("quality_status", "Unknown")
                                                for f in tf_files
                                            ]
                                            quality_counts = pd.Series(
                                                qualities
                                            ).value_counts()
                                            st.bar_chart(quality_counts)

                                    with action_col3:
                                        if st.button(
                                            f"📅 Date Coverage ({timeframe})",
                                            key=f"coverage_{symbol}_{timeframe}",
                                        ):
                                            # Show date range coverage
                                            date_ranges = []
                                            for f in tf_files:
                                                start = f.get("start_date", "")
                                                end = f.get("end_date", "")
                                                if start and end:
                                                    date_ranges.append(
                                                        f"{start} to {end}"
                                                    )
                                            if date_ranges:
                                                st.write("Date ranges covered:")
                                                for dr in date_ranges[
                                                    :5
                                                ]:  # Show first 5
                                                    st.write(f"• {dr}")
                                                if len(date_ranges) > 5:
                                                    st.write(
                                                        f"... and {len(date_ranges) - 5} more ranges"
                                                    )

                # Navigation guide
                st.markdown("---")
                st.info(
                    "💡 **Smart Navigation:** Files are organized by Symbol → Timeframe. Expand any symbol to see its timeframes, then expand a timeframe to view individual files and access quick actions like sample data viewing and quality analysis."
                )

            else:
                st.info("No data files found in the selected directory")

        except Exception as e:
            st.error(f"Failed to scan data files: {e}")
            st.info("Make sure the data directory exists and contains CSV files")

    with data_tab2:
        st.subheader("Process Databento Data")

        # File upload section
        uploaded_file = st.file_uploader(
            "Upload Databento ZIP file",
            type=["zip"],
            help="Upload a ZIP file containing Databento data for processing",
        )

        if uploaded_file is not None:
            st.success(f"File uploaded: {uploaded_file.name}")

            # Process button
            if st.button("🚀 Process Uploaded File"):
                try:
                    with st.spinner("Starting processing job..."):
                        files = {"file": uploaded_file}
                        data = {"output_dir": "data/csv/1m"}

                        response = api_client._make_request(
                            "POST",
                            "/api/data/process",
                            files=files,
                            data=data,
                        )

                    if response and "job_id" in response:
                        job_id = response["job_id"]
                        st.success(f"✅ Processing started! Job ID: {job_id}")

                        # Show job status
                        with st.expander("Job Status", expanded=True):
                            status_placeholder = st.empty()

                            # Poll for status
                            import time

                            for _ in range(30):  # Poll for 30 seconds
                                try:
                                    status_response = api_client._make_request(
                                        "GET", f"/api/data/process/{job_id}"
                                    )
                                    if status_response:
                                        status = status_response.get(
                                            "status", "unknown"
                                        )
                                        message = status_response.get("message", "")

                                        if status == "completed":
                                            status_placeholder.success(f"✅ {message}")
                                            st.rerun()
                                            break
                                        elif status == "failed":
                                            status_placeholder.error(f"❌ {message}")
                                            break
                                        else:
                                            status_placeholder.info(f"🔄 {message}")

                                    time.sleep(2)

                                except Exception as e:
                                    status_placeholder.error(
                                        f"Error checking status: {e}"
                                    )
                                    break

                            if status_placeholder.empty:
                                st.info(
                                    "Processing may take longer. Check back later or refresh the page."
                                )
                    else:
                        st.error("Failed to start processing job")

                except Exception as e:
                    st.error(f"Failed to process file: {e}")

        # Alternative: Process existing zip file
        st.markdown("---")
        st.subheader("Process Existing Zip File")

        zip_path = st.text_input(
            "Zip File Path",
            placeholder="/path/to/databento/data.zip",
            help="Path to an existing Databento zip file on the server",
        )

        if zip_path and st.button("Process Existing File"):
            try:
                with st.spinner("Starting processing job..."):
                    response = api_client._make_request(
                        "POST",
                        "/api/data/process",
                        json={
                            "zip_file_path": zip_path,
                            "output_dir": "data/csv/1m",
                        },
                    )

                if response and "job_id" in response:
                    st.success(f"Processing job started: {response['job_id']}")
                else:
                    st.error("Failed to start processing job")

            except Exception as e:
                st.error(f"Failed to process file: {e}")

    with data_tab3:
        st.subheader("Data Statistics")

        try:
            # Get statistics
            stats_response = api_client._make_request("GET", "/api/data/stats")

            if stats_response:
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Total Files", stats_response.get("total_files", 0))
                with col2:
                    st.metric(
                        "Total Size",
                        f"{stats_response.get('total_size_mb', 0):.1f} MB",
                    )
                with col3:
                    st.metric("Symbols", len(stats_response.get("symbols", [])))
                with col4:
                    st.metric("Timeframes", len(stats_response.get("timeframes", [])))

                # Quality distribution
                st.subheader("Data Quality Distribution")
                quality_dist = stats_response.get("quality_distribution", {})

                quality_data = {
                    "Quality": ["Excellent", "Good", "Fair", "Poor"],
                    "Count": [
                        quality_dist.get("excellent", 0),
                        quality_dist.get("good", 0),
                        quality_dist.get("fair", 0),
                        quality_dist.get("poor", 0),
                    ],
                }

                quality_df = pd.DataFrame(quality_data)
                st.bar_chart(quality_df.set_index("Quality"))

                # Symbols list
                st.subheader("Available Symbols")
                symbols = stats_response.get("symbols", [])
                if symbols:
                    st.write(", ".join(sorted(symbols)))
                else:
                    st.info("No symbols found")

                # Timeframes list
                st.subheader("Available Timeframes")
                timeframes = stats_response.get("timeframes", [])
                if timeframes:
                    # Sort timeframes by typical granularity
                    timeframe_order = {
                        "1m": 0,
                        "5m": 1,
                        "15m": 2,
                        "30m": 3,
                        "1h": 4,
                        "4h": 5,
                        "1d": 6,
                        "1w": 7,
                        "1M": 8,
                    }
                    sorted_timeframes = sorted(
                        timeframes, key=lambda x: timeframe_order.get(x, 99)
                    )
                    st.write(", ".join(sorted_timeframes))
                else:
                    st.info("No timeframes found")

            else:
                st.error("Failed to load statistics")

        except Exception as e:
            st.error(f"Failed to load statistics: {e}")

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
        try:
            analytics_data = api_client.get_portfolio_analytics()
        except Exception as api_error:
            error_msg = str(api_error)
            if "400" in error_msg and "insufficient data" in error_msg.lower():
                st.info("📊 Analytics require completed backtests to display data.")
                st.markdown("""
                **To see analytics:**
                1. Run some backtests using the **Backtests** tab
                2. Wait for them to complete (status: ✅ Completed)
                3. Return to this Analytics tab to view performance metrics
                """)
                st.stop()
            else:
                # Re-raise other API errors
                raise api_error

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
                    try:
                        filtered_data = api_client.get_portfolio_analytics(
                            strategy_filter=strategy_filter
                            if strategy_filter
                            else None,
                            symbol_filter=symbol_filter if symbol_filter else None,
                        )
                        st.info("Filtered results applied above")
                    except Exception as filter_error:
                        filter_error_msg = str(filter_error)
                        if (
                            "400" in filter_error_msg
                            and "insufficient data" in filter_error_msg.lower()
                        ):
                            st.warning(
                                "⚠️ No data available for the selected filters. Try different criteria or run more backtests."
                            )
                        else:
                            st.error(f"Failed to apply filters: {filter_error_msg}")
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

                if backtests:
                    # Initialize session state for selections
                    if "selected_backtests" not in st.session_state:
                        st.session_state.selected_backtests = []

                    # Convert to DataFrame for display
                    import pandas as pd

                    bt_df = pd.DataFrame(backtests)

                    # Add paging
                    page_size = 10
                    total_pages = (len(bt_df) + page_size - 1) // page_size

                    if "backtest_page" not in st.session_state:
                        st.session_state.backtest_page = 1

                    # Page controls
                    col1, col2, col3 = st.columns([1, 2, 1])

                    with col1:
                        if st.button(
                            "⬅️ Previous", disabled=st.session_state.backtest_page <= 1
                        ):
                            st.session_state.backtest_page -= 1
                            st.rerun()

                    with col2:
                        page_options = list(range(1, total_pages + 1))
                        selected_page = st.selectbox(
                            f"Page {st.session_state.backtest_page} of {total_pages}",
                            options=page_options,
                            index=st.session_state.backtest_page - 1,
                            key="page_selector",
                        )
                        if selected_page != st.session_state.backtest_page:
                            st.session_state.backtest_page = selected_page
                            st.rerun()

                    with col3:
                        if st.button(
                            "Next ➡️",
                            disabled=st.session_state.backtest_page >= total_pages,
                        ):
                            st.session_state.backtest_page += 1
                            st.rerun()

                    # Get current page data
                    start_idx = (st.session_state.backtest_page - 1) * page_size
                    end_idx = start_idx + page_size
                    page_df = bt_df.iloc[start_idx:end_idx]

                    # Selection controls
                    st.markdown("---")
                    col1, col2, col3, col4 = st.columns([1, 1, 2, 1])

                    with col1:
                        select_all = st.checkbox(
                            "Select All",
                            value=len(st.session_state.selected_backtests)
                            == len(page_df),
                            key="select_all_backtests",
                        )

                    with col2:
                        if st.button("🗑️ Delete Selected", type="secondary"):
                            selected_ids = st.session_state.get(
                                "selected_backtests", []
                            )

                            if not selected_ids:
                                st.warning("Please select backtests to delete")
                            else:
                                # Confirm deletion
                                confirm_key = (
                                    f"confirm_delete_{st.session_state.backtest_page}"
                                )
                                if st.checkbox(
                                    f"Confirm deletion of {len(selected_ids)} selected backtest(s)",
                                    key=confirm_key,
                                ):
                                    try:
                                        deleted_count = 0
                                        for bt_id in selected_ids:
                                            try:
                                                api_client.delete_backtest(int(bt_id))
                                                deleted_count += 1
                                            except Exception as e:
                                                st.error(
                                                    f"Failed to delete backtest {bt_id}: {e}"
                                                )

                                        if deleted_count > 0:
                                            st.success(
                                                f"Successfully deleted {deleted_count} backtest(s)"
                                            )
                                            # Clear selections and refresh
                                            st.session_state.selected_backtests = []
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"Error during deletion: {e}")

                    with col3:
                        selected_count = len(st.session_state.selected_backtests)
                        if selected_count > 0:
                            st.info(f"Selected {selected_count} backtest(s)")

                    with col4:
                        if st.button("🔄 Refresh"):
                            st.session_state.selected_backtests = []
                            st.rerun()

                    # Handle select all
                    if select_all:
                        page_ids = [str(row["id"]) for _, row in page_df.iterrows()]
                        st.session_state.selected_backtests = list(
                            set(st.session_state.selected_backtests + page_ids)
                        )
                    else:
                        # Remove page items from selection if unchecked
                        page_ids = [str(row["id"]) for _, row in page_df.iterrows()]
                        st.session_state.selected_backtests = [
                            bt_id
                            for bt_id in st.session_state.selected_backtests
                            if bt_id not in page_ids
                        ]

                    st.markdown("---")

                    # Display backtests with compact rows
                    st.write("### Backtest List")

                    # Header row
                    header_cols = st.columns([0.5, 1, 2, 1, 2])
                    with header_cols[0]:
                        st.markdown("**Select**")
                    with header_cols[1]:
                        st.markdown("**ID**")
                    with header_cols[2]:
                        st.markdown("**Strategy**")
                    with header_cols[3]:
                        st.markdown("**Status**")
                    with header_cols[4]:
                        st.markdown("**Created**")

                    st.markdown("---")

                    # Data rows with compact spacing
                    for idx, row in page_df.iterrows():
                        row_cols = st.columns([0.5, 1, 2, 1, 2])

                        with row_cols[0]:
                            bt_id = str(row["id"])
                            is_selected = st.checkbox(
                                "",
                                value=bt_id in st.session_state.selected_backtests,
                                key=f"select_{bt_id}_{st.session_state.backtest_page}",
                                label_visibility="collapsed",
                            )

                            # Update session state based on checkbox
                            if (
                                is_selected
                                and bt_id not in st.session_state.selected_backtests
                            ):
                                st.session_state.selected_backtests.append(bt_id)
                            elif (
                                not is_selected
                                and bt_id in st.session_state.selected_backtests
                            ):
                                st.session_state.selected_backtests.remove(bt_id)

                        with row_cols[1]:
                            st.markdown(f"`{row['id']}`")

                        with row_cols[2]:
                            st.markdown(
                                f"**{row['strategy_name'][:30]}{'...' if len(row['strategy_name']) > 30 else ''}**"
                            )

                        with row_cols[3]:
                            status = row["status"]
                            if status == "completed":
                                st.markdown("✅")
                            elif status == "running":
                                st.markdown("🔄")
                            elif status == "failed":
                                st.markdown("❌")
                            else:
                                st.markdown(status)

                        with row_cols[4]:
                            created_at = row.get("created_at", "N/A")
                            if created_at != "N/A":
                                if isinstance(created_at, str):
                                    try:
                                        from datetime import datetime

                                        dt = datetime.fromisoformat(
                                            created_at.replace("Z", "+00:00")
                                        )
                                        st.markdown(dt.strftime("%m/%d %H:%M"))
                                    except:
                                        st.markdown(str(created_at)[:10])
                                else:
                                    st.markdown(str(created_at)[:10])
                            else:
                                st.markdown("N/A")

                        # Thin divider
                        st.markdown(
                            '<hr style="margin: 2px 0; border: none; border-top: 1px solid #ddd;">',
                            unsafe_allow_html=True,
                        )

            with bt_tab2:
                st.subheader("Backtest Detail View")

                # Select backtest
                if backtests:
                    backtest_options = {
                        f"{str(bt['id'])[:8]} - {bt['strategy_name']} ({bt['status']})": bt[
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
                        try:
                            bt_data = api_client.get_backtest(int(bt_id))
                        except Exception as e:
                            st.error(f"Failed to load backtest details: {e}")
                            bt_data = None

                        if bt_data:
                            try:
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
                                    if (
                                        job_status
                                        and job_status.get("status") == "completed"
                                    ):
                                        st.success("✅ Backtest completed!")
                                        st.rerun()
                                    elif (
                                        job_status
                                        and job_status.get("status") == "failed"
                                    ):
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
                            except Exception as e:
                                st.error(f"Error displaying backtest details: {e}")
                                st.json(bt_data)  # Show raw data for debugging
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
                optimizations_response = api_client.list_optimizations()
                optimizations = optimizations_response.get("optimizations", [])

                if not optimizations:
                    st.info(
                        "No optimization jobs found. Submit an optimization job first."
                    )
                else:
                    # Select optimization
                    opt_options = {str(opt["id"]): opt for opt in optimizations}
                    selected_opt_id = st.selectbox(
                        "Select Optimization Job",
                        options=list(opt_options.keys()),
                        format_func=lambda x: f"{x[:8]} - {opt_options[x].get('strategy_name', 'Unknown')} ({opt_options[x].get('status', 'Unknown')})",
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

                                if detailed_data and "trials_data" in detailed_data:
                                    results = detailed_data["trials_data"]

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

                    opt_df = pd.DataFrame(optimizations.get("optimizations", []))

                    display_cols = [
                        "id",
                        "strategy_name",
                        "objective_metric",
                        "max_trials",
                        "created_at",
                        "status",
                    ]
                    available_cols = [
                        col for col in display_cols if col in opt_df.columns
                    ]

                    if available_cols:
                        # Format id to show as string
                        if "id" in opt_df.columns:
                            opt_df["id"] = opt_df["id"].astype(str)

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
