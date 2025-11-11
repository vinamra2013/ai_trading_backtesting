-- QuantConnect Backtesting Framework - PostgreSQL Schema
-- Run: psql -U postgres -d trading -f scripts/db_schema.sql

-- Strategy definitions (master list of all strategies)
CREATE TABLE IF NOT EXISTS strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL,  -- mean_reversion, momentum, volatility, futures, hybrid, event_based
    asset_class VARCHAR(50) NOT NULL,  -- etf, equity, futures, forex, crypto
    lean_project_path VARCHAR(255) NOT NULL,

    -- Strategy metadata
    description TEXT,
    hypothesis TEXT,
    expected_min_trades INT DEFAULT 100,
    expected_min_sharpe DECIMAL(5, 2) DEFAULT 1.0,
    expected_max_drawdown DECIMAL(5, 4) DEFAULT 0.15,

    -- Status tracking
    status VARCHAR(20) NOT NULL DEFAULT 'planned',  -- planned, testing, rejected, passed, deployed
    priority INT DEFAULT 0,  -- Higher = more important

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Optimization runs (one per optimization execution)
CREATE TABLE IF NOT EXISTS optimization_runs (
    id SERIAL PRIMARY KEY,
    strategy_id INT REFERENCES strategies(id) ON DELETE CASCADE,

    -- Configuration
    config_file VARCHAR(255),
    optimization_type VARCHAR(50),  -- grid_search, euler_search, walk_forward
    target_metric VARCHAR(50),  -- sharpe_ratio, total_return, calmar_ratio
    target_direction VARCHAR(10),  -- max, min

    -- Execution tracking
    total_combinations INT,
    completed_combinations INT DEFAULT 0,
    passed_combinations INT DEFAULT 0,

    -- Timestamps
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,

    -- Status
    status VARCHAR(20) DEFAULT 'running',  -- running, completed, failed, cancelled
    error_message TEXT
);

-- Individual backtest results (one row per parameter combination tested)
CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,
    optimization_run_id INT REFERENCES optimization_runs(id) ON DELETE CASCADE,
    strategy_id INT REFERENCES strategies(id) ON DELETE CASCADE,

    -- Parameters (JSONB for flexibility - any number of parameters)
    parameters JSONB NOT NULL,

    -- Performance metrics
    sharpe_ratio DECIMAL(10, 4),
    sortino_ratio DECIMAL(10, 4),
    calmar_ratio DECIMAL(10, 4),

    -- Returns
    total_return DECIMAL(10, 4),
    annual_return DECIMAL(10, 4),
    compounding_annual_return DECIMAL(10, 4),

    -- Risk metrics
    max_drawdown DECIMAL(10, 4),
    drawdown_recovery_days INT,
    annual_std_dev DECIMAL(10, 4),
    annual_variance DECIMAL(10, 4),

    -- Trading metrics
    total_trades INT,
    win_rate DECIMAL(5, 4),
    loss_rate DECIMAL(5, 4),
    avg_win DECIMAL(10, 4),
    avg_loss DECIMAL(10, 4),
    profit_loss_ratio DECIMAL(10, 4),

    -- Portfolio metrics
    total_fees DECIMAL(10, 2),
    net_profit DECIMAL(10, 2),
    portfolio_turnover DECIMAL(10, 4),
    estimated_capacity DECIMAL(15, 2),

    -- Greek metrics
    alpha DECIMAL(10, 4),
    beta DECIMAL(10, 4),

    -- Pass/Fail evaluation
    meets_criteria BOOLEAN DEFAULT false,
    rejection_reasons TEXT[],

    -- QuantConnect metadata
    qc_backtest_url VARCHAR(500),
    backtest_id VARCHAR(100) UNIQUE,
    backtest_name VARCHAR(200),

    -- Timestamps
    completed_at TIMESTAMP DEFAULT NOW()
);

-- Strategy leaderboard view (best performing strategies)
CREATE OR REPLACE VIEW strategy_leaderboard AS
SELECT
    ROW_NUMBER() OVER (ORDER BY b.sharpe_ratio DESC) as rank,
    s.name as strategy_name,
    s.category,
    s.asset_class,
    b.parameters,
    b.sharpe_ratio,
    b.total_return,
    b.annual_return,
    b.max_drawdown,
    b.total_trades,
    b.win_rate,
    b.avg_win,
    b.avg_loss,
    b.total_fees,
    b.qc_backtest_url,
    b.completed_at
FROM backtest_results b
JOIN strategies s ON b.strategy_id = s.id
WHERE b.meets_criteria = true
ORDER BY b.sharpe_ratio DESC;

