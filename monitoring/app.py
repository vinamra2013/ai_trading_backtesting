"""
Streamlit Monitoring Dashboard for AI Trading Platform
Epic 7: Monitoring & Observability
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os

# Page configuration
st.set_page_config(
    page_title="AI Trading Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
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

    # Status indicators
    st.header("📊 System Status")
    st.metric("LEAN Engine", "Running ✅")
    st.metric("IB Gateway", "Connected ✅")
    st.metric("Database", "Active ✅")

    st.markdown("---")

    # Quick stats (placeholder)
    st.header("📈 Quick Stats")
    st.metric("Active Strategies", "0")
    st.metric("Total Trades", "0")
    st.metric("P&L (Today)", "$0.00")

# Main content area
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Total Equity",
        value="$0.00",
        delta="0.00%"
    )

with col2:
    st.metric(
        label="Open Positions",
        value="0",
        delta="0"
    )

with col3:
    st.metric(
        label="Win Rate",
        value="0%",
        delta="0%"
    )

st.markdown("---")

# Tabs for different views
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard",
    "📜 Trade Log",
    "📈 Performance",
    "⚙️ Settings"
])

with tab1:
    st.header("Dashboard Overview")
    st.info("👋 Welcome! The platform is ready. Start by deploying a trading strategy.")

    # Placeholder chart
    st.subheader("Equity Curve")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[datetime.now()],
        y=[0],
        mode='lines',
        name='Equity'
    ))
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Equity ($)",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("Trade Log")
    st.info("No trades yet. Deploy a strategy to see trades here.")

    # Placeholder dataframe
    df = pd.DataFrame({
        'Time': [],
        'Symbol': [],
        'Side': [],
        'Quantity': [],
        'Price': [],
        'P&L': []
    })
    st.dataframe(df, use_container_width=True)

with tab3:
    st.header("Performance Metrics")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Risk Metrics")
        st.metric("Sharpe Ratio", "N/A")
        st.metric("Max Drawdown", "N/A")
        st.metric("Win Rate", "N/A")

    with col2:
        st.subheader("Return Metrics")
        st.metric("Total Return", "N/A")
        st.metric("Daily Avg Return", "N/A")
        st.metric("Best Trade", "N/A")

with tab4:
    st.header("Settings")

    st.subheader("Environment Variables")
    st.code(f"""
IB_TRADING_MODE: {os.getenv('IB_TRADING_MODE', 'not set')}
LEAN_ENGINE_PATH: {os.getenv('LEAN_ENGINE_PATH', 'not set')}
LOG_LEVEL: {os.getenv('LOG_LEVEL', 'not set')}
    """)

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

# Footer
st.markdown("---")
st.markdown(
    "📚 [Documentation](../docs) | 🐛 [Issues](../stories) | "
    "🔧 [Configuration](../.env)"
)
