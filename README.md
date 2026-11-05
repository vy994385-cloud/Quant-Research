# QRQuant — Financial Research Workspace

QRQuant aims to bring company research, financial analysis, market context, events/news, screening, comparison, monitoring, and research outputs into one clear workspace.

## Current scope

The repository currently centres on **India-listed equities**, with recorded research data for six companies: TCS, RELIANCE, INFY, HDFCBANK, SUNPHARMA, and M&M. Existing areas include company research, financial history/insights, market and technical observations, events/news/corporate actions, evidence lineage, coverage gaps, screener and comparison APIs, reports, and exports.

A visible page does not guarantee a complete data pipeline. Some experiences are partial, device-local, or awaiting data/infrastructure. ETFs, mutual funds, IPO workflows, and F&O are not yet implemented as complete research datasets. See [PRODUCT_BLUEPRINT.md](./PRODUCT_BLUEPRINT.md) for the intended product, capability map, and delivery plan.

## Principles

- Make the next step obvious: discover → analyze → compare → monitor → report/export.
- Show source, reporting period, units, freshness, and reported-vs-derived status.
- Separate verified facts, calculations, hypotheses, and unknowns.
- Never invent live data, coverage, alerts, saved state, ratings, or asset-class support.
- Preserve point-in-time correctness and historical source context.
- No buy/sell calls, opaque company scores, or winner/loser rankings.
- Prioritise readable tables, accessibility, and responsive behaviour over decorative UI.

## Stack

- Frontend: React, TypeScript, Vite, React Router
- Backend: Python, FastAPI
- Tests: Vitest / Testing Library and pytest
- Current data: recorded research fixtures and source metadata

## Local development

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Frontend checks:

```bash
npm run lint
npm test -- --run
npm run build
```

Run backend tests from the repository root using the project's configured Python environment:

```bash
pytest -q
```

Follow [DEPLOYMENT.md](./DEPLOYMENT.md) for backend startup, environment variables, and deployment checks. Production builds must use an explicit `VITE_API_URL`; historical test counts in progress notes are not proof of current branch health.

## Delivery discipline

Keep `main` intact while work is reviewed on feature branches. A capability is complete only when its data path, failure states, tests, accessible interactions, source/freshness semantics, and deployment behaviour are verified. Do not merge the current draft landing-page work until its stated checks have been run.
