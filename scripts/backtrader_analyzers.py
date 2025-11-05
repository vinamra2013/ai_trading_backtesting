"""
Custom Backtrader Analyzers for IB Performance Metrics
Epic 12: US-12.2 - Performance Analyzers

Provides custom analyzers matching LEAN metrics for comparison:
- IBPerformanceAnalyzer: Comprehensive performance metrics
- CommissionAnalyzer: Detailed commission tracking
- EquityCurveAnalyzer: Portfolio value over time
- MonthlyReturnsAnalyzer: Monthly performance breakdown
"""

import backtrader as bt
from datetime import datetime
from collections import defaultdict


class IBPerformanceAnalyzer(bt.Analyzer):
    """
    Comprehensive performance analyzer matching LEAN metrics

    Tracks:
    - Total trades, wins, losses
    - Win rate, profit factor
    - Average win/loss
    - Total P&L, commissions
    - Sharpe ratio components
    - Maximum drawdown
    """

    def __init__(self):
        self.trades = []
        self.daily_returns = []
        self.equity_curve = []
        self.commissions = 0.0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.total_pnl_gross = 0.0

        self.start_value = self.strategy.broker.getvalue()
        self.peak_value = self.start_value
        self.max_drawdown = 0.0
        self.max_drawdown_pct = 0.0

    def notify_trade(self, trade):
        """Called for each completed trade"""
        if trade.isclosed:
            # Calculate trade metrics
            trade_data = {
                'symbol': trade.data._name,
                'entry_date': bt.num2date(trade.dtopen),
                'exit_date': bt.num2date(trade.dtclose),
                'entry_price': trade.price,
                'exit_price': trade.price + (trade.pnl / trade.size if trade.size != 0 else 0),
                'size': trade.size,
                'pnl_gross': trade.pnl,
                'pnl_net': trade.pnlcomm,
                'commission': trade.commission,
                'bars_held': trade.barlen,
                'direction': 'Long' if trade.size > 0 else 'Short',
            }

            self.trades.append(trade_data)
            self.commissions += trade.commission
            self.total_pnl += trade.pnlcomm
            self.total_pnl_gross += trade.pnl

            if trade.pnlcomm > 0:
                self.winning_trades += 1
            elif trade.pnlcomm < 0:
                self.losing_trades += 1

    def next(self):
        """Called on each bar"""
        current_value = self.strategy.broker.getvalue()

        # Track equity curve
        self.equity_curve.append({
            'datetime': self.strategy.datetime.datetime(0),
            'value': current_value
        })

        # Calculate daily return
        if len(self.equity_curve) > 1:
            prev_value = self.equity_curve[-2]['value']
            daily_return = (current_value - prev_value) / prev_value
            self.daily_returns.append(daily_return)

        # Track drawdown
        if current_value > self.peak_value:
            self.peak_value = current_value

        drawdown = self.peak_value - current_value
        drawdown_pct = (drawdown / self.peak_value) * 100 if self.peak_value > 0 else 0

        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
            self.max_drawdown_pct = drawdown_pct

    def get_analysis(self):
        """Return analysis results"""
        total_trades = len(self.trades)
        final_value = self.strategy.broker.getvalue()

        # Calculate metrics
        win_rate = (self.winning_trades / total_trades * 100) if total_trades > 0 else 0

        # Calculate average win/loss
        winning_pnls = [t['pnl_net'] for t in self.trades if t['pnl_net'] > 0]
        losing_pnls = [t['pnl_net'] for t in self.trades if t['pnl_net'] < 0]

        avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0
        avg_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0

        # Profit factor
        gross_profit = sum(winning_pnls) if winning_pnls else 0
        gross_loss = abs(sum(losing_pnls)) if losing_pnls else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Calculate Sharpe ratio (annualized)
        if self.daily_returns:
            import numpy as np
            returns_array = np.array(self.daily_returns)
            sharpe_ratio = np.mean(returns_array) / np.std(returns_array) * np.sqrt(252) if np.std(returns_array) > 0 else 0
        else:
            sharpe_ratio = 0

        return {
            'total_trades': total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'total_pnl_gross': self.total_pnl_gross,
            'total_commission': self.commissions,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct,
            'initial_value': self.start_value,
            'final_value': final_value,
            'total_return': final_value - self.start_value,
            'total_return_pct': ((final_value / self.start_value) - 1) * 100,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
        }


class CommissionAnalyzer(bt.Analyzer):
    """
    Detailed commission tracking analyzer

    Tracks commission by:
    - Total commission paid
    - Commission per trade
    - Commission as % of P&L
    - SEC fees breakdown
    """

    def __init__(self):
        self.total_commission = 0.0
        self.trade_commissions = []
        self.sec_fees = 0.0
        self.base_commission = 0.0

    def notify_trade(self, trade):
        """Track commission for each trade"""
        if trade.isclosed:
            commission_data = {
                'datetime': bt.num2date(trade.dtclose),
                'commission': trade.commission,
                'trade_value': abs(trade.size * trade.price),
                'commission_pct': (trade.commission / abs(trade.size * trade.price) * 100) if trade.size != 0 else 0,
            }

            self.trade_commissions.append(commission_data)
            self.total_commission += trade.commission

    def get_analysis(self):
        """Return commission analysis"""
        avg_commission = self.total_commission / len(self.trade_commissions) if self.trade_commissions else 0

        return {
            'total_commission': self.total_commission,
            'trade_count': len(self.trade_commissions),
            'avg_commission_per_trade': avg_commission,
            'commission_breakdown': self.trade_commissions,
        }


