# RESUMIND AI — Launch Readiness

**Review date:** 2026-10-30  
**Scope:** Current source in `D:\RESUMIND-AI`; no public deployment performed.

**Verdict:** **Ready for local use.** The complete synthetic browser workflow passed against the production frontend and an isolated FastAPI/SQLite backend, including live Ollama inference on this machine. The project is **not ready for controlled beta or public deployment** until the application CSP hardening and deployment-specific HTTPS, production CORS, shared rate limiting, PostgreSQL operations/backups, and secret management are completed and verified.

## Implemented and verified

- Resume parsing for PDF and DOCX, including section normalization, continuation handling, categorized skills, projects, education, and contact extraction.
- Anonymous session cookie lifecycle, SHA-256 token hash storage, session-scoped queries and storage, expiry cleanup, and cross-session isolation tests.
- Deterministic ATS Readiness and distinct Job Match analysis with source evidence.
- Rewrite proposal controls and a pluggable Ollama provider; live `llama3.2` rewriting is verified on this machine, and automated suites can inject a deterministic mock.
- One canonical ATS Professional Builder template, saved content, visibility/order controls, and consistent PDF/DOCX exporters.
- Differential Reanalysis with honest locked state, a preserved ATS baseline, saved revision requirement, template-only change exclusion, and optional Job Match delta.
- Upload checks including a bounded 10 MB stream, file signatures, DOCX expansion limits, and a 100-page PDF limit.
- In-process API, upload, and AI rewrite/generation sliding-window rate limits with 429/Retry-After responses; IP-based quotas use the direct ASGI client address and session-specific AI quotas use a SHA-256 cookie hash.
- FastAPI and Next.js baseline security headers; Next.js CSP allows the configured API origin. Development CSP adds `unsafe-eval` for React debugging only; the production policy omits it. HSTS is conditional on production secure-cookie settings for the API and `ENABLE_HSTS=true` for HTTPS frontend builds.
- Production configuration rejects debug mode, insecure/non-HttpOnly cookies, unsupported SameSite values, disabled rate limits, SQLite, and non-HTTPS or wildcard CORS origins. The API skips automatic table creation in production and requires Alembic migrations first.
- Production environment templates for backend and frontend with safe placeholder values.
- Synthetic PDF and DOCX exports reopened and checked for content and reading order; the generated PDF was rendered and visually inspected. No clipping, overlap, or blank page was found in that fixture.
- Alembic migration chain applied to an isolated temporary SQLite database through revision `d5e89a421b01`.
- Production-browser E2E coverage is now reproducible with Playwright and a locally cached Chromium headless shell. It uses synthetic resume files, random local ports, a temporary SQLite database, and temporary storage; it does not read or modify `backend/resumind.db`.

## Verification results

| Check | Result |
| :--- | :--- |
| Full backend pytest suite | **144 passed**, 0 failures; 695 upstream deprecation warnings, chiefly `pytest-asyncio` event-loop-policy deprecations on Python 3.14 and the Starlette/httpx TestClient deprecation; no skipped tests were reported |
| Focused security/config tests | **15 passed**, including rate-limit enforcement, CORS preflight/header behavior, HSTS gating, hashed session quota keys, invalid production configuration, and validation error secret redaction |
| Python compile check | `python -m compileall -q app tests` passed |
| Focused builder and export regressions | `pytest tests/test_builder.py tests/test_export.py -q`: **23 passed**, 181 warnings |
| Frontend ESLint | Passed |
| Frontend TypeScript | `npx tsc --noEmit` passed |
| Next production build | Passed; static routes generated for `/` and `/rewrite` |
| Production configuration validation | Passed synthetic valid/invalid configuration cases; no production database or deployment was started |
| Wired FastAPI smoke | `/api/health` and a CORS preflight returned 200 with security headers using an isolated in-memory SQLite database |
| Production Next header smoke | Local production server returned 200 with CSP, HSTS, standard headers, and the configured API origin; temporary server was stopped afterward |
| Alembic migration chain | Passed on an isolated temporary SQLite database; no project database was migrated |
| Synthetic PDF/DOCX export inspection | Passed for fixture content; PDF rendered pages visually inspected; DOCX reopened with python-docx |
| Local HTTP smoke checks | Frontend `/` returned 200 and API `/api/health` returned 200 |
| Browser upload/edit/export and live rewrite workflow | `npm.cmd run test:e2e:launch-gate`: **31 launch-gate checks passed**: 24 browser workflows, 4 fixture/migration/server/build checks, and 3 development/production CSP checks. The real Ollama proposal stayed pending until explicit acceptance, then was restored |
| Live Ollama inference | Installed Ollama 0.40.13 and configured `llama3.2:latest` (2.0 GB). `GET http://localhost:11434/api/tags` returned the model; after `ollama ps` confirmed the model was unloaded, Chromium made a real cold-start rewrite request, received a proposal with `status=identified`, and verified explicit accept and restore controls. The model ran on the RTX 4050 GPU |

