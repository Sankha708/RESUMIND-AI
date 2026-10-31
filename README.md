# RESUMIND AI
**Privacy-first resume analysis and editing, with anonymous sessions, evidence-grounded recommendations, and ATS-oriented PDF/DOCX exports.**

RESUMIND AI helps job seekers understand how their resume is parsed, compare verified resume evidence with a target job description, make optional edits, and export a clean single-column resume. It is a local-first project; ATS scores are heuristic guidance, not a prediction of employer decisions.

> **Project status:** Local development and synthetic browser workflow are documented in [`docs/LAUNCH_READINESS.md`](docs/LAUNCH_READINESS.md). Public deployment has not been performed; review the limitations and security notes before hosting it or using real resumes.

## Why this project
Resume tools often combine formatting feedback with job fit, obscure their evidence, or encourage unsupported claims. RESUMIND AI separates document **ATS Readiness** from role-specific **Job Match**, cites source evidence, and requires user control over proposed rewrites. It does not promise interviews, employer rankings, or universal compatibility.

## Features
- PDF/DOCX upload with size, file-signature, and parser resource checks.
- Editable review of extracted contact details, work history, education, projects, and categorized skills.
- Separate ATS Readiness and optional evidence-backed Job Match analysis.
- Optional local Ollama rewrite suggestions with explicit Accept, Reject, and Edit controls.
- One single-column ATS Professional Builder template with saved draft state.
- Session-scoped PDF/DOCX resume exports and a diagnostic PDF report.
- Differential analysis only when a fresh baseline and saved revision are available.
- Anonymous session cookies and time-limited local session storage; no account is required.

## Architecture and technology
| Layer | Technology | Role |
| :--- | :--- | :--- |
| Web application | Next.js App Router, React, TypeScript | Responsive *Frost & Chrome* interface and Builder |
| API | FastAPI, Pydantic v2, Python | Async endpoints, validation, session-scoped workflows |
| Persistence | SQLAlchemy async, Alembic, SQLite locally | Session and document state; production configuration requires PostgreSQL |
| Document processing | PyMuPDF, `python-docx` | PDF/DOCX parsing and resume exports |
| AI provider | Pluggable `LLMProvider`, local Ollama | Optional rewrite proposals; no automatic cloud fallback |
| Tests | pytest, ESLint, TypeScript, Playwright launch gate | Synthetic backend, build, and browser workflow verification |

## Project structure
```text
backend/          FastAPI application, models, services, providers, Alembic and pytest
frontend/         Next.js application, public assets and Playwright launch gate
docs/             Product, design, security, launch readiness and implementation notes
scripts/          Windows PowerShell setup, test and startup helpers
storage/          Local session uploads/exports/reports (generated data; do not commit)
tests/             Shared synthetic fixture location
```

## Prerequisites
- Windows 10/11 with PowerShell; the commands below are written for PowerShell.
- Python 3.11 or newer (the existing local environment may use a newer Python; use a supported version for your own environment).
- Node.js 20.9 or newer and npm (required by the installed Next.js version).
- Ollama is **optional** and needed only for live rewrite generation. Model downloads, hardware requirements, and latency are separate from application setup.

## Windows local setup
From a PowerShell window in the repository root:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
if (-not (Test-Path frontend/.env.local)) { Copy-Item frontend/.env.example frontend/.env.local }
./scripts/setup-backend.ps1
./scripts/setup-frontend.ps1
```

The backend setup script creates `backend/.venv`, installs `backend/requirements.txt`, and applies migrations to the configured local database. The frontend setup script uses `npm ci` and builds the application. Keep `.env` and `.env.local` private; the templates contain safe local defaults.

### Database migrations
Local SQLite defaults to `backend/resumind.db` (ignored by Git). From the repository root after backend setup:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m alembic upgrade head
```

For production, provide PostgreSQL configuration and run Alembic migrations as a controlled deployment step. Do not treat local automatic table creation as a production migration mechanism.

### Start the application
Start the backend in one PowerShell window from the repository root:

```powershell
./scripts/start-backend.ps1
```

Start the frontend in a second window:

```powershell
./scripts/start-frontend.ps1
```

Open `http://127.0.0.1:3000`. The API health endpoint is `http://127.0.0.1:8000/api/health`.

### Tests and build checks
```powershell
./scripts/test-backend.ps1
Set-Location frontend
npm.cmd run lint
npx.cmd tsc --noEmit
npm.cmd run build
npm.cmd run test:e2e:launch-gate
```