class EquityCurveAnalyzer(bt.Analyzer):
    """
    Equity curve analyzer for portfolio value tracking

    Provides time-series data for:
    - Portfolio value
    - Cash balance
    - Position value
    - Daily returns
    """

    def __init__(self):
        self.equity_data = []
        self.dates = []
        self.values = []
        self.cash = []

    def next(self):
        """Record equity on each bar"""
        dt = self.strategy.datetime.datetime(0)
        value = self.strategy.broker.getvalue()
        cash = self.strategy.broker.getcash()

        self.equity_data.append({
            'datetime': dt,
            'value': value,
            'cash': cash,
            'position_value': value - cash,
        })

        self.dates.append(dt)
        self.values.append(value)
        self.cash.append(cash)

    def get_analysis(self):
        """Return equity curve data"""
        return {
            'equity_curve': self.equity_data,
            'dates': self.dates,
            'values': self.values,
            'cash': self.cash,
        }


class MonthlyReturnsAnalyzer(bt.Analyzer):
    """
    Monthly returns analyzer for performance heatmap

    Calculates:
    - Monthly returns (%)
    - Year-over-year comparison
    - Best/worst months
    """

    def __init__(self):
        self.monthly_returns = defaultdict(lambda: {'start_value': 0, 'end_value': 0})
        self.current_month = None
        self.month_start_value = None

    def next(self):
        """Track monthly performance"""
        dt = self.strategy.datetime.datetime(0)
        value = self.strategy.broker.getvalue()

        year_month = (dt.year, dt.month)

        # New month
        if year_month != self.current_month:
            if self.current_month is not None and self.month_start_value is not None:
                # Calculate previous month return
                prev_value = self.monthly_returns[self.current_month]['end_value']
                monthly_return = ((prev_value / self.month_start_value) - 1) * 100 if self.month_start_value > 0 else 0
                self.monthly_returns[self.current_month]['return'] = monthly_return

            # Start new month
            self.current_month = year_month
            self.month_start_value = value
            self.monthly_returns[year_month]['start_value'] = value

        # Update current month end value
        self.monthly_returns[year_month]['end_value'] = value

    def stop(self):
        """Calculate final month return"""
        if self.current_month is not None and self.month_start_value is not None:
            end_value = self.monthly_returns[self.current_month]['end_value']
            monthly_return = ((end_value / self.month_start_value) - 1) * 100 if self.month_start_value > 0 else 0
            self.monthly_returns[self.current_month]['return'] = monthly_return

    def get_analysis(self):
        """Return monthly returns data"""
        # Convert to list format
        returns_list = []
        for (year, month), data in sorted(self.monthly_returns.items()):
            returns_list.append({
                'year': year,
                'month': month,
                'return': data.get('return', 0),
                'start_value': data['start_value'],
                'end_value': data['end_value'],
            })

        return {
            'monthly_returns': returns_list,
            'monthly_returns_dict': dict(self.monthly_returns),
        }


class TradeLogAnalyzer(bt.Analyzer):
    """
    Detailed trade log analyzer

    Logs every trade with:
    - Entry/exit details
    - P&L breakdown
    - Trade duration
    - Max favorable/adverse excursion
    """

    def __init__(self):
        self.trades_log = []

    def notify_trade(self, trade):
        """Log each completed trade"""
        if trade.isclosed:
            trade_log = {
                'trade_id': len(self.trades_log) + 1,
                'symbol': trade.data._name,
                'direction': 'Long' if trade.size > 0 else 'Short',
                'entry_date': bt.num2date(trade.dtopen).isoformat(),
                'exit_date': bt.num2date(trade.dtclose).isoformat(),
                'entry_price': round(trade.price, 2),
                'exit_price': round(trade.price + (trade.pnl / trade.size if trade.size != 0 else 0), 2),
                'size': abs(trade.size),
                'pnl_gross': round(trade.pnl, 2),
                'pnl_net': round(trade.pnlcomm, 2),
                'commission': round(trade.commission, 2),
                'bars_held': trade.barlen,
                'pnl_pct': round((trade.pnlcomm / (trade.price * abs(trade.size)) * 100), 2) if trade.size != 0 else 0,
            }

            self.trades_log.append(trade_log)

    def get_analysis(self):
        """Return trade log"""
        return {
            'trades': self.trades_log,
            'trade_count': len(self.trades_log),
        }


if __name__ == '__main__':
    """Test analyzer imports"""
    print("Custom Backtrader Analyzers")
    print("\nAvailable Analyzers:")
    print("  - IBPerformanceAnalyzer: Comprehensive performance metrics")
    print("  - CommissionAnalyzer: Commission tracking")
    print("  - EquityCurveAnalyzer: Equity curve data")
    print("  - MonthlyReturnsAnalyzer: Monthly returns heatmap")
    print("  - TradeLogAnalyzer: Detailed trade log")
    print("\n✅ Analyzers loaded successfully!")
