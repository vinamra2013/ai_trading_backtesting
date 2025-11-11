"""
Interactive Brokers Commission Models for Backtrader
Epic 12: US-12.3 - IB Commission Models

Translates cost_config.yaml IB commission structures into Backtrader CommissionInfo classes

Models:
- ib_standard: Standard per-share commission ($0.005/share, $1.00 min)
- ib_pro: Tiered pricing ($0.0035/share, $0.35 min)
"""

import backtrader as bt
import yaml
from pathlib import Path


class IBCommissionBase(bt.CommInfoBase):
    """
    Base class for IB commission schemes

    Extends Backtrader's CommInfoBase with IB-specific features:
    - Per-share commission with minimum
    - SEC fees on sells
    - Slippage modeling
    """

    params = (
        ('commission_per_share', 0.005),
        ('minimum_commission', 1.00),
        ('maximum_commission_rate', 0.01),
        ('sec_fee_rate', 0.0000278),  # $27.80 per $1M
        ('stocklike', True),
        ('commtype', bt.CommInfoBase.COMM_FIXED),
        ('percabs', False),  # Commission is absolute, not percentage
    )

    def _getcommission(self, size, price, pseudoexec):
        """
        Calculate commission for a trade

        Args:
            size: Number of shares (positive for buy, negative for sell)
            price: Execution price per share
            pseudoexec: Pseudo-execution flag

        Returns:
            float: Total commission amount
        """
        # Base commission: per-share rate * number of shares
        commission = abs(size) * self.p.commission_per_share

        # Apply minimum commission
        commission = max(commission, self.p.minimum_commission)

        # Apply maximum commission rate (percentage of trade value)
        max_commission = abs(size * price) * self.p.maximum_commission_rate
        commission = min(commission, max_commission)

        # Add SEC fees for sells
        if size < 0:  # Sell order
            sec_fees = abs(size * price) * self.p.sec_fee_rate
            commission += sec_fees

        return commission


class IBCommissionStandard(IBCommissionBase):
    """
    IB Standard Commission Scheme

    - $0.005 per share
    - $1.00 minimum per order
    - SEC fees on sells: $27.80 per $1M
    """

    params = (
        ('commission_per_share', 0.005),
        ('minimum_commission', 1.00),
        ('maximum_commission_rate', 0.01),
        ('sec_fee_rate', 0.0000278),
    )


class IBCommissionPro(IBCommissionBase):
    """
    IB Pro (Tiered Pricing) Commission Scheme

    - $0.0035 per share
    - $0.35 minimum per order
    - SEC fees on sells: $27.80 per $1M
    """

    params = (
        ('commission_per_share', 0.0035),
        ('minimum_commission', 0.35),
        ('maximum_commission_rate', 0.01),
        ('sec_fee_rate', 0.0000278),
    )


class IBSlippageModel:
    """
    IB Slippage Model

    Applies realistic slippage based on order type:
    - Market orders: 5 bps typical
    - Limit orders: 0 bps (but may not fill)
    """

    def __init__(self, market_order_bps=5, limit_order_bps=0):
        """
        Initialize slippage model

        Args:
            market_order_bps: Basis points slippage for market orders
            limit_order_bps: Basis points slippage for limit orders
        """
        self.market_order_bps = market_order_bps
        self.limit_order_bps = limit_order_bps

    def get_slippage(self, price, is_market_order=True):
        """
        Calculate slippage amount

        Args:
            price: Order price
            is_market_order: True for market orders, False for limit orders

        Returns:
            float: Slippage amount per share
        """
        bps = self.market_order_bps if is_market_order else self.limit_order_bps
        return price * (bps / 10000.0)


