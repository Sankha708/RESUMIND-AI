# RESUMIND AI — Design System: Frost & Chrome

> **Version:** 1.0.0  
> **Status:** Phase 0 Visual Architecture  
> **Theme:** Frost & Chrome (Minimalist, Editorial, Atmospheric)  
> **Repository:** `D:\RESUMIND-AI`

---

## 1. Design Philosophy & Aesthetic Vision

The visual identity of RESUMIND AI is **Frost & Chrome**. It is rooted in architectural minimalism, refined editorial typography, subtle liquid glass surfaces, and fine chrome metallic reflections. It projects the quiet confidence of an executive suite rather than the hyperactive noise of a flashy startup.

### Guiding Tenets
1. **Generous Whitespace & Calm Hierarchy:** Content is given room to breathe. High visual density is reserved for structured comparison tables, never for marketing screens.
2. **Subtle & Realistic Liquid Glass:** Glassmorphism is used with extreme restraint (`backdrop-blur-md` or `backdrop-blur-lg` paired with 1px semi-transparent borders). It enhances depth without compromising text readability.
3. **Decoupled Aesthetics (App vs. Export):** The web application UI is expressive, modern, and atmospheric. However, **all exported resumes are strictly ATS-compliant, high-contrast, minimalist, and devoid of graphic gimmicks that confound document parsers.**
4. **Prohibited Visual Tropes:**
   - **NO** neon/electric-lime or toxic-green branding.
   - **NO** generic pulsing AI orbs or floating sparkle particles.
   - **NO** cluttered, low-contrast "SaaS dashboard" templates filled with fake vanity charts.
   - **NO** illegible, milky glass overlays that fail accessibility standards.

---

## 2. Color System & Design Tokens

### 2.1 Primary Brand Tokens

| Token Name | Hex Code | HSL Equivalent | Role & Context |
| :--- | :--- | :--- | :--- |
| **Pearl Canvas** | `#F3F5F6` | `200°, 9%, 96%` | Primary background canvas in Light Theme; clean, non-glaring off-white. |
| **Primary Ink** | `#181A1D` | `216°, 9%, 10%` | Primary typography and deep contrast elements; rich obsidian ink. |
| **Chrome Silver** | `#9CA6B2` | `213°, 12%, 66%` | Subtle borders, structural dividers, inactive states, metallic reflections. |
| **Frosted Surface** | `#D9E0E6` | `207°, 18%, 88%` | Semi-transparent card surfaces, pill backgrounds, subtle hover planes. |
| **Steel Blue** | `#5477B8` | `219°, 42%, 53%` | Active interactive elements, focused input states, primary CTAs, accents. |

### 2.2 Semantic & Adaptive Color Tokens

```css
/* Light Mode Tokens (Default) */
:root {
  --canvas-bg: #F3F5F6;
  --surface-card: rgba(255, 255, 255, 0.75);
  --surface-card-border: rgba(156, 166, 178, 0.35);
  --surface-frost: rgba(217, 224, 230, 0.65);
  --text-primary: #181A1D;
  --text-secondary: #58616D;
  --text-muted: #838F9E;
  
  --accent-steel: #5477B8;
  --accent-steel-hover: #43629C;
  --accent-steel-subtle: rgba(84, 119, 184, 0.12);

  --status-success: #2E7D5A;
  --status-success-bg: rgba(46, 125, 90, 0.10);
  --status-warning: #B87333; /* Warm Copper */
  --status-warning-bg: rgba(184, 115, 51, 0.10);
  --status-critical: #B33939;
  --status-critical-bg: rgba(179, 57, 57, 0.10);
}

/* Dark Mode Tokens (Adaptive) */
.dark {
  --canvas-bg: #0E1013;
  --surface-card: rgba(24, 26, 29, 0.80);
  --surface-card-border: rgba(156, 166, 178, 0.20);
  --surface-frost: rgba(32, 36, 42, 0.70);
  --text-primary: #F0F2F5;
  --text-secondary: #A0ABB8;
  --text-muted: #64707D;

  --accent-steel: #6E90D1;
  --accent-steel-hover: #82A2E0;
  --accent-steel-subtle: rgba(110, 144, 209, 0.15);

  --status-success: #4EAD82;
  --status-success-bg: rgba(78, 173, 130, 0.15);
  --status-warning: #D98E48;
  --status-warning-bg: rgba(217, 142, 72, 0.15);
  --status-critical: #D9534F;
  --status-critical-bg: rgba(217, 83, 79, 0.15);
}
```

---

## 3. Typography & Editorial Scale

The typographic hierarchy combines the editorial authority of high-end publication design with the mathematical legibility of technical interfaces.

- **Primary Display & Headings:** `Plus Jakarta Sans` or `Inter` (500 Medium, 600 Semi-Bold, 700 Bold) — clean, modern, and open geometric forms.
- **Resume document template:** one single-column ATS Professional layout with readable sans-serif typography and restrained navy accents; the app may use editorial fonts in its interface, but exported resumes use conventional document styles.
- **Data & Monospace Metrics:** `JetBrains Mono` or `Geist Mono` for file sizes, score breakdowns, checksums, and token counters.

