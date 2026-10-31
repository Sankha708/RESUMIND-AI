# RESUMIND AI — Quick Reference

> A one-page companion to
> [`RESUMIND_AI_COMPLETE_LEARNING_GUIDE.md`](RESUMIND_AI_COMPLETE_LEARNING_GUIDE.md).
> All facts below are verified against the current source.

## System architecture at a glance

```text
Browser (Next.js 16 / React 19 / TS)
   │  fetch + credentials:"include"  (HttpOnly cookie resumind_session)
   ▼
FastAPI app  (backend/app/main.py)
   │  SecurityRateLimitMiddleware → CORSMiddleware  (security headers + quotas)
   ▼
Routers: session · resume · assessment · job_match · improvement · builder · export · reanalysis
   ▼
Services: session · storage · parser · scoring · job_match · improvement · builder · pdf_export · docx_export · reanalysis
   ├── SQLAlchemy async ──► SQLite (local) / PostgreSQL (prod via asyncpg)
   ├── PyMuPDF + python-docx ──► parse & generate documents
   ├── ephemeral storage/{uploads,exports,reports}/{session_id}/
   └── LLMProvider ──► Ollama (optional, localhost:11434)
```

## Repository map

```text
AGENTS.md  README.md  .gitignore
docs/                     specifications, audits, THIS guide + companions
scripts/                  setup-backend/frontend, start-backend/frontend, test-backend (.ps1)
backend/app/main.py       app + middleware + lifespan + routers
backend/app/config.py     Settings (env / CORS / cookie / rate limits / Ollama)
backend/app/database.py   async engine + get_db
backend/app/models/       session, resume, assessment, job_match, improvement, builder
backend/app/schemas/      Pydantic contracts per feature
backend/app/routers/      one file per feature area
backend/app/services/     engines + storage + export
backend/app/providers/    LLMProvider, OllamaProvider, prompts, grounding
backend/alembic/          migrations
backend/tests/            pytest suite + synthetic_generator.py
frontend/src/app/         layout.tsx, page.tsx, globals.css
frontend/src/components/  screens (upload, review, ats, job match, improve, builder, export)
frontend/src/context/     SessionContext, ThemeContext
frontend/src/lib/api.ts   API base URL resolution
frontend/scripts/         launch-gate-e2e.mjs (Playwright)
storage/                  runtime data (git-ignored contents)
```

## API endpoints

| Method | Path | Purpose |
| :--- | :--- | :--- |
| GET | `/api/health` | Liveness |
| POST | `/api/session` | Create/reuse anonymous session |
| GET | `/api/session` | Current session |
| POST | `/api/session/reset` | Revoke + purge files |
| POST | `/api/resume/upload` | Upload + parse resume (≤10 MB) |
| GET / PUT / DELETE | `/api/resume` | Get / update / delete active resume |
| POST / GET | `/api/assessment` | Compute / fetch ATS readiness |
| POST / GET | `/api/job-match` | Compute / fetch job match |
| POST | `/api/improvement/generate` | Rule-based suggestions |
| GET | `/api/improvement` | List suggestions |
| PUT | `/api/improvement/{suggestion_id}` | Accept / reject / edit |
| POST | `/api/improvement/batch-accept` | Batch accept |
| POST | `/api/improvement/{id}/restore` | Restore original |
| POST | `/api/improvement/{id}/rewrite` | AI rewrite (Ollama) |
| GET | `/api/improvement/provider/status` | Ollama status |
| GET / PUT | `/api/builder` | Fetch / save Builder doc |
| POST | `/api/builder/reset` | Reset from resume/blank |
| GET | `/api/export/status` | Export readiness |
| GET | `/api/export/resume/pdf` | Resume PDF |
| GET | `/api/export/resume/docx` | Resume DOCX |
| GET | `/api/export/report/pdf` | Diagnostic report PDF |
| GET | `/api/reanalysis` | Baseline vs revision |

Docs UI: `http://127.0.0.1:8000/api/docs`.

## Database tables

