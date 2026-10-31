# RESUMIND AI — Technical Glossary

> Plain-language definitions of the terms used throughout the RESUMIND AI codebase and
> documents. Each entry explains the idea and, where useful, points to where it appears in
> this project.

## A

**ABC (Abstract Base Class)** — A Python class that defines required methods without
implementing them. `LLMProvider` in `providers/base.py` is an ABC; concrete providers must
implement `check_health` and `generate_rewrite`.

**Alembic** — A database migration tool for SQLAlchemy. It applies versioned schema changes
(`alembic upgrade head`). Lives in `backend/alembic/`.

**Anonymisation / anonymous session** — Using a temporary, random identity instead of a
login. RESUMIND AI mints a random token per browser and stores only its hash.

**API (Application Programming Interface)** — A defined way for programs to talk to each
other. Here, the FastAPI HTTP API under `/api/*`.

**Async / await** — Python keywords for non-blocking operations. `async def` marks a
coroutine; `await` pauses it until the awaited I/O finishes, letting the server serve other
requests (used throughout the backend).

**ATS (Applicant Tracking System)** — Software employers use to receive, parse, and filter
resumes. RESUMIND AI measures *readiness* for such systems, not employer outcomes.

**ATS Readiness** — A 0–100 heuristic score of how machine-parseable and well-structured a
resume is. Computed by `scoring_service.py`. Distinct from Job Match.

**auth / authorization vs authentication** — Authentication proves *who* you are;
authorization decides *what* you may access. RESUMIND AI has no login; it uses a session
token for identification only.

## B

**Bearer / cookie token** — A token that grants access to a session. RESUMIND AI stores it in
an HttpOnly cookie named `resumind_session`.

**Blocking I/O** — Code that waits without yielding (e.g. synchronous file writes). In async
handlers this can tie up the event loop; noted as a limitation.

## C

**CASCADE (delete)** — A database rule where deleting a parent row also deletes its child
rows. Sessions cascade to resumes, assessments, etc.

**CSP (Content Security Policy)** — A browser security header restricting what scripts/styles
may run. The frontend sets one; inline scripts are currently allowed (hardening pending).

**CORS (Cross-Origin Resource Sharing)** — Browser rules for requests between different
origins (e.g. frontend `:3000` → API `:8000`). Configured in `main.py` via
`CORSMiddleware` and `settings.cors_origin_list`.

**Coroutine** — A function defined with `async def`. Calling it returns an object you must
`await` (or schedule with `asyncio.create_task`).

**CSRF (Cross-Site Request Forgery)** — An attack where another site triggers actions using
your cookies. RESUMIND AI relies on `SameSite=Lax`; there is no separate CSRF token.

**Cookie / HttpOnly** — A small key-value the browser stores and sends automatically.
`HttpOnly` hides it from JavaScript. `Secure` limits it to HTTPS. `SameSite` limits
cross-site sending.

**Cyclic / cyclic dependency** — Modules importing each other. Avoided here by a strict
direction: routers → services → models/schemas.

## D

**Declarative Base (`Base`)** — The SQLAlchemy base class all ORM models inherit
(`database.py`). It collects table definitions.

**Dependency injection (FastAPI `Depends`)** — Framework-provided values passed into a
handler, e.g. `db: AsyncSession = Depends(get_db)`.

**Deterministic** — Produces the same output for the same input every time. The scoring
engines are deterministic (no randomness, no model).

**DOCX** — Microsoft Word's XML-based document format. Read/written with `python-docx`.

**Domain competencies** — Higher-level skill areas (e.g. distributed systems, security &
auth) matched in Job Match.

## E

**Endpoint** — A specific API URL + method, e.g. `POST /api/resume/upload`.

**Ephemeral storage** — Temporary files deleted later. RESUMIND AI stores uploads/exports
under `storage/{category}/{session_id}/` and purges them via cleanup.

**Enum / union type** — A type limited to specific values. In TypeScript, `AppView` is a union
of view names.

**Environment variable** — A configuration value provided by the OS or a `.env` file
(`config.py` reads these).

**Exception hierarchy** — A family of error classes. `LLMProviderError` is the base for
`OllamaUnavailableError`, `ModelNotFoundError`, `OllamaTimeoutError`, etc.

## F

**FastAPI** — A Python web framework for async APIs with automatic validation and OpenAPI docs.

**Foreign key (FK)** — A column referencing another table's primary key (e.g. `resume_id` →
`uploaded_resumes.id`).

**Frontend / backend** — Frontend is the browser app (Next.js here); backend is the server API
(FastAPI here).

## G

**Grounding** — Ensuring generated text stays faithful to source facts. `grounding.py` flags
any number or date in a rewrite that was not in the original bullet.

**Grounded evidence / verbatim snippet** — An exact quote from the resume proving a match.
The job matcher only returns snippets that are literal substrings of the resume.

## H

**Hash / SHA-256** — A one-way fingerprint of data. The raw session token is hashed with
SHA-256; only the hash is stored and looked up.

**Heuristic** — An approximate rule-of-thumb method. ATS Readiness and Job Match are heuristics.

**HSTS** — An HTTP security header forcing HTTPS; enabled only in production with secure cookies.

## I

**idempotent** — Safe to repeat with the same effect. Session cleanup and normalisation are
idempotent.

**Index** — A database structure that speeds lookups (e.g. `token_hash`, `expires_at`).

**In-process rate limiter** — Counting requests inside the app process. Works for one worker;
multiple workers need a shared store or edge limiter.

**Integration test** — A test exercising several parts together (router + service + DB).

## J

**JD (Job Description)** — The posting text matched against the resume in Job Match.

**JSON** — Text data format for API bodies (`{"key": "value"}`). Stored in JSON columns for
structured profile and reports.

