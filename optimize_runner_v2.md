# V2 Parallel Optimization System - Implementation Prompt

## 🎯 **MISSION BRIEF**
You are tasked with implementing the **V2 Parallel Optimization System** for the AI Trading Backtesting Platform. This replaces the problematic bulk LEAN optimization with a robust parallel system that runs individual backtests with proper resource management and real-time monitoring.

## 📖 **REQUIRED READING**
**MANDATORY**: Read `V2_OPTIMIZATION_STORY.md` completely before starting any work. This file contains:
- Complete technical specifications
- Database schema details
- API endpoint specifications
- Implementation phases and timelines
- Testing and deployment strategies

## 🎯 **IMPLEMENTATION OBJECTIVES**

### **Primary Goal**
Build a system where researchers can run strategy optimizations with 100+ parameter combinations without system lockup, getting reliable results with real-time progress monitoring.

### **Key Success Criteria**
- ✅ CPU usage stays <80% during optimization
- ✅ No hanging processes (HTTP timeouts vs infinite waits)
- ✅ Real-time progress monitoring via API
- ✅ Individual job failure isolation
- ✅ Results automatically aggregated
- ✅ Proper Docker container cleanup

## 🏗️ **IMPLEMENTATION PHASES**

### **Phase 1: Database Foundation (Day 1)**
```bash
# 1. Start PostgreSQL
docker compose up -d postgres

# 2. Create V2 schema
docker exec -i mlflow-postgres psql -U mlflow -d trading < scripts/db_schema_v2.sql

# 3. Verify setup
./scripts/reset_db.sh status
./scripts/reset_db.sh leaderboard
```

**Deliverables:**
- ✅ Single "trading" database with all V2 tables
- ✅ All 15 strategies populated with correct Lean paths
- ✅ Success criteria configured
- ✅ Views and indexes created

### **Phase 2: FastAPI Backend (Days 2-4)**

**Project Structure to Create:**
```
backend/
├── main.py                 # FastAPI app with CORS
├── routers/
│   ├── __init__.py
│   ├── optimization.py     # /api/optimization/* endpoints
│   └── backtests.py        # /api/backtests/* endpoints
├── services/
│   ├── __init__.py
│   ├── optimization_service.py  # Parameter generation & job management
│   └── backtest_service.py      # Individual LEAN backtest execution
├── models/
│   ├── __init__.py
│   └── database.py         # SQLAlchemy models
└── schemas/
    ├── __init__.py
    ├── optimization.py     # Pydantic models
    └── backtest.py
```

**Key Components to Implement:**

#### **1. Database Models** (`backend/models/database.py`)
- `BacktestJob` - Individual job tracking
- `OptimizationBatch` - Batch management
- `BacktestResult` - Results with JSON metrics
- `SuccessCriteria` - Validation rules

#### **2. Core Services**

**OptimizationService** (`backend/services/optimization_service.py`):
```python
def generate_parameter_combinations(config_path: str) -> List[Dict[str, Any]]
def create_optimization_batch(config_path: str, combinations: List) -> str
def submit_backtest_jobs(batch_id: str, combinations: List, config: Dict, max_concurrent: int) -> List[str]
```

**BacktestService** (`backend/services/backtest_service.py`):
```python
def submit_backtest(strategy: str, lean_project: str, parameters: Dict, symbols: List) -> Tuple[str, str]
def build_lean_command(lean_project: str, parameters: Dict, symbols: List) -> List[str]
def run_lean_container(cmd: List[str], job_id: str) -> Container
```

#### **3. API Endpoints**

**POST /api/optimization/run-parallel**
- Generate parameter combinations from config
- Create batch record
- Submit jobs with concurrency control
- Return batch_id for monitoring

**GET /api/optimization/batches/{batch_id}**
- Return real-time progress
- Include current best results
- Estimate completion time

**GET /api/optimization/batches/{batch_id}/results**
- Aggregate final results
- Apply success criteria filtering
- Return parameter analysis

### **Phase 3: CLI Client (Days 5-6)**

**File**: `scripts/optimize_runner_v2.py`

**Features:**
- Parse optimization config files
- Submit jobs to FastAPI backend
- Monitor progress with polling
- Display results in real-time
- Handle errors gracefully

**Usage Examples:**
```bash
# Run optimization
python scripts/optimize_runner_v2.py --config configs/optimizations/STR-001_rsi_etf_lowfreq.yaml

# Custom concurrency
python scripts/optimize_runner_v2.py --config configs/optimizations/STR-001_rsi_etf_lowfreq.yaml --max-concurrent 2

# Monitor existing batch
python scripts/optimize_runner_v2.py --monitor opt_20241112_143052_abc123
```

### **Phase 4: Docker & Infrastructure (Day 7)**

**Update `docker-compose.yml`:**
```yaml
# Ensure single database
postgres:
  environment:
    POSTGRES_DB: trading  # Not mlflow/backend/trading confusion

# Add FastAPI backend service
fastapi-backend:
  build:
    context: .
    dockerfile: Dockerfile.backend
  ports:
    - "8230:8230"
  environment:
    - DATABASE_URL=postgresql://mlflow:mlflow_secure_password@postgres:5432/trading
```