| Table | Purpose |
| :--- | :--- |
| `anonymous_sessions` | Session id (UUID), `token_hash` (SHA-256), timestamps, `is_active` |
| `uploaded_resumes` | File metadata, `raw_text`, `structured_data` (JSON) |
| `ats_assessments` | `overall_score`, `dimension_scores` (JSON), `report_data` (JSON) |
| `job_match_assessments` | `job_title`, `overall_score`, `score_withheld`, `report_data` |
| `improvement_suggestions` | Text, status, AI metadata, grounding lists |
| `resume_builder_documents` | `content`, `section_order`, `section_visibility`, `version` |

All child tables carry `session_id` with cascade delete.

## Important services

| File | Role |
| :--- | :--- |
| `services/session_service.py` | Token mint/hash, expiry, cleanup |
| `services/storage_service.py` | Path-safe per-session dirs |
| `services/parser_service.py` | Validate + extract + structure resumes |
| `services/scoring_service.py` | 5-dimension ATS heuristic (weights 25/20/15/25/15 %) |
| `services/job_match_service.py` | 4-dimension grounded match (40/30/15/15 %) |
| `services/improvement_service.py` | Suggestions + apply/restore + stale detection |
| `services/builder_service.py` | Profile ↔ Builder content |
| `services/pdf_export_service.py` | PyMuPDF PDF generation |
| `services/docx_export_service.py` | python-docx generation |
| `services/reanalysis_service.py` | Baseline vs saved revision deltas |
| `providers/ollama_provider.py` | Ollama health + JSON rewrite + grounding |

## Local startup (Windows PowerShell)

```powershell
# first time
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
if (-not (Test-Path frontend/.env.local)) { Copy-Item frontend/.env.example frontend/.env.local }
./scripts/setup-backend.ps1
./scripts/setup-frontend.ps1

# migrations (optional; setup applies them)
cd backend; .\.venv\Scripts\python.exe -m alembic upgrade head; cd ..

# run
./scripts/start-backend.ps1     # terminal 1  -> :8000
./scripts/start-frontend.ps1    # terminal 2  -> :3000
```

URLs: frontend `http://127.0.0.1:3000` · health `http://127.0.0.1:8000/api/health`.

## Test commands

```powershell
./scripts/test-backend.ps1
cd frontend
npm.cmd run lint
npx.cmd tsc --noEmit
npm.cmd run build
npm.cmd run test:e2e:launch-gate    # needs Chromium headless shell / RESUMIND_CHROMIUM_PATH
```

## Common debugging commands

```powershell
# health / port
curl.exe -s http://127.0.0.1:8000/api/health
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue

# compile check
cd backend; .\.venv\Scripts\python.exe -m compileall -q app tests

# run one focused test
.\.venv\Scripts\python.exe -m pytest -q tests/test_scoring.py

# DB schema check on a throwaway DB (never the live file while running)
$env:DATABASE_URL="sqlite+aiosqlite:///$env:TEMP\verify.db"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic check
Remove-Item Env:DATABASE_URL

# back up the local DB
Copy-Item backend\resumind.db ("backend\resumind.db.backup-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
```

## Scoring formulas (quick)

- **ATS:** `Σ dimension_score × {0.25, 0.20, 0.15, 0.25, 0.15}` → rounded to 1 decimal.
- **Job Match:** per-category `(points / max_points) × 100`, then weighted-sum using
  pro-rata normalised weights for applicable categories.

## Environment variables (key)

`APP_ENV`, `DEBUG`, `DATABASE_URL`, `CORS_ORIGINS`, `SESSION_COOKIE_*`, `SESSION_TTL_HOURS`,
`SESSION_CLEANUP_INTERVAL_SECONDS`, `RATE_LIMIT_*`, `STORAGE_ROOT`, `OLLAMA_BASE_URL`,
`OLLAMA_MODEL`. Templates live in `backend/.env.example` and `frontend/.env.example`.

## Safety reminders

- Never commit `backend/resumind.db`, `.env`, storage contents, or exports.
- Never print or share resume `raw_text`/`structured_data` or `token_hash`.
- Production requires HTTPS, secure cookies, HTTPS CORS, PostgreSQL, and a shared rate limiter.
