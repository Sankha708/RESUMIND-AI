# RESUMIND AI — Agent Operating Guidelines

> **Target Workspace:** `D:\RESUMIND-AI`  
> **Coding Agent Standard:** Google Antigravity Agent  
> **Status:** Active Project Governance Protocol

---

## 1. Prime Directives for All Development Phases

1. **Strict Phase Gate Adherence**
   - Implement **ONLY** the currently approved phase specified by the user.
   - Do **NOT** skip ahead, pre-implement components for future phases, or introduce architectural drift.
   - At the conclusion of every phase:
     1. Summarize all files created, modified, or verified.
     2. Report test results accurately (passes, failures, skips, and unverified items).
     3. State open questions or architectural decisions requiring human feedback.
     4. **STOP and await explicit user approval** before proceeding to the next phase.

2. **Context & Specification First**
   - Before writing or modifying any code, **read this file (`AGENTS.md`)** and the relevant design/product specifications in `/docs`:
     - [`PRODUCT_SPEC.md`](file:///D:/RESUMIND-AI/docs/PRODUCT_SPEC.md)
     - [`IMPLEMENTATION_PLAN.md`](file:///D:/RESUMIND-AI/docs/IMPLEMENTATION_PLAN.md)
     - [`DESIGN_SYSTEM.md`](file:///D:/RESUMIND-AI/docs/DESIGN_SYSTEM.md)
     - [`SECURITY.md`](file:///D:/RESUMIND-AI/docs/SECURITY.md)
   - Inspect specific relevant files directly. Avoid exhaustive directory re-scans, unneeded multi-file dumps, or redundant subagent invocations.

3. **Workspace Integrity & Non-Destructive Operations**
   - Preserve existing work, tests, documentation, and Git history.
   - **NEVER** run destructive commands (`git reset --hard`, `rm -rf`, dropping tables without migration tests, deleting production files, or force-pushing).
   - If a file needs alteration, use targeted file edits rather than sweeping wholesale rewrites whenever possible.

4. **Security, Secrets, & Privacy**
   - **NEVER** print, log, commit, or request API keys, credentials, tokens, or private environment variables.
   - Use `.env.example` templates with sanitized dummy placeholder values.
   - Respect user privacy: Anonymous sessions are isolated. Resumes, parsed tokens, and user inputs are strictly scoped to the active session and scheduled for automatic ephemeral purging.
   - Never claim security properties are verified before automated or manual tests have concretely proven them.

5. **Free-First & Local-First Philosophy**
   - Local development must **NEVER** require paid APIs, credit cards, or proprietary cloud databases.
   - AI interactions must default to a local or self-hosted provider (e.g., **Ollama** running locally) via a clean, replaceable provider interface.
   - Local database must use **SQLite** (via SQLAlchemy & Alembic), migrating smoothly to **PostgreSQL** in production environments.
   - Clearly document that free tier hosting and self-hosted AI models have practical capacity and latency limits; never promise unlimited free production inference.

6. **Truthful AI & Ethical Scoring Guardrails**
   - **Zero Hallucination Tolerance:** The platform must **NEVER** fabricate, infer, or embellish qualifications, job titles, dates, certifications, employers, metrics, or experiences that are not grounded in the user's resume or verified inputs.
   - **ATS vs. Job Match Clarity:** Distinctly decouple general **ATS Readiness** (formatting, machine readability, structural hygiene) from **Job Match Fit** (semantic alignment with a specific job description).
   - **No False Guarantees:** Never guarantee an employer's ATS outcome, ranking, or an interview invitation. All recommendations must be framed as heuristic improvements and guidance.
   - When suggesting rewrites, always display:
     - Original source bullet / sentence.
     - Proposed revision.
     - Rationale explaining the enhancement (e.g., active verb, quantifiable impact).
     - Explicit user controls: **Accept**, **Reject**, or **Edit**.

7. **Test Discipline & Authentic Reporting**
   - Use **synthetic test data** exclusively for automated tests, unit suites, and UI previews. Never use real personally identifiable information (PII).
   - Run focused tests (unit, lint, type-check, and integration) appropriate to the phase.
   - **Report all test outcomes honestly:** Never fabricate test results, hide warnings, suppress linter errors with blanket disables, or claim a phase is complete if tests are failing or skipped.

---

## 2. Fixed Technology Stack

The project technology choices are locked and must be respected across all implementation phases:

| Layer | Technology | Key Constraints |
| :--- | :--- | :--- |
| **Frontend Framework** | Next.js (App Router), React 19 / latest stable, TypeScript | Strict type checking, server/client boundary discipline |
| **Styling & Components**| Tailwind CSS, shadcn/ui, Radix UI primitives | Strict adhesion to the *Frost & Chrome* design tokens; no ad-hoc Tailwind colors |
| **Animation / Motion**  | Motion (formerly Framer Motion) | Subtle micro-interactions; realistic glass and metallic sheen transitions |
| **Backend API**         | Python 3.11+, FastAPI, Pydantic v2 | Async endpoints, typed schemas, strict upload validation |
| **Database & ORM**      | SQLAlchemy 2.0 (async), Alembic | SQLite for local development (`resumind.db`); PostgreSQL dialect compatibility |
| **Resume Parsing**      | PyMuPDF (`fitz`), `python-docx` | Native text extraction, formatting detection, structural block parsing |
| **AI Layer**            | Ollama via an abstract `LLMProvider` interface | Pluggable interface (`generate`, `stream`, `analyze`); no hardcoded vendor lock-in |
| **Testing Suite**       | `pytest` (backend), Vitest/Jest + Playwright (frontend) | Synthetic fixtures, deterministic mocking of LLM provider |

---

## 3. Design System Alignment (*Frost & Chrome*)

All UI components and layouts must conform to [`DESIGN_SYSTEM.md`](file:///D:/RESUMIND-AI/docs/DESIGN_SYSTEM.md):
- **Pearl Canvas:** `#F3F5F6` (light) / Deep Obsidian `#0E1013` (dark)
- **Primary Ink:** `#181A1D` (light) / Crisp Off-White `#F0F2F5` (dark)
- **Chrome Silver:** `#9CA6B2` (neutral accents, subtle borders)
- **Frosted Surface:** `#D9E0E6` (translucent backdrop with backdrop-blur)
- **Steel Blue:** `#5477B8` (intentional focus states, active badges, highlights)
- **Prohibited:** No neon/electric-lime palettes, no generic AI orb animations, no cluttered low-contrast dashboards, and no illegible heavy blur effects.
- **Exported Resumes:** While the web interface is atmospheric and styled with liquid glass, **all exported PDF and DOCX documents must be crisp, minimalist, high-contrast, and strictly ATS-friendly** (single-column or ATS-safe tables, standard margins, clear standard section headers).

---

## 4. Phase Workflow & Communication

Whenever starting or finishing work:
1. State the current active phase.
2. Outline specific steps being taken.
3. Verify changes with tests or linters.
4. Provide a clear summary with direct file links using Markdown `file:///` format.
5. Halt for user confirmation before proceeding to subsequent numbered phases.