The pytest warnings were emitted by the installed async test plugin and Starlette/httpx on Python 3.14. They were not suppressed. No skipped tests were reported in the full-suite run.

### Maintenance re-verification (2026-10-31)

A repository clean-up pass removed only ephemeral runtime and test artifacts (session uploads/exports/reports, `temp/`, caches, `debug.log`, build state, the local DB backup, unused default Next.js SVGs, and the empty root `tests/` placeholder). Source was unaffected except for the two fixes below. After that pass, on the same Windows host:

- Full backend pytest suite: **149 passed, 0 failed, 0 skipped**. The total increased from 144 because five regression tests were added for the boolean environment hardening described below.
- Focused security/config tests: **16 passed** (previously 15), including the new stray-`DEBUG` cases.
- `python -m compileall -q app tests`: passed.
- Isolated Alembic `upgrade head` and `check` on a fresh temporary SQLite database: passed, `No new upgrade operations detected.` The live `backend/resumind.db` was not migrated.
- Frontend `npx tsc --noEmit`, `npm run lint`, and `npm run build`: passed; static routes generated for `/`, `/_not-found`, and `/rewrite`.

Two defects were fixed during this pass:

1. **Stray ambient boolean environment variables.** A machine-level `DEBUG=release` (and similar generic variables exported by unrelated tooling) caused a `Pydantic ValidationError` at startup because pydantic-settings matches field names case-insensitively. `app/config.py` now coerces recognized boolean strings (`true/false/1/0/yes/no/on/off`) and, outside production, ignores unrecognized values with a logged warning so the field default applies. In production an unrecognized value still fails closed. Regression tests cover all three paths.
2. **Fixed `--basetemp` in `pytest.ini`.** The absolute `../temp/pytest` scratch path could collide with a stale or permission-locked directory left by an interrupted run. The setting was removed so pytest uses its standard temporary location, and `scripts/test-backend.ps1` now supplies a unique per-run basetemp with the cache provider disabled.

**Local environment note:** three directories on this specific machine (`temp/pytest`, `backend/.pytest_cache`, and `%TEMP%\pytest-of-sankh`) carry a corrupted security descriptor that denies access even to their owner and cannot be removed, renamed, or taken ownership of without elevated privileges. They are empty, both project-side paths are covered by `.gitignore`, and they are never part of the repository. Removing them requires an administrator to repair the ACLs (for example, `icacls <path> /reset /T`) or a reboot; this does not affect the application, tests, or release contents.

## Final browser E2E evidence

The launch-gate browser runner is `frontend/scripts/launch-gate-e2e.mjs`; run it from `frontend` after installing dependencies and placing a compatible Chromium headless-shell executable in Playwright's cache (or setting `RESUMIND_CHROMIUM_PATH`). It uses isolated Next.js output, a temporary TypeScript config, database, and storage paths plus real local backend/frontend processes, so it does not overwrite another local Next.js dev server or add generated type paths to the project `tsconfig.json`. It removes those temporary paths after the run. The exact command was:

```powershell
npm.cmd run test:e2e:launch-gate
```

All 31 checks passed: 24 exercise browser workflows, 4 verify fixture creation, isolated database migration, backend startup, and the production frontend build, and 3 check the development CSP header, development browser rendering, and production CSP header. The browser workflows exercised were:

