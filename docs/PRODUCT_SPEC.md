# RESUMIND AI — Product Specification

> **Version:** 1.0.0 (Master Draft)  
> **Status:** Phase 0 Architecture Blueprint  
> **Target Platform:** Web (Desktop & Mobile Responsive)  
> **Repository:** `D:\RESUMIND-AI`

---

## 1. Executive Summary & Product Vision

**RESUMIND AI** is a privacy-first, no-login AI resume optimization and document crafting platform designed for modern professionals. The platform empowers job seekers to transform their raw career documents into high-impact, applicant tracking system (ATS) compliant resumes tailored precisely to target roles without compromising their privacy or signing up for recurring subscriptions.

Unlike existing tools that trap users behind paywalls, harvest personal resumes, fabricate credentials, or obscure their scoring formulas behind deceptive "instant hire" percentages, RESUMIND AI operates on three core principles:
1. **Zero Login Friction:** Users immediately access the full evaluation and editing suite via cryptographically secure, isolated anonymous sessions.
2. **Absolute Ethical Grounding:** The system strictly optimizes existing evidence. It **never fabricates** job titles, employers, dates, metrics, skills, or experiences.
3. **Decoupled Evaluation Dimensions:** Machine readability and parsing hygiene (**ATS Readiness**) are strictly separated from role alignment (**Job Match Fit**), preventing false confidence.

---

## 2. Target Personas & Core Use Cases

### 2.1 Target Personas
- **The Career Transitioner:** Needs to understand how their transferable achievements map to unfamiliar job requirements and identify unsubstantiated skill claims.
- **The Active Applicant:** Frustrated by automated rejections, seeking concrete technical validation that their resume is cleanly parseable by modern corporate ATS engines (Workday, Greenhouse, Lever, Taleo).
- **The Modernizer:** Possesses an outdated, poorly formatted resume and wants a refined, modern presentation without fighting brittle word-processor formatting or breaking ATS readability.

### 2.2 Core Use Cases
- Evaluating a standalone resume for parser-friendliness, structure, and impact without providing a job description.
- Comparing a verified resume against a target job description to pinpoint hard requirement gaps with verbatim textual evidence.
- Polishing bullet points with active verbs and quantifiable business impact using transparent AI rewrites with granular accept/reject/edit controls.
- Exporting ATS-compliant PDF/DOCX resumes alongside an executive-ready diagnostic PDF improvement report.
- Performing differential re-analysis between the original resume and the optimized revision.

---

## 3. End-to-End User Journey (10-Step Flow)

```
 [1. Upload] ──> [2. Extraction Review] ──> [3. ATS Readiness Analysis]
                                                      │
         ┌────────────────────────────────────────────┴────────────────────────────────────────┐
         │ (Optional Job Description Flow)                                                     │ (Skip JD Flow)
         ▼                                                                                     ▼
 [4. Target JD Input] ──> [5. Role Match & Evidence] ──> [6. AI Rewrite Studio] ──> [7. Resume Builder Studio]
                                                                                               │
                                                               ┌───────────────────────────────┴─────────────────┐
                                                               ▼                                                 ▼
                                                  [8. PDF / DOCX Resume Download]               [9. PDF Improvement Report]
                                                               │
                                                               ▼
                                               [10. Differential Reanalysis & Delta Compare]
```

### Step 1: Upload PDF or DOCX Resume
- User arrives at the clean, atmospheric landing screen and drops their current resume (PDF or DOCX, max 10MB).
- Session cookie is minted in the background (HttpOnly, Secure, SameSite=Lax).
- Document is validated for magic bytes, MIME type, and non-corrupt structure before being staged in ephemeral session storage.

### Step 2: Extraction Review & Verification
- PyMuPDF or `python-docx` extracts raw text and structural metadata (contact info, work history, education, skills, certifications, projects).
- User is presented with a two-pane verification screen: original document preview alongside structured, editable extracted fields.
- **Critical Guardrail:** The user verifies or corrects dates, titles, and extracted blocks to establish a verified baseline ground truth.