**Job Match** — A 0–100 heuristic of textual overlap between resume and a specific posting.
Distinct from ATS Readiness.

## L

**Lifespan** — FastAPI startup/shutdown hook. `main.py` uses it to create tables (dev) and to
schedule session cleanup.

**LLM (Large Language Model)** — A model that generates text. RESUMIND AI optionally uses a
local Ollama model for rewrite proposals.

**LLMProvider** — The project's abstraction over any LLM (`providers/base.py`).

**Lint / ESLint** — Static code-quality checks. `npm run lint` runs ESLint on the frontend.

## M

**Middleware** — Code wrapping every request and response (rate limiting, CORS, headers).

**Migration** — A versioned, repeatable schema change (Alembic).

**Mock provider** — A fake LLM used in tests (`set_provider_override`) so tests are
deterministic and need no Ollama.

**Model (ORM) vs model (LLM)** — An ORM model is a Python class mapped to a table
(`models/*.py`). An LLM model is a neural network like `llama3.2`. Context disambiguates.

## N

**Next.js / App Router** — The React framework. App Router uses files under `src/app/` as
routes (`layout.tsx`, `page.tsx`).

**Normalisation (text)** — Cleaning characters/whitespace so parsing is consistent
(`normalize_text_encoding`).

**NLP (Natural Language Processing)** — Computational handling of text. Here it is largely
rule/regex-based, not deep learning.

## O

**Ollama** — A local server that runs open LLMs over HTTP (`localhost:11434`). Optional here.

**On-delete cascade** — The SQL rule behind the ORM cascade; deleting a session removes its
rows.

**OpenAPI** — A machine-readable API description; FastAPI serves it at `/api/openapi.json`
and interactive docs at `/api/docs`.

**Optimistic concurrency** — Writing only if the version matches what you last saw; otherwise
409. Used when saving the Builder document.

**ORM (Object-Relational Mapper)** — Maps Python classes to database tables. SQLAlchemy is
the ORM here.

## P

**Pagination** — Splitting content across multiple pages (the PDF generator paginates).

**Path traversal** — An attack using `../` to escape a directory. Prevented by validating
session IDs and checking `is_relative_to`.

**PDF (Portable Document Format)** — Fixed-layout document format. Generated here with
PyMuPDF, with selectable text.

**PII (Personally Identifiable Information)** — Data that identifies a person. Tests use only
synthetic data; real resumes are never committed.

**Primary key (PK)** — The unique identifier of a row (UUID string in this project).

**Prompt** — Instructions given to an LLM. `prompts.py` defines the system instruction and
user message; version `1.0.0`.

**Prompt injection** — Malicious instructions hidden in input text. The prompt marks resume/JD
text as untrusted and forbids following embedded instructions.

**Pydantic** — A Python library for typed data validation; all request/response schemas use it.

**PyMuPDF (`fitz`)** — A PDF library used for text extraction and PDF generation.

**pytest / pytest-asyncio** — The backend testing tools (async-aware).

## Q

**Query scoping** — Filtering every database query by the current session's id to enforce
isolation.

## R

**Rate limiting** — Restricting how many requests a client can make in a time window (429 when
exceeded).

**Reanalysis** — Comparing a saved baseline assessment to a later Builder revision, producing
deltas (only when genuine content changes exist).

**REST** — An API style using resources and HTTP verbs (GET/POST/PUT/DELETE).

**Rollback** — Undoing uncommitted database changes; `get_db` rolls back on exceptions.

**Router (FastAPI)** — A module grouping related endpoints (one per feature).

## S

**Schema (Pydantic)** — A class defining validated input/output shape (the `schemas/` folder).

**Scope (request hooks/state)** — In React `useEffect`, the dependency array controls when an
effect re-runs.

**Session** — A temporary identity plus its data. Here: `anonymous_sessions` row + cookie.

**SameSite** — Cookie attribute limiting cross-site sending (`Lax` here).

**Sliding window** — A rate-limit technique counting requests in the last N seconds.

**SQL** — The language for relational databases. SQLAlchemy generates SQL from Python.

**SQLAlchemy** — The Python ORM/SQL toolkit used with async sessions.

**SQLite** — A file-based relational database used locally (`resumind.db`).

**Stateless vs stateful** — Stateless endpoints keep no memory between requests; RESUMIND AI
is *stateful per session* via the database and cookie.

## T

**Test fixture** — Reusable test setup (temporary DB, synthetic files, mock provider).

**Token** — A secret string proving a session. Generated with `secrets.token_urlsafe(32)`.

**Transaction** — A group of database changes committed together or rolled back.

**TSX** — TypeScript + JSX files for React components (`*.tsx`).

## U

**Upload validation** — Checking extension, size, and signature before parsing (rejects
mismatches, oversize files, and bombs).

**UUID** — A universally unique identifier; used as primary keys.

## V

**Verbatim** — Exactly as written. Grounded evidence must be a verbatim substring of the source.

**Version (document version)** — A monotonic integer on the Builder document used for
optimistic concurrency; also used to reject stale exports.

## W

**WCAG** — Web Content Accessibility Guidelines. The spec targets AA; a formal audit is not
recorded.

**WebSocket / streaming** — Not used for AI here; the Ollama call is non-streaming
(`stream: false`) and returns complete JSON.

## X / Y / Z

**XSS (Cross-Site Scripting)** — Injecting scripts into pages. HttpOnly cookies and React
escaping reduce exposure; CSP hardening is pending.

**YAML** — A human-readable config format (used by tooling, not core app config).

**Zero-hallucination guardrail** — The combined defences against inventing facts: a prompt
that forbids invention, a JSON output contract, and the grounding check that flags new
numbers/dates.