`scripts/test-backend.ps1` compiles the backend and runs the full pytest suite with a unique per-run temporary directory. It needs no manual environment variables; stray machine-level variables such as `DEBUG=release` are ignored outside production.

The browser launch gate requires Playwright's Chromium headless shell (or `RESUMIND_CHROMIUM_PATH`) and uses synthetic resumes, isolated temporary database/storage paths, and local app processes. See [`docs/LAUNCH_READINESS.md`](docs/LAUNCH_READINESS.md) for the dated verification record; rerun checks for a release candidate.

### Optional local Ollama
Install and start Ollama separately if you want live rewrite proposals, then install a model supported by your hardware. Configure `OLLAMA_BASE_URL` and `OLLAMA_MODEL` in your private `backend/.env`. The example defaults target a local Ollama server and `llama3.2`. RESUMIND AI does not download models, call a paid provider, or silently fall back to a remote LLM. Without Ollama, rewrite generation is unavailable; deterministic mock providers are used in automated tests. Model capacity and response time depend on local hardware.

### PDF and DOCX processing
Upload a PDF or DOCX through the app. The parser enforces a 10 MB upload limit and format-specific checks; PDF page count and DOCX archive expansion are also bounded. After reviewing extracted fields and editing the Builder, the Export Center generates PDF and DOCX resumes plus a separate diagnostic PDF. Exported resumes use the one single-column ATS Professional template and are checked against synthetic fixtures; results do not guarantee behavior in every ATS.

## Security and privacy
Anonymous session tokens are high entropy; the server stores a SHA-256 hash rather than the raw token. Session cookies are HttpOnly and SameSite=Lax; `Secure` is disabled for local HTTP and must be enabled behind HTTPS. Uploads, generated exports, and session records are scoped to a session and purged after inactivity by the application cleanup task; filesystem deletion is not forensic erasure.

The API has application-level upload validation, session isolation, in-process rate limits, CORS configuration, and baseline response headers. These controls are not a security certification. Production requires HTTPS, secure cookies, exact HTTPS CORS origins, trusted deployment secrets, reverse-proxy limits, PostgreSQL operations/backups, resource controls, and shared/edge rate limiting for multiple workers. The current CSP still allows inline scripts/styles, and parsing is not OS-sandboxed. Review [`docs/SECURITY.md`](docs/SECURITY.md) and [`docs/LAUNCH_READINESS.md`](docs/LAUNCH_READINESS.md) before deployment.

## Current limitations
- No production deployment, independent security assessment, or public service is provided.
- ATS and Job Match scores are heuristics; there is no employer ATS guarantee or hiring prediction.
- Extraction can require user correction; candidate-added claims are not independently verified.
- Local Ollama performance requires suitable hardware and depends on model startup/latency.
- The in-process rate limiter is for a single API worker; scaling needs a trusted edge or shared limiter.
- Production CSP inline allowances, parser sandboxing, and deployment/backup operations need further hardening and validation.
- Session cleanup is ordinary deletion, not secure media erasure.

## Future improvements
Potential follow-up work includes nonce-based CSP with browser regression coverage, a shared production rate limiter and trusted proxy configuration, isolated document parsing, independent accessibility/security review, and tested PostgreSQL backup/restore and deployment procedures. These are not represented as completed features.

## Documentation
- [Complete project learning guide](docs/RESUMIND_AI_COMPLETE_LEARNING_GUIDE.md) — source-verified walkthrough of the whole app, for beginners and reviewers
- [Quick reference](docs/RESUMIND_AI_QUICK_REFERENCE.md) — architecture, API, tables, commands
- [Beginner learning roadmap](docs/RESUMIND_AI_BEGINNER_LEARNING_ROADMAP.md) — hands-on lessons
- [Technical glossary](docs/RESUMIND_AI_TECHNICAL_GLOSSARY.md) — terminology
- [Security and privacy](docs/SECURITY.md)
- [Launch readiness and verification record](docs/LAUNCH_READINESS.md)
- [Product specification](docs/PRODUCT_SPEC.md)
- [Frost & Chrome design system](docs/DESIGN_SYSTEM.md)
- [Phased implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [GitHub release audit](docs/GITHUB_RELEASE_AUDIT.md)

## License
No license has been selected. Until the owner chooses and adds a license, do not assume this repository grants permission to use, modify, or redistribute its contents.
