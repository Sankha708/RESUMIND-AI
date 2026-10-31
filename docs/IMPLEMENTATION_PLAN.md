# RESUMIND AI — Implementation Plan

> **Version:** 1.0.0 (Master Plan)  
> **Repository:** `D:\RESUMIND-AI`  
> **Development Model:** Phased, Test-Driven, Human-Gated

---

## 1. Architectural Strategy & Phasing Philosophy

Implementation is structured into **12 discrete, independently testable phases**. Each phase builds upon verified foundations and must satisfy its specific **Definition of Done (DoD)** and pass all automated tests before advancing.

### Core Governance Rules
1. **Human Approval Gates:** At the completion of each phase, the agent must present a summary of work, test coverage, and any architectural questions, then **stop for explicit user sign-off**.
2. **Never Claim Without Verifying:** No feature, security assertion, or score is marked as working or complete until verified via automated test output or verified browser execution.
3. **Synthetic Test Data Only:** All test fixtures, sample resumes, and job postings must use synthetic data with zero real personal information (PII).
4. **Preservation of Work:** File edits are surgical; no destructive resets, arbitrary overwrites, or dependency bloat.

---

## 2. Phase-by-Phase Execution Roadmap

```
Phase 0: Specifications & Architecture (baseline reference)
   │
   ▼
Phase 1: Project Scaffolding & Core Foundations
   │
   ▼
Phase 2: Cryptographic Anonymous Sessions & Ephemeral Storage
   │
   ▼
Phase 3: Frost & Chrome Design System & Frontend Shell
   │
   ▼
Phase 4: High-Fidelity Resume Parsing Engine (PDF & DOCX)
   │
   ▼
Phase 5: Extraction Review & Verification Studio (Screen 2)
   │
   ▼
Phase 6: Standalone ATS Readiness Engine & Dashboard (Screen 3)
   │
   ▼
Phase 7: Target Job Match & Evidence Matrix Engine (Screen 4)
   │
   ▼
Phase 8: AI Improvement & Rewrite Studio (Screen 5)
   │
   ▼
Phase 9: Resume Builder & Template Studio (Screen 6)
   │
   ▼
Phase 10: Export Engine (PDF, DOCX, & PDF Audit Report)
   │
   ▼
Phase 11: Differential Reanalysis & Delta Compare (Screen 7)
   │
   ▼
Phase 12: End-to-End Testing, Security Hardening, & Deployment
```

## Current Source Snapshot Status (verified 2026-10-30)

| Area | Source status |
| :--- | :--- |
| Product flows | Core product flows for Phases 0–11 are implemented; see the phase descriptions and [`LAUNCH_READINESS.md`](LAUNCH_READINESS.md). |
| Differential Reanalysis | Implemented behind `GET /api/reanalysis`; requires a fresh baseline and saved revision and is session-scoped. |
| Security and deployment | Application-level rate limits and baseline security headers are implemented. Production deployment, browser accessibility audits, shared multi-worker rate limiting, and deployment-specific controls remain outstanding. |
| Verification | The launch-readiness report records backend tests, frontend lint/type-check/build, isolated SQLite migrations, synthetic PDF/DOCX checks, visual PDF inspection, and the Playwright launch gate. Results are dated and are not a substitute for rerunning checks on a proposed release. |

These notes describe the documented source snapshot, not a production certification. See [`LAUNCH_READINESS.md`](LAUNCH_READINESS.md) for detailed historical checks, warnings, blockers, and local commands.

---

### Phase 0: Master Specifications & Governance *(Baseline reference)*
- **Objective:** Establish comprehensive technical documentation, architectural blueprints, design tokens, security policies, and agent instructions.
- **Inputs:** User requirements and vision directives.
- **Outputs:**
  - `AGENTS.md`
  - `docs/PRODUCT_SPEC.md`
  - `docs/IMPLEMENTATION_PLAN.md`
  - `docs/DESIGN_SYSTEM.md`
  - `docs/SECURITY.md`
  - `README.md`
  - `.gitignore`
