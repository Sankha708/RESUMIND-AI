# RESUMIND AI — Beginner Learning Roadmap

> Hands-on lessons that use **this actual project** as the classroom. Work through them in
> order. Each lesson tells you exactly which files to open, what to do, what you should see,
> and how to check yourself. No prior experience with React, FastAPI, SQL, or AI is assumed.

**How to use this document**

- Read one lesson, then **do the exercise** before moving on.
- Open files in your editor while reading; follow along.
- Keep a scratch note of answers to the 5 self-assessment questions at the end of each lesson.
- When stuck, see Part 17 of the
  [Complete Learning Guide](RESUMIND_AI_COMPLETE_LEARNING_GUIDE.md#17-testing-and-debugging).

---

## Level 1 — Application fundamentals

**Objective:** Understand what runs where and how a request travels.

**Concepts:** client, server, browser, HTTP request/response, port, JSON, process.

**Files to open**
- `README.md` (architecture table)
- `backend/app/main.py` (routes + middleware)
- `frontend/src/app/page.tsx` (top of file: `"use client"`, state)

**Study**
- Notice `app.include_router(...)` lines: each router is a feature.
- Notice `"use client"`: `page.tsx` runs in the browser.

**Exercise**
1. Start both servers (`./scripts/start-backend.ps1`, `./scripts/start-frontend.ps1`).
2. Open `http://127.0.0.1:8000/api/health`. You should see `{"status":"healthy",...}`.
3. Open `http://127.0.0.1:3000` and open the browser DevTools → Network tab.
4. Reload and find the `POST /api/session` request. Look at its **response headers**.

**Expected result:** you can identify a JSON response and a `Set-Cookie` header.

**Common mistakes**
- Opening `127.0.0.1` for one app and `localhost` for the other (breaks cookies).
- Forgetting the backend is a separate process from the frontend.

**Self-assessment**
1. What port is the backend on? 2. What port is the frontend on? 3. What file mounts the
routers? 4. Why does the frontend send `credentials: "include"`? 5. What does `/api/health` return?

---

## Level 2 — Python fundamentals used in the backend

**Objective:** Read and slightly modify Python code.

**Concepts:** modules, functions, classes, type hints, `async`/`await`, decorators,
exceptions, `with`.

**Files to open**
- `backend/app/services/storage_service.py` (small, readable)
- `backend/app/services/session_service.py`

**Study**
- `def validate_session_id(...)` and `raise StorageSecurityError(...)`.
- `async def create_session(...)` and `await db.flush()`.
- `@router.post(...)` in `backend/app/routers/session.py`.

**Exercise**
Add a temporary `print` (or `logging.info`) at the start of `create_session` and call
`POST /api/session` from `/api/docs` → watch the backend terminal. Remove it afterwards.

**Expected result:** You see one log line per new session.

**Common mistakes**
- Editing files while the server runs without reloading (use `--reload`, which the start
  script uses).
- Forgetting to remove debug prints.

**Self-assessment**
1. What does `await` do? 2. What is a decorator? 3. Where is the transport of a session token
hashed? 4. What exception is raised for an unsafe session id? 5. What is `Path(...).resolve()` for?

---

## Level 3 — React, Next.js, TypeScript fundamentals

**Objective:** Understand components, props, state, hooks, and the view machine.

**Concepts:** component, props, state, hooks (`useState`, `useEffect`, `useCallback`),
context, JSX, TypeScript union types.

**Files to open**
- `frontend/src/app/page.tsx`
- `frontend/src/context/SessionContext.tsx`
- `frontend/src/app/layout.tsx`

**Study**
- `type AppView = ...` and `useState<AppView>("upload")`.
- `useEffect(() => { ... }, [sessionLoading, backendOnline])`.

**Exercise**
Add a small read-only badge to `Header` showing `session ? "Session active" : "No session"`
(use `useSession()` from `SessionContext`). Verify it appears after load.

**Expected result:** The badge shows "Session active".

**Common mistakes**
- Calling `useSession()` outside the `SessionProvider` (it throws).
- Changing state directly instead of using the setter.

**Self-assessment**
1. What is a prop vs state? 2. What triggers a re-render? 3. Why `useCallback`? 4. Where is
`SessionProvider` mounted? 5. What does a TypeScript union type prevent?

---

## Level 4 — APIs and frontend↔backend communication

**Objective:** Trace a full request from a button click to a JSON response.

**Concepts:** REST, HTTP methods, status codes, CORS, cookies, error handling.

**Files to open**
- `frontend/src/app/page.tsx` (`runAssessment`, `handleSaveCorrections`)
- `backend/app/routers/assessment.py`
- `frontend/src/lib/api.ts`

**Study**
- `method`, `credentials`, `headers`, `body`.
- `if (!response.ok) throw ...`.

**Exercise**
In the browser, upload a synthetic resume, then click "Proceed". In DevTools → Network,
open the `POST /api/assessment` request and inspect the JSON response (`overall_score`,
`subscores`, `prioritized_findings`).

**Expected result:** You can read the score and findings directly from the API.

**Common mistakes**
- Ignoring the `response.ok` check.
- Expecting a value from a `fetch` without `await`ing it.

**Self-assessment**
1. What HTTP method saves corrections? 2. What status means validation failed? 3. What does
`getApiBaseUrl()` normalise? 4. What header carries the session? 5. Why check `res.ok` first?

---

## Level 5 — Database and ORM

**Objective:** Understand tables, relationships, and safe queries.

**Concepts:** table, primary key, foreign key, relationship, cascade, JSON column, query
scoping, migration.

**Files to open**
- `backend/app/models/session.py`
- `backend/app/models/resume.py`
- `backend/app/database.py`
- `backend/alembic/versions/`

**Study**
- `__tablename__`, `Mapped[...]`, `relationship(..., cascade="all, delete-orphan")`.
- `foreach review query: where(UploadedResume.session_id == session.id)`.

**Exercise**
Back up the DB, then copy it and inspect tables as shown in the Quick Reference. Confirm a
resume row has `structured_data`.

**Expected result:** You see the tables and row counts.

**Common mistakes**
- Querying without `session_id` scoping.
- Deleting the live DB instead of a copy.

**Self-assessment**
1. What is a cascade delete? 2. Where is `session_id` used? 3. What is a migration? 4. Why
avoid dumping `raw_text`? 5. What does `expire_on_commit=False` mean?

---

## Level 6 — Resume parsing and document processing

**Objective:** Follow extraction from bytes to structured profile.

**Concepts:** file signature, text layer, encoding, section detection, regex.

**Files to open**
- `backend/app/services/parser_service.py`
  (`parse_resume_document`, `extract_contact_info`, `_heading_prefix`, `_parse_skill_categories`)

**Study**
- The order: validate → extract → normalise → structure.
- Where warnings are appended (`"No distinct education section header was recognized."`).

**Exercise**
Upload the synthetic fixture from `backend/tests/synthetic_generator.py` (or any text-based
PDF). Open DevTools → Network and inspect `structured_data` in the upload response.

**Expected result:** Contact, skills, and experience fields are populated; some warnings may
appear.

**Common mistakes**
- Expecting scanned PDFs to parse (they yield little text).
- Assuming headings are always exact.

**Self-assessment**
1. What function is the entry point? 2. What is signature validation for? 3. Why is encoding
normalised? 4. What happens to unlabelled skills? 5. Where do unusual headings go?

---

## Level 7 — ATS scoring and NLP concepts

**Objective:** Compute a score by hand and reproduce it in code.

**Concepts:** weighted sum, ratio, regex metrics, deterministic heuristics.

**Files to open**
- `backend/app/services/scoring_service.py` (`WEIGHTS`, each `evaluate_*`, `calculate_ats_score`)

**Study**
- The bullet-impact point bands (40/30/20/10).
- The overall weighted sum.

**Exercise**
Run `POST /api/assessment` for a resume. Open `report_data.subscores`, note each
`score`/`weight`/`weighted_score`, and verify the sum equals `overall_score`.

**Expected result:** Your arithmetic matches the API (within rounding).

**Common mistakes**
- Forgetting that scores are rounded per dimension first.
- Mixing ATS Readiness with Job Match.

**Self-assessment**
1. What are the five weights? 2. How is `bullet_impact` action-verb score computed? 3. What
happens with no bullets? 4. Is the score random? 5. Does it depend on a job description?

---

## Level 8 — LLM integration and grounding

**Objective:** Understand the provider abstraction and the safety check.

**Concepts:** interface/ABC, HTTP client, JSON contract, temperature, grounding, prompt
injection.

**Files to open**
- `backend/app/providers/base.py`
- `backend/app/providers/ollama_provider.py`
- `backend/app/providers/grounding.py`
- `backend/app/providers/prompts.py`

**Study**
- `check_health()` → `/api/tags`.
- `inspect_grounding`: `unsupported_numbers = new_numbers - orig_numbers`.

**Exercise**
With Ollama running and a model installed, generate an improvement, trigger a rewrite, and
inspect the returned `potential_new_claims`. Stop Ollama and retry: confirm a clean error,
while rule-based suggestions still work.

**Expected result:** Rewrites appear with a proposal; offline you get a clear status message.

**Common mistakes**
- Assuming a mock provider test proves the live model works.
- Expecting auto-accept (never happens).

**Self-assessment**
1. What methods define a provider? 2. Why `format="json"`? 3. What sets
`needs_user_verification`? 4. What is prompt injection and how is it guarded? 5. What is the
fallback when Ollama is down?

---

## Level 9 — PDF and DOCX generation

**Objective:** See how a saved Builder document becomes a downloadable file.

**Concepts:** page geometry (points), fonts, line wrapping, pagination, document structure.

**Files to open**
- `backend/app/services/pdf_export_service.py`
- `backend/app/services/docx_export_service.py`

**Study**
- `PAGE_WIDTH/PAGE_HEIGHT` and the font map.
- Where text is inserted and wrapped.

**Exercise**
Save a Builder document, then hit `GET /api/export/resume/pdf` and open the file. Also fetch
`.../docx` and open it in Word or `python-docx`. Re-extract the PDF text with PyMuPDF and
compare it to the Builder content.

**Expected result:** Selectable PDF text and a valid, editable DOCX.

**Common mistakes**
- Exporting with empty content (returns 422).
- Using a stale `version` (returns 409).

**Self-assessment**
1. What library makes the PDF? 2. What is the page size? 3. Why is selectable text
important? 4. What makes the DOCX ATS-friendly? 5. What protects against stale exports?

---

## Level 10 — Security, debugging, and testing

**Objective:** Understand the protections and how to verify them.

**Concepts:** hashing, HttpOnly, SameSite, CORS, rate limiting, path traversal, isolation,
tests.

**Files to open**
- `backend/app/services/session_service.py`
- `backend/app/middleware/security.py`
- `backend/app/services/storage_service.py`
- `backend/tests/` (session isolation, security, config tests)

**Study**
- `hashlib.sha256(token...)`.
- `is_relative_to(root)` traversal check.
- `SlidingWindowRateLimiter.check`.

**Exercise**
Run `./scripts/test-backend.ps1`. Then send rapid requests to a rate-limited endpoint and
observe a `429` with `Retry-After`.

**Expected result:** Tests pass; the limiter returns 429.

**Common mistakes**
- Thinking `Secure` cookies work over plain HTTP locally.
- Assuming rate limiting scales across workers.

**Self-assessment**
1. Why store only the hash? 2. What stops path traversal? 3. What does SameSite=Lax do? 4.
Why is the limiter single-worker? 5. Which tests prove isolation?

---

## Level 11 — Architecture and independent maintenance

**Objective:** Make a safe change end-to-end and explain the architecture.

**Concepts:** separation of concerns (router/service/model/schema), versioning, migration,
regression testing.

**Files to open**
- Any router + its service + its model + its schema (pick one feature).

**Exercise**
Make a small, safe change (for example, adjust a wording string in a scoring finding),
run the backend tests, and confirm nothing regresses. Then revert the change with Git.

**Expected result:** Tests still pass and you understand the change's blast radius.

**Common mistakes**
- Editing a model without a migration.
- Skipping the test run.

**Self-assessment**
1. What is a router's job? 2. What is a service's job? 3. When do you need a migration? 4.
How do you verify a change? 5. Where would you add a new feature?

---

## Suggested weekly plan

| Week | Lessons | Focus |
| :--- | :--- | :--- |
| 1 | 1–2 | Understand and run the app, basic Python |
| 2 | 3–4 | Frontend and API communication |
| 3 | 5 | Database and ORM |
| 4 | 6–7 | Parsing and scoring |
| 5 | 8–9 | AI and document generation |
| 6 | 10–11 | Security, testing, and maintenance |

## Milestones

- **Milestone A:** Explain the request lifecycle (Part 6.2) without notes.
- **Milestone B:** Compute an ATS score by hand and verify it against the API.
- **Milestone C:** Explain grounding and why it matters.
- **Milestone D:** Make one safe code change, test it, and revert it cleanly.
- **Milestone E:** Give the 5-minute architecture demonstration (Part 19.1).
