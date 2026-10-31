"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { getApiBaseUrl } from "@/lib/api";
import { ParsedResume } from "./ResumeUploadSurface";

export interface ContactInfo {
  name: string;
  headline?: string;
  email?: string;
  phone?: string;
  location?: string;
  website?: string;
  linkedin?: string;
  github?: string;
}

export interface ExperienceItem {
  id: string;
  company: string;
  role: string;
  location?: string;
  start_date?: string;
  end_date?: string;
  current: boolean;
  bullets: string[];
}

export interface ProjectItem {
  id: string;
  title: string;
  role?: string;
  url?: string;
  start_date?: string;
  end_date?: string;
  bullets: string[];
  tech_stack: string[];
}

export interface EducationItem {
  id: string;
  institution: string;
  degree?: string;
  field_of_study?: string;
  start_date?: string;
  end_date?: string;
  gpa?: string;
  highlights: string[];
}

export interface SkillCategory {
  id: string;
  category: string;
  skills: string[];
}

export interface CertificationItem {
  id: string;
  name: string;
  issuer?: string;
  issue_date?: string;
  expiry_date?: string;
  url?: string;
}

export interface AdditionalSectionItem {
  id: string;
  section_title: string;
  bullets: string[];
}

export interface BuilderContent {
  contact: ContactInfo;
  summary?: string;
  experience: ExperienceItem[];
  projects: ProjectItem[];
  skills: SkillCategory[];
  education: EducationItem[];
  certifications: CertificationItem[];
  additional: AdditionalSectionItem[];
}

export interface TemplateConfig {
  font_family: "inter" | "merriweather" | "roboto_mono";
  font_size: "compact" | "medium" | "spacious";
  margin_size: "compact" | "standard" | "wide";
  line_spacing: "tight" | "normal" | "relaxed";
  accent_color: string;
}

export interface ResumeBuilderDocument {
  id: string;
  session_id: string;
  source_resume_id?: string | null;
  version: number;
  template_id: "ats_professional";
  template_config: TemplateConfig;
  section_order: string[];
  section_visibility: Record<string, boolean>;
  content: BuilderContent;
  created_at: string;
  updated_at: string;
}

interface ResumeBuilderViewProps {
  resume?: ParsedResume | null;
  onBackToAssessments: () => void;
  onBackToReview?: () => void;
  onProceedToExport?: () => void;
}

const API_BASE = getApiBaseUrl();
const CANONICAL_TEMPLATE_CONFIG: TemplateConfig = {
  font_family: "inter",
  font_size: "medium",
  margin_size: "standard",
  line_spacing: "normal",
  accent_color: "#254B78",
};

function normalizeBuilderDocument(document: ResumeBuilderDocument): ResumeBuilderDocument {
  return {
    ...document,
    template_id: "ats_professional",
    template_config: { ...CANONICAL_TEMPLATE_CONFIG },
  };
}

const SECTION_METADATA: Record<string, { label: string; icon: string }> = {
  contact: {
    label: "Contact Information",
    icon: "M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
  },
  summary: {
    label: "Professional Summary",
    icon: "M4 6h16M4 12h16M4 18h7",
  },
  experience: {
    label: "Work Experience",
    icon: "M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
  },
  projects: {
    label: "Technical Projects",
    icon: "M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4",
  },
  skills: {
    label: "Skills & Proficiencies",
    icon: "M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z",
  },
  education: {
    label: "Education & Credentials",
    icon: "M12 14l9-5-9-5-9 5 9 5zm0 0l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14zm-4 6v-7.5",
  },
  certifications: {
    label: "Certifications & Licenses",
    icon: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z",
  },
  additional: {
    label: "Honors, Awards & Activities",
    icon: "M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z",
  },
};

