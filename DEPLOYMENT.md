# L8 Deployment Guide

## Status

- Backend: EXISTS at `https://quant-research-api-50u0.onrender.com` (health OK)
- Frontend: NOT YET DEPLOYED
- CORS: Configured via FRONTEND_ORIGINS env var (set in render.yaml)

## Architecture

- Backend: Python 3.12 FastAPI, pure computation API (no database, no secrets)
- Frontend: React 19 + TypeScript + Vite, static site
- Data: Recorded fixtures only (no live network in production)

## Deployment Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Python 3.12 backend image (optional Docker deployment) |
| `render.yaml` | Render Blueprint config for both services |
| `frontend/.env.production` | Points to deployed backend URL |
| `.dockerignore` | Excludes tests, node_modules, non-essential data |
| `.gitignore` | Un-ignores `data/raw/research`, `data/raw/research_api`, `data/raw/universe` — recorded data MUST be committed |

## Critical Constraint

The production backend is a pure computation API over **committed recorded
fixtures**. If `data/raw/research_api`, `data/raw/research`,
`data/raw/universe/nse_equities.csv`, or `fixtures/real_data` are missing from
the git checkout, `/health` still returns OK but every `/api/v1` endpoint is
empty/unavailable. These paths are referenced by `src/api/main.py:187,929`,
`src/api/recorded_research.py:47`, and `src/verification/real_data.py:89`.

## API Endpoints (38 v1 + legacy)

All verified with 2561 backend tests + frontend vitest suite:

```
GET /health
GET /api/v1/companies
GET /api/v1/companies/compare
GET /api/v1/discovery
GET /api/v1/discovery/trending
GET /api/v1/evidence/search
GET /api/v1/screener/fields
POST /api/v1/screener
GET /api/v1/companies/{symbol}/research
GET /api/v1/companies/{symbol}/intelligence
GET /api/v1/companies/{symbol}/timeline
GET /api/v1/companies/{symbol}/rankings
GET /api/v1/companies/{symbol}/deep-financial-insights
GET /api/v1/companies/{symbol}/source-statuses
GET /api/v1/companies/{symbol}/hidden-information
GET /api/v1/companies/{symbol}/cross-domain
GET /api/v1/companies/{symbol}/research-gaps
GET /api/v1/companies/{symbol}/deep-technicals
GET /api/v1/companies/{symbol}/chart-data
GET /api/v1/companies/{symbol}/news
GET /api/v1/companies/{symbol}/corporate-actions
GET /api/v1/companies/{symbol}/industry-context
GET /api/v1/companies/{symbol}/tracking
GET /api/v1/companies/{symbol}/evidence
GET /api/v1/companies/{symbol}/evidence/{evidence_id}
GET /api/v1/companies/{symbol}/export
GET /api/v1/companies/{symbol}/research-report
GET /api/v1/companies/{symbol}/backtest
GET /api/v1/companies/{symbol}/deep-fundamentals
GET /api/v1/companies/{symbol}/financial-history
GET /api/v1/companies/{symbol}/business-intelligence
GET /api/v1/companies/{symbol}/events
GET /api/v1/companies/{symbol}/ownership
GET /api/v1/companies/{symbol}/ownership-summary
GET /api/v1/companies/{symbol}/analyst-intelligence
GET /api/v1/companies/{symbol}/price-attribution
GET /api/v1/companies/{symbol}/research-timeline
GET /api/v1/rankings/{horizon}
GET /api/v1/validation/{horizon}
```

Legacy endpoints (not used by frontend):
```
GET /api/stocks/search
GET /api/stocks
GET /api/stocks/{symbol}
GET /api/stocks/{symbol}/research
GET /api/stocks/{symbol}/rankings
GET /api/rankings/{horizon}
GET /api/research/demo
```

## Supported Companies

TCS, RELIANCE, INFY, HDFCBANK, SUNPHARMA, M&M (6 verified companies with recorded fixtures)

## Environment Variables

| Variable | Where | Value |
|----------|-------|-------|
| `FRONTEND_ORIGINS` | Backend | Comma-separated origins; must contain the **actual** deployed frontend origin + local dev origins |
| `VITE_API_URL` | Frontend | `https://quant-research-api-50u0.onrender.com` (set in render.yaml and `.env.production`; Vite bakes it in at build time) |

> **URL suffix caveat:** Render appends a random suffix to new service URLs
> (the backend is `...-50u0.onrender.com`). The frontend's real origin will
> likely be `https://quant-research-frontend-XXXX.onrender.com`, NOT
> `https://quant-research-frontend.onrender.com`. After the first frontend
> deploy, read its exact URL from the dashboard and update `FRONTEND_ORIGINS`
> on the backend (redeploy required). A CORS mismatch shows up as browser
> console errors with every API call failing.

## Manual Steps (Render Dashboard)

### Step 0: Commit and push this repo

The recorded research data (~8.7 MB, 2227 files), render.yaml, and .gitignore
changes must be committed and pushed before Render can build correctly.

### Step 1: Apply the Blueprint

1. Go to https://dashboard.render.com
2. **New** > **Blueprint**, connect this GitHub repo
3. Render reads render.yaml and creates/adopts:
   - `quant-research-api` (Python web service, health check `/health`)
   - `quant-research-frontend` (static site, SPA rewrite `/* -> /index.html`)
4. If a service name already exists, Render applies the blueprint config to
   that existing service instead of creating a duplicate.

(Alternative without Blueprint: create the two services manually with the
commands from render.yaml.)

### Step 2: Verify backend

```
curl https://quant-research-api-50u0.onrender.com/health          # {"status": "ok"}-style 200
curl https://quant-research-api-50u0.onrender.com/api/v1/companies # must list the 6 recorded companies — proves data dirs deployed
```

If `/api/v1/companies` returns empty/error, the data commit did not reach the
deployed checkout.

### Step 3: Fix FRONTEND_ORIGINS to the real frontend URL

1. Open the `quant-research-frontend` service page; copy its exact URL
2. Backend service > **Environment** > ensure `FRONTEND_ORIGINS` contains that
   exact origin (plus `http://127.0.0.1:5173,http://localhost:5173`)
3. Save (triggers backend redeploy)

### Step 4: Verify End-to-End

1. Open the frontend URL
2. Search for "TCS" and click it
3. Verify: research panel loads with evidence, rankings, timeline, intelligence
4. Deep-link refresh (e.g. reload while on `/reports`) must not 404 (SPA rewrite)
5. Check browser console for CORS errors (should be none)

## Data Directories

Backend requires these data directories in the repo root:

- `data/raw/universe/nse_equities.csv` — NSE stock universe
- `data/raw/research_api/` — Recorded company sources (6 companies)
- `data/raw/research/` — Recorded market data fixtures
- `fixtures/real_data/` — Additional test fixtures

All data is committed to the repo. No live network access required in production.
