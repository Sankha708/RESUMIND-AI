# RESUMIND AI — Security & Privacy Architecture

> **Version:** 1.1.0 (As-built snapshot)  
> **Status:** Source and test review updated 2026-10-30  
> **Repository:** `D:\RESUMIND-AI`

---

## 1. Security Architecture Principles

RESUMIND AI uses anonymous sessions and per-session storage. This document distinguishes controls present in the current source from controls still required before public deployment; passing unit tests is not a security certification.

> **Scope:** Verification described here is limited to source inspection and the synthetic automated tests listed below. Production deployment, live browser behavior, and third-party security review have not been performed.

---

## 2. Cryptographic Anonymous Sessions

### 2.1 Session Identifier Generation
- Anonymous sessions are identified by a 256-bit cryptographically secure pseudorandom token generated via Python's `secrets.token_urlsafe(32)` (or equivalent CSPRNG).
- The raw token is stored in an **HttpOnly, SameSite=Lax** cookie named `resumind_session`. `Secure` is configurable and defaults to false for local HTTP; production HTTPS configuration must enable it.
- In the database, the session token is hashed using SHA-256 (`session_hash = hashlib.sha256(token.encode()).hexdigest()`). The database never stores the plaintext session token, preventing token harvesting in the event of an unauthorized database snapshot read.

```
Browser Client                    FastAPI Middleware                SQLite / PostgreSQL
      │                                    │                                  │
      ├─── Initial Request (No Cookie) ───>│                                  │
      │                                    ├─ Generate 256-bit CSPRNG Token   │
      │                                    ├─ Compute SHA-256 Hash            │
      │                                    ├─ Create Session Record ─────────>│
      │<── Set-Cookie (HttpOnly, Secure) ──┤                                  │
      │    Cookie: resumind_session        │                                  │
```

### 2.2 Cookie Configuration Standards
The current defaults and production requirements are:
- `HttpOnly: true` (prevents access via client-side JavaScript, mitigating XSS token theft).
- `SameSite: Lax`.
- `Path: /` (the application default).
- `Secure: false` for local HTTP; set `SESSION_COOKIE_SECURE=true` behind HTTPS.
- `Max-Age: SESSION_TTL_HOURS` (default 24 hours, refreshed as a rolling inactivity expiry).

### 2.3 Strict Session Isolation
- Every database query must scope records by the active `session_id`.
- File storage paths are separated under `storage/uploads/{session_id}`, `storage/exports/{session_id}`, and `storage/reports/{session_id}`; resolved paths are checked to remain within their category root.
- Endpoints use the active opaque cookie token to resolve the session and scope stored records. The cookie is not signed; its random 256-bit token is matched by its SHA-256 database hash.
- Synthetic tests exercise cookie lifecycle, expiry, cleanup, path validation, and cross-session resume isolation. They do not certify all production configurations.

---

## 3. Ephemeral Lifecycle & Automated Data Purge

### 3.1 Session Expiration Policies
- **Inactivity Expiration:** The active session is extended on requests; it expires after `SESSION_TTL_HOURS` (default 24) without activity. There is no separate four-hour idle timeout or fixed 24-hour-from-creation hard expiry.

### 3.2 Scheduled Cleanup Task
- An automated asynchronous cleanup job runs periodically (e.g., every 60 minutes):
  1. Queries the database for sessions where `expires_at <= current_timestamp()` or the session is inactive.
  2. Identifies the associated directories under `storage/uploads/{session_id}`, `storage/exports/{session_id}`, and `storage/reports/{session_id}`.
  3. Deletes session-scoped directories and enclosed files using ordinary filesystem deletion (not forensic secure erasure).
  4. Deletes corresponding database records via cascading delete.
- In local development, this is implemented as an async background task within FastAPI. In containerized production, it runs as a dedicated cron or worker process.

---

## 4. File Upload Validation & Processing Safety

Uploading untrusted documents can exhaust parser resources. The current application applies the following checks; parsing runs in the API process and is not sandboxed:

```
 Incoming File Upload
         │
         ▼
 [Layer 1: Bounded streaming upload size (Max 10MB)]
         │ (Pass)
         ▼
 [Layer 2: Extension Whitelist (.pdf, .docx only)]
         │ (Pass)
         ▼
 [Layer 3: Magic Bytes Verification (%PDF- or PK\x03\x04)]
         │ (Pass)
         ▼
 [Layer 4: Filename Sanitization & Path Traversal Guard]
         │ (Pass)
         ▼
 [Layer 5: Guarded PyMuPDF / python-docx parsing]
```

### 4.1 Validation Rules
1. **File Size Limit:** FastAPI reads the upload in bounded chunks and rejects the body after 10 MB with `413`. A reverse-proxy request limit is not configured in this repository and must be set in deployment.
2. **File Extension Whitelist:** Only `.pdf` and `.docx` extensions are accepted. All other extensions are rejected with `400 Bad Request`.
3. **Magic Bytes Inspection:**
   - PDF files must begin with `%PDF-` (`0x25 0x50 0x44 0x46 0x2D`).
   - DOCX files must have a ZIP signature and contain both `[Content_Types].xml` and `word/document.xml`.
