# Technology Stack Decision
## Yield Intelligence Platform
### Version 1.0 | April 2026

---

## Architecture Overview

```
┌─────────────────────────────────┐
│         React Frontend          │  Port 3000
│   (Tailwind, Recharts, Lucide)  │
├─────────────────────────────────┤
│         FastAPI Backend         │  Port 8000
│    (Python 3.12, Uvicorn)       │
├─────────────────────────────────┤
│      Engine Layer (Python)      │
│  NumPy, SciPy, Pandas, PyMC    │
│  Prophet, Statsmodels           │
├─────────────────────────────────┤
│     Data Layer (CSV/Excel)      │
│   Openpyxl, Pandas, FileIO     │
└─────────────────────────────────┘
```

## Frontend

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Framework | React 18 (JSX) | Component model, hooks, ecosystem |
| Styling | Tailwind CSS (CDN) | Utility-first, no build step for prototype |
| Charts | Recharts | React-native, responsive, composable |
| Icons | Lucide React | Lightweight, consistent icon set |
| State | React hooks (useState, useMemo, useCallback) | Sufficient for single-page app |
| Build | Vite (recommended for production) | Fast HMR, ESBuild |

## Backend

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Runtime | Python 3.12 | Ecosystem for data science / ML |
| API | FastAPI 0.100+ | Async, auto-docs, Pydantic validation |
| Server | Uvicorn | ASGI, production-ready |
| Data Processing | Pandas 2.0+ | DataFrame operations, CSV/Excel I/O |
| Numerical | NumPy 1.24+ | Array operations, linear algebra |
| Optimization | SciPy 1.10+ | SLSQP solver, curve fitting |
| Bayesian | PyMC 5.0+ | MCMC sampling, Bayesian inference |
| Forecasting | Prophet 1.1+ | Seasonal decomposition, trend |
| Time-Series | Statsmodels 0.14+ | ARIMA fallback |
| Excel | Openpyxl 3.1+ | XLSX read/write |
| Inference | ArviZ 0.15+ | Posterior analysis for PyMC |

## Data Layer

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Input Format | CSV (primary), XLSX (secondary) | Universal, no database dependency |
| Storage | File-based (Phase 1) | No database required for prototype |
| Future Database | PostgreSQL + TimescaleDB | Time-series optimized, SQL standard |
| Future Cache | Redis | Model result caching, session state |
| Future Pipeline | Apache Airflow or Prefect | Scheduled data refreshes, API pulls |

## Deployment (Recommended)

| Environment | Choice | Rationale |
|-------------|--------|-----------|
| Containerization | Docker + Docker Compose | Reproducible, portable |
| Cloud | AWS (ECS/Fargate) or GCP (Cloud Run) | Serverless container hosting |
| CDN | CloudFront or Cloudflare | Static frontend serving |
| CI/CD | GitHub Actions | Automated testing and deployment |
| Monitoring | Datadog or CloudWatch | API health, model performance |

## Security Considerations

| Area | Recommendation |
|------|----------------|
| Authentication | OAuth 2.0 / SSO (Azure AD for EY) |
| Authorization | Role-based (CMO, Analyst, Planner, Admin) |
| Data Encryption | TLS in transit, AES-256 at rest |
| API Security | Rate limiting, CORS, input validation |
| File Upload | Size limits, type validation, virus scanning |
| Audit Trail | Log all data uploads, model runs, exports |

## Scaling Path

| Phase | Infrastructure | Capacity |
|-------|---------------|----------|
| Phase 1 (Current) | Single server, file-based | 1-5 concurrent users |
| Phase 2 | Docker, PostgreSQL, Redis | 10-50 concurrent users |
| Phase 3 | Kubernetes, distributed compute | 100+ concurrent users, scheduled jobs |
