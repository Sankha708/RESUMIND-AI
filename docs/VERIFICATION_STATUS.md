# RESUMIND AI — Historical Verification Status (Superseded)

> This file records an earlier packaged-source audit. Its blockers and results below do not describe the current workspace. The authoritative current verification record is [`LAUNCH_READINESS.md`](LAUNCH_READINESS.md), updated 2026-10-30.

This document records checks performed on the packaged source in the audit environment. It distinguishes passed checks from checks that still require the target Windows environment.

## Verified on the packaged source

- `python -m compileall -q app tests` — passed.
- `PYTHONPATH=. python -m pytest -q tests/test_resume_pipeline_regressions.py` — 4 passed.
- Synthetic resume parse/build regression checks cover section aliases, continuation lines, categorized skills, certifications, CGPA, and contact extraction.
- Synthetic PDF and DOCX generation was exercised by the regression suite; content was reopened/extracted and placeholder labels were checked.
- Rendered synthetic PDF pages were visually inspected.
- The test-fix patch is integrated into this archive: the end-to-end test expects the canonical `ats_professional` template; the outdated all-templates test is replaced with a populated single-template export test and a blank-document rejection test.
- Archive contents exclude local databases, virtual environments, dependency folders, `.env` secrets, Python caches, and test output folders.

## Not verified in this environment

- The full backend suite could not be collected because `aiosqlite` is not installed here and package download access is unavailable. The project's `backend/requirements.txt` includes `aiosqlite`.
- Frontend TypeScript/lint/production build could not be run because frontend dependencies were not installed in this environment and the npm registry is unreachable here.
- Real browser upload/cookie flow, live Ollama inference, and deployment have not been verified.
- Existing local Builder records are not automatically repaired. Review any saved document and back up its database before modifying existing data.
- The proposed Differential Reanalysis screen/engine is not included in this source snapshot.

## Required Windows release gates

From the project root, run `scripts\setup-backend.ps1`, then `scripts\test-backend.ps1`. Run `scripts\setup-frontend.ps1`. Start the services with `scripts\start-backend.ps1` and `scripts\start-frontend.ps1` in separate PowerShell terminals.

Before public deployment, also verify HTTPS and secure cookies, production origins/CORS, secret management, resource limits, live local/remote Ollama architecture, and end-to-end browser upload plus PDF/DOCX downloads.

**Current readiness classification: local verification candidate, not yet certified production-ready.**