- Homepage rendering and anonymous HttpOnly session creation.
- Synthetic PDF upload and extraction of the expected name, email, phone, LinkedIn URL, both experience entries and bullets, project, skills, and education. The review screen saved a correction and the backend returned it.
- Unsupported upload rejection with visible validation feedback.
- Real ATS Readiness (`83.9`) and separate Job Match (`82.4`) responses with different dimensions/categories.
- Baseline-locked differential comparison, then actual saved-revision results (`83.9` baseline, `89.8` revised, `+5.9`).
- Suggestion edit, explicit accept, restore, and reject controls.
- The single `ATS Professional` template; Builder save advanced the version, refresh restored the saved content, and a stale second-tab write returned a visible conflict.
- Browser downloads for resume PDF, resume DOCX, and diagnostic PDF.
- Diagnostic PDF contents were compared with same-session API results: ATS score `83.9`, Job Match score `82/100` (from API score `82.4`), current document version `v3`, and the notice that the assessment evaluated an earlier snapshot.
- PDF reopened with PyMuPDF, selectable expected text extracted, and page rendered at `frontend/test-results/launch-gate/resume-page-1.png` for visual review. The page is crisp, single-column, has no clipped/overlapping content, and shows the corrected contact, experience, project, skills, education, and certifications. Education dates appear once. DOCX reopened with `python-docx` (25 paragraphs) and preserved the corrected profile and experience.
- A second anonymous session could not read the first session's resume and successfully parsed a separate synthetic DOCX profile.
- Expired-session `401`, backend outage messaging, and absence of uncaught browser page errors.
- Before Ollama was installed, the offline path was exercised: the actual rewrite endpoint returned HTTP 503, the error stayed inline, the draft remained unchanged, and no browser dialog opened.
- After installing Ollama 0.40.13 and `llama3.2:latest`, the browser made a real rewrite request. The proposal stayed `identified` until explicit acceptance; the test then restored the original statement.
- In development, Chromium rendered the homepage without the screenshot's React `eval()` CSP error. The development response includes `'unsafe-eval'`; the production response was checked and excludes it.

The PDF, DOCX, diagnostic report, rendered PNG, JSON browser evidence, and extracted-text inspection are retained under the ignored directory `frontend/test-results/launch-gate/` for local review; they are generated test artifacts, not source-controlled fixtures.

### Commands and exact final results

Run from the listed working directory. `npm.cmd`/`npx.cmd` avoid PowerShell script-policy alias issues on this Windows setup.

| Working directory | Command | Result |
| :--- | :--- | :--- |
| `backend` | `$env:DEBUG='false'; $env:APP_ENV='test'; .\.venv\Scripts\python.exe -m pytest tests -q` | **144 passed**, 695 warnings, 0 failed, no skipped tests reported (16.48s) |
| `backend` | `.\.venv\Scripts\python.exe -m compileall -q app tests` | Passed |
| `frontend` | `npm.cmd run lint` | Passed |
| `frontend` | `npx.cmd tsc --noEmit` | Passed |
| `frontend` | `npm.cmd run build` | Passed; Next.js 16.4.3 production build generated `/`, `/_not-found`, and `/rewrite` |
| `frontend` | `npm.cmd run test:e2e:launch-gate` | **31 passed** (24 browser workflow, 4 setup/build, 3 CSP checks); runner built and ran both development and production frontends and performed a live local rewrite |
| `backend` with temporary `DATABASE_URL=sqlite+aiosqlite:///...` and `STORAGE_ROOT` | `python -m alembic upgrade head`; `python -m alembic check` | Upgrade reached `d5e89a421b01`; check reported `No new upgrade operations detected.` The E2E independently applied the same chain to its temporary DB. |

The migration checks used a temporary database and storage directory and removed them afterward; the configured local `backend/resumind.db` was not migrated or used by the browser test.

## Reproduced defects fixed in this gate

- **Builder state disappeared after refresh.** The page created/restored the anonymous session but did not reload the saved resume and Builder document into the client view. Session-ready rehydration now requests the saved resume/export state and restores the Builder. The browser test saves, refreshes, and checks the saved title.
- **Experience and education could be lost or duplicated in Builder/export data.** PDF extraction represented date and label separators with a middle dot, but Builder conversion recognized only dash variants. The converter now handles the actual extracted separator, and `backend/tests/test_builder.py` includes parser-shaped experience and education regressions. PDF and DOCX content checks verify roles, bullets, dates, and degree/institution.
- **Diagnostic history warning could be omitted for a quick edit.** The report treated changes within a five-second window as simultaneous, hiding real edits made shortly after an assessment. It now compares the stored timestamps directly; `backend/tests/test_export.py` covers an updated Builder document and the historical-assessment notice.
- **Stale autosaves and backend failures were hard to interpret.** The Builder now surfaces the backend's version-conflict detail as an alert, and export/comparison network failures explain that the backend is unavailable and retryable. Browser checks reproduce stale two-tab edits and a stopped-backend request.
- **Offline AI rewrite interrupted the user with a browser dialog.** The rewrite handler used `alert()` for provider errors, blocking the editing workflow. It now renders the backend error inline in the affected suggestion, explains that the draft is unchanged and heuristic editing remains available, and allows retry after Ollama is ready. The browser regression check triggers the real offline 503, verifies there is no dialog, and confirms the draft is unchanged.
- **First live inference exceeded the 45-second timeout.** The initial local request returned HTTP 504 at the fixed timeout. The default generation timeout is now 120 seconds and the E2E wait is 180 seconds; the API was restarted with the new timeout. After confirming Ollama had unloaded the model, the browser gate completed cold-start generation, explicit acceptance, and restore.
- **Development React tooling was blocked by CSP.** The shared development/production policy omitted `'unsafe-eval'`, so React's development error overlay reported that `eval()` was unsupported. `next.config.ts` now adds the directive only when `NODE_ENV=development`; browser regression checks verify the development page renders without the error and the production header excludes the directive.

