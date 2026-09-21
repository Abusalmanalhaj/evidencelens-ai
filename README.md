# EvidenceLens AI

AI-powered startup technical due diligence platform. Upload a pitch deck PDF, extract technical claims, map supporting evidence, and generate transparent assessment reports.

## Architecture

```
┌─────────────┐     REST API      ┌──────────────────────────────────────┐
│  React SPA  │ ◄──────────────► │  FastAPI Backend                      │
│  (Vite/TS)  │                   │  ├── Auth (JWT)                      │
└─────────────┘                   │  ├── Project CRUD                    │
                                  │  ├── PDF Upload + PyMuPDF extraction │
                                  │  ├── LangGraph analysis workflow     │
                                  │  ├── Assessment scoring              │
                                  │  └── ReportLab PDF reports           │
                                  └──────────┬───────────────────────────┘
                                             │
                                  ┌──────────▼───────────┐
                                  │  PostgreSQL          │
                                  └──────────────────────┘
```

### LangGraph Workflow

1. **Extract Claims** — Identify technical/business claims from deck text (LLM or heuristic fallback)
2. **Map Evidence** — Link supporting/contradictory/missing evidence with page references
3. **Assess** — Compute transparent support scores from evidence strength, traceability, specificity

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- OpenAI API key (optional — heuristic mode works without it)
- PostgreSQL or Docker (optional — **SQLite works out of the box** for local dev)

### Local Development (no Docker required)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Tables are auto-created on startup when using SQLite (default)
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### Docker Compose (full stack)

```bash
cp .env.example .env
# Optionally set OPENAI_API_KEY in .env
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Async PostgreSQL connection | localhost |
| `SECRET_KEY` | JWT signing key | (change in prod) |
| `OPENAI_API_KEY` | OpenAI API key for LLM analysis | empty (heuristic mode) |
| `OPENAI_MODEL` | Model name | gpt-4o-mini |
| `CORS_ORIGINS` | Allowed frontend origins | localhost:5173 |
| `MAX_UPLOAD_SIZE_MB` | PDF upload limit | 25 |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register user |
| POST | `/api/v1/auth/login` | Login, get JWT |
| GET | `/api/v1/auth/me` | Current user |
| CRUD | `/api/v1/projects` | Project management |
| POST | `/api/v1/projects/{id}/documents` | Upload PDF |
| POST | `/api/v1/projects/{id}/analysis/run` | Start analysis |
| GET | `/api/v1/projects/{id}/analysis/status` | Analysis progress |

## Separate Vercel and Render Deployment

The frontend and backend use separate environment files:

- Vercel: copy `frontend/.env.example` into the Vercel project settings and set `VITE_API_URL` to the deployed Render API URL.
- Render: use `backend/.env.example` as the variable checklist. Set `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, and optionally `OPENAI_API_KEY` in the Render service settings.
- `CORS_ORIGINS` must contain the exact Vercel origin, including `https://` and without a trailing slash.
- The Vercel project root is the repository root; `vercel.json` builds the frontend and serves `frontend/dist` with SPA rewrites.
- The Render blueprint in `render.yaml` deploys the API from `backend` and exposes `/health` for health checks.

Uploads on Render's default filesystem are temporary. Use persistent storage or object storage before relying on uploaded PDFs in production.
| GET | `/api/v1/projects/{id}/claims` | List claims |
| GET | `/api/v1/projects/{id}/dashboard` | Analytics metrics |
| GET | `/api/v1/projects/{id}/reports/download` | Download PDF report |
| PATCH | `/api/v1/projects/{id}/claims/{cid}/category` | Human review |
| PATCH | `/api/v1/projects/{id}/claims/{cid}/evidence/{eid}` | Mark evidence relevance |

Full OpenAPI docs at `/docs` when the backend is running.

## Testing

```bash
cd backend
pytest tests/ -v
```

Tests use SQLite in-memory and mocked/heuristic workflows — no OpenAI key required.

## Screenshots

Capture screenshots after running the app:

1. Register/login page
2. Projects dashboard with a created project
3. PDF upload and analysis progress
4. Analytics dashboard with Recharts visualizations
5. Claim detail with evidence and human review controls
6. Downloaded PDF report

## Implemented Features

- [x] User registration/login with JWT
- [x] Project CRUD with ownership enforcement
- [x] PDF upload, validation, PyMuPDF text extraction
- [x] LangGraph claim extraction workflow
- [x] Evidence mapping with page traceability
- [x] Transparent assessment scoring framework
- [x] Analytics dashboard with Recharts
- [x] Human review (category correction, evidence relevance)
- [x] PDF report generation
- [x] Docker Compose deployment
- [x] GitHub Actions CI
- [x] Heuristic fallback when OpenAI key is missing

## Limitations

- Analysis quality depends on PDF text extractability (scanned PDFs may fail)
- Heuristic mode provides basic claim detection without LLM sophistication
- Support scores measure deck evidence support, not factual verification
- No external data source verification (by design — deck-only analysis)
- Background analysis uses FastAPI BackgroundTasks (not a dedicated job queue)

## License

MIT
