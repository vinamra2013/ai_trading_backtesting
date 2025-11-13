-- QuantConnect Backtesting Framework - V2 Schema
-- Single "trading" database for all components
-- Supports individual backtest jobs and batch optimization

-- Strategy definitions (master list)
CREATE TABLE IF NOT EXISTS strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL,           -- mean_reversion, momentum, volatility, futures, hybrid, event_based
    asset_class VARCHAR(50) NOT NULL,        -- etf, equity, futures, forex, crypto
    lean_project_path VARCHAR(255) NOT NULL, -- Must match actual directory names (STR-001_*, etc.)
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'planned', -- planned, testing, rejected, passed, deployed
    priority INT DEFAULT 0,                  -- Higher = more important
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Individual backtest jobs (V2 core - replaces bulk optimization)
CREATE TABLE IF NOT EXISTS backtest_jobs (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(100),                   -- Groups related jobs (opt_20241112_143052_abc123)
    strategy_name VARCHAR(255) NOT NULL,
    lean_project_path VARCHAR(255) NOT NULL,
    parameters JSONB NOT NULL,               -- Individual parameter set {"rsi_period": 14, "entry_threshold": 30}
    symbols JSONB DEFAULT '["SPY"]'::jsonb,  -- List of symbols as JSON array
    status VARCHAR(50) DEFAULT 'queued',     -- queued, running, completed, failed
    container_id VARCHAR(100),               -- Docker container tracking
    result_path VARCHAR(500),                -- LEAN output directory path
    error_message TEXT,                      -- Failure details
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Optimization batches (V2 batch management)
CREATE TABLE IF NOT EXISTS optimization_batches (
    id VARCHAR(100) PRIMARY KEY,            -- Unique batch ID (opt_20241112_143052_abc123)
    strategy_name VARCHAR(255) NOT NULL,
    config_file VARCHAR(500),                -- Source config file path
    total_jobs INT NOT NULL,                 -- Total number of jobs in batch
    completed_jobs INT DEFAULT 0,            -- Jobs completed so far
    status VARCHAR(50) DEFAULT 'running',    -- running, completed, failed
    best_result_id INT REFERENCES backtest_jobs(id), -- Best performing job
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Backtest results (V2 extended with JSON metrics)
CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,
    job_id INT REFERENCES backtest_jobs(id) ON DELETE CASCADE,
    batch_id VARCHAR(100) REFERENCES optimization_batches(id),
    parameters JSONB,                        -- Duplicate for querying (denormalized)
    metrics JSONB NOT NULL,                  -- All metrics as JSON {"sharpe_ratio": 1.45, "total_return": 0.234, ...}
    meets_criteria BOOLEAN DEFAULT false,    -- Whether result passes success criteria
    rejection_reasons JSON,                  -- Array of reasons as JSON ["insufficient_trades", "high_drawdown"]
    qc_backtest_id VARCHAR(100) UNIQUE,      -- QuantConnect backtest ID
    created_at TIMESTAMP DEFAULT NOW()
);

-- Success criteria (V2 configuration)
CREATE TABLE IF NOT EXISTS success_criteria (
    id SERIAL PRIMARY KEY,
    strategy_name VARCHAR(255) NOT NULL,     -- Links to strategies.name
    min_trades INT DEFAULT 100,              -- Minimum trades for statistical significance
    min_sharpe DECIMAL(5,2) DEFAULT 1.0,     -- Minimum Sharpe ratio
    max_drawdown DECIMAL(5,4) DEFAULT 0.15,  -- Maximum drawdown (15%)
    min_win_rate DECIMAL(5,4) DEFAULT 0.45,  -- Minimum win rate (45%)
    max_fee_pct DECIMAL(5,4) DEFAULT 0.30,   -- Maximum fees as % of capital (30%)
    min_avg_win DECIMAL(10,4) DEFAULT 0.01,  -- Minimum average winning trade (1%)
    max_fee_per_trade DECIMAL(10,4),         -- Maximum fee per trade
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(strategy_name)                    -- One criteria per strategy
);

-- Legacy tables (keep for backward compatibility)
CREATE TABLE IF NOT EXISTS optimization_runs (
    id SERIAL PRIMARY KEY,
    strategy_id INT REFERENCES strategies(id) ON DELETE CASCADE,
    config_file VARCHAR(255),
    optimization_type VARCHAR(50),
    target_metric VARCHAR(50),
    target_direction VARCHAR(10),
    total_combinations INT,
    completed_combinations INT DEFAULT 0,
    passed_combinations INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'running',
    error_message TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS backtest_results_legacy (
    id SERIAL PRIMARY KEY,
    optimization_run_id INT REFERENCES optimization_runs(id) ON DELETE CASCADE,
    strategy_id INT REFERENCES strategies(id) ON DELETE CASCADE,
    parameters JSONB NOT NULL,
    sharpe_ratio DECIMAL(10, 4),
    sortino_ratio DECIMAL(10, 4),
    total_return DECIMAL(10, 4),
    annual_return DECIMAL(10, 4),
    compounding_annual_return DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),
    annual_std_dev DECIMAL(10, 4),
    annual_variance DECIMAL(10, 4),
    total_trades INT,
    win_rate DECIMAL(5, 4),
    loss_rate DECIMAL(5, 4),
    avg_win DECIMAL(10, 4),
    avg_loss DECIMAL(10, 4),
    profit_loss_ratio DECIMAL(10, 4),
    total_fees DECIMAL(10, 2),
    net_profit DECIMAL(10, 2),
    portfolio_turnover DECIMAL(10, 4),
    estimated_capacity DECIMAL(15, 2),
    alpha DECIMAL(10, 4),
    beta DECIMAL(10, 4),
    meets_criteria BOOLEAN DEFAULT false,
    rejection_reasons TEXT[],
    qc_backtest_url VARCHAR(500),
    backtest_id VARCHAR(100) UNIQUE,
    backtest_name VARCHAR(200),
    completed_at TIMESTAMP DEFAULT NOW()
);

-- Views for analytics (updated for V2)
CREATE OR REPLACE VIEW strategy_leaderboard AS
SELECT
    ROW_NUMBER() OVER (ORDER BY (br.metrics->>'sharpe_ratio')::float DESC) as rank,
    s.name as strategy_name,
    s.category,
    s.asset_class,
    br.parameters,
    (br.metrics->>'sharpe_ratio')::float as sharpe_ratio,
    (br.metrics->>'total_return')::float as total_return,
    (br.metrics->>'annual_return')::float as annual_return,
    (br.metrics->>'max_drawdown')::float as max_drawdown,
    (br.metrics->>'total_trades')::int as total_trades,
    (br.metrics->>'win_rate')::float as win_rate,
    (br.metrics->>'avg_win')::float as avg_win,
    (br.metrics->>'avg_loss')::float as avg_loss,
    (br.metrics->>'total_fees')::float as total_fees,
    br.created_at
FROM backtest_results br
JOIN backtest_jobs bj ON br.job_id = bj.id
JOIN strategies s ON bj.strategy_name = s.name
WHERE br.meets_criteria = true
ORDER BY (br.metrics->>'sharpe_ratio')::float DESC;

-- Parameter performance analysis view
CREATE OR REPLACE VIEW parameter_performance AS
SELECT
    s.name as strategy_name,
    jsonb_object_keys(br.parameters) as parameter_name,
    br.parameters->>jsonb_object_keys(br.parameters) as parameter_value,
    AVG((br.metrics->>'sharpe_ratio')::float) as avg_sharpe,
    AVG((br.metrics->>'total_return')::float) as avg_return,
    AVG((br.metrics->>'max_drawdown')::float) as avg_drawdown,
    AVG((br.metrics->>'win_rate')::float) as avg_win_rate,
    COUNT(*) as test_count
FROM backtest_results br
JOIN backtest_jobs bj ON br.job_id = bj.id
JOIN strategies s ON bj.strategy_name = s.name
GROUP BY s.name, parameter_name, parameter_value
ORDER BY avg_sharpe DESC;

-- Fee analysis view
CREATE OR REPLACE VIEW fee_analysis AS
SELECT
    s.name as strategy_name,
    AVG((br.metrics->>'total_fees')::float) as avg_fees,
    AVG((br.metrics->>'total_fees')::float / 1000.0 * 100) as avg_fee_pct_of_capital,
    AVG((br.metrics->>'total_trades')::int) as avg_trades,
    AVG((br.metrics->>'total_fees')::float / NULLIF((br.metrics->>'total_trades')::int, 0)) as avg_fee_per_trade,
    COUNT(*) as backtest_count
FROM backtest_results br
JOIN backtest_jobs bj ON br.job_id = bj.id
JOIN strategies s ON bj.strategy_name = s.name
GROUP BY s.name
ORDER BY avg_fee_pct_of_capital DESC;

-- Daily summary view
CREATE OR REPLACE VIEW daily_summary AS
SELECT
    DATE(br.created_at) as date,
    COUNT(*) as total_backtests,
    SUM(CASE WHEN br.meets_criteria THEN 1 ELSE 0 END) as passed,
    MAX((br.metrics->>'sharpe_ratio')::float) as best_sharpe,
    AVG((br.metrics->>'sharpe_ratio')::float) as avg_sharpe,
    COUNT(DISTINCT bj.strategy_name) as strategies_tested
FROM backtest_results br
JOIN backtest_jobs bj ON br.job_id = bj.id
GROUP BY DATE(br.created_at)
ORDER BY date DESC;

-- Indexes for V2 performance
CREATE INDEX IF NOT EXISTS idx_jobs_batch ON backtest_jobs(batch_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON backtest_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_strategy ON backtest_jobs(strategy_name);
CREATE INDEX IF NOT EXISTS idx_batches_status ON optimization_batches(status);
CREATE INDEX IF NOT EXISTS idx_results_batch ON backtest_results(batch_id);
CREATE INDEX IF NOT EXISTS idx_results_job ON backtest_results(job_id);
CREATE INDEX IF NOT EXISTS idx_results_criteria ON backtest_results(meets_criteria);
CREATE INDEX IF NOT EXISTS idx_parameters_gin ON backtest_results USING gin(parameters);
CREATE INDEX IF NOT EXISTS idx_metrics_gin ON backtest_results USING gin(metrics);

-- Sample data with CORRECT Lean project paths (matching actual directories)
INSERT INTO strategies (name, category, asset_class, lean_project_path, description, status, priority)
VALUES
    ('RSI_MeanReversion_ETF', 'mean_reversion', 'etf', 'STR-001_RSI_MeanReversion_ETF',
     'RSI-based mean reversion on SPY with relaxed thresholds', 'testing', 10),

    ('BollingerBand_ETF', 'mean_reversion', 'etf', 'STR-002_BollingerBand_ETF',
     'Bollinger Band mean reversion with wider bands for low frequency', 'testing', 9),

    ('SMA_Crossover_ETF', 'momentum', 'etf', 'STR-003_SMA_Crossover_ETF',
     'SMA crossover strategy for ETFs', 'planned', 8),

    ('Breakout_Momentum_Equity', 'momentum', 'equity', 'STR-004_Breakout_Momentum_Equity',
     'Price breakout with volume confirmation', 'planned', 7),

    ('ATR_Breakout_ETF', 'breakout', 'etf', 'STR-005_ATR_Breakout_ETF',
     'ATR-based breakout strategy', 'planned', 6),

    ('VIX_Market_Timing', 'timing', 'index', 'STR-006_VIX_Market_Timing',
     'VIX-based market timing', 'planned', 5),

    ('RSI_MACD_Combo_ETF', 'combo', 'etf', 'STR-008_RSI_MACD_Combo_ETF',
     'RSI + MACD combination strategy', 'planned', 4),

    ('MeanReversion_TrendFilter_ETF', 'mean_reversion', 'etf', 'STR-009_MeanReversion_TrendFilter_ETF',
     'Mean reversion with trend filtering', 'planned', 3),

    ('Earnings_Momentum', 'momentum', 'equity', 'STR-010_Earnings_Momentum',
     'Earnings-based momentum strategy', 'planned', 2),

    ('Statistical_Pairs_Trading', 'pairs', 'equity', 'STR-011_Statistical_Pairs_Trading',
     'Statistical pairs trading', 'planned', 1),

    ('Relative_Strength_Leaders', 'momentum', 'equity', 'STR-012_Relative_Strength_Leaders',
     'Relative strength momentum', 'planned', 1),

    ('Gap_Trading_Overnight', 'gap', 'equity', 'STR-013_Gap_Trading_Overnight',
     'Overnight gap trading', 'planned', 1),

    ('Donchian_Breakout_ETF', 'breakout', 'etf', 'STR-014_Donchian_Breakout_ETF',
     'Donchian channel breakout', 'planned', 1),

    ('Quality_Factor_Momentum', 'factor', 'equity', 'STR-015_Quality_Factor_Momentum',
     'Quality factor momentum', 'planned', 1)
ON CONFLICT (name) DO NOTHING;

-- Success criteria for each strategy
INSERT INTO success_criteria (strategy_name, min_trades, min_sharpe, max_drawdown, min_win_rate, max_fee_pct)
VALUES
    ('RSI_MeanReversion_ETF', 100, 1.0, 0.15, 0.45, 0.30),
    ('BollingerBand_ETF', 50, 0.8, 0.20, 0.50, 0.25),
    ('SMA_Crossover_ETF', 100, 1.0, 0.15, 0.45, 0.30),
    ('Breakout_Momentum_Equity', 50, 0.8, 0.20, 0.50, 0.25),
    ('ATR_Breakout_ETF', 50, 0.8, 0.20, 0.50, 0.25)
ON CONFLICT (strategy_name) DO NOTHING;

-- Comments for documentation
COMMENT ON TABLE strategies IS 'Master list of all trading strategies';
COMMENT ON TABLE backtest_jobs IS 'Individual backtest jobs with container tracking (V2)';
COMMENT ON TABLE optimization_batches IS 'Batch management for grouped optimizations (V2)';
COMMENT ON TABLE backtest_results IS 'Extended results with JSON metrics (V2)';
COMMENT ON TABLE success_criteria IS 'Success criteria for each strategy (V2)';
COMMENT ON TABLE optimization_runs IS 'Legacy bulk optimization tracking';
COMMENT ON TABLE backtest_results_legacy IS 'Legacy results table for backward compatibility';
COMMENT ON VIEW strategy_leaderboard IS 'Top performing strategies ranked by Sharpe ratio (V2 compatible)';
COMMENT ON VIEW parameter_performance IS 'Analysis of how different parameter values affect performance (V2)';
COMMENT ON VIEW fee_analysis IS 'Fee impact analysis across strategies (V2)';
COMMENT ON VIEW daily_summary IS 'Daily backtesting activity summary (V2)';