| Style Role | Font Family | Size | Weight | Line Height | Tracking |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Hero Display** | Plus Jakarta Sans | `44px` / `2.75rem` | 700 Bold | 1.15 | `-0.025em` |
| **Section Title (H1)** | Plus Jakarta Sans | `32px` / `2.00rem` | 600 Semi-Bold | 1.25 | `-0.020em` |
| **Card Header (H2)** | Plus Jakarta Sans | `22px` / `1.375rem`| 600 Semi-Bold | 1.30 | `-0.015em` |
| **Subhead (H3)** | Plus Jakarta Sans | `16px` / `1.00rem` | 600 Semi-Bold | 1.40 | `-0.010em` |
| **Body Large** | Inter | `16px` / `1.00rem` | 400 Regular | 1.60 | `0.000em` |
| **Body Regular** | Inter | `14px` / `0.875rem`| 400 Regular | 1.55 | `0.005em` |
| **Caption / Meta** | Inter | `12px` / `0.75rem` | 500 Medium | 1.45 | `0.015em` |
| **Code / Score** | JetBrains Mono | `13px` / `0.8125rem`| 500 Medium | 1.40 | `-0.010em` |

---

## 4. Glass Materials & Surface Elevation

Glass layers in RESUMIND AI are designed to emulate precision optical glass and brushed chrome.

### 4.1 Surface Levels
1. **Level 0 (Canvas):** Solid background (`--canvas-bg`) with an extremely subtle radial gradient of Steel Blue (`radial-gradient(circle at 50% 0%, rgba(84, 119, 184, 0.05) 0%, transparent 65%)`).
2. **Level 1 (Frosted Card):**
   - Background: `var(--surface-card)`
   - Backdrop filter: `blur(12px)`
   - Border: `1px solid var(--surface-card-border)`
   - Box shadow: `0 4px 24px -2px rgba(24, 26, 29, 0.04), 0 1px 2px rgba(24, 26, 29, 0.02)`
3. **Level 2 (Active Hover & Interactive Panels):**
   - Background: `rgba(255, 255, 255, 0.90)` (light) / `rgba(32, 36, 42, 0.85)` (dark)
   - Border: `1px solid var(--accent-steel)` (subtle metallic sheen)
   - Box shadow: `0 8px 32px -4px rgba(84, 119, 184, 0.12)`
4. **Level 3 (Modals & Overlays):**
   - Background: `rgba(255, 255, 255, 0.96)` (light) / `rgba(18, 20, 23, 0.96)` (dark)
   - Backdrop backdrop: `rgba(24, 26, 29, 0.40)` with `blur(8px)`

---

## 5. Hero Illustration Art Direction

### The Concept: "The Translucent Horizon"
Rather than using generic robotic figures, artificial brain nodes, or glowing neon orbs, RESUMIND AI features a signature hero illustration titled **The Translucent Horizon**:
- **Visual Description:** A multi-layered, semi-transparent resume sheet crafted from frosted glass rests at a gentle isometric perspective. Its structured bullet points and lines gently dissolve and transform into clean, luminescent chrome stepping stones that ascend toward an open horizon line.
- **Lighting & Texture:** Soft directional lighting catches the beveled edges of the frosted resume sheet, producing subtle prismatic chrome reflections (`#9CA6B2` to `#5477B8`).
- **Implementation:** Vector SVG with layered gradients for instant, crisp rendering at all screen densities, with optional gentle floating motion via Motion.

---

## 6. Reusable Component Specifications (shadcn/ui + Tailwind)

### 6.1 Buttons (`Button`)
- **Primary:** Background `var(--accent-steel)`, text white, subtle top-edge chrome highlight (`box-shadow: inset 0 1px 0 rgba(255,255,255,0.2)`).
- **Secondary / Ghost:** Frosted background `var(--surface-frost)`, border `1px solid var(--surface-card-border)`, text `var(--text-primary)`.
- **Destructive / Reject:** Subdued warm copper/red tint (`var(--status-critical-bg)`), text `var(--status-critical)`.

### 6.2 Gauges & Score Cards (`ScoreArc`)
- Minimalist circular arc or semi-circle SVG meter.
- Stroke width: 8px. Track color: `var(--chrome-silver)` with 20% opacity.
- Fill color: Dynamic based on score tier (Green for 80+, Copper for 60–79, Slate/Red for <60).
- Center text: Big numeric metric in `JetBrains Mono` with small muted label below.

### 6.3 Requirement Badges (`EvidencePill`)
- **Matched:** Green tint with check icon (`✓ Matched`). Hover reveals tooltip with direct resume quotation.
- **Partial:** Amber/Copper tint with alert icon (`~ Partial`). Hover explains the missing scope.
- **Unsubstantiated:** Slate tint with minus icon (`✕ Gap`). Hover explains why the skill is flagged as absent.