export function ResumeBuilderView({
  resume,
  onBackToAssessments,
  onBackToReview,
  onProceedToExport,
}: ResumeBuilderViewProps) {
  const [doc, setDoc] = useState<ResumeBuilderDocument | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveStatus, setSaveStatus] = useState<"synced" | "saving" | "unsaved" | "conflict">("synced");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Active editor tab: "content" | "layout" | "style"
  const [editorTab, setEditorTab] = useState<"content" | "layout" | "style">("content");
  const [activeSectionId, setActiveSectionId] = useState<string>("contact");

  // Zoom controls for live preview
  const [zoomLevel, setZoomLevel] = useState<number>(0.85);

  // Modal / Feedback state
  const [showResetModal, setShowResetModal] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);

  // Auto-save debounce timer ref
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // ── 1. Fetch initial builder document ──────────────────────────────────────
  const fetchBuilderDocument = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const response = await fetch(`${API_BASE}/api/builder`, {
        credentials: "include",
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to load resume builder (${response.status})`);
      }

      const data: ResumeBuilderDocument = await response.json();
      setDoc(normalizeBuilderDocument(data));
      setSaveStatus("synced");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to initialize resume builder.";
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    async function loadBuilder() {
      try {
        const response = await fetch(`${API_BASE}/api/builder`, {
          credentials: "include",
        });

        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(err.detail || `Failed to load resume builder (${response.status})`);
        }

        const data: ResumeBuilderDocument = await response.json();
        if (!ignore) {
          setDoc(normalizeBuilderDocument(data));
          setSaveStatus("synced");
        }
      } catch (err: unknown) {
        if (!ignore) {
          const msg = err instanceof Error ? err.message : "Failed to initialize resume builder.";
          setErrorMessage(msg);
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }
    loadBuilder();
    return () => {
      ignore = true;
    };
  }, []);

  // ── 2. Persist builder document ────────────────────────────────────────────
  const persistDocument = useCallback(
    async (currentDoc: ResumeBuilderDocument) => {
      setIsSaving(true);
      setSaveStatus("saving");
      try {
        const response = await fetch(`${API_BASE}/api/builder`, {
          method: "PUT",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            version: currentDoc.version,
            template_id: "ats_professional",
            template_config: currentDoc.template_config,
            section_order: currentDoc.section_order,
            section_visibility: currentDoc.section_visibility,
            content: currentDoc.content,
          }),
        });

        if (response.status === 409) {
          setSaveStatus("conflict");
          setErrorMessage("Version mismatch: The document was updated in another session. Please reload to sync.");
          return;
        }

        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(err.detail || `Failed to save changes (${response.status})`);
        }

        const updated: ResumeBuilderDocument = await response.json();
        setDoc(normalizeBuilderDocument(updated));
        setSaveStatus("synced");
      } catch (err: unknown) {
        setSaveStatus("unsaved");
        const msg = err instanceof Error ? err.message : "Failed to save builder changes.";
        setErrorMessage(msg);
      } finally {
        setIsSaving(false);
      }
    },
    []
  );

  // Trigger auto-save with debounce
  const queueAutoSave = useCallback(
    (newDoc: ResumeBuilderDocument) => {
      setDoc(newDoc);
      setSaveStatus("unsaved");

      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }

      saveTimeoutRef.current = setTimeout(() => {
        persistDocument(newDoc);
      }, 1200);
    },
    [persistDocument]
  );

  // ── 3. Reset document ──────────────────────────────────────────────────────
  const handleResetDocument = useCallback(
    async (source: "reviewed_resume" | "empty") => {
      setIsResetting(true);
      setErrorMessage(null);
      try {
        const response = await fetch(`${API_BASE}/api/builder/reset`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ source }),
        });

        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(err.detail || "Failed to reset resume document.");
        }

        const data: ResumeBuilderDocument = await response.json();
        setDoc(normalizeBuilderDocument(data));
        setSaveStatus("synced");
        setShowResetModal(false);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Error resetting builder document.";
        setErrorMessage(msg);
      } finally {
        setIsResetting(false);
      }
    },
    []
  );

  // ── Helper state mutators ──────────────────────────────────────────────────
  const updateContent = useCallback(
    (updater: (prevContent: BuilderContent) => BuilderContent) => {
      if (!doc) return;
      const nextContent = updater(doc.content);
      const nextDoc: ResumeBuilderDocument = {
        ...doc,
        content: nextContent,
      };
      queueAutoSave(nextDoc);
    },
    [doc, queueAutoSave]
  );

  const moveSection = useCallback(
    (index: number, direction: "up" | "down") => {
      if (!doc) return;
      const targetIndex = direction === "up" ? index - 1 : index + 1;
      if (targetIndex < 0 || targetIndex >= doc.section_order.length) return;

      const newOrder = [...doc.section_order];
      const temp = newOrder[index];
      newOrder[index] = newOrder[targetIndex];
      newOrder[targetIndex] = temp;

      const nextDoc: ResumeBuilderDocument = {
        ...doc,
        section_order: newOrder,
      };
      queueAutoSave(nextDoc);
    },
    [doc, queueAutoSave]
  );

  const toggleSectionVisibility = useCallback(
    (sectionKey: string) => {
      if (!doc) return;
      const current = doc.section_visibility[sectionKey] ?? true;
      const nextVisibility = {
        ...doc.section_visibility,
        [sectionKey]: !current,
      };
      const nextDoc: ResumeBuilderDocument = {
        ...doc,
        section_visibility: nextVisibility,
      };
      queueAutoSave(nextDoc);
    },
    [doc, queueAutoSave]
  );

  // ── Render Template Typography & Spacing Styles ────────────────────────────
  const fontFamilyClass = "font-sans";
  const fontSizeClass = "text-xs";
  const marginClass = "p-8";
  const lineSpacingClass = "leading-normal";

  if (isLoading) {
    return (
      <div className="flex min-h-[500px] flex-col items-center justify-center space-y-4">
        <div className="h-10 w-10 animate-spin rounded-full border-3 border-[#5477B8]/20 border-t-[#5477B8] dark:border-[#6E90D1]/20 dark:border-t-[#6E90D1]" />
        <p className="text-sm font-medium text-[#58616D] dark:text-[#A0ABB8]">
          Initializing Resume Builder & Template Studio...
        </p>
      </div>
    );
  }

  if (errorMessage && !doc) {
    return (
      <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-8 text-center backdrop-blur-md">
        <h3 className="text-base font-bold text-red-600 dark:text-red-400">Builder Unavailable</h3>
        <p className="mt-2 text-xs text-[#58616D] dark:text-[#A0ABB8]">{errorMessage}</p>
        <button
          onClick={fetchBuilderDocument}
          className="mt-4 rounded-xl bg-[#5477B8] px-4 py-2 text-xs font-semibold text-white hover:bg-[#43629C]"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  if (!doc) return null;

  return (
    <div className="flex flex-col space-y-6">
      {/* ── Top Workspace Bar ───────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 rounded-2xl border border-[#9CA6B2]/20 bg-white/70 p-4 shadow-xs backdrop-blur-md dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/70">
        <div className="flex items-center space-x-3">
          <button
            type="button"
            onClick={onBackToAssessments}
            className="flex items-center space-x-1.5 rounded-xl border border-[#9CA6B2]/30 bg-white px-3 py-1.5 text-xs font-semibold text-[#181A1D] transition hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24] dark:text-[#F0F2F5]"
            title="Return to Assessments Dashboard"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            <span>Assessments</span>
          </button>

          {onBackToReview && (
            <button
              type="button"
              onClick={onBackToReview}
              className="hidden sm:flex items-center space-x-1 rounded-xl border border-transparent px-2.5 py-1.5 text-xs font-medium text-[#58616D] transition hover:bg-[#9CA6B2]/10 dark:text-[#A0ABB8]"
            >
              Review Studio
            </button>
          )}

          <div className="h-4 w-px bg-[#9CA6B2]/30" />

          <div>
            <h2 className="text-sm font-bold text-[#181A1D] dark:text-[#F0F2F5]">
              {doc.content.contact.name || resume?.filename || "Resume Builder"}
            </h2>
            <p className="text-[11px] text-[#838F9E] dark:text-[#64707D]">
              Real-time ATS Builder • ATS Professional
            </p>
          </div>
        </div>

        {/* Status Indicators & Save / Reset controls */}
        <div className="flex items-center space-x-2.5">
          {/* Sync badge */}
          <div
            className={`flex items-center space-x-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium border ${
              saveStatus === "saving"
                ? "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400"
                : saveStatus === "conflict"
                ? "border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400"
                : "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                saveStatus === "saving"
                  ? "bg-amber-500 animate-pulse"
                  : saveStatus === "conflict"
                  ? "bg-red-500"
                  : "bg-emerald-500"
              }`}
            />
            <span>
              {saveStatus === "saving"
                ? "Saving..."
                : saveStatus === "conflict"
                ? "Sync Conflict"
                : `Saved v${doc.version}`}
            </span>
          </div>

          <button
            type="button"
            onClick={() => persistDocument(doc)}
            disabled={isSaving}
            className="rounded-xl border border-[#9CA6B2]/30 bg-white/80 px-3 py-1.5 text-xs font-semibold text-[#181A1D] shadow-xs transition hover:bg-[#F3F5F6] disabled:opacity-50 dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/80 dark:text-[#F0F2F5]"
          >
            {isSaving ? "Saving..." : "Save Now"}
          </button>

          <button
            type="button"
            onClick={() => setShowResetModal(true)}
            className="rounded-xl border border-[#9CA6B2]/30 px-3 py-1.5 text-xs font-medium text-[#838F9E] transition hover:bg-red-500/10 hover:text-red-600 dark:border-[#9CA6B2]/20 dark:text-[#A0ABB8] dark:hover:text-red-400"
          >
            Reset
          </button>

          {onProceedToExport && (
            <button
              id="proceedToExportHubBtn"
              type="button"
              onClick={onProceedToExport}
              className="flex items-center space-x-1.5 rounded-xl bg-[#5477B8] px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs transition hover:bg-[#43629C] dark:bg-[#6E90D1]"
            >
              <span>Export Center</span>
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* ── Conflict Banner if detected ─────────────────────────────────────── */}
      {saveStatus === "conflict" && (
        <div role="alert" className="flex items-center justify-between rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-700 dark:text-red-400">
          <span>{errorMessage || "Document was modified in another tab. Reload to ensure consistency."}</span>
          <button
            onClick={fetchBuilderDocument}
            className="font-bold underline hover:no-underline ml-2"
          >
            Reload Latest Draft
          </button>
        </div>
      )}

      {/* ── Main Dual-Pane Workbench ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* ── LEFT PANE: Editor & Template Studio Controls (Col 1-5) ────────── */}
        <div className="lg:col-span-5 flex flex-col space-y-4">
          {/* Editor Mode Tabs */}
          <div className="flex rounded-xl border border-[#9CA6B2]/20 bg-white/60 p-1 backdrop-blur-sm dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/60">
            <button
              type="button"
              onClick={() => setEditorTab("content")}
              className={`flex-1 rounded-lg py-1.5 text-xs font-semibold transition ${
                editorTab === "content"
                  ? "bg-[#5477B8] text-white shadow-xs dark:bg-[#6E90D1]"
                  : "text-[#58616D] hover:text-[#181A1D] dark:text-[#A0ABB8] dark:hover:text-[#F0F2F5]"
              }`}
            >
              Content Editor
            </button>
            <button
              type="button"
              onClick={() => setEditorTab("layout")}
              className={`flex-1 rounded-lg py-1.5 text-xs font-semibold transition ${
                editorTab === "layout"
                  ? "bg-[#5477B8] text-white shadow-xs dark:bg-[#6E90D1]"
                  : "text-[#58616D] hover:text-[#181A1D] dark:text-[#A0ABB8] dark:hover:text-[#F0F2F5]"
              }`}
            >
              Hierarchy & Order
            </button>
            <button
              type="button"
              onClick={() => setEditorTab("style")}
              className={`flex-1 rounded-lg py-1.5 text-xs font-semibold transition ${
                editorTab === "style"
                  ? "bg-[#5477B8] text-white shadow-xs dark:bg-[#6E90D1]"
                  : "text-[#58616D] hover:text-[#181A1D] dark:text-[#A0ABB8] dark:hover:text-[#F0F2F5]"
              }`}
            >
              Document Style
            </button>
          </div>

          {/* ── TAB 1: CONTENT EDITOR ────────────────────────────────────────── */}
          {editorTab === "content" && (
            <div className="rounded-2xl border border-[#9CA6B2]/20 bg-white/70 p-5 shadow-xs backdrop-blur-md dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/70 flex flex-col space-y-5">
              {/* Section selector chips */}
              <div className="flex flex-wrap gap-1.5 pb-2 border-b border-[#9CA6B2]/15">
                {doc.section_order.map((secKey) => {
                  const meta = SECTION_METADATA[secKey] || { label: secKey };
                  const isVisible = doc.section_visibility[secKey] ?? true;
                  const isActive = activeSectionId === secKey;
                  return (
                    <button
                      key={secKey}
                      type="button"
                      onClick={() => setActiveSectionId(secKey)}
                      className={`flex items-center space-x-1.5 rounded-lg px-2.5 py-1 text-[11px] font-medium transition ${
                        isActive
                          ? "bg-[#181A1D] text-white dark:bg-[#F0F2F5] dark:text-[#181A1D]"
                          : isVisible
                          ? "bg-[#9CA6B2]/10 text-[#58616D] hover:bg-[#9CA6B2]/20 dark:text-[#A0ABB8]"
                          : "bg-transparent text-[#9CA6B2]/60 line-through"
                      }`}
                    >
                      <span>{meta.label.split(" ")[0]}</span>
                      {!isVisible && <span className="text-[9px]">hidden</span>}
                    </button>
                  );
                })}
              </div>

              {/* ── Sub-Editor: Contact Info ── */}
              {activeSectionId === "contact" && (
                <div className="space-y-3.5">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[#5477B8] dark:text-[#6E90D1]">
                      Contact Details & Headline
                    </h3>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-medium text-[#58616D] dark:text-[#A0ABB8]">
                        Full Name *
                      </label>
                      <input
                        type="text"
                        value={doc.content.contact.name}
                        onChange={(e) =>
                          updateContent((prev) => ({
                            ...prev,
                            contact: { ...prev.contact, name: e.target.value },
                          }))
                        }
                        placeholder="e.g. Jordan Miller"
                        className="mt-1 w-full rounded-xl border border-[#9CA6B2]/30 bg-white/60 px-3 py-1.5 text-xs text-[#181A1D] focus:border-[#5477B8] focus:outline-hidden dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/60 dark:text-[#F0F2F5]"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-[#58616D] dark:text-[#A0ABB8]">
                        Professional Headline
                      </label>
                      <input
                        type="text"
                        value={doc.content.contact.headline || ""}
                        onChange={(e) =>
                          updateContent((prev) => ({
                            ...prev,
                            contact: { ...prev.contact, headline: e.target.value },
                          }))
                        }
                        placeholder="e.g. Senior Software Architect"
                        className="mt-1 w-full rounded-xl border border-[#9CA6B2]/30 bg-white/60 px-3 py-1.5 text-xs text-[#181A1D] focus:border-[#5477B8] focus:outline-hidden dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/60 dark:text-[#F0F2F5]"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-[#58616D] dark:text-[#A0ABB8]">
                        Email Address
                      </label>
                      <input
                        type="email"
                        value={doc.content.contact.email || ""}
                        onChange={(e) =>
                          updateContent((prev) => ({
                            ...prev,
                            contact: { ...prev.contact, email: e.target.value },
                          }))
                        }
                        placeholder="jordan@example.com"
                        className="mt-1 w-full rounded-xl border border-[#9CA6B2]/30 bg-white/60 px-3 py-1.5 text-xs text-[#181A1D] focus:border-[#5477B8] focus:outline-hidden dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/60 dark:text-[#F0F2F5]"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-[#58616D] dark:text-[#A0ABB8]">
                        Phone Number
                      </label>
                      <input
                        type="text"
                        value={doc.content.contact.phone || ""}
                        onChange={(e) =>
                          updateContent((prev) => ({
                            ...prev,
                            contact: { ...prev.contact, phone: e.target.value },
                          }))
                        }
                        placeholder="+1 (555) 019-2831"
                        className="mt-1 w-full rounded-xl border border-[#9CA6B2]/30 bg-white/60 px-3 py-1.5 text-xs text-[#181A1D] focus:border-[#5477B8] focus:outline-hidden dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/60 dark:text-[#F0F2F5]"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-[#58616D] dark:text-[#A0ABB8]">
                        Location (City, State / Country)
                      </label>
                      <input
                        type="text"
                        value={doc.content.contact.location || ""}
                        onChange={(e) =>
                          updateContent((prev) => ({
                            ...prev,
                            contact: { ...prev.contact, location: e.target.value },
                          }))
                        }
                        placeholder="San Francisco, CA"
                        className="mt-1 w-full rounded-xl border border-[#9CA6B2]/30 bg-white/60 px-3 py-1.5 text-xs text-[#181A1D] focus:border-[#5477B8] focus:outline-hidden dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/60 dark:text-[#F0F2F5]"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-[#58616D] dark:text-[#A0ABB8]">
                        Portfolio Website
                      </label>
                      <input
                        type="text"
                        value={doc.content.contact.website || ""}
                        onChange={(e) =>
                          updateContent((prev) => ({
                            ...prev,
                            contact: { ...prev.contact, website: e.target.value },
                          }))
                        }
                        placeholder="https://jordan.dev"
                        className="mt-1 w-full rounded-xl border border-[#9CA6B2]/30 bg-white/60 px-3 py-1.5 text-xs text-[#181A1D] focus:border-[#5477B8] focus:outline-hidden dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/60 dark:text-[#F0F2F5]"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-[#58616D] dark:text-[#A0ABB8]">
                        LinkedIn Profile URL
                      </label>
                      <input
                        type="text"
                        value={doc.content.contact.linkedin || ""}
                        onChange={(e) =>
                          updateContent((prev) => ({
                            ...prev,
                            contact: { ...prev.contact, linkedin: e.target.value },
                          }))
                        }
                        placeholder="https://linkedin.com/in/jordan"
                        className="mt-1 w-full rounded-xl border border-[#9CA6B2]/30 bg-white/60 px-3 py-1.5 text-xs text-[#181A1D] focus:border-[#5477B8] focus:outline-hidden dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/60 dark:text-[#F0F2F5]"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-[#58616D] dark:text-[#A0ABB8]">
                        GitHub Profile URL
                      </label>
                      <input
                        type="text"
                        value={doc.content.contact.github || ""}
                        onChange={(e) =>
                          updateContent((prev) => ({
                            ...prev,
                            contact: { ...prev.contact, github: e.target.value },
                          }))
                        }
                        placeholder="https://github.com/jordan"
                        className="mt-1 w-full rounded-xl border border-[#9CA6B2]/30 bg-white/60 px-3 py-1.5 text-xs text-[#181A1D] focus:border-[#5477B8] focus:outline-hidden dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/60 dark:text-[#F0F2F5]"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* ── Sub-Editor: Professional Summary ── */}
              {activeSectionId === "summary" && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[#5477B8] dark:text-[#6E90D1]">
                      Executive & Professional Summary
                    </h3>
                    <span className="text-[10px] text-[#838F9E]">
                      {doc.content.summary?.trim().split(/\s+/).filter(Boolean).length || 0} words
                    </span>
                  </div>
                  <textarea
                    rows={5}
                    value={doc.content.summary || ""}
                    onChange={(e) =>
                      updateContent((prev) => ({
                        ...prev,
                        summary: e.target.value,
                      }))
                    }
                    placeholder="Provide a concise 3-4 sentence overview of your core domain specialization, leadership background, and notable achievements..."
                    className="w-full rounded-xl border border-[#9CA6B2]/30 bg-white/60 p-3 text-xs text-[#181A1D] leading-relaxed focus:border-[#5477B8] focus:outline-hidden dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/60 dark:text-[#F0F2F5]"
                  />
                </div>
              )}

              {/* ── Sub-Editor: Work Experience ── */}
              {activeSectionId === "experience" && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[#5477B8] dark:text-[#6E90D1]">
                      Work Experience Entries ({doc.content.experience.length})
                    </h3>
                    <button
                      type="button"
                      onClick={() =>
                        updateContent((prev) => ({
                          ...prev,
                          experience: [
                            ...prev.experience,
                            {
                              id: `exp_${Date.now()}`,
                              company: "New Company",
                              role: "Role / Title",
                              location: "City, State",
                              start_date: "2022",
                              end_date: "Present",
                              current: true,
                              bullets: ["Engineered core capability resulting in quantifiable efficiency increase."],
                            },
                          ],
                        }))
                      }
                      className="rounded-lg bg-[#5477B8]/10 px-2.5 py-1 text-[11px] font-semibold text-[#5477B8] hover:bg-[#5477B8]/20 dark:text-[#6E90D1]"
                    >
                      + Add Position
                    </button>
                  </div>

                  {doc.content.experience.length === 0 ? (
                    <p className="text-xs text-[#838F9E] italic text-center py-4">
                      No experience entries yet. Click &quot;+ Add Position&quot; above to create one.
                    </p>
                  ) : (
                    <div className="space-y-4">
                      {doc.content.experience.map((item, idx) => (
                        <div
                          key={item.id}
                          className="rounded-xl border border-[#9CA6B2]/20 bg-white/40 p-3.5 space-y-3 dark:border-[#9CA6B2]/15 dark:bg-[#1A1E24]/40"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[11px] font-bold text-[#181A1D] dark:text-[#F0F2F5]">
                              #{idx + 1} {item.role || "Untitled"} at {item.company || "Company"}
                            </span>
                            <button
                              type="button"
                              onClick={() =>
                                updateContent((prev) => ({
                                  ...prev,
                                  experience: prev.experience.filter((_, i) => i !== idx),
                                }))
                              }
                              className="text-[10px] text-red-500 hover:underline"
                            >
                              Delete
                            </button>
                          </div>

                          <div className="grid grid-cols-2 gap-2">
                            <input
                              type="text"
                              value={item.company}
                              onChange={(e) =>
                                updateContent((prev) => {
                                  const updated = [...prev.experience];
                                  updated[idx] = { ...updated[idx], company: e.target.value };
                                  return { ...prev, experience: updated };
                                })
                              }
                              placeholder="Company"
                              className="rounded-lg border border-[#9CA6B2]/30 px-2.5 py-1 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                            />
                            <input
                              type="text"
                              value={item.role}
                              onChange={(e) =>
                                updateContent((prev) => {
                                  const updated = [...prev.experience];
                                  updated[idx] = { ...updated[idx], role: e.target.value };
                                  return { ...prev, experience: updated };
                                })
                              }
                              placeholder="Role / Title"
                              className="rounded-lg border border-[#9CA6B2]/30 px-2.5 py-1 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                            />
                            <input
                              type="text"
                              value={item.start_date || ""}
                              onChange={(e) =>
                                updateContent((prev) => {
                                  const updated = [...prev.experience];
                                  updated[idx] = { ...updated[idx], start_date: e.target.value };
                                  return { ...prev, experience: updated };
                                })
                              }
                              placeholder="Start Date (e.g. 2021)"
                              className="rounded-lg border border-[#9CA6B2]/30 px-2.5 py-1 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                            />
                            <input
                              type="text"
                              value={item.end_date || ""}
                              onChange={(e) =>
                                updateContent((prev) => {
                                  const updated = [...prev.experience];
                                  updated[idx] = { ...updated[idx], end_date: e.target.value };
                                  return { ...prev, experience: updated };
                                })
                              }
                              placeholder="End Date (or Present)"
                              className="rounded-lg border border-[#9CA6B2]/30 px-2.5 py-1 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                            />
                          </div>

                          {/* Bullets */}
                          <div className="space-y-1.5 pt-1">
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-semibold text-[#58616D] dark:text-[#A0ABB8]">
                                Impact Bullets
                              </span>
                              <button
                                type="button"
                                onClick={() =>
                                  updateContent((prev) => {
                                    const updated = [...prev.experience];
                                    updated[idx] = {
                                      ...updated[idx],
                                      bullets: [...updated[idx].bullets, "New accomplishment statement."],
                                    };
                                    return { ...prev, experience: updated };
                                  })
                                }
                                className="text-[10px] text-[#5477B8] hover:underline dark:text-[#6E90D1]"
                              >
                                + Add Bullet
                              </button>
                            </div>

                            {item.bullets.map((bullet, bIdx) => (
                              <div key={bIdx} className="flex items-center space-x-1.5">
                                <span className="text-[10px] text-[#9CA6B2]">•</span>
                                <input
                                  type="text"
                                  value={bullet}
                                  onChange={(e) =>
                                    updateContent((prev) => {
                                      const updated = [...prev.experience];
                                      const bullets = [...updated[idx].bullets];
                                      bullets[bIdx] = e.target.value;
                                      updated[idx] = { ...updated[idx], bullets };
                                      return { ...prev, experience: updated };
                                    })
                                  }
                                  className="flex-1 rounded-md border border-[#9CA6B2]/25 px-2 py-1 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                                />
                                <button
                                  type="button"
                                  onClick={() =>
                                    updateContent((prev) => {
                                      const updated = [...prev.experience];
                                      const bullets = updated[idx].bullets.filter((_, i) => i !== bIdx);
                                      updated[idx] = { ...updated[idx], bullets };
                                      return { ...prev, experience: updated };
                                    })
                                  }
                                  className="text-xs text-[#9CA6B2] hover:text-red-500 px-1"
                                  title="Remove bullet"
                                >
                                  ×
                                </button>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* ── Sub-Editor: Technical Projects ── */}
              {activeSectionId === "projects" && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[#5477B8] dark:text-[#6E90D1]">
                      Projects ({doc.content.projects.length})
                    </h3>
                    <button
                      type="button"
                      onClick={() =>
                        updateContent((prev) => ({
                          ...prev,
                          projects: [
                            ...prev.projects,
                            {
                              id: `proj_${Date.now()}`,
                              title: "Project Name",
                              role: "Lead Developer",
                              url: "https://github.com/...",
                              start_date: "2023",
                              end_date: "2024",
                              bullets: ["Built microservice application utilizing modern asynchronous stack."],
                              tech_stack: ["Python", "FastAPI", "PostgreSQL"],
                            },
                          ],
                        }))
                      }
                      className="rounded-lg bg-[#5477B8]/10 px-2.5 py-1 text-[11px] font-semibold text-[#5477B8] hover:bg-[#5477B8]/20 dark:text-[#6E90D1]"
                    >
                      + Add Project
                    </button>
                  </div>

                  {doc.content.projects.map((proj, idx) => (
                    <div
                      key={proj.id}
                      className="rounded-xl border border-[#9CA6B2]/20 bg-white/40 p-3.5 space-y-3 dark:border-[#9CA6B2]/15 dark:bg-[#1A1E24]/40"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold text-[#181A1D] dark:text-[#F0F2F5]">
                          #{idx + 1} {proj.title || "Project"}
                        </span>
                        <button
                          type="button"
                          onClick={() =>
                            updateContent((prev) => ({
                              ...prev,
                              projects: prev.projects.filter((_, i) => i !== idx),
                            }))
                          }
                          className="text-[10px] text-red-500 hover:underline"
                        >
                          Delete
                        </button>
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        <input
                          type="text"
                          value={proj.title}
                          onChange={(e) =>
                            updateContent((prev) => {
                              const updated = [...prev.projects];
                              updated[idx] = { ...updated[idx], title: e.target.value };
                              return { ...prev, projects: updated };
                            })
                          }
                          placeholder="Project Title"
                          className="rounded-lg border border-[#9CA6B2]/30 px-2.5 py-1 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                        />
                        <input
                          type="text"
                          value={proj.role || ""}
                          onChange={(e) =>
                            updateContent((prev) => {
                              const updated = [...prev.projects];
                              updated[idx] = { ...updated[idx], role: e.target.value };
                              return { ...prev, projects: updated };
                            })
                          }
                          placeholder="Your Role"
                          className="rounded-lg border border-[#9CA6B2]/30 px-2.5 py-1 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                        />
                        <input
                          type="text"
                          value={proj.url || ""}
                          onChange={(e) =>
                            updateContent((prev) => {
                              const updated = [...prev.projects];
                              updated[idx] = { ...updated[idx], url: e.target.value };
                              return { ...prev, projects: updated };
                            })
                          }
                          placeholder="Repository or Demo URL"
                          className="rounded-lg border border-[#9CA6B2]/30 px-2.5 py-1 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                        />
                        <input
                          type="text"
                          value={proj.tech_stack.join(", ")}
                          onChange={(e) =>
                            updateContent((prev) => {
                              const updated = [...prev.projects];
                              const tech = e.target.value
                                .split(",")
                                .map((s) => s.trim())
                                .filter(Boolean);
                              updated[idx] = { ...updated[idx], tech_stack: tech };
                              return { ...prev, projects: updated };
                            })
                          }
                          placeholder="Tech stack (comma-separated)"
                          className="rounded-lg border border-[#9CA6B2]/30 px-2.5 py-1 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                        />
                      </div>

                      {/* Bullets */}
                      <div className="space-y-1.5 pt-1">
                        {proj.bullets.map((bullet, bIdx) => (
                          <div key={bIdx} className="flex items-center space-x-1.5">
                            <span className="text-[10px] text-[#9CA6B2]">•</span>
                            <input
                              type="text"
                              value={bullet}
                              onChange={(e) =>
                                updateContent((prev) => {
                                  const updated = [...prev.projects];
                                  const bullets = [...updated[idx].bullets];
                                  bullets[bIdx] = e.target.value;
                                  updated[idx] = { ...updated[idx], bullets };
                                  return { ...prev, projects: updated };
                                })
                              }
                              className="flex-1 rounded-md border border-[#9CA6B2]/25 px-2 py-1 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                            />
                            <button
                              type="button"
                              onClick={() =>
                                updateContent((prev) => {
                                  const updated = [...prev.projects];
                                  const bullets = updated[idx].bullets.filter((_, i) => i !== bIdx);
                                  updated[idx] = { ...updated[idx], bullets };
                                  return { ...prev, projects: updated };
                                })
                              }
                              className="text-xs text-[#9CA6B2] hover:text-red-500 px-1"
                            >
                              ×
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* ── Sub-Editor: Skills ── */}
              {activeSectionId === "skills" && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[#5477B8] dark:text-[#6E90D1]">
                      Skill Categories ({doc.content.skills.length})
                    </h3>
                    <button
                      type="button"
                      onClick={() =>
                        updateContent((prev) => ({
                          ...prev,
                          skills: [
                            ...prev.skills,
                            {
                              id: `cat_${Date.now()}`,
                              category: "Languages & Frameworks",
                              skills: ["TypeScript", "Python", "React", "Next.js"],
                            },
                          ],
                        }))
                      }
                      className="rounded-lg bg-[#5477B8]/10 px-2.5 py-1 text-[11px] font-semibold text-[#5477B8] hover:bg-[#5477B8]/20 dark:text-[#6E90D1]"
                    >
                      + Add Category
                    </button>
                  </div>

                  {doc.content.skills.map((skillGroup, idx) => (
                    <div
                      key={skillGroup.id}
                      className="rounded-xl border border-[#9CA6B2]/20 bg-white/40 p-3.5 space-y-2 dark:border-[#9CA6B2]/15 dark:bg-[#1A1E24]/40"
                    >
                      <div className="flex items-center justify-between">
                        <input
                          type="text"
                          value={skillGroup.category}
                          onChange={(e) =>
                            updateContent((prev) => {
                              const updated = [...prev.skills];
                              updated[idx] = { ...updated[idx], category: e.target.value };
                              return { ...prev, skills: updated };
                            })
                          }
                          className="font-bold text-xs bg-transparent border-b border-[#9CA6B2]/30 px-1 py-0.5 focus:border-[#5477B8] focus:outline-hidden dark:text-[#F0F2F5]"
                        />
                        <button
                          type="button"
                          onClick={() =>
                            updateContent((prev) => ({
                              ...prev,
                              skills: prev.skills.filter((_, i) => i !== idx),
                            }))
                          }
                          className="text-[10px] text-red-500 hover:underline"
                        >
                          Delete
                        </button>
                      </div>

                      <textarea
                        rows={2}
                        value={skillGroup.skills.join(", ")}
                        onChange={(e) =>
                          updateContent((prev) => {
                            const updated = [...prev.skills];
                            const list = e.target.value
                              .split(",")
                              .map((s) => s.trim())
                              .filter(Boolean);
                            updated[idx] = { ...updated[idx], skills: list };
                            return { ...prev, skills: updated };
                          })
                        }
                        placeholder="Comma-separated skill tokens (e.g. Docker, Kubernetes, AWS, Terraform)"
                        className="w-full rounded-lg border border-[#9CA6B2]/25 bg-white/60 p-2 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                      />
                    </div>
                  ))}
                </div>
              )}

              {/* ── Sub-Editor: Education ── */}
              {activeSectionId === "education" && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[#5477B8] dark:text-[#6E90D1]">
                      Education Credentials ({doc.content.education.length})
                    </h3>
                    <button
                      type="button"
                      onClick={() =>
                        updateContent((prev) => ({
                          ...prev,
                          education: [
                            ...prev.education,
                            {
                              id: `edu_${Date.now()}`,
                              institution: "University Name",
                              degree: "B.S. in Computer Science",
                              field_of_study: "Software Engineering",
                              start_date: "2018",
                              end_date: "2022",
                              gpa: "",
                              highlights: [],
                            },
                          ],
                        }))
                      }
                      className="rounded-lg bg-[#5477B8]/10 px-2.5 py-1 text-[11px] font-semibold text-[#5477B8] hover:bg-[#5477B8]/20 dark:text-[#6E90D1]"
                    >
                      + Add Education
                    </button>
                  </div>

                  {doc.content.education.map((edu, idx) => (
                    <div
                      key={edu.id}
                      className="rounded-xl border border-[#9CA6B2]/20 bg-white/40 p-3.5 space-y-2 dark:border-[#9CA6B2]/15 dark:bg-[#1A1E24]/40"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold text-[#181A1D] dark:text-[#F0F2F5]">
                          #{idx + 1} {edu.institution || "Institution"}
                        </span>
                        <button
                          type="button"
                          onClick={() =>
                            updateContent((prev) => ({
                              ...prev,
                              education: prev.education.filter((_, i) => i !== idx),
                            }))
                          }
                          className="text-[10px] text-red-500 hover:underline"
                        >
                          Delete
                        </button>
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        <input
                          type="text"
                          value={edu.institution}
                          onChange={(e) =>
                            updateContent((prev) => {
                              const updated = [...prev.education];
                              updated[idx] = { ...updated[idx], institution: e.target.value };
                              return { ...prev, education: updated };
                            })
                          }
                          placeholder="Institution"
                          className="rounded-lg border border-[#9CA6B2]/30 px-2.5 py-1 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                        />
                        <input
                          type="text"
                          value={edu.degree || ""}
                          onChange={(e) =>
                            updateContent((prev) => {
                              const updated = [...prev.education];
                              updated[idx] = { ...updated[idx], degree: e.target.value };
                              return { ...prev, education: updated };
                            })
                          }
                          placeholder="Degree / Major"
                          className="rounded-lg border border-[#9CA6B2]/30 px-2.5 py-1 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                        />
                        <input
                          type="text"
                          value={edu.start_date || ""}
                          onChange={(e) =>
                            updateContent((prev) => {
                              const updated = [...prev.education];
                              updated[idx] = { ...updated[idx], start_date: e.target.value };
                              return { ...prev, education: updated };
                            })
                          }
                          placeholder="Start Date"
                          className="rounded-lg border border-[#9CA6B2]/30 px-2.5 py-1 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                        />
                        <input
                          type="text"
                          value={edu.end_date || ""}
                          onChange={(e) =>
                            updateContent((prev) => {
                              const updated = [...prev.education];
                              updated[idx] = { ...updated[idx], end_date: e.target.value };
                              return { ...prev, education: updated };
                            })
                          }
                          placeholder="End Date"
                          className="rounded-lg border border-[#9CA6B2]/30 px-2.5 py-1 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* ── Sub-Editor: Certifications ── */}
              {activeSectionId === "certifications" && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[#5477B8] dark:text-[#6E90D1]">
                      Certifications ({doc.content.certifications.length})
                    </h3>
                    <button
                      type="button"
                      onClick={() =>
                        updateContent((prev) => ({
                          ...prev,
                          certifications: [
                            ...prev.certifications,
                            {
                              id: `cert_${Date.now()}`,
                              name: "AWS Certified Solutions Architect",
                              issuer: "Amazon Web Services",
                              issue_date: "2023",
                              expiry_date: "2026",
                              url: "https://aws.amazon.com/...",
                            },
                          ],
                        }))
                      }
                      className="rounded-lg bg-[#5477B8]/10 px-2.5 py-1 text-[11px] font-semibold text-[#5477B8] hover:bg-[#5477B8]/20 dark:text-[#6E90D1]"
                    >
                      + Add Certificate
                    </button>
                  </div>

                  {doc.content.certifications.map((cert, idx) => (
                    <div
                      key={cert.id}
                      className="rounded-xl border border-[#9CA6B2]/20 bg-white/40 p-3.5 space-y-2 dark:border-[#9CA6B2]/15 dark:bg-[#1A1E24]/40"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold text-[#181A1D] dark:text-[#F0F2F5]">
                          #{idx + 1} {cert.name || "Certification"}
                        </span>
                        <button
                          type="button"
                          onClick={() =>
                            updateContent((prev) => ({
                              ...prev,
                              certifications: prev.certifications.filter((_, i) => i !== idx),
                            }))
                          }
                          className="text-[10px] text-red-500 hover:underline"
                        >
                          Delete
                        </button>
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        <input
                          type="text"
                          value={cert.name}
                          onChange={(e) =>
                            updateContent((prev) => {
                              const updated = [...prev.certifications];
                              updated[idx] = { ...updated[idx], name: e.target.value };
                              return { ...prev, certifications: updated };
                            })
                          }
                          placeholder="Certificate Name"
                          className="rounded-lg border border-[#9CA6B2]/30 px-2.5 py-1 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                        />
                        <input
                          type="text"
                          value={cert.issuer || ""}
                          onChange={(e) =>
                            updateContent((prev) => {
                              const updated = [...prev.certifications];
                              updated[idx] = { ...updated[idx], issuer: e.target.value };
                              return { ...prev, certifications: updated };
                            })
                          }
                          placeholder="Issuing Organization"
                          className="rounded-lg border border-[#9CA6B2]/30 px-2.5 py-1 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                        />
                        <input
                          type="text"
                          value={cert.issue_date || ""}
                          onChange={(e) =>
                            updateContent((prev) => {
                              const updated = [...prev.certifications];
                              updated[idx] = { ...updated[idx], issue_date: e.target.value };
                              return { ...prev, certifications: updated };
                            })
                          }
                          placeholder="Issue Year"
                          className="rounded-lg border border-[#9CA6B2]/30 px-2.5 py-1 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                        />
                        <input
                          type="text"
                          value={cert.url || ""}
                          onChange={(e) =>
                            updateContent((prev) => {
                              const updated = [...prev.certifications];
                              updated[idx] = { ...updated[idx], url: e.target.value };
                              return { ...prev, certifications: updated };
                            })
                          }
                          placeholder="Verification Link"
                          className="rounded-lg border border-[#9CA6B2]/30 px-2.5 py-1 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* ── Sub-Editor: Additional Sections ── */}
              {activeSectionId === "additional" && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[#5477B8] dark:text-[#6E90D1]">
                      Additional Honors & Activities
                    </h3>
                    <button
                      type="button"
                      onClick={() =>
                        updateContent((prev) => ({
                          ...prev,
                          additional: [
                            ...prev.additional,
                            {
                              id: `add_${Date.now()}`,
                              section_title: "Awards & Recognition",
                              bullets: ["Recognized for exceptional engineering delivery."],
                            },
                          ],
                        }))
                      }
                      className="rounded-lg bg-[#5477B8]/10 px-2.5 py-1 text-[11px] font-semibold text-[#5477B8] hover:bg-[#5477B8]/20 dark:text-[#6E90D1]"
                    >
                      + Add Section
                    </button>
                  </div>

                  {doc.content.additional.map((item, idx) => (
                    <div
                      key={item.id}
                      className="rounded-xl border border-[#9CA6B2]/20 bg-white/40 p-3.5 space-y-2 dark:border-[#9CA6B2]/15 dark:bg-[#1A1E24]/40"
                    >
                      <div className="flex items-center justify-between">
                        <input
                          type="text"
                          value={item.section_title}
                          onChange={(e) =>
                            updateContent((prev) => {
                              const updated = [...prev.additional];
                              updated[idx] = { ...updated[idx], section_title: e.target.value };
                              return { ...prev, additional: updated };
                            })
                          }
                          className="font-bold text-xs bg-transparent border-b border-[#9CA6B2]/30 px-1 py-0.5 focus:border-[#5477B8] focus:outline-hidden dark:text-[#F0F2F5]"
                        />
                        <button
                          type="button"
                          onClick={() =>
                            updateContent((prev) => ({
                              ...prev,
                              additional: prev.additional.filter((_, i) => i !== idx),
                            }))
                          }
                          className="text-[10px] text-red-500 hover:underline"
                        >
                          Delete
                        </button>
                      </div>

                      <div className="space-y-1 pt-1">
                        {item.bullets.map((b, bIdx) => (
                          <div key={bIdx} className="flex items-center space-x-1.5">
                            <span className="text-[10px] text-[#9CA6B2]">•</span>
                            <input
                              type="text"
                              value={b}
                              onChange={(e) =>
                                updateContent((prev) => {
                                  const updated = [...prev.additional];
                                  const bullets = [...updated[idx].bullets];
                                  bullets[bIdx] = e.target.value;
                                  updated[idx] = { ...updated[idx], bullets };
                                  return { ...prev, additional: updated };
                                })
                              }
                              className="flex-1 rounded-md border border-[#9CA6B2]/25 px-2 py-1 text-xs dark:border-[#9CA6B2]/20 dark:bg-[#14171C]"
                            />
                            <button
                              type="button"
                              onClick={() =>
                                updateContent((prev) => {
                                  const updated = [...prev.additional];
                                  const bullets = updated[idx].bullets.filter((_, i) => i !== bIdx);
                                  updated[idx] = { ...updated[idx], bullets };
                                  return { ...prev, additional: updated };
                                })
                              }
                              className="text-xs text-[#9CA6B2] hover:text-red-500 px-1"
                            >
                              ×
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── TAB 2: HIERARCHY & REORDERING ─────────────────────────────────── */}
          {editorTab === "layout" && (
            <div className="rounded-2xl border border-[#9CA6B2]/20 bg-white/70 p-5 shadow-xs backdrop-blur-md dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/70 space-y-4">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#5477B8] dark:text-[#6E90D1]">
                  Section Sequence & Visibility
                </h3>
                <p className="mt-1 text-[11px] text-[#838F9E] dark:text-[#64707D]">
                  Reorder sections using the arrows. Toggle the eye icon to hide or show sections on your resume.
                </p>
              </div>

              <div className="space-y-2">
                {doc.section_order.map((secKey, idx) => {
                  const meta = SECTION_METADATA[secKey] || { label: secKey };
                  const isVisible = doc.section_visibility[secKey] ?? true;

                  return (
                    <div
                      key={secKey}
                      className={`flex items-center justify-between rounded-xl border p-3 transition ${
                        isVisible
                          ? "border-[#9CA6B2]/20 bg-white/60 dark:border-[#9CA6B2]/15 dark:bg-[#1A1E24]/60"
                          : "border-dashed border-[#9CA6B2]/30 bg-[#9CA6B2]/5 opacity-60 dark:bg-[#14171C]/40"
                      }`}
                    >
                      <div className="flex items-center space-x-2.5">
                        <span className="flex h-6 w-6 items-center justify-center rounded-md bg-[#9CA6B2]/15 text-[10px] font-bold text-[#58616D] dark:text-[#A0ABB8]">
                          {idx + 1}
                        </span>
                        <span className="text-xs font-semibold text-[#181A1D] dark:text-[#F0F2F5]">
                          {meta.label}
                        </span>
                      </div>

                      <div className="flex items-center space-x-1.5">
                        {/* Move Up */}
                        <button
                          type="button"
                          onClick={() => moveSection(idx, "up")}
                          disabled={idx === 0}
                          className="rounded-md border border-[#9CA6B2]/30 p-1 text-[#58616D] hover:bg-[#F3F5F6] disabled:opacity-30 dark:border-[#9CA6B2]/20 dark:text-[#A0ABB8] dark:hover:bg-[#14171C]"
                          title="Move section up"
                        >
                          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                          </svg>
                        </button>

                        {/* Move Down */}
                        <button
                          type="button"
                          onClick={() => moveSection(idx, "down")}
                          disabled={idx === doc.section_order.length - 1}
                          className="rounded-md border border-[#9CA6B2]/30 p-1 text-[#58616D] hover:bg-[#F3F5F6] disabled:opacity-30 dark:border-[#9CA6B2]/20 dark:text-[#A0ABB8] dark:hover:bg-[#14171C]"
                          title="Move section down"
                        >
                          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>

                        {/* Visibility Toggle */}
                        <button
                          type="button"
                          onClick={() => toggleSectionVisibility(secKey)}
                          className={`rounded-md border p-1 transition ${
                            isVisible
                              ? "border-[#5477B8]/30 bg-[#5477B8]/10 text-[#5477B8] dark:text-[#6E90D1]"
                              : "border-[#9CA6B2]/30 bg-transparent text-[#9CA6B2]"
                          }`}
                          title={isVisible ? "Section is visible" : "Section is hidden"}
                        >
                          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            {isVisible ? (
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                              />
                            ) : (
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18"
                              />
                            )}
                          </svg>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ── TAB 3: DOCUMENT STYLE & TYPOGRAPHY ───────────────────────────────── */}
          {editorTab === "style" && (
            <div className="rounded-2xl border border-[#9CA6B2]/20 bg-white/70 p-5 shadow-xs backdrop-blur-md dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/70">
              <div className="rounded-xl border border-[#5477B8]/25 bg-[#5477B8]/5 p-4 dark:border-[#6E90D1]/25 dark:bg-[#6E90D1]/10">
                <h3 className="text-sm font-bold text-[#254B78] dark:text-[#9DB8EB]">ATS Professional</h3>
                <p className="mt-1 text-xs leading-relaxed text-[#58616D] dark:text-[#A0ABB8]">
                  One fixed, single-column A4 layout with readable sans-serif text, standard margins, dark text, and restrained navy headings. The same resume content is used in the preview, PDF, and DOCX exports.
                </p>
              </div>
              <ul className="mt-4 space-y-2 text-xs text-[#58616D] dark:text-[#A0ABB8]">
                <li>• Standard section headings and native text paragraphs</li>
                <li>• Consistent spacing and page margins</li>
                <li>• No charts, columns, meters, or decorative color controls</li>
              </ul>
              <p className="mt-4 text-[11px] leading-relaxed text-[#838F9E]">
                ATS parsing differs across employers. Review the exported file before submitting it.
              </p>
            </div>
          )}
        {/* ── RIGHT PANE: Live A4 Document Preview (Col 6-12) ────────────────── */}
        </div>
        <div className="lg:col-span-7 flex flex-col space-y-3">
          {/* Canvas Floating Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[#9CA6B2]/20 bg-white/80 p-2 shadow-xs backdrop-blur-md dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/80">
            {/* Zoom Controls */}
            <div className="flex items-center space-x-1.5">
              <span className="text-[11px] font-medium text-[#58616D] dark:text-[#A0ABB8] pl-2">
                Zoom:
              </span>
              <button
                type="button"
                onClick={() => setZoomLevel((z) => Math.max(0.4, Number((z - 0.1).toFixed(2))))}
                className="rounded-md border border-[#9CA6B2]/30 px-2 py-0.5 text-xs text-[#58616D] hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/20 dark:text-[#A0ABB8]"
                title="Zoom Out"
              >
                −
              </button>
              <span className="text-xs font-mono font-semibold text-[#181A1D] dark:text-[#F0F2F5] min-w-[3rem] text-center">
                {Math.round(zoomLevel * 100)}%
              </span>
              <button
                type="button"
                onClick={() => setZoomLevel((z) => Math.min(1.4, Number((z + 0.1).toFixed(2))))}
                className="rounded-md border border-[#9CA6B2]/30 px-2 py-0.5 text-xs text-[#58616D] hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/20 dark:text-[#A0ABB8]"
                title="Zoom In"
              >
                +
              </button>
              <button
                type="button"
                onClick={() => setZoomLevel(0.85)}
                className="rounded-md border border-[#9CA6B2]/20 px-2 py-0.5 text-[10px] text-[#838F9E] hover:bg-[#F3F5F6] dark:text-[#64707D]"
              >
                Fit
              </button>
            </div>

            {onProceedToExport && (
              <button
                type="button"
                onClick={onProceedToExport}
                className="rounded-lg bg-[#5477B8] px-2.5 py-1 text-[11px] font-semibold text-white shadow-xs transition hover:bg-[#43629C] dark:bg-[#6E90D1]"
              >
                Open Export Center
              </button>
            )}
          </div>

          {/* Live Document Canvas Box */}
          <div className="relative min-h-[750px] overflow-auto rounded-2xl border border-[#9CA6B2]/25 bg-[#E5E9EE] p-6 dark:border-[#9CA6B2]/15 dark:bg-[#0B0D0F] flex justify-center items-start">
            <div
              style={{
                transform: `scale(${zoomLevel})`,
                transformOrigin: "top center",
                transition: "transform 150ms ease-out",
                width: "794px", // Standard A4 width at 96 DPI
                minHeight: "1123px", // Standard A4 height at 96 DPI
              }}
              className={`bg-white text-black shadow-2xl rounded-xs select-text ${fontFamilyClass} ${fontSizeClass} ${marginClass} ${lineSpacingClass}`}
            >
              {/* ── ATS PROFESSIONAL: CANONICAL SINGLE-COLUMN TEMPLATE ─────────────────────────────── */}
              {doc.template_id === "ats_professional" && (
                <div className="space-y-4 font-sans">
                  {/* ATS Professional Header */}
                  {doc.section_visibility.contact !== false && (
                    <div className="pb-3 border-b border-neutral-200">
                      <div className="flex justify-between items-end">
                        <div>
                          <h1
                            className="text-2xl font-bold tracking-tight"
                            style={{ color: doc.template_config.accent_color }}
                          >
                            {doc.content.contact.name || "Your Name"}
                          </h1>
                          {doc.content.contact.headline && (
                            <p className="text-xs text-neutral-500 font-medium">
                              {doc.content.contact.headline}
                            </p>
                          )}
                        </div>
                        <div className="text-right text-[10px] text-neutral-600 space-y-0.5">
                          {doc.content.contact.email && <div>{doc.content.contact.email}</div>}
                          {doc.content.contact.phone && <div>{doc.content.contact.phone}</div>}
                          {doc.content.contact.location && <div>{doc.content.contact.location}</div>}
                        </div>
                      </div>
                      <div className="mt-2 flex gap-3 text-[10px] text-neutral-500">
                        {doc.content.contact.linkedin && <span>{doc.content.contact.linkedin}</span>}
                        {doc.content.contact.github && <span>{doc.content.contact.github}</span>}
                      </div>
                    </div>
                  )}

                  {/* Sections */}
                  {doc.section_order.map((secKey) => {
                    if (secKey === "contact") return null;
                    if (doc.section_visibility[secKey] === false) return null;

                    if (secKey === "summary" && doc.content.summary) {
                      return (
                        <div key="summary" className="space-y-1">
                          <h3
                            className="text-[11px] font-bold uppercase tracking-widest"
                            style={{ color: doc.template_config.accent_color }}
                          >
                            Summary
                          </h3>
                          <p className="text-neutral-700 leading-relaxed">
                            {doc.content.summary}
                          </p>
                        </div>
                      );
                    }

                    if (secKey === "experience" && doc.content.experience.length > 0) {
                      return (
                        <div key="experience" className="space-y-3">
                          <h3
                            className="text-[11px] font-bold uppercase tracking-widest"
                            style={{ color: doc.template_config.accent_color }}
                          >
                            Experience
                          </h3>
                          <div className="space-y-2.5">
                            {doc.content.experience.map((item) => (
                              <div key={item.id} className="space-y-1">
                                <div className="flex justify-between items-baseline">
                                  <div>
                                    <span className="font-semibold text-neutral-900">{item.role}</span>
                                    <span className="text-neutral-500 text-[11px]"> · {item.company}</span>
                                  </div>
                                  <span className="text-[10px] text-neutral-400">
                                    {item.start_date} – {item.end_date || (item.current ? "Present" : "")}
                                  </span>
                                </div>
                                <ul className="list-disc pl-4 space-y-0.5 text-neutral-700">
                                  {item.bullets.map((b, bi) => (
                                    <li key={bi}>{b}</li>
                                  ))}
                                </ul>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    }

                    if (secKey === "projects" && doc.content.projects.length > 0) {
                      return (
                        <div key="projects" className="space-y-2.5">
                          <h3
                            className="text-[11px] font-bold uppercase tracking-widest"
                            style={{ color: doc.template_config.accent_color }}
                          >
                            Projects
                          </h3>
                          <div className="space-y-2">
                            {doc.content.projects.map((proj) => (
                              <div key={proj.id} className="space-y-0.5">
                                <div className="flex justify-between items-baseline">
                                  <span className="font-semibold text-neutral-900">{proj.title}</span>
                                  <span className="text-[10px] text-neutral-400">{proj.url}</span>
                                </div>
                                <ul className="list-disc pl-4 space-y-0.5 text-neutral-700">
                                  {proj.bullets.map((b, bi) => (
                                    <li key={bi}>{b}</li>
                                  ))}
                                </ul>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    }

                    if (secKey === "skills" && doc.content.skills.length > 0) {
                      return (
                        <div key="skills" className="space-y-1">
                          <h3
                            className="text-[11px] font-bold uppercase tracking-widest"
                            style={{ color: doc.template_config.accent_color }}
                          >
                            Skills
                          </h3>
                          <div className="space-y-1 text-neutral-700">
                            {doc.content.skills.map((sg) => (
                              <div key={sg.id} className="flex">
                                <span className="font-medium min-w-[120px] text-neutral-900">{sg.category}:</span>
                                <span>{sg.skills.join(", ")}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    }

                    if (secKey === "education" && doc.content.education.length > 0) {
                      return (
                        <div key="education" className="space-y-1">
                          <h3
                            className="text-[11px] font-bold uppercase tracking-widest"
                            style={{ color: doc.template_config.accent_color }}
                          >
                            Education
                          </h3>
                          <div className="space-y-1">
                            {doc.content.education.map((edu) => (
                              <div key={edu.id} className="flex justify-between items-baseline">
                                <div>
                                  <span className="font-semibold text-neutral-900">{edu.institution}</span>
                                  <span className="text-neutral-500 text-[11px]"> · {edu.degree}</span>
                                </div>
                                <span className="text-[10px] text-neutral-400">
                                  {edu.start_date} – {edu.end_date}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    }

                    if (secKey === "certifications" && doc.content.certifications.length > 0) {
                      return (
                        <div key="certifications" className="space-y-1">
                          <h3
                            className="text-[11px] font-bold uppercase tracking-widest"
                            style={{ color: doc.template_config.accent_color }}
                          >
                            Certifications
                          </h3>
                          <div className="space-y-0.5">
                            {doc.content.certifications.map((c) => (
                              <div key={c.id} className="flex justify-between items-baseline">
                                <span className="font-medium text-neutral-900">{c.name}</span>
                                <span className="text-[10px] text-neutral-500">{c.issuer}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    }

                    if (secKey === "additional" && doc.content.additional.length > 0) {
                      return (
                        <div key="additional" className="space-y-1">
                          {doc.content.additional.map((item) => (
                            <div key={item.id} className="space-y-1">
                              <h3
                                className="text-[11px] font-bold uppercase tracking-widest"
                                style={{ color: doc.template_config.accent_color }}
                              >
                                {item.section_title}
                              </h3>
                              <ul className="list-disc pl-4 space-y-0.5 text-neutral-700">
                                {item.bullets.map((b, bi) => (
                                  <li key={bi}>{b}</li>
                                ))}
                              </ul>
                            </div>
                          ))}
                        </div>
                      );
                    }

                    return null;
                  })}
                </div>
              )}

            </div>
          </div>
        </div>
      </div>

      {/* ── RESET CONFIRMATION MODAL ───────────────────────────────────────── */}
      {showResetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-2xl border border-[#9CA6B2]/20 bg-white p-6 shadow-2xl dark:border-[#9CA6B2]/15 dark:bg-[#14171C]">
            <h3 className="text-base font-bold text-[#181A1D] dark:text-[#F0F2F5]">
              Reset Resume Canvas
            </h3>
            <p className="mt-2 text-xs text-[#58616D] dark:text-[#A0ABB8]">
              Choose how you want to reset your working resume document:
            </p>

            <div className="mt-4 space-y-2.5">
              <button
                type="button"
                onClick={() => handleResetDocument("reviewed_resume")}
                disabled={isResetting}
                className="w-full rounded-xl border border-[#5477B8]/30 bg-[#5477B8]/5 p-3 text-left transition hover:bg-[#5477B8]/10 dark:border-[#6E90D1]/30 dark:bg-[#6E90D1]/10"
              >
                <div className="text-xs font-bold text-[#5477B8] dark:text-[#6E90D1]">
                  Re-import from Reviewed Resume
                </div>
                <div className="mt-0.5 text-[11px] text-[#58616D] dark:text-[#A0ABB8]">
                  Restores extracted profile data and any improvements accepted in the Improvement Studio.
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleResetDocument("empty")}
                disabled={isResetting}
                className="w-full rounded-xl border border-red-500/20 bg-red-500/5 p-3 text-left transition hover:bg-red-500/10 dark:border-red-500/20 dark:bg-red-500/10"
              >
                <div className="text-xs font-bold text-red-600 dark:text-red-400">
                  Reset to Blank Canvas
                </div>
                <div className="mt-0.5 text-[11px] text-[#58616D] dark:text-[#A0ABB8]">
                  Clears all sections so you can start completely from scratch.
                </div>
              </button>
            </div>

            <div className="mt-5 flex justify-end">
              <button
                type="button"
                onClick={() => setShowResetModal(false)}
                className="rounded-xl border border-[#9CA6B2]/30 px-4 py-2 text-xs font-medium text-[#58616D] hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/20 dark:text-[#A0ABB8]"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