4. **Filename Sanitization:**
   - Raw user filenames are **never** used as storage paths.
   - Uploads are saved under the session's upload directory with a generated UUID filename.
   - This eliminates all path traversal vectors (`../`, null bytes, control characters).
5. **Parser Safeguards:**
   - PDF parsing rejects encrypted/corrupt documents and inputs exceeding 100 pages.
   - DOCX ZIP metadata is checked before python-docx parsing: at most 1,000 members, 50 MB total expanded size, 25 MB per member, and a 200:1 expansion ratio cap for members of at least 1 MB. Encrypted archive parts are rejected.
   - These checks bound common expansion cases but do not sandbox native/parser code; deploy with process/container resource limits and keep parsing dependencies patched.

---

## 5. Rate Limiting & Abuse Prevention

The FastAPI application applies in-process sliding-window limits:

| Request class | Limit | Key |
| :--- | :--- | :--- |
| API requests (excluding health, API docs, OpenAPI, and OPTIONS) | 60 per minute | Direct ASGI client IP |
| Resume uploads | 5 per 10 minutes | Direct ASGI client IP, in addition to the API limit |
| Improvement generation and AI rewrites | 10 per 5 minutes | SHA-256 of the session cookie; direct client IP when no cookie is present, in addition to the API limit |

Rejected requests receive `429`, `Retry-After`, and rate-limit headers. The in-memory key map is bounded to 10,000 keys and resets when the process restarts. The middleware does not trust `X-Forwarded-For`; behind a proxy, configure the server to accept forwarded client addresses only from explicitly trusted proxy IPs. This limiter is appropriate for one API worker. Multi-worker or scaled production deployments need equivalent enforcement at a trusted edge or shared limiter.

---

## 6. Secret Management & Zero-Leak Policy

- **Zero Hardcoded Secrets:** No API keys, database credentials, encryption salts, or tokens may exist in source code, commit history, or client bundles.
- **Environment Configuration:**
  - Local and production `.env` examples contain safe placeholders only (`backend/.env.example`, `backend/.env.production.example`, and `frontend/.env.production.example`).
  - Actual `.env` and `.env.local` files are strictly excluded via `.gitignore`.
- **Client-Side Boundary:** Next.js environment variables exposed to the browser must strictly use the `NEXT_PUBLIC_` prefix and contain **only** non-sensitive public configuration (e.g., API base URL).
- Production startup rejects debug mode, insecure/non-HttpOnly cookies, unsupported SameSite settings, disabled rate limits, SQLite, and non-HTTPS or wildcard CORS origins. Production must apply Alembic migrations before starting; automatic `create_all` is limited to non-production startup.

---

## 7. Production Hardening & Deployment Security

The source installs response headers, but production still needs HTTPS termination and deployment-specific review:
1. **Content Security Policy (CSP):** Next.js sends a policy derived from the configured API origin. Development mode also allows `unsafe-eval` for React's development debugging overlay; the production policy does not. Both modes currently allow inline scripts and styles for the existing application, which weakens CSP protection against some injection attacks; a nonce-based policy would require an application rendering change.
   ```http
   Content-Security-Policy: default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self' <configured-api-origin>
   ```
2. FastAPI and Next.js send `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, and a restrictive `Permissions-Policy`. API HSTS is enabled for production with secure cookies. Frontend HSTS requires `ENABLE_HSTS=true` at build time and must only be used when the frontend is served exclusively over HTTPS.
3. **CORS:** FastAPI allows credentials from the explicit `CORS_ORIGINS` list. Production validation rejects wildcard and non-HTTPS origins; set the exact frontend origin.
4. Set `SESSION_COOKIE_SECURE=true`, serve only over HTTPS, configure reverse-proxy upload/body and request-time limits, and keep the API/database/storage off public interfaces where possible.
5. Production deployments still need protected runtime secrets, PostgreSQL backups, tested migration/rollback procedures, process/container resource limits, monitoring, and a trusted proxy or shared rate limiter when using multiple API workers.

---

## 8. Verification Strategy & Test Assertions

The following table records current synthetic test coverage and open deployment controls. Passing tests do not establish security compliance:

| Test ID | Security Property Tested | Current evidence/status |
| :--- | :--- | :--- |
| **SEC-01** | Anonymous Session Token | Synthetic tests verify token/cookie lifecycle and SHA-256-backed lookup; no security certification. |
| **SEC-02** | Session Isolation | Synthetic API tests verify cross-session resume reads are denied. |
| **SEC-03** | Storage Path Safety | Tests reject unsafe session IDs; uploads use generated filenames. |
| **SEC-04** | File Validation | Synthetic tests cover signature mismatch, malformed files, 10 MB limit, DOCX expansion, and PDF page limit. |
| **SEC-05** | Expiry/Purge | Synthetic tests exercise expired session cleanup and storage removal. |
| **SEC-06** | Rate Limits | Synthetic middleware tests cover API exemptions, upload and AI quotas, hashed session keys, `429`, and `Retry-After`; multi-worker enforcement remains a deployment requirement. |
| **SEC-07** | Security Headers | Synthetic middleware tests cover API headers, HSTS gating, CORS preflight headers, and CSP is configured in Next.js; deployed proxy behavior and browser CSP compatibility remain unverified. |