### Step 3: Standalone ATS Readiness Analysis (No Job Description Required)
- System runs algorithmic checks assessing parser reliability:
  - Font embedding, text layer integrity, and glyph corruption.
  - Multi-column risk, table traps, text-box anomalies, and non-standard symbols.
  - Standard section header taxonomy (e.g., "Experience" vs. idiosyncratic labels).
  - Contact information parseability (email, phone, LinkedIn, location).
  - Chronological consistency and date formatting.
  - Bullet count, verb strength, and quantification density.
- Outputs an **ATS Readiness Score (0–100)** with categorized actionable findings.

### Step 4: Optional Job Description Ingestion
- User can opt to paste target job description text or provide structured role details.
- System validates minimum length (e.g., at least 150 characters) to ensure sufficient context for semantic evaluation.

### Step 5: Job Match Assessment & Evidence Matrix
- Independent from ATS readiness, the engine parses the job description into:
  - Hard technical requirements / tools.
  - Core domain competencies.
  - Educational / certification thresholds.
  - Years of experience criteria.
- Categorizes each requirement into one of three strict states:
  1. **Fully Matched:** Direct, unambiguous evidence in the verified resume (with exact citation).
  2. **Partially Supported:** Related experience exists, but the specific tool, scope, or depth is not explicitly stated.
  3. **Unsubstantiated / Missing:** No grounding found in the resume.
- Outputs a **Job Match Score (0–100)** accompanied by an evidence-backed gap report.

### Step 6: AI Rewriting & Optimization Studio
- Granular, line-by-line improvement engine targeting weak, passive, or unquantified resume bullets.
- For each suggested rewrite, the UI presents:
  - Original verbatim text.
  - Proposed optimized text (enhanced action verb, refined grammar, highlighted impact prompt).
  - Rationale explaining the revision.
  - Interactive controls: **Accept**, **Reject**, or **Edit Manually**.
- **Guardrail:** The AI is strictly instructed to flag places where metrics are needed (e.g., `[insert % increase]`) rather than hallucinating artificial numbers.

### Step 7: Resume Builder & Template Studio
- User transitions verified, polished content into a responsive, live-preview resume builder.
- A single clean, conventional, single-column ATS Professional template with restrained navy accents. Avoid universal ATS compatibility claims.
- Real-time editing of sections, ordering, typography scaling, and margin balance.

### Step 8: Production Resume Export (PDF & DOCX)
- High-fidelity PDF rendering via headless vector engine or print styling, ensuring standard single-column text flow that ATS parsers parse reliably.
- Clean DOCX generation using native open-xml formatting (standard paragraphs, genuine bullet lists, zero floating shapes).