### 6.4 Rewrite Cards (`RevisionCard`)
- Distinct dual-zone card:
  - Top zone: Original bullet with struck-through or highlighted weak phrase.
  - Bottom zone: Suggested revision with bolded action verb and metric prompt in brackets (`[e.g., increased by 20%]`).
  - Rationale footer: Collapsible or subtle italicized explanation.
  - Right-aligned action buttons: `Accept` (Steel Blue), `Edit` (Ghost), `Reject` (Subtle muted).

---

## 7. Motion & Interaction Design

Micro-interactions are restrained, realistic, and purposeful:
- **Duration Scale:** Micro-actions: `150ms–200ms`; Screen transitions: `300ms`; Modal overlays: `250ms`.
- **Easing:** Standard ease-out curve (`cubic-bezier(0.16, 1, 0.3, 1)` — "exponential out") for physical, responsive feel.
- **Hover Transitions:** Cards subtly translate upward by `2px` on hover with a smooth border glow transition.
- **Score Gauges:** Smooth count-up animation on initial screen load (duration: `800ms`).
- **Zero Motion Safety:** Full support for `prefers-reduced-motion` media queries; all animations instantly resolve to final static states when enabled.

---

## 8. Screen-by-Screen Layout & Spatial Hierarchy (All 7 Screens)

### Screen 1: Landing & Upload Experience (`/`)
- **Layout:** Centered single-column hero with max-width 900px.
- **Top:** Brand navigation bar (height: 64px) with fixed blur backdrop.
- **Middle:** Hero headline, subtitle, and primary Dropzone card (height: 280px) with dashed chrome border, drop icon, and file type indicators.
- **Bottom:** Three minimalist feature callouts (Zero Login, Grounded Evidence, Dual ATS/Job Evaluation) and Privacy Guarantee badge.

### Screen 2: Extraction Review & Verification (`/review`)
- **Layout:** 50/50 desktop split (stacked on mobile).
- **Left Column:** PDF page viewer with zoom controls (50% to 150%) and page pagination.
- **Right Column:** Scrollable form container with tab navigation (`Contact`, `Experience`, `Education`, `Skills`). Each section contains editable cards with add/delete triggers.
- **Sticky Footer Bar:** "Confirm Ground Truth & Run ATS Analysis" primary button with progress pill.

### Screen 3: Standalone ATS Readiness Dashboard (`/readiness`)
- **Layout:** Top overview banner with central score arc; 3-column metric cards below (File Integrity, Structural Taxonomy, Impact Density).
- **Lower Section:** Two-column split:
  - Left (60%): Categorized Finding List (Critical Issues, Format Warnings, Linguistic Polish).
  - Right (40%): Action Panel with "Add Job Description for Targeted Match" card and "Jump to Resume Builder".

### Screen 4: Target Job Match & Gap Analysis (`/job-match`)
- **Layout:** Top bar showing Dual Score Comparison (ATS Score alongside Job Match Score).
- **Main Body:** Three-column or tabbed requirement board:
  - Column 1: Hard Skills & Tools (Matched vs. Missing).
  - Column 2: Domain Experience & Responsibilities.
  - Column 3: Credentials, Education, & Scope.
- **Interactive Drawer:** Job description viewer allowing users to see where in the posting specific requirements were detected.

### Screen 5: AI Improvement & Rewrite Studio (`/rewrite`)
- **Layout:** Centered single-column focus studio (max-width 840px).
- **Header:** Sticky banner with optimization tally (e.g., *"6 of 14 bullets reviewed"*).
- **Card Stream:** Vertically stacked `RevisionCard` elements with keyboard navigation shortcuts (`A` for Accept, `R` for Reject, `E` for Edit).

### Screen 6: Resume Builder & Template Studio (`/builder`)
- **Layout:** Full-height application workbench.
  - Left Sidebar (320px): Section hierarchy tree, the single ATS Professional document style, and limited readability controls.
  - Center Canvas: Real-time rendered document canvas simulating a physical A4/Letter sheet with shadows.
  - Right Floating Toolbar: Zoom controls, page boundary indicators, and undo/redo buttons.

### Screen 7: Export Center & Differential Reanalysis (`/export`)
- **Layout:** Two balanced quadrants:
  - Left Quadrant: Export download center with large download cards for ATS PDF, OpenXML DOCX, and Audit Report PDF.
  - Right Quadrant: Differential Reanalysis Module (active when baseline and revised drafts exist), showing side-by-side score deltas and resolved warning badges.

---

## 9. Exported Resume Typography & ATS-Safe Rules

While the application interface is styled with modern glass and chrome, **all exported resumes adhere to strict ATS formatting standards:**
- Single-column flow or standard two-cell table layout without nested frames.
- Standard universal fonts (Helvetica, Arial, Times New Roman, Calibri, Garamond).
- No floating text boxes, graphics, photos, chart icons, or background colors.
- Standard 0.5" to 0.75" page margins.
- Clean text hierarchy with recognized headers: `SUMMARY`, `EXPERIENCE`, `EDUCATION`, `SKILLS`, `CERTIFICATIONS`.
