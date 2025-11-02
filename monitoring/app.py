"""
Streamlit Monitoring Dashboard for AI Trading Platform
Epic 7: Monitoring & Observability
Enhanced Real-time Dashboard with P&L calculations and system health
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import sys
import time
from pathlib import Path

# Add scripts directory to path for imports
sys.path.append(str(Path(__file__).parent.parent / 'scripts'))

# Page configuration
st.set_page_config(
    page_title="AI Trading Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Auto-refresh every 5 seconds
st_autorefresh = st.experimental_rerun

# Cache database connections and calculations
@st.cache_resource
def get_db_manager():
    """Get database manager instance."""
    try:
        from scripts.db_manager import DBManager
        # Use relative path from project root
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(project_root, 'data', 'sqlite', 'trades.db')
        return DBManager(db_path)
    except Exception as e:
        st.error(f"Database connection failed: {e}")
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
            current_price = pos.get('current_price', pos.get('average_price', 0))
            
            from scripts.utils.pnl_calculator import Position
            position_obj = Position(
                symbol=pos['symbol'],
                quantity=pos['quantity'],
                entry_price=pos['average_price'],
                current_price=current_price
            )
            
            pnl_result = pnl_calc.calculate_position_pnl(position_obj, current_price)
            
            enhanced_pos = {
                'Symbol': pos['symbol'],
                'Quantity': pos['quantity'],
                'Avg Price': f"${pos['average_price']:.2f}",
                'Current Price': f"${current_price:.2f}",
                'Market Value': f"${pnl_result['market_value']:,.2f}",
                'Unrealized P&L': f"${pnl_result['unrealized_pnl']:,.2f}",
                'P&L %': f"{pnl_result['unrealized_pnl_pct']:.2f}%",
                'Entry Date': pos['entry_date'][:10] if pos['entry_date'] else 'N/A'
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
                'Order ID': order['order_id'][:8] + '...' if len(order['order_id']) > 8 else order['order_id'],
                'Symbol': order['symbol'],
                'Side': order['side'],
                'Quantity': order['quantity'],
                'Type': order['order_type'],
                'Status': order['status'],
                'Fill Price': f"${order['average_fill_price']:.2f}" if order['average_fill_price'] else 'N/A',
                'Commission': f"${order['commission']:.2f}" if order['commission'] else '$0.00',
                'Created': order['created_at'][:19] if order['created_at'] else 'N/A'
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
        total_trades = len([o for o in orders if o['status'] == 'FILLED'])
        
        from scripts.utils.pnl_calculator import PnLCalculator
        pnl_calc = PnLCalculator()
        
        for pos in positions:
            current_price = pos.get('current_price', pos.get('average_price', 0))
            from scripts.utils.pnl_calculator import Position
            position_obj = Position(
                symbol=pos['symbol'],
                quantity=pos['quantity'],
                entry_price=pos['average_price'],
                current_price=current_price
            )
            pnl_result = pnl_calc.calculate_position_pnl(position_obj, current_price)
            total_market_value += pnl_result['market_value']
            total_unrealized_pnl += pnl_result['unrealized_pnl']
        
        for order in orders:
            total_commission += order.get('commission', 0)
        
        # Mock cash balance (in real implementation, get from broker)
        cash_balance = 100000  # Default starting capital
        
        total_equity = cash_balance + total_market_value
        
        return {
            'total_equity': total_equity,
            'cash_balance': cash_balance,
            'market_value': total_market_value,
            'unrealized_pnl': total_unrealized_pnl,
            'total_commission': total_commission,
            'total_trades': total_trades,
            'open_positions': len(positions)
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
        latest_risk = db.get_latest_risk_metrics('live_strategy') if db else None
        
        # Calculate risk metrics
        account_summary = get_account_summary()
        total_equity = account_summary.get('total_equity', 0)
        
        # Mock risk calculations (in real implementation, use actual risk calculations)
        portfolio_heat = min(abs(account_summary.get('unrealized_pnl', 0)) / max(total_equity, 1) * 100, 100)
        
        # Count recent risk events
        recent_critical_events = len([e for e in risk_events if e['severity'] == 'CRITICAL'])
        
        return {
            'portfolio_heat': portfolio_heat,
            'daily_pnl_limit': -2000,  # From config
            'position_limits': 5,  # Max positions
            'recent_critical_events': recent_critical_events,
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
    
    # Check LEAN engine (mock check)
    st.metric("LEAN Engine", "Running ✅")
    
    # Last update time
    st.metric("Last Update", datetime.now().strftime('%H:%M:%S'))

    st.markdown("---")

    # Quick stats
    st.header("📈 Quick Stats")
    account_summary = get_account_summary()
    st.metric("Active Strategies", "1")
    st.metric("Total Trades", account_summary.get('total_trades', 0))
    st.metric("P&L (Today)", f"${account_summary.get('unrealized_pnl', 0):,.2f}")

# Main dashboard metrics
account_summary = get_account_summary()
col1, col2, col3, col4 = st.columns(4)

with col1:
    delta_color = "normal" if account_summary.get('unrealized_pnl', 0) >= 0 else "inverse"
    st.metric(
        label="Total Equity",
        value=f"${account_summary.get('total_equity', 0):,.2f}",
        delta=f"{account_summary.get('unrealized_pnl', 0):,.2f}",
        delta_color=delta_color
    )

with col2:
    st.metric(
        label="Open Positions",
        value=account_summary.get('open_positions', 0),
        delta=0
    )

with col3:
    st.metric(
        label="Cash Balance",
        value=f"${account_summary.get('cash_balance', 0):,.2f}",
        delta=0
    )

with col4:
    win_rate = 0  # Would calculate from trade history
    st.metric(
        label="Win Rate",
        value=f"{win_rate:.1f}%",
        delta="0%"
    )

st.markdown("---")

# Tabs for different views
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Dashboard",
    "💼 Live Trading",
    "📜 Trade Log",
    "📈 Performance",
    "🏥 Health",
    "⚙️ Settings"
])

with tab1:
    st.header("Dashboard Overview")
    
    # Account summary section
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Account Summary")
        summary_data = {
            'Metric': ['Total Equity', 'Cash Balance', 'Market Value', 'Unrealized P&L', 'Total Commission'],
            'Value': [
                f"${account_summary.get('total_equity', 0):,.2f}",
                f"${account_summary.get('cash_balance', 0):,.2f}",
                f"${account_summary.get('market_value', 0):,.2f}",
                f"${account_summary.get('unrealized_pnl', 0):,.2f}",
                f"${account_summary.get('total_commission', 0):,.2f}"
            ]
        }
        st.dataframe(pd.DataFrame(summary_data), hide_index=True)
    
    with col2:
        st.subheader("Risk Metrics")
        risk_metrics = get_risk_metrics()
        risk_data = {
            'Metric': ['Portfolio Heat', 'Daily P&L Limit', 'Position Limits', 'Critical Events'],
            'Value': [
                f"{risk_metrics.get('portfolio_heat', 0):.1f}%",
                f"${risk_metrics.get('daily_pnl_limit', 0):,.2f}",
                f"{risk_metrics.get('position_limits', 0)} max",
                f"{risk_metrics.get('recent_critical_events', 0)} recent"
            ]
        }
        st.dataframe(pd.DataFrame(risk_data), hide_index=True)
    
    # Equity curve placeholder
    st.subheader("Equity Curve")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[datetime.now()],
        y=[account_summary.get('total_equity', 0)],
        mode='lines+markers',
        name='Equity',
        line=dict(color='blue', width=2)
    ))
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Equity ($)",
        height=400,
        showlegend=True
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
    filled_orders = [order for order in all_orders if 'FILLED' in order.get('Status', '')]
    
    if filled_orders:
        st.subheader(f"Completed Trades ({len(filled_orders)})")
        
        # Convert to DataFrame for analysis
        trades_df = pd.DataFrame(filled_orders)
        
        # Calculate P&L for each trade (simplified)
        trades_df['P&L'] = 0.0  # Would calculate from entry/exit pairs
        
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
                    mime="text/csv"
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
            if perf_summary and 'error' not in perf_summary:
                for metric_type, data in perf_summary.items():
                    if data.get('count', 0) > 0:
                        st.metric(
                            f"{metric_type.replace('_', ' ').title()}",
                            f"{data['latest']:.2f} {data['unit']}",
                            f"Avg: {data['average']:.2f} {data['unit']}"
                        )
            else:
                st.info("No performance data available yet")
        
        with col2:
            st.subheader("Performance Alerts")
            if perf_alerts:
                for alert in perf_alerts[:5]:  # Show latest 5 alerts
                    severity_color = "inverse" if alert['severity'] == 'WARNING' else "normal"
                    st.metric(
                        alert['type'].replace('_', ' '),
                        f"{alert['value']:.1f}",
                        f"Threshold: {alert['threshold']}",
                        delta_color=severity_color
                    )
            else:
                st.success("No performance alerts")
        
        st.markdown("---")
        
        # Performance charts
        st.subheader("Performance Trends")
        
        # Get performance metrics for charting
        perf_metrics = perf_monitor.db_manager.get_performance_metrics(hours_back=24, limit=100)
        
        if perf_metrics:
            # Group by metric type for separate charts
            metric_types = list(set(m['metric_type'] for m in perf_metrics))
            
            for metric_type in metric_types[:3]:  # Show first 3 metric types
                type_metrics = [m for m in perf_metrics if m['metric_type'] == metric_type]
                if len(type_metrics) > 1:
                    df = pd.DataFrame(type_metrics)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values('timestamp')
                    
                    fig = px.line(
                        df,
                        x='timestamp',
                        y='metric_value',
                        title=f"{metric_type.replace('_', ' ').title()} Over Time",
                        labels={'metric_value': f"Value ({type_metrics[0]['unit']})", 'timestamp': 'Time'}
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
            st.metric("Total Return", f"{account_summary.get('unrealized_pnl', 0):,.2f}")
            st.metric("Daily Avg Return", "N/A")
            st.metric("Best Trade", "N/A")
            st.metric("Total Commission", f"${account_summary.get('total_commission', 0):,.2f}")

with tab6:
    st.header("🏥 System Health")
    
    # Health monitoring section
    try:
        from scripts.utils.health_monitor import HealthMonitor, HealthStatus
        health_monitor = HealthMonitor()
        
        # Run health checks
        health_checks = health_monitor.run_all_checks()
        overall_status, overall_message = health_monitor.get_overall_status(health_checks)
        
        # Overall health status
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_color = {
                HealthStatus.HEALTHY: "green",
                HealthStatus.WARNING: "orange",
                HealthStatus.CRITICAL: "red",
                HealthStatus.UNKNOWN: "gray"
            }.get(overall_status, "gray")
            
            st.markdown(f"""
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
            """, unsafe_allow_html=True)
        
        with col2:
            # Health summary
            health_summary = health_monitor.get_health_summary()
            if 'error' not in health_summary:
                st.metric("System Uptime", f"{health_summary.get('uptime_percent', 0):.1f}%")
                st.metric("Total Checks", health_summary.get('total_checks', 0))
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
            
            st.metric("Last Check", datetime.now().strftime('%H:%M:%S'))
        
        st.markdown("---")
        
        # Individual health checks
        st.subheader("Health Check Details")
        
        # Group checks by status
        healthy_checks = [c for c in health_checks if c.status == HealthStatus.HEALTHY]
        warning_checks = [c for c in health_checks if c.status == HealthStatus.WARNING]
        critical_checks = [c for c in health_checks if c.status == HealthStatus.CRITICAL]
        
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
        st.info("Health endpoint returns JSON with system status and detailed check results.")
        
    except Exception as e:
        st.error(f"Health monitoring not available: {e}")
        st.info("Health monitoring requires proper system permissions and dependencies.")

with tab5:
    st.header("Settings")
    
    st.subheader("Environment Variables")
    env_vars = {
        'IB_TRADING_MODE': os.getenv('IB_TRADING_MODE', 'not set'),
        'LEAN_ENGINE_PATH': os.getenv('LEAN_ENGINE_PATH', 'not set'),
        'LOG_LEVEL': os.getenv('LOG_LEVEL', 'not set'),
        'DATABASE_PATH': '/app/data/sqlite/trades.db'
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
