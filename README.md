# Yield Intelligence Platform
## Marketing ROI & Budget Optimization Engine

### What it does
Omnichannel marketing analytics engine that answers three questions:
1. **What happened?** — ROI, attribution, trends across all channels and campaigns
2. **What should we do?** — AI-backed recommendations with QoQ/YoY context, cross-channel reasoning, phased action plans
3. **What's the business case?** — Budget optimization with scenario comparison, value-at-risk quantification

### Architecture
- **Backend**: FastAPI (Python 3.12) with 20+ statistical engines (scipy, statsmodels, prophet, pymc)
- **Frontend**: React + Recharts + Lucide (Vite build system, CDN fallback for portability)
- **Persistence**: SQLite (sessions, scenarios, users)
- **Auth**: JWT + RBAC (admin / analyst / viewer roles)

### Key Features

**Analytics Engines (22 engines, 4,230 lines)**
- Response Curves: Power-Law, Hill Saturation, Auto-select per channel
- Marketing Mix Model: Bayesian (PyMC), MLE (scipy), OLS + Bootstrap, 3-tier fallback
- Attribution: Last Touch, Linear, Position-Based, Markov Chain, Shapley Values
- Optimizer: SLSQP constrained, Multi-Objective Pareto, sensitivity analysis
- Forecasting: Prophet, ARIMA, linear fallback
- Plus: adstock, cross-channel correlation, geo-lift, funnel analysis, trend analysis

**Model Control Panel**
- All models selectable with real names (Bayesian PyMC NUTS, Markov Chain, SLSQP, etc.)
- Diagnostic metrics visible (R², convergence, MAPE)
- Auto-runs full engine chain when model selection changes

**Smart Recommendations (13+ types)**
- Paragraph-style with historical context and QoQ/YoY trends
- Cross-channel reasoning: "Shift $45K/month from Display to Paid Search"
- Phased plans: Month 1 test, Month 2-3 scale, conditions for scaling
- Model provenance: "Source: Response Curves + Markov Attribution"
- Types: REALLOCATE, DECLINING, FIX_CX, HIDDEN_VALUE, SCALE, REDUCE, FIX, RETARGET, MAINTAIN

**External Data Integration (3 CSV uploads)**
- Competitive Intelligence (SEMrush/SimilarWeb exports) → DEFEND, OPPORTUNITY, DIFFERENTIATE
- Market Events (seasonal calendar, competitor actions) → PREPARE, MITIGATE, CAPITALIZE
- Market Trends (CPC/CPM trends, benchmarks) → BENCHMARK, COST_ALERT

**Infrastructure**
- SQLite persistence (sessions survive restarts)
- JWT authentication with 3 roles (admin, analyst, viewer)
- Scenario save/load/compare (side-by-side with channel-level diffs)
- Vite build system (180KB gzipped production bundle)
- Docker deployment (Railway/Render ready)

### Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn api:app --reload --port 8000

# Frontend (development)
cd frontend
npm install
npm run dev

# Frontend (production build)
cd frontend
npm run build
# Serves from /app endpoint on backend
```

### API Endpoints (40+)

| Category | Endpoints |
|----------|-----------|
| Core | `/api/health`, `/api/load-mock-data`, `/api/full-state` |
| Upload | `/api/upload`, `/api/upload-journeys`, `/api/upload-competitive`, `/api/upload-events`, `/api/upload-trends` |
| Analysis | `/api/response-curves`, `/api/recommendations`, `/api/pillars`, `/api/insights` |
| Models | `/api/model-selections`, `/api/mmm`, `/api/adstock`, `/api/markov-attribution`, `/api/shapley` |
| Optimization | `/api/optimize`, `/api/sensitivity`, `/api/multi-objective` |
| Intelligence | `/api/trend-analysis`, `/api/funnel-analysis`, `/api/forecast`, `/api/cross-channel` |
| Auth | `/api/auth/register`, `/api/auth/login`, `/api/auth/me` |
| Scenarios | `/api/scenarios`, `/api/scenarios/save`, `/api/scenarios/compare` |
| Export | `/api/executive-summary`, `/api/download-template` |

### Honest Limitations
- Frontend is React via CDN (Vite build available but not served by default from backend)
- SQLite is single-file, not horizontally scalable (PostgreSQL recommended for teams)
- MMM Bayesian path needs PyMC which requires specific system libraries
- Mock data is synthetic — response curves will differ with real campaign data
- In-browser Babel fallback still used when Vite dist is not deployed
- Auth is basic JWT — no OAuth, no SSO, no MFA
- Scenario comparison is parameter-level, not visual diff

### File Structure
```
yield-intelligence/
├── backend/
│   ├── api.py                    # FastAPI — 40+ endpoints
│   ├── auth.py                   # JWT + RBAC
│   ├── persistence.py            # SQLite state management
│   ├── mock_data.py              # 48-month demo data
│   ├── validator.py              # Upload validation
│   ├── test_integration.py       # 69-test suite
│   └── engines/                  # 22 statistical engines
│       ├── response_curves.py    # Power-Law, Hill, Auto
│       ├── optimizer.py          # SLSQP, sensitivity
│       ├── mmm.py                # Bayesian, MLE, OLS
│       ├── insights.py           # Smart recommendations + QoQ/YoY
│       ├── external_data.py      # Competitive, Events, Trends
│       ├── attribution.py        # Last Touch, Linear, Position-Based
│       ├── markov_attribution.py # Markov Chain + bootstrap
│       ├── diagnostics.py        # Statistical recommendations
│       ├── leakage.py            # Value at Risk (3 pillars)
│       ├── forecasting.py        # Prophet, ARIMA
│       └── ...                   # 12 more engines
├── frontend/
│   ├── app.jsx                   # React frontend (7 screens)
│   ├── index.html                # CDN fallback entry
│   ├── main.jsx                  # Vite entry
│   ├── vite.config.js            # Vite build config
│   └── package.json              # Node dependencies
├── templates/                    # 5 CSV upload templates
├── docs/                         # Model specs, data dictionary, blueprints
├── Dockerfile                    # Production container
└── README.md
```

### Tests
```bash
cd backend && python test_integration.py
# Expected: 69 passed, 0 failed
```