### Step 9: Dedicated PDF Improvement Report Download
- Separate executive audit report (8.5x11" portrait PDF) containing:
  - Session overview and document checksum.
  - ATS Readiness audit breakdown and warnings.
  - Role match matrix (if JD was provided) with matched citations and missing gaps.
  - Actionable checklist of completed and pending optimizations.

### Step 10: Reanalysis & Differential Comparison
- Once an updated resume is generated or uploaded, the user can trigger a differential audit.
- Available **only** when both an initial baseline and a revised version exist in the session.
- Side-by-side delta visualization showing score trajectories, resolved formatting traps, newly verified requirements, and bullet strength improvements.

---

## 4. Screen-by-Screen Functional Specifications (7 Screens)

### Screen 1: Landing & Upload Experience (`/`)
- **Header:** Minimalist brand mark ("RESUMIND AI"), Dark/Light theme toggle, "How it Works" modal trigger.
- **Hero:** Deep editorial typography, Frost & Chrome aesthetic, custom illustration of translucent document morphing into opportunity paths. Clear tagline: *"No Login. No Hallucinations. Precision Resume Intelligence."*
- **Dropzone:** High-contrast frosted glass container accepting `.pdf` and `.docx` (drag-and-drop or file browser). Max size: 10MB.
- **Privacy Assurance Badge:** Visible note explaining: *"Files are processed in an isolated ephemeral session and automatically expunged after 24 hours. No sign-up required."*
- **Quick Demo Action:** "Try with synthetic sample resume" button for instant testing without uploading personal documents.

### Screen 2: Extraction Review & Verification (`/review`)
- **Layout:** Split-screen layout.
  - Left: Interactive original document canvas (page-by-page rendering).
  - Right: Tabbed/accordion structured editor with extracted blocks:
    - Contact Info (Name, Email, Phone, Location, Portfolio/LinkedIn).
    - Work History (Role, Employer, Location, Dates, Verbatim Bullets).
    - Education (Degree, Major, Institution, Graduation Date).
    - Skills & Technologies (Categorized tags).
    - Certifications & Projects.
- **Controls:** Add item, Delete item, Reorder, Inline edit, "Confirm & Analyze" primary CTA.
- **Validation Alerts:** Highlights unparsed dates, overlapping tenures, or missing contact identifiers.

### Screen 3: Standalone ATS Readiness Dashboard (`/readiness`)
- **Scorecard:** Central circular or arc gauge displaying ATS Readiness Score (0–100) with rating classification (e.g., Needs Remediation <60, Moderate 60–79, Optimal 80–100).
- **Audit Breakdown Panels:**
  - *Parser Compatibility:* Font embedding status, layout complexity check, multi-column alerts.
  - *Structural Hygiene:* Section naming standardization check, contact parseability index.
  - *Content Density:* Action verb density, quantifiable impact ratio (bullets with numbers vs. descriptive text).
- **Issue Action List:** Filterable by Severity (Critical, Warning, Optimization). Each card contains an explanation, affected snippet, and direct fix recommendation.
- **Next Step CTAs:** "Add Job Description for Targeted Match" (Primary) or "Proceed to Direct Resume Polish" (Secondary).

### Screen 4: Target Job Match & Gap Analysis (`/job-match`)
- **Input Drawer / Modal:** Text area with character counter (min 150, max 10,000 chars) for pasting job posting.
- **Dual Score View:** Displays ATS Readiness Score alongside Job Match Score (0–100).
- **Three-Tier Requirement Matrix:**
  1. *Strong Match (Green Pill):* Shows job requirement matched with highlighted resume excerpt.
  2. *Partial Match (Amber Pill):* Shows partial overlap with guidance on what nuance is missing.
  3. *Unsubstantiated Gap (Slate Pill):* Identifies requested skill/qualification not present in resume.
- **Honesty Shield:** Explicit callout: *"Do not add unsubstantiated skills unless you genuinely possess this experience. ATS algorithms search for context, and technical interviewers test for depth."*

### Screen 5: AI Improvement & Rewrite Studio (`/rewrite`)
- **Interactive Focus List:** Displays resume bullet points flagged for weak impact, missing context, or grammatical vagueness.
- **Revision Card Component:**
  - Original Text (with highlighted weak verbs or run-ons).
  - Proposed Revision (featuring strong action verb and outcome framing).
  - Rationale (e.g., *"Replaced passive 'Responsible for' with active 'Spearheaded'; restructured to front-load technical results."*).
  - Action Controls:
    - `[Accept]` — Applies changes directly to current session draft.
    - `[Edit]` — Opens inline editor for user personalization.
    - `[Reject]` — Dismisses recommendation without modifying text.
- **Batch Controls:** "Accept All High-Confidence Grammar Enhancements".

### Screen 6: Resume Builder & Template Studio (`/builder`)
- **Dual Workspace:**
  - Left Pane: Section navigator and live content editor (drag-and-drop section reordering, bullet addition, WYSIWYG formatting).
  - Right Pane: Real-time rendered document canvas with dynamic zoom (50%, 75%, 100%, Fit to Width).
- **Template Selector:**
  - **ATS Professional:** One conventional, single-column layout with a clear hierarchy, restrained navy accents, readable typography, and native text throughout. Avoid claims of universal ATS compatibility.
- **Export Bar:** Quick buttons for `Export ATS PDF`, `Export DOCX`, and `Download Audit Report`.

### Screen 7: Export Center & Differential Reanalysis (`/export`)
- **Download Hub:**
  - Primary Download: `.pdf` (single-column, text-based ATS-oriented PDF).
  - Alternative Download: `.docx` (Editable OpenXML).
  - Diagnostic Download: `RESUMIND_Audit_Report.pdf`.
- **Differential Comparison Module (Available if original and revised versions exist):**
  - Side-by-side diff view of modified sections.
  - Delta Scorecard (e.g., *ATS Readiness: 68 -> 92 (+24)*; *Job Match: 54 -> 78 (+24)*).
  - Breakdown of resolved warnings (e.g., *3 multi-column parsing traps eliminated, 6 passive verbs replaced, 4 quantifiable results added*).

---

## 5. Transparent Scoring Framework (Proposed Architecture)

> **Important Notice:** In accordance with Phase 0 directives, this scoring framework is fully documented herein for review and architectural approval. **No scoring code will be implemented until this specification is explicitly approved by the user.**

### 5.1 ATS Readiness Score (Max: 100 Points)
The ATS Readiness Score evaluates the *mechanical, structural, and linguistic parseability* of the resume. It does **not** evaluate whether the candidate is qualified for a specific job.

$$\text{ATS Readiness Score} = \sum_{i=1}^{5} W_i \cdot S_i$$

| Dimension ($i$) | Weight ($W_i$) | Metrics & Inputs | Calculation Rationale |
| :--- | :--- | :--- | :--- |
| **1. File & Text Integrity** | 25% | - Extracted glyph validity ratio<br>- Embedded font verification<br>- Layout flow: 0 multi-column traps or floating text boxes | If an ATS cannot extract pure text cleanly without symbol scrambling or text interleaving, all subsequent keyword matches fail. |
| **2. Structural Taxonomy** | 20% | - Standard section headers recognized (Experience, Education, Skills, Contact)<br>- Standard chronological order detection | Unrecognized header names (e.g., "Where I've Been") cause parsers to discard work history or misclassify skills. |
| **3. Contact Information Parseability** | 15% | - Valid RFC-compliant email<br>- E.164 or standard formatted telephone<br>- Single primary location/city<br>- Valid professional URL (LinkedIn/GitHub) | ATS candidate deduplication and recruiter outreach depend on error-free extraction of contact keys. |
| **4. Bullet Construction & Impact** | 25% | - Percentage of bullets starting with recognized action verbs (target: >85%)<br>- Metric/quantifier presence ratio (target: >35% of bullets include numerical/percentage/scale impact)<br>- Length distribution (target: 12–35 words per bullet) | Parsers and initial human screeners penalize dense, run-on blocks or passive "responsible for" lists. |
| **5. Length & Section Hygiene** | 15% | - Page budget vs. years of experience (1 page for <5 yrs, 2 pages for 5+ yrs)<br>- Date format consistency (e.g., consistently `MM/YYYY` or `Month YYYY`)<br>- Absence of graphics/photos/tables | Inconsistent dates break timeline reconstruction in systems like Workday and Greenhouse. |

#### Score Interpretation
- **90–100 (Optimal):** Document extracts cleanly across all standard parser specifications. Format is robust and ATS-safe.
- **75–89 (Good):** Minor issues detected (e.g., non-standard date format, low metric density). Readable by modern parsers.
- **60–74 (Moderate Risk):** Structural anomalies or complex formatting detected. Risk of misparsed sections in legacy ATS engines.
- **<60 (Critical Action Needed):** Unextractable text layers, graphic columns, or broken hierarchies detected. Significant parsing failure risk.

### 5.2 Job Match Score (Max: 100 Points)
The Job Match Score evaluates the *semantic overlap and grounded requirement satisfaction* between the verified resume and a specific job posting.

$$\text{Job Match Score} = 0.40(S_{\text{hard}}) + 0.30(S_{\text{domain}}) + 0.15(S_{\text{experience}}) + 0.15(S_{\text{education}})$$

| Category | Weight | Description | Grounding Rule |
| :--- | :--- | :--- | :--- |
| **Hard Technical Skills ($S_{\text{hard}}$)** | 40% | Exact or synonymous technical proficiencies, tools, frameworks, and programming languages required by the JD. | Must exist in Skills or Work Experience bullets. Inferred tools without resume mention are marked unsubstantiated. |
| **Domain & Competencies ($S_{\text{domain}}$)** | 30% | Key responsibilities, methodologies (e.g., Agile, CI/CD, Financial Modeling), and industry practices. | Semantic similarity search requiring contextual evidence in experience descriptions. |
| **Experience Scope ($S_{\text{experience}}$)** | 15% | Seniority alignment, years of relevant experience, and leadership scope compared to stated requirements. | Calculated by summing dated tenures in relevant job roles. |
| **Education & Credentials ($S_{\text{education}}$)** | 15% | Required degrees, fields of study, licenses, or professional certifications (e.g., PMP, AWS Certified). | Strict verification against extracted Education and Certification nodes. |

#### Honesty & Non-Hallucination Guardrails
1. **The Evidence Mandate:** For every requirement counted in $S_{\text{hard}}$ or $S_{\text{domain}}$, the system must return the exact source snippet from the resume.
2. **Explicit Gap Categorization:** Requirements with no textual grounding receive a score of 0 in that sub-metric and are placed into the "Unsubstantiated Gap" list with advice on real-world projects or courses needed.
3. **No Inflated Scoring:** Scores are bounded strictly between 0 and 100. Match scores cannot be elevated by keyword stuffing in hidden text or meta tags.

### 5.3 Limitations & Disclaimers
- **No Guarantee of Employment:** ATS Readiness indicates format readability, not applicant suitability.
- **Proprietary Variance:** Different corporate ATS installations apply custom parsing heuristics and recruiter filters. RESUMIND AI evaluates against consensus industry standards.

---

## 6. Non-Functional Requirements & System Constraints

| Category | Requirement | Target Metric / Verification Method |
| :--- | :--- | :--- |
| **Performance** | Upload to initial parsed view latency | < 2.5 seconds on standard 2-page PDF/DOCX |
| **Performance** | Standalone ATS analysis completion | < 3.0 seconds (algorithmic checks) |
| **Performance** | AI rewrite suggestion generation | < 5.0 seconds (streamed response via Ollama/local provider) |
| **Privacy & Storage**| Ephemeral session lifecycle | Uploaded files and session state expunged automatically after 24 hours of inactivity |
| **Accessibility** | WCAG 2.1 Compliance | AA level compliance across all 7 screens (contrast ratios > 4.5:1, keyboard navigation, aria-labels) |
| **Responsiveness** | Cross-device compatibility | Fully responsive down to 360px viewport width; mobile-optimized builder view |
| **Reliability** | Parsing error handling | Graceful fallback for malformed PDFs, password-protected files, or corrupted archives with human-readable error messages |

---

## 7. Acceptance Criteria for Complete Product Validation

- [ ] **AC-1:** User can complete the full journey from file upload through revised PDF/DOCX export without ever creating an account or entering an email address.
- [ ] **AC-2:** Uploading both `.pdf` and `.docx` files accurately extracts contact info, experience, education, and skills into editable review blocks.
- [ ] **AC-3:** ATS Readiness analysis functions independently without requiring a job description and flags known format hazards (tables, multiple columns, unparsed glyphs).
- [ ] **AC-4:** Job match assessment accurately categorizes requirements into Matched, Partially Supported, and Unsubstantiated with verbatim textual evidence.
- [ ] **AC-5:** AI rewrite suggestions never invent credentials or metrics; all revisions provide original text, proposed text, rationale, and accept/reject/edit controls.
- [ ] **AC-6:** Resume builder supports real-time editing and a live canvas preview using the single ATS Professional template.
- [ ] **AC-7:** Export engine produces readable, text-based PDF and editable DOCX documents plus a separate PDF audit report; generated files are checked for content and reading order without promising universal ATS compatibility.
- [ ] **AC-8:** Differential comparison is accessible only when an initial assessment and a modified version both exist in the active session.
- [ ] **AC-9:** All local development functions completely offline/locally using SQLite and Ollama without requiring paid cloud API keys.
