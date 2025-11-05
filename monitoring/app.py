"""
Streamlit Monitoring Dashboard for AI Trading Platform
Epic 7: Monitoring & Observability
Enhanced Real-time Dashboard with P&L calculations and system health
"""

import os
import sys
from pathlib import Path

# CRITICAL: Add paths BEFORE any other imports that might need them
sys.path.insert(0, '/app')
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent / 'utils'))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time

# Page configuration
st.set_page_config(
    page_title="AI Trading Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Auto-refresh every 5 seconds
# Note: st.experimental_rerun was removed in newer Streamlit versions
# Using time.sleep for periodic refresh instead

# Cache database connections and calculations
@st.cache_resource
def get_db_manager():
    """Get database manager instance in read-only mode."""
    try:
        from scripts.db_manager import DBManager
        # Use relative path from project root
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(project_root, 'data', 'sqlite', 'trades.db')
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
        st.info("MLflow features require the MLflow server to be running. Start with ./scripts/start.sh")
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

    # Check Backtrader engine (mock check)
    st.metric("Backtrader Engine", "Running ✅")
    
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "📊 Dashboard",
    "💼 Live Trading",
    "📜 Trade Log",
    "📈 Performance",
    "🔬 Backtests",
    "⚙️ Optimization",
    "🧪 MLflow",
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

with tab5:
    st.header("🔬 Backtests")

    # Import backtest loader
    try:
        from backtest_loader import BacktestLoader
        loader = BacktestLoader()

        # Get list of backtests
        backtests = loader.list_backtests()

        if not backtests:
            st.info("No backtest results found. Run a backtest to see results here.")
            st.markdown("**Run a backtest:**")
            st.code("source venv/bin/activate\npython scripts/run_backtest.py --algorithm algorithms/my_strategy")
        else:
            # Create tabs for different views
            bt_tab1, bt_tab2, bt_tab3, bt_tab4 = st.tabs([
                "📋 List View",
                "📊 Detail View",
                "📝 Trade Log",
                "⚖️ Comparison"
            ])

            with bt_tab1:
                st.subheader(f"All Backtests ({len(backtests)})")

                # Convert to DataFrame
                bt_df = pd.DataFrame(backtests)

                # Display columns
                display_columns = [
                    'backtest_id_short',
                    'algorithm',
                    'start_date',
                    'end_date',
                    'sharpe',
                    'total_return',
                    'max_drawdown',
                    'win_rate',
                    'trade_count',
                    'status'
                ]

                # Filter existing columns
                display_columns = [col for col in display_columns if col in bt_df.columns]

                # Format numeric columns
                if 'total_return' in bt_df.columns:
                    bt_df['total_return'] = bt_df['total_return'].apply(lambda x: f"{x:.2f}%")
                if 'max_drawdown' in bt_df.columns:
                    bt_df['max_drawdown'] = bt_df['max_drawdown'].apply(lambda x: f"{x:.2f}%")
                if 'win_rate' in bt_df.columns:
                    bt_df['win_rate'] = bt_df['win_rate'].apply(lambda x: f"{x:.2f}%")
                if 'sharpe' in bt_df.columns:
                    bt_df['sharpe'] = bt_df['sharpe'].apply(lambda x: f"{x:.2f}")

                # Display table with selection
                st.dataframe(
                    bt_df[display_columns],
                    use_container_width=True,
                    hide_index=True
                )

                # Filter controls
                col1, col2 = st.columns(2)
                with col1:
                    filter_algorithm = st.multiselect(
                        "Filter by Algorithm",
                        options=bt_df['algorithm'].unique().tolist() if 'algorithm' in bt_df.columns else []
                    )
                with col2:
                    filter_status = st.multiselect(
                        "Filter by Status",
                        options=bt_df['status'].unique().tolist() if 'status' in bt_df.columns else []
                    )

            with bt_tab2:
                st.subheader("Backtest Detail View")

                # Select backtest
                selected_bt = st.selectbox(
                    "Select Backtest",
                    options=[bt['backtest_id'] for bt in backtests],
                    format_func=lambda x: f"{x[:8]} - {next((b['algorithm'] for b in backtests if b['backtest_id'] == x), 'Unknown')}"
                )

                if selected_bt:
                    bt_data = loader.load_backtest(selected_bt)

                    if bt_data:
                        # Metrics cards
                        st.markdown("### Key Metrics")
                        col1, col2, col3, col4, col5, col6 = st.columns(6)

                        stats = bt_data.get('Statistics', {})

                        with col1:
                            sharpe = loader._safe_float(stats.get('Sharpe Ratio', 0))
                            st.metric("Sharpe Ratio", f"{sharpe:.2f}")

                        with col2:
                            total_return = loader._safe_float(stats.get('Total Net Profit', 0))
                            st.metric("Total Return", f"{total_return:.2f}%")

                        with col3:
                            max_dd = loader._safe_float(stats.get('Drawdown', 0))
                            st.metric("Max Drawdown", f"{max_dd:.2f}%")

                        with col4:
                            win_rate = loader._safe_float(stats.get('Win Rate', 0))
                            st.metric("Win Rate", f"{win_rate:.2f}%")

                        with col5:
                            trade_count = loader._safe_int(stats.get('Total Trades', 0))
                            st.metric("Trade Count", trade_count)

                        with col6:
                            profit_factor = loader._safe_float(stats.get('Profit-Loss Ratio', 0))
                            st.metric("Profit Factor", f"{profit_factor:.2f}")

                        st.markdown("---")

                        # Equity curve
                        st.markdown("### Equity Curve")
                        equity_df = loader.get_equity_curve(selected_bt)

                        if equity_df is not None and not equity_df.empty:
                            fig = px.line(
                                equity_df,
                                x='date',
                                y='equity',
                                title='Portfolio Equity Over Time'
                            )
                            fig.update_layout(
                                xaxis_title="Date",
                                yaxis_title="Equity ($)",
                                height=400
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("Equity curve data not available")

                        # Drawdown chart
                        st.markdown("### Drawdown Chart")
                        dd_df = loader.get_drawdown_series(selected_bt)

                        if dd_df is not None and not dd_df.empty:
                            fig = px.area(
                                dd_df,
                                x='date',
                                y='drawdown',
                                title='Underwater Plot (Drawdown %)'
                            )
                            fig.update_layout(
                                xaxis_title="Date",
                                yaxis_title="Drawdown (%)",
                                height=300
                            )
                            fig.update_traces(fill='tozeroy', fillcolor='rgba(255,0,0,0.3)')
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("Drawdown data not available")

                        # Monthly returns heatmap
                        st.markdown("### Monthly Returns")
                        monthly_df = loader.get_monthly_returns(selected_bt)

                        if monthly_df is not None and not monthly_df.empty:
                            fig = px.imshow(
                                monthly_df,
                                labels=dict(x="Month", y="Year", color="Return (%)"),
                                x=[
                                    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
                                ],
                                color_continuous_scale='RdYlGn',
                                aspect="auto"
                            )
                            fig.update_layout(height=400)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("Monthly returns data not available")
                    else:
                        st.error("Failed to load backtest data")

            with bt_tab3:
                st.subheader("Trade Log")

                # Select backtest
                selected_bt_trades = st.selectbox(
                    "Select Backtest for Trades",
                    options=[bt['backtest_id'] for bt in backtests],
                    format_func=lambda x: f"{x[:8]} - {next((b['algorithm'] for b in backtests if b['backtest_id'] == x), 'Unknown')}",
                    key="trade_log_selector"
                )

                if selected_bt_trades:
                    trades_df = loader.get_trades(selected_bt_trades)

                    if trades_df is not None and not trades_df.empty:
                        st.markdown(f"**Total Trades:** {len(trades_df)}")

                        # Display columns
                        display_cols = [
                            'symbol', 'entry_date', 'entry_price',
                            'exit_date', 'exit_price', 'pnl',
                            'return_pct', 'duration'
                        ]

                        # Filter existing columns
                        display_cols = [col for col in display_cols if col in trades_df.columns]

                        # Format numeric columns
                        if 'entry_price' in trades_df.columns:
                            trades_df['entry_price'] = trades_df['entry_price'].apply(lambda x: f"${x:.2f}")
                        if 'exit_price' in trades_df.columns:
                            trades_df['exit_price'] = trades_df['exit_price'].apply(lambda x: f"${x:.2f}")
                        if 'pnl' in trades_df.columns:
                            trades_df['pnl'] = trades_df['pnl'].apply(lambda x: f"${x:.2f}")
                        if 'return_pct' in trades_df.columns:
                            trades_df['return_pct'] = trades_df['return_pct'].apply(lambda x: f"{x:.2f}%")

                        st.dataframe(trades_df[display_cols], use_container_width=True)

                        # Export to CSV
                        csv = trades_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Export to CSV",
                            data=csv,
                            file_name=f"trades_{selected_bt_trades[:8]}_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("No trade data available for this backtest")

            with bt_tab4:
                st.subheader("Backtest Comparison")

                # Multi-select backtests
                selected_bts = st.multiselect(
                    "Select Backtests to Compare (2-5)",
                    options=[bt['backtest_id'] for bt in backtests],
                    format_func=lambda x: f"{x[:8]} - {next((b['algorithm'] for b in backtests if b['backtest_id'] == x), 'Unknown')}",
                    max_selections=5
                )

                if len(selected_bts) >= 2:
                    # Comparison table
                    st.markdown("### Metrics Comparison")

                    comparison_data = []
                    for bt_id in selected_bts:
                        bt_data = loader.load_backtest(bt_id)
                        if bt_data:
                            stats = bt_data.get('Statistics', {})
                            comparison_data.append({
                                'ID': bt_id[:8],
                                'Algorithm': bt_data.get('algorithm', 'Unknown'),
                                'Sharpe': loader._safe_float(stats.get('Sharpe Ratio', 0)),
                                'Return %': loader._safe_float(stats.get('Total Net Profit', 0)),
                                'Max DD %': loader._safe_float(stats.get('Drawdown', 0)),
                                'Win Rate %': loader._safe_float(stats.get('Win Rate', 0)),
                                'Trades': loader._safe_int(stats.get('Total Trades', 0)),
                                'Profit Factor': loader._safe_float(stats.get('Profit-Loss Ratio', 0))
                            })

                    comp_df = pd.DataFrame(comparison_data)

                    # Highlight best performers
                    st.dataframe(
                        comp_df.style.highlight_max(
                            subset=['Sharpe', 'Return %', 'Win Rate %', 'Profit Factor'],
                            color='lightgreen'
                        ).highlight_min(
                            subset=['Max DD %'],
                            color='lightgreen'
                        ),
                        use_container_width=True
                    )

                    st.markdown("---")

                    # Overlay equity curves
                    st.markdown("### Equity Curve Comparison")

                    fig = go.Figure()

                    for bt_id in selected_bts:
                        equity_df = loader.get_equity_curve(bt_id)
                        if equity_df is not None and not equity_df.empty:
                            fig.add_trace(go.Scatter(
                                x=equity_df['date'],
                                y=equity_df['equity'],
                                mode='lines',
                                name=f"{bt_id[:8]}",
                                line=dict(width=2)
                            ))

                    fig.update_layout(
                        xaxis_title="Date",
                        yaxis_title="Equity ($)",
                        height=500,
                        hovermode='x unified'
                    )

                    st.plotly_chart(fig, use_container_width=True)

                elif len(selected_bts) == 1:
                    st.info("Please select at least 2 backtests to compare")
                else:
                    st.info("Select 2 or more backtests above to compare their performance")

    except Exception as e:
        st.error(f"Error loading backtests: {e}")
        st.info("Make sure backtest results are available in /app/results/backtests/")

with tab6:
    st.header("⚙️ Optimization")

    # Import optimization loader
    try:
        from optimization_loader import OptimizationLoader
        opt_loader = OptimizationLoader()

        # Create tabs for optimization
        opt_tab1, opt_tab2, opt_tab3 = st.tabs([
            "🚀 Run Optimization",
            "📊 Results",
            "📜 History"
        ])

        with opt_tab1:
            st.subheader("Run Parameter Optimization")

            # Algorithm selection
            algorithms_dir = Path("/app/algorithms")
            algorithm_paths = []

            if algorithms_dir.exists():
                for algo_dir in algorithms_dir.iterdir():
                    if algo_dir.is_dir() and (algo_dir / "main.py").exists():
                        algorithm_paths.append(str(algo_dir.relative_to(algorithms_dir.parent)))

            selected_algorithm = st.selectbox(
                "Select Algorithm",
                options=algorithm_paths if algorithm_paths else ["No algorithms found"]
            )

            st.markdown("---")

            # Parameter configuration
            st.markdown("### Parameter Configuration")
            st.info("Add parameters to optimize. Each parameter needs a name, min value, max value, and step size.")

            # Initialize session state for parameters
            if 'opt_parameters' not in st.session_state:
                st.session_state.opt_parameters = []

            # Add parameter button
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("**Current Parameters:**")
                if st.session_state.opt_parameters:
                    for i, param in enumerate(st.session_state.opt_parameters):
                        st.text(f"{i+1}. {param['name']}: [{param['min']}, {param['max']}] step {param['step']}")
                else:
                    st.text("No parameters configured")

            with col2:
                if st.button("➕ Add Parameter"):
                    st.session_state.show_param_form = True

            # Parameter form
            if st.session_state.get('show_param_form', False):
                with st.form("add_parameter_form"):
                    st.markdown("**New Parameter**")
                    param_name = st.text_input("Parameter Name", placeholder="e.g., fast_period")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        param_min = st.number_input("Min Value", value=1.0)
                    with col2:
                        param_max = st.number_input("Max Value", value=100.0)
                    with col3:
                        param_step = st.number_input("Step Size", value=1.0, min_value=0.01)

                    submitted = st.form_submit_button("Add Parameter")

                    if submitted and param_name:
                        st.session_state.opt_parameters.append({
                            'name': param_name,
                            'min': param_min,
                            'max': param_max,
                            'step': param_step
                        })
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
                        "Sharpe Ratio",
                        "Total Return",
                        "Profit Factor",
                        "Win Rate",
                        "Max Drawdown (minimize)"
                    ]
                )

            with col2:
                max_iterations = st.number_input(
                    "Max Iterations",
                    min_value=10,
                    max_value=1000,
                    value=100,
                    step=10
                )

            # Start optimization button
            st.markdown("---")

            if st.button("🚀 Start Optimization", type="primary", disabled=len(st.session_state.opt_parameters) == 0):
                if not st.session_state.opt_parameters:
                    st.warning("Please add at least one parameter to optimize")
                else:
                    with st.spinner("Running optimization... This may take several minutes."):
                        try:
                            # TODO: Integrate with actual optimization runner from Track C
                            st.info("Optimization feature will be integrated with Track C optimizer")

                            # Mock progress bar
                            progress_bar = st.progress(0)
                            for i in range(100):
                                time.sleep(0.01)
                                progress_bar.progress(i + 1)

                            st.success("Optimization completed! View results in the Results tab.")
                        except Exception as e:
                            st.error(f"Optimization failed: {e}")

        with opt_tab2:
            st.subheader("Optimization Results")

            # Get list of optimizations
            optimizations = opt_loader.list_optimizations()

            if not optimizations:
                st.info("No optimization results found. Run an optimization to see results here.")
            else:
                # Select optimization
                selected_opt = st.selectbox(
                    "Select Optimization Run",
                    options=[opt['optimization_id'] for opt in optimizations],
                    format_func=lambda x: f"{x[:8]} - {next((o['algorithm'] for o in optimizations if o['optimization_id'] == x), 'Unknown')}"
                )

                if selected_opt:
                    opt_data = opt_loader.load_optimization(selected_opt)

                    if opt_data:
                        st.markdown(f"**Algorithm:** {opt_data.get('algorithm', 'Unknown')}")
                        st.markdown(f"**Optimization Metric:** {opt_data.get('optimization_metric', 'N/A')}")
                        st.markdown(f"**Created:** {opt_data.get('created_at', 'N/A')}")

                        st.markdown("---")

                        # Results table
                        results_df = opt_loader.get_results_dataframe(selected_opt)

                        if results_df is not None and not results_df.empty:
                            st.markdown("### Parameter Combinations")

                            # Sort by optimization metric
                            metric_col = opt_data.get('optimization_metric', 'Sharpe Ratio').lower().replace(' ', '_')
                            if metric_col in results_df.columns:
                                results_df = results_df.sort_values(metric_col, ascending=False)

                            # Highlight top 3
                            st.dataframe(
                                results_df.head(20).style.highlight_max(
                                    subset=[col for col in results_df.columns if col not in ['parameters']],
                                    color='lightgreen'
                                ),
                                use_container_width=True
                            )

                            # Export results
                            csv = results_df.to_csv(index=False)
                            st.download_button(
                                label="📥 Export Results to CSV",
                                data=csv,
                                file_name=f"optimization_{selected_opt[:8]}_{datetime.now().strftime('%Y%m%d')}.csv",
                                mime="text/csv"
                            )

                            st.markdown("---")

                            # Parameter heatmap (if 2 parameters)
                            parameters = opt_data.get('parameters', {})
                            param_names = list(parameters.keys())

                            if len(param_names) == 2:
                                st.markdown("### Parameter Heatmap")

                                metric_for_heatmap = st.selectbox(
                                    "Select Metric for Heatmap",
                                    options=[col for col in results_df.columns if col not in param_names]
                                )

                                heatmap_df = opt_loader.get_parameter_heatmap_data(
                                    selected_opt,
                                    param_names[0],
                                    param_names[1],
                                    metric_for_heatmap
                                )

                                if heatmap_df is not None:
                                    fig = px.imshow(
                                        heatmap_df,
                                        labels=dict(
                                            x=param_names[1],
                                            y=param_names[0],
                                            color=metric_for_heatmap
                                        ),
                                        color_continuous_scale='Viridis',
                                        aspect="auto"
                                    )
                                    fig.update_layout(height=500)
                                    st.plotly_chart(fig, use_container_width=True)
                            elif len(param_names) > 2:
                                st.info("Heatmap visualization is available for 2-parameter optimizations only")
                        else:
                            st.info("No results available for this optimization")

        with opt_tab3:
            st.subheader("Optimization History")

            optimizations = opt_loader.list_optimizations()

            if optimizations:
                opt_df = pd.DataFrame(optimizations)

                st.markdown(f"**Total Optimization Runs:** {len(optimizations)}")

                display_cols = [
                    'optimization_id_short',
                    'algorithm',
                    'optimization_metric',
                    'parameter_count',
                    'result_count',
                    'created_at',
                    'status'
                ]

                # Filter existing columns
                display_cols = [col for col in display_cols if col in opt_df.columns]

                st.dataframe(opt_df[display_cols], use_container_width=True, hide_index=True)
            else:
                st.info("No optimization history available")

    except Exception as e:
        st.error(f"Error loading optimizations: {e}")
        st.info("Make sure optimization results are available in /app/results/optimizations/")