- **Verification / Tests:** Visual inspection of document completeness, link validation, and syntax validation.
- **Definition of Done:** All 7 documents created, zero code/dependency bloat introduced, and user approval granted.

---

### Phase 1: Project Scaffolding & Core Foundations
- **Objective:** Establish the clean monorepo or adjacent backend/frontend structure with shared typing, test runners, and configuration.
- **Inputs:** Technical constraints (Next.js App Router, FastAPI, Python 3.11+, TypeScript, SQLite).
- **Target Structure:**
  - `/frontend`: Next.js (App Router, Tailwind CSS, TypeScript).
  - `/backend`: FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic.
  - `/tests`: Synthetic fixture directory (`tests/fixtures/resumes/`).
- **Outputs:**
  - Initialized backend with health-check endpoint (`GET /api/health`).
  - Initialized frontend with Next.js development server and base layout.
  - SQLite database initialized via initial Alembic migration.
  - Configured test runners (`pytest` for backend, `vitest`/`jest` for frontend).
- **Verification / Tests:**
  - `pytest` executes and passes backend health check test.
  - Frontend builds cleanly (`npm run build`) with zero TypeScript errors.
- **Definition of Done:** Both frontend and backend start cleanly in development mode; automated health tests pass.

---

### Phase 2: Cryptographic Anonymous Sessions & Ephemeral Storage
- **Objective:** Implement zero-login session architecture using cryptographically secure session IDs, HttpOnly cookies, and automatic data expiration.
- **Inputs:** Security specifications in [`SECURITY.md`](file:///D:/RESUMIND-AI/docs/SECURITY.md).
- **Outputs:**
  - FastAPI endpoints issue an HttpOnly cookie carrying a high-entropy opaque token (`resumind_session`); the database stores only its SHA-256 hash.
  - SQLAlchemy `Session` model (session ID hash, created_at, last_active, expires_at).
  - Isolated file storage manager (`storage/uploads/{session_id}/`).
  - Ephemeral background cleanup task purging expired session records and directories after 24 hours.
- **Verification / Tests:**
  - Pytest: Session creation generates high-entropy UUIDv4/hex token.
  - Pytest: Session isolation test proving Session A cannot read Session B files or records.
  - Pytest: Ephemeral purge job successfully deletes expired session directories and retains active ones.
- **Definition of Done:** Complete session lifecycle automated with 100% test coverage for session isolation and expiration.

---

### Phase 3: Frost & Chrome Design System & Frontend Shell
- **Objective:** Implement the visual foundation, theme provider, and primary navigation using Tailwind CSS, shadcn/ui primitives, and Motion.
- **Inputs:** Specifications in [`DESIGN_SYSTEM.md`](file:///D:/RESUMIND-AI/docs/DESIGN_SYSTEM.md).
- **Outputs:**
  - Design tokens configured in Tailwind (`pearl-canvas`, `primary-ink`, `chrome-silver`, `frosted-surface`, `steel-blue`).
  - Adaptive Light/Dark mode provider with glassmorphism surface utilities.
  - Reusable components: `Button`, `Card`, `Badge`, `ProgressRing`, `Modal`, `Toast`.
  - Landing Screen (Screen 1) shell featuring custom SVG "Translucent Resume Path" hero art and drag-and-drop dropzone.
- **Verification / Tests:**
  - Visual theme toggle test (Light to Dark transition without layout shifts).
  - Responsive layout test across mobile (375px), tablet (768px), and desktop (1280px).
  - WCAG contrast verification on all primary tokens.
- **Definition of Done:** Landing screen renders the Frost & Chrome aesthetic cleanly with functional file dropzone UI and zero console errors.

---

### Phase 4: High-Fidelity Resume Parsing Engine
- **Objective:** Build robust document parsers utilizing PyMuPDF and `python-docx` to extract text, structural blocks, and formatting metadata.
- **Inputs:** Uploaded synthetic PDF and DOCX files.
- **Outputs:**
  - Parser service layer: `PDFParser` (PyMuPDF) and `DocxParser` (`python-docx`).
  - Pydantic models for structured resume representation: `ParsedResume`, `WorkExperience`, `Education`, `SkillGroup`, `ContactInfo`.
  - Extraction diagnostics: font embedding status, multi-column detection flag, glyph integrity check.
- **Verification / Tests:**
  - Pytest suite using 4 synthetic resumes: standard single-column PDF, complex multi-column PDF, DOCX file, and corrupted file.
  - Assertion that phone, email, and dates are accurately extracted without truncation.
- **Definition of Done:** Parser handles both formats reliably, flags layout hazards, and rejects malformed/executable files gracefully.

---

### Phase 5: Extraction Review & Verification Studio (Screen 2)
- **Objective:** Create the two-pane extraction verification interface where users inspect original documents alongside editable extracted fields.
- **Inputs:** `ParsedResume` payload from backend parser.
- **Outputs:**
  - Screen 2 UI (`/review`) with document preview pane and structured form pane.
  - Inline editing capabilities for work history, skills, education, and dates.
  - API endpoint (`PUT /api/session/resume/verified`) to persist user corrections as the verified ground truth.
- **Verification / Tests:**
  - Frontend component tests verifying state updates on field edits.
  - Backend integration test confirming edited payload updates the session database accurately.
- **Definition of Done:** User can review extracted data, edit any field, add missing entries, and confirm the baseline without data loss.

---

### Phase 6: Standalone ATS Readiness Engine & Dashboard (Screen 3)
- **Objective:** Implement the transparent 5-dimension ATS Readiness scoring algorithm and interactive dashboard.
- **Inputs:** Verified resume data and layout diagnostics from Phase 4 & 5.
- **Outputs:**
  - Heuristic scoring engine calculating ATS Readiness Score (0–100) across File Integrity, Structure, Contact Info, Bullet Impact, and Length.
  - Actionable issue classifier categorizing items into Critical, Warning, and Optimization.
  - Screen 3 UI (`/readiness`) displaying score arc, dimensional gauges, and interactive remediation cards.
- **Verification / Tests:**
  - Unit tests validating score outputs against synthetic resumes (high-scoring vs. intentionally flawed formats).
  - Test ensuring scoring runs independently without any job description input.
- **Definition of Done:** Algorithmic scoring produces consistent, deterministic results; UI presents clear diagnostic findings with direct fix suggestions.

---

### Phase 7: Target Job Match & Evidence Matrix Engine (Screen 4)
- **Objective:** Implement the job description parser and requirement matching matrix with strict textual evidence citations.
- **Inputs:** Verified resume data and user-provided job posting text.
- **Outputs:**
  - Job parser extracting technical skills, domain responsibilities, experience levels, and certifications.
  - Matching engine scoring alignment (0–100) and categorizing each requirement as **Matched**, **Partially Supported**, or **Unsubstantiated Gap**.
  - Screen 4 UI (`/job-match`) rendering dual scores and the Three-Tier Requirement Matrix with verbatim resume citations.
- **Verification / Tests:**
  - Unit tests verifying that unmatched skills are strictly flagged as unsubstantiated (zero fabrication).
  - Integration test confirming that citations match exact source resume text.
- **Definition of Done:** Job match evaluation runs cleanly, displays exact evidence snippets for matches, and never hallucinates candidate experience.

---

### Phase 8: AI Improvement & Rewrite Studio (Screen 5)
- **Objective:** Implement the local AI rewriting engine using Ollama with transparent rationales and accept/reject/edit controls.
- **Inputs:** Flagged weak resume bullets and target job context (if available).
- **Outputs:**
  - Pluggable `LLMProvider` interface (with local `OllamaProvider` implementation and mock fallback provider for CI/CD).
  - Constrained prompts enforcing action-verb front-loading and metric placeholders (`[insert %]`) without fabricating data.
  - Screen 5 UI (`/rewrite`) featuring interactive rewrite cards with side-by-side original/revised comparison, rationale, and user action buttons.
- **Verification / Tests:**
  - Unit test verifying prompt constraints prevent hallucinated numbers and company names.
  - Mock provider tests verifying streaming response handling in FastAPI and Next.js.
  - UI test verifying that clicking `[Accept]` immediately updates the active resume state.
- **Definition of Done:** Bullet rewrites stream smoothly, adhere strictly to ethical guardrails, and grant users total editorial control.

---

### Phase 9: Resume Builder & Template Studio (Screen 6)
- **Objective:** Provide a real-time, responsive resume builder featuring one conventional ATS Professional template.
- **Inputs:** Verified and polished resume state.
- **Outputs:**
  - Screen 6 UI (`/builder`) with editable sections and live preview.
  - One conventional single-column **ATS Professional** template, used consistently for the builder, PDF, and DOCX exporters.
  - Content editing, section visibility/order controls, and saved draft persistence; obsolete multi-template and template-specific typography/margin controls are removed.
- **Verification / Tests:**
  - Visual regression tests verifying template rendering integrity at various zoom levels.
  - State persistence test verifying modifications sync to the backend session draft.
- **Definition of Done:** User can customize resume content in the single canonical template, with PDF/DOCX exports preserving the saved content.

---

### Phase 10: Multi-Format Export Engine & Diagnostic Audit Report
- **Objective:** Generate professionally formatted, ATS-oriented PDF and DOCX resumes, plus a separate PDF improvement audit report.
- **Inputs:** Finalized resume state and session evaluation metrics.
- **Outputs:**
  - Single-column vector/text-based PDF generator with selectable text and tested reading order on synthetic fixtures.
  - OpenXML DOCX generator producing native, uncorrupted Word documents.
  - Diagnostic PDF Improvement Report generator (executive summary, ATS audit breakdown, requirement match matrix, actionable checklist).
  - Screen 7 UI (`/export`) download hub.
- **Verification / Tests:**
  - Tests reopening generated PDF/DOCX files and checking expected content, text extraction, and reading order on synthetic fixtures.
  - File size and format integrity tests.
- **Definition of Done:** All three documents generate and download, open in supported document readers, and pass content/reading-order checks on test fixtures; universal ATS compatibility is not claimed.

---

### Phase 11: Reanalysis Engine & Differential Comparison (Export Center)
- **Objective:** Enable side-by-side delta comparison between the original uploaded resume and the finalized optimized version.
- **Inputs:** Baseline session snapshot and optimized session snapshot.
- **Outputs:**
  - Session-scoped API calculating score trajectories and changed sections from a stored baseline and saved Builder revision.
  - Export Center displays supported ATS and Job Match deltas, changed sections, and resolved report findings.
  - Safeguards: remain unavailable without a fresh baseline and saved revision; ignore template-only changes; do not mutate the original baseline; label unverified candidate-added claims.
- **Verification / Tests:**
  - Backend tests cover locked state, template-only changes, actual saved revision, baseline immutability, session isolation, and ATS/Job Match delta calculations.
- **Definition of Done:** Side-by-side comparison clearly displays the before-and-after transformation with accurate mathematical deltas.

---

### Phase 12: End-to-End Testing, Security Hardening, & Deployment Readiness
- **Objective:** Validate the entire platform via automated Playwright tests, execute accessibility audits, harden security configurations, and package for deployment.
- **Inputs:** Complete integrated application.
- **Outputs:**
  - Backend integration/unit suite, frontend lint/type-check/production build, and a reproducible Playwright launch gate.
  - Application-level rate limiting and baseline API/frontend security headers; deployment-specific controls still require a production environment.
  - Production build verification (`npm run build`) and isolated Alembic chain validation.
- **Verification / Tests:**
  - See the dated results in [`LAUNCH_READINESS.md`](LAUNCH_READINESS.md); rerun all checks against the release candidate.
  - Synthetic PDF/DOCX exports are reopened and checked for expected content and reading order; the report documents visual inspection of its generated fixture.
  - Public deployment, independent accessibility audits, concurrent-load privacy testing, production operations, and third-party security review remain unverified or not implemented.
- **Definition of Done:** Platform passes the agreed end-to-end tests, builds cleanly for production, and is ready for local deployment. This does not certify readiness for public hosting.
