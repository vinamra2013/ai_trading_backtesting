# Epic: FastAPI Backtest Backend

### Summary

This epic introduces a dedicated **FastAPI backend service** to manage and orchestrate all backtesting, optimization, and analytics workflows in the quantitative trading research system. The backend will be integrated into the existing **Docker Compose stack** that already runs Streamlit, MLflow, PostgreSQL, and related services. It will serve as the central API layer, enabling both human users (via the Streamlit dashboard) and AI agents to trigger backtests, optimizations, and portfolio analyses seamlessly.

---

## 🧩 Epic Details

**Epic Name:** FastAPI Backtest Backend
**Owner:** Quant Research Infrastructure Team
**Priority:** High
**User Type:** Quant Director / AI Agents / Streamlit UI
**Tech Stack:** FastAPI, PostgreSQL, MLflow, Docker Compose, Pydantic, SQLAlchemy, Backtrader
**Goal:** Build a modular, scalable backend API that exposes backtesting and optimization workflows, integrates with MLflow for experiment tracking, persists results in PostgreSQL, and communicates with the Streamlit dashboard.

---

## 🌐 Context & Motivation

Currently, the quantitative trading platform consists of multiple standalone components:

* **Backtesting engine:** Backtrader scripts managed by Claude Code orchestration.
* **Experiment tracking:** MLflow stores metrics, parameters, and artifacts.
* **Database:** PostgreSQL stores metadata and configurations.
* **Visualization:** Streamlit displays results and dashboards.

However, there is **no unified backend API** that ties these components together. Each module is manually triggered, making automation and integration with AI agents inefficient.
This epic aims to **unify orchestration, persistence, and visualization** through a single backend service that:

* Provides consistent APIs for backtesting and optimization.
* Centralizes data in PostgreSQL for easy querying.
* Enables Streamlit and AI agents to communicate programmatically.
* Supports modular future expansion (live trading, report generation, etc.).

---

## 📚 Developer Stories

### Story 1: Backend Setup & Docker Integration

**As a** developer,
**I want** to set up the FastAPI backend as a Docker service integrated with the existing stack,
**so that** all services can communicate internally and share resources (DB, MLflow).

**Acceptance Criteria:**

* Add a new `fastapi-backend` service in `docker-compose.yml` with dependency links to PostgreSQL and MLflow.
* Configure internal hostname resolution (e.g., `fastapi-backend:8000`).
* Create FastAPI project with modular folder structure:

  ```
  backend/
    ├── main.py
    ├── routers/
    ├── models/
    ├── schemas/
    ├── services/
    ├── utils/
  ```
* Health check endpoint `/health` returns `{status: 'ok'}`.

**Deliverables:**

* Dockerfile for FastAPI backend.
* Updated `docker-compose.yml`.
* Folder scaffolding and initial commit.

---

### Story 2: Database Schema for Backtests

**As a** backend engineer,
**I want** to define PostgreSQL tables to persist backtest and optimization metadata,
**so that** results are queryable, traceable, and linked to MLflow.

**Acceptance Criteria:**

* Create tables:

  * `backtests` (strategy_name, symbols, parameters, metrics, status, mlflow_run_id, timestamps)
  * `optimizations` (strategy_name, parameter_space, objective_metric, best_result_id, timestamps)
  * `analytics_cache` (aggregated metrics for portfolio insights)
* Implement SQLAlchemy models and Alembic migrations.
* Add helper methods for inserting and retrieving records.
* Unit tests confirm schema and data integrity.

**Deliverables:**

* `models/backtest.py`, `models/optimization.py`.
* `alembic/versions` migration scripts.
* Database connectivity utilities.

---

### Story 3: Run New Backtest Endpoint

**As a** user or AI agent,
**I want** to trigger a new backtest with configurable parameters,
**so that** the system can run and record results automatically.

**Acceptance Criteria:**

* Endpoint: `POST /api/backtests/run`
* Accept body:

  ```json
  {
    "strategy": "momentum_strategy",
    "symbols": ["AAPL", "MSFT"],
    "parameters": {"window": 20, "threshold": 0.02},
    "timeframe": "1h"
  }
  ```