**Resource Limits:**
- Container CPU limit: 1.0 (1 core per job)
- Memory limit: 2GB per container
- Concurrent jobs: 4 maximum

### **Phase 5: Testing & Validation (Days 8-9)**

#### **Unit Tests**
- Parameter combination generation
- API request/response validation
- Database model operations
- Docker command construction

#### **Integration Tests**
- Full optimization workflow (10-20 combinations)
- API endpoint functionality
- Database persistence
- Docker container lifecycle

#### **Performance Tests**
- Resource usage monitoring
- Concurrent job limits testing
- Database query performance
- API response times

#### **Manual Testing Checklist**
- [ ] Submit small optimization (10 combinations)
- [ ] Monitor progress via CLI
- [ ] Check API endpoints manually
- [ ] Verify database records
- [ ] Test error handling
- [ ] Validate results aggregation

## 🧪 **TESTING STRATEGY**

### **Test Data**
Create `configs/optimizations/test_config.yaml` with small parameter space:
```yaml
strategy:
  name: "RSI_MeanReversion_ETF"
  lean_project_path: "STR-001_RSI_MeanReversion_ETF"

parameters:
  rsi_period:
    start: 14
    end: 16
    step: 1
  entry_threshold:
    start: 25
    end: 30
    step: 5
```

### **Success Metrics**
- **Performance**: CPU <80%, Memory <8GB, Completion <30 minutes for test
- **Reliability**: >95% job success rate, proper error handling
- **Monitoring**: Real-time status always available
- **Data Quality**: 100% results match LEAN output

## 🚀 **DEPLOYMENT CHECKLIST**

### **Pre-Deployment**
- [ ] All unit tests passing
- [ ] Integration tests successful
- [ ] Performance benchmarks met
- [ ] Manual testing completed

### **Deployment Steps**
```bash
# 1. Update docker-compose.yml
docker compose down
docker compose up -d --build

# 2. Verify services
curl http://localhost:8230/health
docker compose ps

# 3. Test full workflow
python scripts/optimize_runner_v2.py --config configs/optimizations/test_config.yaml
```

### **Post-Deployment**
- [ ] Run production test with 50+ combinations
- [ ] Monitor resource usage
- [ ] Validate results accuracy
- [ ] Update documentation

## 🔧 **DEVELOPMENT ENVIRONMENT**

### **Required Tools**
- Python 3.12+
- Docker & Docker Compose
- PostgreSQL client
- Git

### **Development Workflow**
1. **Read the story** - Understand all requirements
2. **Start with database** - Get schema working first
3. **Build incrementally** - API → Services → CLI
4. **Test continuously** - Don't wait until the end
5. **Document as you go** - Update README and API docs

### **Code Standards**
- **Type hints**: Mandatory for all functions
- **Error handling**: Comprehensive try/catch blocks
- **Logging**: Structured logging throughout
- **Documentation**: Docstrings for all public functions
- **Testing**: Unit tests for all components

## 🎯 **DELIVERABLES**

### **Code Deliverables**
- ✅ Complete FastAPI backend (`backend/` directory)
- ✅ CLI client (`scripts/optimize_runner_v2.py`)
- ✅ Updated Docker configuration
- ✅ Database schema and migrations
- ✅ Comprehensive test suite

### **Documentation Deliverables**
- ✅ API documentation (OpenAPI/Swagger)
- ✅ CLI usage documentation
- ✅ Deployment guide
- ✅ Troubleshooting guide

### **Quality Deliverables**
- ✅ >80% test coverage
- ✅ Performance benchmarks met
- ✅ Security review passed
- ✅ Production deployment successful

## 🚨 **CRITICAL REQUIREMENTS**

### **Must-Have Features**
- **No hanging processes** - HTTP timeouts, not infinite waits
- **Resource control** - CPU/memory limits per container
- **Real-time monitoring** - Live progress updates
- **Error isolation** - Individual job failures don't affect others
- **Proper cleanup** - Docker containers auto-remove

### **Non-Negotiable Quality Standards**
- **Zero data loss** - All results must be captured
- **Reliable execution** - >95% success rate
- **Performance** - Stay within resource limits
- **Monitoring** - Always know what's happening

## 📞 **COMMUNICATION**

### **Daily Standups**
- Progress updates
- Blocker identification
- Next steps planning

### **Code Reviews**
- All PRs require review
- Focus on error handling and performance
- Test coverage requirements

### **Success Celebration**
When the first full optimization runs successfully with real-time monitoring and proper resource usage, we've achieved the mission! 🎉

---

## **START HERE**
1. **Read `V2_OPTIMIZATION_STORY.md`** completely
2. **Set up the database** with the corrected schema
3. **Begin with Phase 1** - Database foundation
4. **Build incrementally** - Don't try to do everything at once

**Remember**: This system must solve the core problems of hanging processes and resource exhaustion. Every design decision should be evaluated against these requirements.

**Good luck!** 🚀</content>
<parameter name="filePath">V2_IMPLEMENTATION_PROMPT.md