The final backend suite passed after these fixes: 144 passed. The focused Builder/export regression run passed 23 tests. The browser test's synthetic contact fixture was also corrected to use a LinkedIn URL matching its synthetic name, and exact URL extraction is asserted.

## Known limits and launch blockers

- **Controlled beta and public deployment are not ready or certified.** No hosting target, domain, TLS certificate, production PostgreSQL instance, backup plan, or protected production secrets are configured. HTTPS, exact frontend `CORS_ORIGINS`, production migrations, backups, proxy limits, monitoring, and resource limits still need deployment-specific setup. No public deployment or paid resource was created.
- The in-memory rate limiter resets on process restart and is suitable only for one API worker. A multi-worker or scaled deployment must use a trusted edge or shared limiter. The middleware does not trust forwarded IP headers by default.
- **Application-code hardening:** development CSP permits inline scripts and adds `unsafe-eval` for React debugging; production CSP omits `unsafe-eval` but still permits inline scripts and styles. The production inline allowances reduce CSP protection against some injection attacks; adopting a nonce-based policy requires an application rendering/configuration change and browser compatibility verification.
- **Deployment configuration:** set `SESSION_COOKIE_SECURE=true`, serve only over HTTPS, enable frontend HSTS at build time with `ENABLE_HSTS=true`, and set `CORS_ORIGINS` to the exact HTTPS frontend origin. Production configuration validation enforces secure cookies, `DEBUG=false`, enabled rate limits, PostgreSQL, and explicit HTTPS origins, but no real hosting environment was configured or exercised.
- **Request and upload limits:** the application enforces a 10 MB streamed upload limit plus file-type, DOCX expansion, and PDF page limits. A reverse proxy's body-size and request-time limits remain to be configured by the host.
- **Rate limiting:** the implemented limiter is process-local and resets on restart. It is adequate for a single API worker; multi-worker or scaled hosting requires a trusted edge limiter or shared store, and trusted proxy IP forwarding must be configured deliberately.
- **Database and backups:** PostgreSQL+asyncpg is required by production configuration and Alembic is available. A production PostgreSQL service, backup/restore procedure, and tested operational rollback are not present.
- **Secrets and deployment variables:** example files contain placeholders. Supply protected runtime secrets and deployment-specific API/database/CORS/storage settings through the selected hosting provider; no secret manager or production environment was configured.
- PDF/DOCX parsing runs in the API process; the parser is guarded by file and expansion/page limits but is not OS-sandboxed.
- Other local machines still need Ollama and the configured model installed. RESUMIND does not download models automatically or use a cloud fallback; here, Ollama 0.40.13 and `llama3.2:latest` were installed explicitly and the live browser rewrite/acceptance flow passed. On this machine the local backend uses a 120-second generation timeout to allow model startup.
- ATS scores and exports are heuristic aids. They do not guarantee employer parsing, ranking, or interview outcomes. Candidate-added claims are not independently verified.
- Session cleanup removes application data from the filesystem and database; it does not provide forensic secure erasure.

## Local Windows startup

From the repository root in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
if (-not (Test-Path frontend/.env.local)) { Copy-Item frontend/.env.example frontend/.env.local }
./scripts/setup-backend.ps1
$env:DEBUG = 'true'
./scripts/test-backend.ps1
./scripts/setup-frontend.ps1
```

Then use two PowerShell windows from the repository root:

```powershell
./scripts/start-backend.ps1
```

```powershell
./scripts/start-frontend.ps1
```

Open `http://127.0.0.1:3000`; API health is at `http://127.0.0.1:8000/api/health`. Setup applies Alembic migrations to the configured local database. Keep `.env` and `.env.local` private. See [`README.md`](../README.md) for environment options and troubleshooting.