* Trigger orchestrator (e.g., Claude Code or Backtrader script) in background.
* Create DB record with `status = 'running'`.
* On completion, update metrics and link MLflow run.
* Return job ID, status, and MLflow run link.

**Deliverables:**

* `routers/backtests.py`
* Background worker service (e.g., asyncio or Celery optional)
* Integration test for job submission and result update.

---

### Story 4: List & Retrieve Backtest Results

**As a** frontend developer,
**I want** to query a list of past backtests and fetch detailed results,
**so that** I can display summaries and charts in Streamlit.

**Acceptance Criteria:**

* `GET /api/backtests` → paginated list (supports filters: strategy, date, status)
* `GET /api/backtests/{id}` → full result including trades, metrics, and MLflow links.
* Include pagination and sorting.
* Streamlit dashboard updates every 10 seconds.

**Deliverables:**

* API endpoints and schemas.
* Query logic with SQLAlchemy ORM.
* Streamlit table view and details modal.

---

### Story 5: Launch Optimization Job

**As a** quant researcher,
**I want** to launch multi-run optimization jobs,
**so that** I can identify optimal parameters for given strategies.

**Acceptance Criteria:**

* Endpoint: `POST /api/optimization/run`
* Accept optimization configuration (parameter grid, objective metric, symbols, etc.).
* Trigger multiple backtests asynchronously.
* Log all runs in MLflow as a grouped experiment.
* Store summary in PostgreSQL `optimizations`.

**Deliverables:**

* `routers/optimization.py`
* Parallel orchestration logic.
* Streamlit UI component for optimization submission and result tracking.

---

### Story 6: MLflow Data Access Layer

**As a** backend engineer,
**I want** to access MLflow experiment and run data programmatically,
**so that** the frontend can render metrics and comparisons.

**Acceptance Criteria:**

* `GET /api/mlflow/experiments` → list all experiments.
* `GET /api/mlflow/runs/{experiment_id}` → retrieve runs and metrics.
* Return parameters, metrics, and artifact URLs.
* Optional caching with Redis for performance.

**Deliverables:**

* `services/mlflow_client.py`
* API route handlers and schema models.
* Integration tests with MLflow backend.

---

### Story 7: Portfolio Ranking & Analytics Endpoint

**As a** quant director,
**I want** to view aggregated portfolio and strategy statistics,
**so that** I can analyze performance and trends.

**Acceptance Criteria:**

* Endpoint: `GET /api/analytics/portfolio`
* Compute metrics: total return, Sharpe ratio, drawdown, win rate, volatility.
* Rank strategies by performance.
* Optional grouping by symbol or timeframe.

**Deliverables:**

* `services/analytics.py`
* Streamlit visualization (bar charts, tables, heatmaps).
* Cached responses for quick loading.

---

### Story 8: Streamlit Frontend Integration

**As a** user,
**I want** to launch, monitor, and visualize all experiments via Streamlit,
**so that** I have one unified interface for research management.

**Acceptance Criteria:**

* Connect Streamlit to FastAPI endpoints for launching and listing jobs.
* Add tabs for Backtests, Optimizations, and Analytics.
* Use polling for updates (no WebSocket).
* Include filters, metric charts, and strategy comparison tables.

**Deliverables:**

* Updated Streamlit components.
* API integration utilities.
* UI/UX test to ensure end-to-end flow.

---

### Story 9: AI Agent Integration & Network Access

**As a** system,
**I want** AI agents to call backend endpoints internally (Docker) or externally (localhost),
**so that** automated research and iterative workflows can run autonomously.

**Acceptance Criteria:**

* Expose FastAPI on both Docker internal network and localhost.
* Enable CORS for external calls.
* No authentication required for local access.
* Confirm agent connectivity via REST calls.

**Deliverables:**

* Docker networking setup.
* CORS configuration.
* Validation test for agent-initiated runs.

---

## ✅ Completion Criteria

* All endpoints available in `/docs` (Swagger UI).
* PostgreSQL schema finalized and populated with data.
* MLflow integration validated.
* Streamlit dashboard fully functional with polling updates.
* AI agents successfully able to trigger and monitor backtests.

---

**End of Epic: FastAPI Backtest Backend**