-- Parameter performance analysis view
CREATE OR REPLACE VIEW parameter_performance AS
SELECT
    s.name as strategy_name,
    jsonb_object_keys(b.parameters) as parameter_name,
    b.parameters->>jsonb_object_keys(b.parameters) as parameter_value,
    AVG(b.sharpe_ratio) as avg_sharpe,
    AVG(b.total_return) as avg_return,
    AVG(b.max_drawdown) as avg_drawdown,
    AVG(b.win_rate) as avg_win_rate,
    COUNT(*) as test_count
FROM backtest_results b
JOIN strategies s ON b.strategy_id = s.id
GROUP BY s.name, parameter_name, parameter_value
ORDER BY avg_sharpe DESC;

-- Fee analysis view
CREATE OR REPLACE VIEW fee_analysis AS
SELECT
    s.name as strategy_name,
    AVG(b.total_fees) as avg_fees,
    AVG(b.total_fees / 1000.0 * 100) as avg_fee_pct_of_capital,
    AVG(b.total_trades) as avg_trades,
    AVG(b.total_fees / NULLIF(b.total_trades, 0)) as avg_fee_per_trade,
    COUNT(*) as backtest_count
FROM backtest_results b
JOIN strategies s ON b.strategy_id = s.id
GROUP BY s.name
ORDER BY avg_fee_pct_of_capital DESC;

-- Daily summary view
CREATE OR REPLACE VIEW daily_summary AS
SELECT
    DATE(completed_at) as date,
    COUNT(*) as total_backtests,
    SUM(CASE WHEN meets_criteria THEN 1 ELSE 0 END) as passed,
    MAX(sharpe_ratio) as best_sharpe,
    AVG(sharpe_ratio) as avg_sharpe,
    COUNT(DISTINCT strategy_id) as strategies_tested
FROM backtest_results
GROUP BY DATE(completed_at)
ORDER BY date DESC;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_backtest_strategy ON backtest_results(strategy_id);
CREATE INDEX IF NOT EXISTS idx_backtest_sharpe ON backtest_results(sharpe_ratio DESC);
CREATE INDEX IF NOT EXISTS idx_backtest_criteria ON backtest_results(meets_criteria);
CREATE INDEX IF NOT EXISTS idx_backtest_date ON backtest_results(completed_at DESC);
CREATE INDEX IF NOT EXISTS idx_opt_run_strategy ON optimization_runs(strategy_id);
CREATE INDEX IF NOT EXISTS idx_parameters_gin ON backtest_results USING gin(parameters);

-- Function to update strategy status based on results
CREATE OR REPLACE FUNCTION update_strategy_status()
RETURNS TRIGGER AS $$
BEGIN
    -- If any backtest passes criteria, mark strategy as passed
    IF NEW.meets_criteria = true THEN
        UPDATE strategies
        SET status = 'passed', updated_at = NOW()
        WHERE id = NEW.strategy_id AND status != 'deployed';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update strategy status
CREATE TRIGGER trigger_update_strategy_status
AFTER INSERT OR UPDATE ON backtest_results
FOR EACH ROW
EXECUTE FUNCTION update_strategy_status();

-- Sample data for testing
INSERT INTO strategies (name, category, asset_class, lean_project_path, description, status, priority)
VALUES
    ('RSI_MeanReversion_ETF', 'mean_reversion', 'etf', 'RSI_MeanReversion_ETF', 'RSI-based mean reversion on liquid ETFs', 'testing', 10),
    ('BollingerBand_ETF', 'mean_reversion', 'etf', 'BollingerBand_MeanReversion_ETFs', 'Bollinger Band mean reversion strategy', 'testing', 9),
    ('Momentum_Breakout', 'momentum', 'equity', 'Momentum_Breakout', 'Price breakout with volume confirmation', 'planned', 8)
ON CONFLICT (name) DO NOTHING;

-- Helper queries for common operations
COMMENT ON TABLE strategies IS 'Master list of all trading strategies';
COMMENT ON TABLE optimization_runs IS 'Tracks each optimization execution';
COMMENT ON TABLE backtest_results IS 'Individual backtest results for each parameter combination';
COMMENT ON VIEW strategy_leaderboard IS 'Top performing strategies ranked by Sharpe ratio';
COMMENT ON VIEW parameter_performance IS 'Analysis of how different parameter values affect performance';
COMMENT ON VIEW fee_analysis IS 'Fee impact analysis across strategies';
COMMENT ON VIEW daily_summary IS 'Daily backtesting activity summary';