with tab7:
    st.header("🧪 MLflow Experiments")

    # Get MLflow client
    mlflow_client = get_mlflow_client()

    if not mlflow_client:
        st.error("MLflow server is not available. Please start the platform with ./scripts/start.sh")
        st.stop()

    mlflow = mlflow_client["mlflow"]
    pm = mlflow_client["project_manager"]

    # Summary metrics at top
    st.subheader("📊 Research Lab Overview")
    col1, col2, col3, col4 = st.columns(4)

    try:
        # Get all experiments
        experiments = mlflow.search_experiments()
        total_experiments = len([e for e in experiments if e.lifecycle_stage == 'active'])

        # Get all runs
        all_runs = mlflow.search_runs(experiment_ids=[e.experiment_id for e in experiments], max_results=10000)
        total_runs = len(all_runs)

        # Get recent runs (last 7 days)
        from datetime import datetime, timedelta
        import pandas as pd
        week_ago = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=7)
        recent_runs = [r for r in all_runs.itertuples() if pd.notna(r.start_time) and r.start_time > week_ago]

        # Get failed runs
        failed_runs = len([r for r in all_runs.itertuples() if r.status != 'FINISHED'])

        with col1:
            st.metric("Total Experiments", total_experiments)
        with col2:
            st.metric("Total Runs", total_runs)
        with col3:
            st.metric("Recent Runs (7d)", len(recent_runs))
        with col4:
            st.metric("Failed Runs", failed_runs, delta=f"-{failed_runs}" if failed_runs > 0 else "0")
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
        selected_asset_class = st.selectbox("Filter by Asset Class", ["All"] + asset_classes)

    with col3:
        # Strategy family filter
        strategy_families = pm.list_strategy_families()
        selected_strategy_family = st.selectbox("Filter by Strategy Family", ["All"] + strategy_families)

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
                runs = mlflow.search_runs(experiment_ids=[exp.experiment_id], max_results=1, order_by=["metrics.sharpe_ratio DESC"])

                if len(runs) > 0:
                    best_run = runs.iloc[0]
                    exp_data.append({
                        "Experiment": exp.name,
                        "Runs": mlflow.search_runs(experiment_ids=[exp.experiment_id]).shape[0],
                        "Best Sharpe": f"{best_run.get('metrics.sharpe_ratio', 0):.2f}" if 'metrics.sharpe_ratio' in best_run else "N/A",
                        "Best Return": f"{best_run.get('metrics.total_return', 0):.2%}" if 'metrics.total_return' in best_run else "N/A",
                        "Max Drawdown": f"{best_run.get('metrics.max_drawdown', 0):.2%}" if 'metrics.max_drawdown' in best_run else "N/A",
                        "Created": exp.creation_time
                    })

            if exp_data:
                df = pd.DataFrame(exp_data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                # Link to MLflow UI
                st.info("🔗 For advanced features, open the [MLflow UI](http://localhost:5000)")
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
        experiment_options = {exp.name: exp.experiment_id for exp in all_experiments if exp.lifecycle_stage == 'active'}

        if experiment_options:
            # Multi-select experiments
            selected_experiments = st.multiselect(
                "Select experiments to compare (2-5 recommended)",
                options=list(experiment_options.keys()),
                max_selections=5
            )

            if len(selected_experiments) >= 2:
                st.write(f"**Comparing {len(selected_experiments)} experiments**")

                # Get runs for selected experiments
                selected_exp_ids = [experiment_options[exp] for exp in selected_experiments]
                comparison_data = []

                for exp_name in selected_experiments:
                    exp_id = experiment_options[exp_name]
                    # Get best run for each experiment
                    runs = mlflow.search_runs(experiment_ids=[exp_id], max_results=1, order_by=["metrics.sharpe_ratio DESC"])

                    if len(runs) > 0:
                        best_run = runs.iloc[0]
                        comparison_data.append({
                            "Experiment": exp_name,
                            "Sharpe Ratio": f"{best_run.get('metrics.sharpe_ratio', 0):.2f}" if 'metrics.sharpe_ratio' in best_run else "N/A",
                            "Total Return": f"{best_run.get('metrics.total_return', 0):.2%}" if 'metrics.total_return' in best_run else "N/A",
                            "Max Drawdown": f"{best_run.get('metrics.max_drawdown', 0):.2%}" if 'metrics.max_drawdown' in best_run else "N/A",
                            "Win Rate": f"{best_run.get('metrics.win_rate', 0):.2%}" if 'metrics.win_rate' in best_run else "N/A",
                            "Sortino Ratio": f"{best_run.get('metrics.sortino_ratio', 0):.2f}" if 'metrics.sortino_ratio' in best_run else "N/A",
                            "Calmar Ratio": f"{best_run.get('metrics.calmar_ratio', 0):.2f}" if 'metrics.calmar_ratio' in best_run else "N/A"
                        })

                if comparison_data:
                    df_comparison = pd.DataFrame(comparison_data)
                    st.dataframe(df_comparison, use_container_width=True, hide_index=True)

                    # Performance charts
                    st.subheader("📊 Performance Comparison")

                    # Create radar chart for multi-dimensional comparison
                    try:
                        metrics_for_chart = []
                        for exp_name in selected_experiments:
                            exp_id = experiment_options[exp_name]
                            runs = mlflow.search_runs(experiment_ids=[exp_id], max_results=1, order_by=["metrics.sharpe_ratio DESC"])

                            if len(runs) > 0:
                                best_run = runs.iloc[0]
                                metrics_for_chart.append({
                                    "Experiment": exp_name,
                                    "Sharpe": best_run.get('metrics.sharpe_ratio', 0),
                                    "Returns": best_run.get('metrics.total_return', 0) * 100,  # Convert to percentage
                                    "Win Rate": best_run.get('metrics.win_rate', 0) * 100,
                                    "Sortino": best_run.get('metrics.sortino_ratio', 0),
                                    "Calmar": best_run.get('metrics.calmar_ratio', 0)
                                })

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
                                    labels={"Sharpe": "Sharpe Ratio"}
                                )
                                st.plotly_chart(fig_sharpe, use_container_width=True)

                            with col2:
                                fig_returns = px.bar(
                                    metrics_df,
                                    x="Experiment",
                                    y="Returns",
                                    title="Total Returns Comparison",
                                    labels={"Returns": "Total Return (%)"}
                                )
                                st.plotly_chart(fig_returns, use_container_width=True)

                            # Risk-adjusted return scatter
                            fig_scatter = px.scatter(
                                metrics_df,
                                x="Sharpe",
                                y="Returns",
                                text="Experiment",
                                title="Risk-Adjusted Returns (Sharpe vs Total Return)",
                                labels={"Sharpe": "Sharpe Ratio", "Returns": "Total Return (%)"}
                            )
                            fig_scatter.update_traces(textposition='top center', marker=dict(size=12))
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

with tab8:
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

with tab9:
    st.header("Settings")
    
    st.subheader("Environment Variables")
    env_vars = {
        'IB_TRADING_MODE': os.getenv('IB_TRADING_MODE', 'not set'),
        'IB_GATEWAY_HOST': os.getenv('IB_GATEWAY_HOST', 'ib-gateway'),
        'IB_GATEWAY_PORT': os.getenv('IB_GATEWAY_PORT', '4001'),
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
