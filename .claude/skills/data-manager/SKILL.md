---
name: data-manager
description: Download, validate, and report on historical market data from Interactive Brokers using LEAN CLI. Handles data quality checks, gap detection, and incremental updates.
---

# Data Manager Skill

Manages historical market data for backtesting using LEAN and Interactive Brokers.

## Capabilities

1. **Download Data**: Download historical data from Interactive Brokers using LEAN CLI
2. **Validate Quality**: Check for missing dates, gaps, OHLCV consistency, and suspicious data
3. **Generate Reports**: Create data quality reports in JSON or HTML format
4. **Incremental Updates**: Download only new data since last update

## Usage

### Download Historical Data

```bash
lean data download \
  --data-provider-historical "Interactive Brokers" \
  --data-type Trade \
  --resolution Daily \
  --security-type Equity \
  --ticker SPY,AAPL,MSFT \
  --market USA \
  --start 20200101 \
  --end 20241231 \
  --ib-user-name $IB_USERNAME \
  --ib-account $IB_ACCOUNT \
  --ib-password $IB_PASSWORD
```

### Validate Data Quality

Run the validation script to check for data quality issues:

```bash
python scripts/data_quality_check.py --symbols SPY AAPL --report-format json
```

### Quality Checks Performed

- **Missing Dates**: Identifies gaps in daily data
- **Intraday Gaps**: Detects missing bars in intraday data
- **OHLCV Consistency**: Validates Open, High, Low, Close relationships (H ≥ O,C,L and L ≤ O,C,H)
- **Zero Volume**: Flags bars with zero or negative volume
- **Suspicious Prices**: Detects anomalous price movements

### Data Quality Report

```python
# Example report structure
{
  "symbols": {
    "SPY": {
      "total_bars": 1000,
      "missing_dates": 2,
      "gaps": 0,
      "ohlcv_violations": 0,
      "zero_volume_bars": 0,
      "quality_score": 0.998
    }
  },
  "overall_quality": 0.998
}
```

## Configuration

Data manager configuration is in `config/data_config.yaml`:

```yaml
data_source: "Interactive Brokers"
resolution: Daily
security_type: Equity
market: USA
validation:
  check_missing_dates: true
  check_ohlcv_consistency: true
  check_zero_volume: true
  max_gap_days: 5
```

## Scripts

- `scripts/download_data.py`: Download historical data wrapper
- `scripts/data_quality_check.py`: Validate data quality
- `scripts/generate_data_report.py`: Generate quality reports
- `scripts/update_data.py`: Incremental data updates

## Dependencies

- LEAN CLI (installed in venv)
- Interactive Brokers credentials (in `.env`)
- pandas, numpy for data processing
- tables, h5py for HDF5 storage (handled by LEAN)

## Notes

- LEAN handles data storage and caching automatically
- Data is stored in `data/` directory with LEAN's format
- IB credentials must be configured in `.env` file
- Quality validation runs post-download
- Supports both paper and live IB accounts