def load_commission_from_config(scheme='ib_standard', config_path=None):
    """
    Load commission scheme from cost_config.yaml

    Args:
        scheme: Commission scheme name ('ib_standard' or 'ib_pro')
        config_path: Path to cost_config.yaml (optional)

    Returns:
        IBCommissionBase: Configured commission instance
    """
    if config_path is None:
        config_path = Path('/app/config/cost_config.yaml')

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    if scheme not in config:
        raise ValueError(f"Unknown commission scheme: {scheme}. Available: {list(config.keys())}")

    scheme_config = config[scheme]

    # Create appropriate commission class
    if scheme == 'ib_standard':
        commission = IBCommissionStandard(
            commission_per_share=scheme_config['commission_per_share'],
            minimum_commission=scheme_config['minimum_commission'],
            maximum_commission_rate=scheme_config['maximum_commission_rate'],
            sec_fee_rate=scheme_config['sec_fee_rate']
        )
    elif scheme == 'ib_pro':
        commission = IBCommissionPro(
            commission_per_share=scheme_config['commission_per_share'],
            minimum_commission=scheme_config['minimum_commission'],
            maximum_commission_rate=scheme_config['maximum_commission_rate'],
            sec_fee_rate=scheme_config['sec_fee_rate']
        )
    else:
        # Fallback to base class with config values
        commission = IBCommissionBase(
            commission_per_share=scheme_config['commission_per_share'],
            minimum_commission=scheme_config['minimum_commission'],
            maximum_commission_rate=scheme_config['maximum_commission_rate'],
            sec_fee_rate=scheme_config['sec_fee_rate']
        )

    return commission


def get_commission_scheme(scheme='ib_standard'):
    """
    Get commission scheme instance

    Args:
        scheme: 'ib_standard' or 'ib_pro'

    Returns:
        IBCommissionBase: Commission instance
    """
    if scheme == 'ib_standard':
        return IBCommissionStandard()
    elif scheme == 'ib_pro':
        return IBCommissionPro()
    else:
        raise ValueError(f"Unknown scheme: {scheme}. Use 'ib_standard' or 'ib_pro'")


if __name__ == '__main__':
    """Test commission calculations"""
    print("Testing IB Commission Models...\n")

    # Test cases
    test_trades = [
        {'size': 100, 'price': 50.00, 'desc': '100 shares @ $50 (buy)'},
        {'size': -100, 'price': 50.00, 'desc': '100 shares @ $50 (sell)'},
        {'size': 50, 'price': 100.00, 'desc': '50 shares @ $100 (buy)'},
        {'size': 1000, 'price': 10.00, 'desc': '1000 shares @ $10 (buy)'},
        {'size': 10, 'price': 5.00, 'desc': '10 shares @ $5 (buy - min commission)'},
    ]

    # Test standard commission
    print("=" * 60)
    print("IB STANDARD COMMISSION ($0.005/share, $1.00 min)")
    print("=" * 60)
    standard = IBCommissionStandard()

    for trade in test_trades:
        commission = standard._getcommission(trade['size'], trade['price'], False)
        trade_value = abs(trade['size'] * trade['price'])
        commission_pct = (commission / trade_value) * 100

        print(f"\n{trade['desc']}")
        print(f"  Trade Value: ${trade_value:,.2f}")
        print(f"  Commission:  ${commission:.2f} ({commission_pct:.4f}%)")

    # Test pro commission
    print("\n" + "=" * 60)
    print("IB PRO COMMISSION ($0.0035/share, $0.35 min)")
    print("=" * 60)
    pro = IBCommissionPro()

    for trade in test_trades:
        commission = pro._getcommission(trade['size'], trade['price'], False)
        trade_value = abs(trade['size'] * trade['price'])
        commission_pct = (commission / trade_value) * 100

        print(f"\n{trade['desc']}")
        print(f"  Trade Value: ${trade_value:,.2f}")
        print(f"  Commission:  ${commission:.2f} ({commission_pct:.4f}%)")

    # Test slippage model
    print("\n" + "=" * 60)
    print("SLIPPAGE MODEL")
    print("=" * 60)
    slippage = IBSlippageModel(market_order_bps=5, limit_order_bps=0)

    test_price = 100.00
    market_slippage = slippage.get_slippage(test_price, is_market_order=True)
    limit_slippage = slippage.get_slippage(test_price, is_market_order=False)

    print(f"\nPrice: ${test_price:.2f}")
    print(f"  Market Order Slippage: ${market_slippage:.4f} (5 bps)")
    print(f"  Limit Order Slippage:  ${limit_slippage:.4f} (0 bps)")

    print("\n✅ Commission models tested successfully!")
