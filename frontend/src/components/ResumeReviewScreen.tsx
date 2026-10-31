"use client";

import React, { useState, useCallback } from "react";
import type { ParsedResume, StructuredProfile } from "./ResumeUploadSurface";

interface ResumeReviewScreenProps {
  resume: ParsedResume;
  onSaveCorrections: (updated: StructuredProfile) => Promise<void>;
  onReset: () => void;
  onProceed: (profile: StructuredProfile, mode: "ats_readiness" | "job_match", jobDescription: string) => void;
  analysisMode: "ats_readiness" | "job_match";
  jobDescription: string;
}

// ── Micro badge for uncertainty indicators ─────────────────────────────────
function UncertainBadge() {
  return (
    <span className="ml-1.5 inline-flex items-center rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
      Review
    </span>
  );
}

// ── Section header component ───────────────────────────────────────────────
function SectionHeader({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div className="flex items-center space-x-2 border-b border-[#9CA6B2]/20 pb-2 mb-3">
      <span className="text-[#5477B8] dark:text-[#6E90D1]">{icon}</span>
      <h3 className="text-xs font-bold uppercase tracking-widest text-[#58616D] dark:text-[#A0ABB8]">
        {label}
      </h3>
    </div>
  );
}

// ── Editable text field ────────────────────────────────────────────────────
function EditableField({
  label,
  value,
  placeholder,
  uncertain,
  onChange,
  multiline = false,
}: {
  label: string;
  value: string;
  placeholder?: string;
  uncertain?: boolean;
  onChange: (val: string) => void;
  multiline?: boolean;
}) {
  const [focused, setFocused] = useState(false);
  const baseClasses =
    "w-full rounded-lg border px-3 py-2 text-xs text-[#181A1D] transition-colors dark:text-[#F0F2F5] placeholder-[#9CA6B2] dark:placeholder-[#64707D] bg-white/80 dark:bg-[#1A1E24]/80";
  const borderClasses = focused
    ? "border-[#5477B8] dark:border-[#6E90D1] ring-1 ring-[#5477B8]/30 dark:ring-[#6E90D1]/30"
    : uncertain
    ? "border-amber-300 dark:border-amber-700"
    : "border-[#9CA6B2]/30 dark:border-[#9CA6B2]/20 hover:border-[#9CA6B2]/60";

  return (
    <div className="space-y-1">
      <label className="flex items-center text-[10px] font-semibold uppercase tracking-wider text-[#838F9E] dark:text-[#64707D]">
        {label}
        {uncertain && <UncertainBadge />}
      </label>
      {multiline ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={placeholder}
          rows={3}
          className={`${baseClasses} ${borderClasses} resize-none leading-relaxed`}
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={placeholder}
          className={`${baseClasses} ${borderClasses}`}
        />
      )}
    </div>
  );
}

// ── Editable list (skills, experience bullets, etc.) ───────────────────────
function EditableList({
  items,
  onChange,
  placeholder,
  maxItems = 50,
}: {
  items: string[];
  onChange: (items: string[]) => void;
  placeholder?: string;
  maxItems?: number;
}) {
  const [newItem, setNewItem] = useState("");

  const handleRemove = (index: number) => {
    const updated = items.filter((_, i) => i !== index);
    onChange(updated);
  };

  const handleEdit = (index: number, value: string) => {
    const updated = [...items];
    updated[index] = value;
    onChange(updated);
  };

  const handleAdd = () => {
    const trimmed = newItem.trim();
    if (trimmed && items.length < maxItems) {
      onChange([...items, trimmed]);
      setNewItem("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAdd();
    }
  };

  return (
    <div className="space-y-1.5">
      {items.map((item, idx) => (
        <div key={idx} className="flex items-center gap-1.5 group">
          <input
            type="text"
            value={item}
            onChange={(e) => handleEdit(idx, e.target.value)}
            className="flex-1 rounded-lg border border-[#9CA6B2]/25 bg-white/60 px-2.5 py-1.5 text-xs text-[#181A1D] transition-colors hover:border-[#9CA6B2]/50 focus:border-[#5477B8] focus:outline-none focus:ring-1 focus:ring-[#5477B8]/20 dark:border-[#9CA6B2]/15 dark:bg-[#1A1E24]/60 dark:text-[#F0F2F5] dark:focus:border-[#6E90D1]"
          />
          <button
            type="button"
            onClick={() => handleRemove(idx)}
            className="flex-shrink-0 rounded p-1 text-[#9CA6B2] opacity-0 group-hover:opacity-100 transition-opacity hover:text-[#B33939] dark:text-[#64707D] dark:hover:text-[#D9534F]"
            aria-label={`Remove item: ${item}`}
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      ))}

      {items.length < maxItems && (
        <div className="flex items-center gap-1.5 mt-1">
          <input
            type="text"
            value={newItem}
            onChange={(e) => setNewItem(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder || "Add item… (Enter to save)"}
            className="flex-1 rounded-lg border border-dashed border-[#9CA6B2]/30 bg-transparent px-2.5 py-1.5 text-xs text-[#838F9E] placeholder-[#9CA6B2]/60 transition-colors focus:border-[#5477B8] focus:outline-none focus:ring-1 focus:ring-[#5477B8]/20 dark:border-[#9CA6B2]/20 dark:text-[#A0ABB8] dark:focus:border-[#6E90D1]"
          />
          <button
            type="button"
            onClick={handleAdd}
            disabled={!newItem.trim()}
            className="flex-shrink-0 rounded-lg border border-[#9CA6B2]/30 bg-white/60 px-2 py-1.5 text-[10px] font-semibold text-[#5477B8] transition hover:bg-[#5477B8]/10 disabled:opacity-40 disabled:cursor-not-allowed dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/60 dark:text-[#6E90D1] dark:hover:bg-[#6E90D1]/10"
          >
            Add
          </button>
        </div>
      )}
    </div>
  );
}

// ── Warning Banner ─────────────────────────────────────────────────────────
function WarningBanner({ warnings }: { warnings: string[] }) {
  const [dismissed, setDismissed] = useState(false);
  if (!warnings.length || dismissed) return null;

  return (
    <div className="rounded-xl border border-amber-300/50 bg-amber-50/80 p-3.5 backdrop-blur-sm dark:border-amber-700/40 dark:bg-amber-900/15">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2">
          <svg className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600 dark:text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400 mb-1">
              Parser notes ({warnings.length})
            </p>
            <ul className="space-y-0.5">
              {warnings.map((w, i) => (
                <li key={i} className="text-xs text-amber-700/80 dark:text-amber-400/80">
                  {w}
                </li>
              ))}
            </ul>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setDismissed(true)}
          className="text-[10px] font-semibold text-amber-600 hover:underline dark:text-amber-400 flex-shrink-0"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────
export function ResumeReviewScreen({
  resume,
  onSaveCorrections,
  onReset,
  onProceed,
  analysisMode,
  jobDescription,
}: ResumeReviewScreenProps) {
  const [profile, setProfile] = useState<StructuredProfile>(() => ({
    ...resume.structured_data,
    contact: { ...resume.structured_data.contact },
  }));
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const updateContact = useCallback((field: string, value: string) => {
    setProfile((prev) => ({
      ...prev,
      contact: { ...prev.contact, [field]: value || null },
    }));
    setSaveSuccess(false);
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      await onSaveCorrections(profile);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch {
      setSaveError("Failed to save changes. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const modeLabel =
    analysisMode === "ats_readiness" ? "Proceed to ATS Readiness Audit" : "Proceed to Job Match Analysis";

  const fileSizeKb = (resume.file_size / 1024).toFixed(1);

  return (
    <div className="flex flex-col space-y-5 w-full">
      {/* ── Top metadata bar ── */}
      <div className="flex items-center justify-between rounded-xl border border-[#9CA6B2]/20 bg-white/50 px-4 py-2.5 backdrop-blur-sm dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/50">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#5477B8]/10 text-[#5477B8] dark:bg-[#6E90D1]/15 dark:text-[#6E90D1]">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <p className="text-xs font-semibold text-[#181A1D] dark:text-[#F0F2F5]">
              {resume.filename}
            </p>
            <p className="text-[10px] text-[#838F9E] dark:text-[#64707D]">
              {resume.file_type.toUpperCase()} · {fileSizeKb} KB · Parsed successfully
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onReset}
          className="text-xs font-medium text-[#838F9E] hover:text-[#5477B8] transition-colors dark:text-[#64707D] dark:hover:text-[#6E90D1]"
          id="resetResumeBtn"
        >
          Upload different file
        </button>
      </div>

      {/* ── Parser warnings ── */}
      {profile.warnings.length > 0 && (
        <WarningBanner warnings={profile.warnings} />
      )}

      {/* ── Review heading ── */}
      <div>
        <p className="text-[10px] font-bold uppercase tracking-widest text-[#9CA6B2] dark:text-[#64707D]">
          Step 2 of 3
        </p>
        <h2 className="mt-0.5 text-lg font-bold text-[#181A1D] dark:text-[#F0F2F5]">
          Review & Correct Extracted Details
        </h2>
        <p className="mt-1 text-xs text-[#58616D] dark:text-[#A0ABB8]">
          The sections below were automatically extracted. Verify accuracy and correct any parsing errors before proceeding.
          Fields marked <UncertainBadge /> may need your attention.
        </p>
      </div>

      {/* ── Contact Information ── */}
      <div className="rounded-xl border border-[#9CA6B2]/20 bg-white/60 p-5 backdrop-blur-sm dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/60">
        <SectionHeader
          label="Contact Information"
          icon={
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          }
        />
        <div className="grid gap-3 sm:grid-cols-2">
          <EditableField
            label="Full Name"
            value={profile.contact.name || ""}
            placeholder="Your name as it appears on the resume"
            uncertain={profile.contact.uncertainty?.name}
            onChange={(v) => updateContact("name", v)}
          />
          <EditableField
            label="Email"
            value={profile.contact.email || ""}
            placeholder="your@email.com"
            uncertain={profile.contact.uncertainty?.email}
            onChange={(v) => updateContact("email", v)}
          />
          <EditableField
            label="Phone"
            value={profile.contact.phone || ""}
            placeholder="+1 (555) 000-0000"
            uncertain={profile.contact.uncertainty?.phone}
            onChange={(v) => updateContact("phone", v)}
          />
          <EditableField
            label="Location"
            value={profile.contact.location || ""}
            placeholder="City, State / Country (optional)"
            onChange={(v) => updateContact("location", v)}
          />
        </div>
        {profile.contact.urls.length > 0 && (
          <div className="mt-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-[#838F9E] dark:text-[#64707D] mb-1.5">
              Detected Links
            </p>
            <div className="flex flex-wrap gap-1.5">
              {profile.contact.urls.map((url, i) => (
                <a
                  key={i}
                  href={url.startsWith("http") ? url : `https://${url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-full border border-[#5477B8]/30 bg-[#5477B8]/8 px-2.5 py-0.5 text-[10px] text-[#5477B8] hover:bg-[#5477B8]/15 transition-colors dark:border-[#6E90D1]/30 dark:text-[#6E90D1]"
                >
                  {url}
                </a>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Professional Summary ── */}
      {(profile.summary !== null || profile.summary === "") && (
        <div className="rounded-xl border border-[#9CA6B2]/20 bg-white/60 p-5 backdrop-blur-sm dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/60">
          <SectionHeader
            label="Professional Summary"
            icon={
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h7" />
              </svg>
            }
          />
          <EditableField
            label="Summary"
            value={profile.summary || ""}
            placeholder="No summary section detected. Add one here if applicable."
            onChange={(v) => {
              setProfile((p) => ({ ...p, summary: v || null }));
              setSaveSuccess(false);
            }}
            multiline
          />
        </div>
      )}

      {/* ── Skills ── */}
      <div className="rounded-xl border border-[#9CA6B2]/20 bg-white/60 p-5 backdrop-blur-sm dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/60">
        <SectionHeader
          label={`Skills (${profile.skills.length})`}
          icon={
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          }
        />
        {profile.skills.length === 0 && (
          <p className="mb-2 text-xs text-[#9CA6B2] dark:text-[#64707D]">
            No skills were detected. Add them below.
          </p>
        )}
        <EditableList
          items={profile.skills}
          onChange={(items) => {
            setProfile((p) => ({ ...p, skills: items }));
            setSaveSuccess(false);
          }}
          placeholder="Add a skill… (Enter to save)"
          maxItems={60}
        />
      </div>

      {/* ── Work Experience ── */}
      <div className="rounded-xl border border-[#9CA6B2]/20 bg-white/60 p-5 backdrop-blur-sm dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/60">
        <SectionHeader
          label={`Work Experience (${profile.experience.length} lines)`}
          icon={
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          }
        />
        {profile.experience.length === 0 && (
          <p className="mb-2 text-xs text-[#9CA6B2] dark:text-[#64707D]">
            No experience section detected. The section header may have a non-standard label.
          </p>
        )}
        <EditableList
          items={profile.experience}
          onChange={(items) => {
            setProfile((p) => ({ ...p, experience: items }));
            setSaveSuccess(false);
          }}
          placeholder="Add experience entry…"
        />
      </div>

      {/* ── Education ── */}
      <div className="rounded-xl border border-[#9CA6B2]/20 bg-white/60 p-5 backdrop-blur-sm dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/60">
        <SectionHeader
          label={`Education (${profile.education.length} entries)`}
          icon={
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path d="M12 14l9-5-9-5-9 5 9 5z" />
              <path d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 14l9-5-9-5-9 5 9 5zm0 0l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14zm-4 6v-7.5l4-2.222" />
            </svg>
          }
        />
        {profile.education.length === 0 && (
          <p className="mb-2 text-xs text-[#9CA6B2] dark:text-[#64707D]">
            No education section detected. Add entries below.
          </p>
        )}
        <EditableList
          items={profile.education}
          onChange={(items) => {
            setProfile((p) => ({ ...p, education: items }));
            setSaveSuccess(false);
          }}
          placeholder="e.g. B.S. Computer Science — University (2018 – 2022)"
        />
      </div>

      {/* ── Projects (collapsible if empty) ── */}
      {profile.projects.length > 0 && (
        <div className="rounded-xl border border-[#9CA6B2]/20 bg-white/60 p-5 backdrop-blur-sm dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/60">
          <SectionHeader
            label={`Projects (${profile.projects.length})`}
            icon={
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            }
          />
          <EditableList
            items={profile.projects}
            onChange={(items) => {
              setProfile((p) => ({ ...p, projects: items }));
              setSaveSuccess(false);
            }}
            placeholder="Add a project entry…"
          />
        </div>
      )}

      {/* ── Certifications (collapsible if empty) ── */}
      {profile.certifications.length > 0 && (
        <div className="rounded-xl border border-[#9CA6B2]/20 bg-white/60 p-5 backdrop-blur-sm dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/60">
          <SectionHeader
            label={`Certifications (${profile.certifications.length})`}
            icon={
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
              </svg>
            }
          />
          <EditableList
            items={profile.certifications}
            onChange={(items) => {
              setProfile((p) => ({ ...p, certifications: items }));
              setSaveSuccess(false);
            }}
            placeholder="Add certification…"
          />
        </div>
      )}

      {/* ── Save + Proceed Actions ── */}
      <div className="flex flex-col gap-2.5">
        {saveError && (
          <div className="rounded-lg border border-[#B33939]/30 bg-[#B33939]/10 p-2.5 text-xs text-[#B33939] dark:border-[#D9534F]/30 dark:bg-[#D9534F]/10 dark:text-[#D9534F]">
            {saveError}
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-2.5">
          {/* Save corrections */}
          <button
            id="saveCorrectionsBtn"
            type="button"
            onClick={handleSave}
            disabled={saving}
            className={`flex items-center justify-center space-x-2 rounded-xl border px-5 py-2.5 text-xs font-semibold transition-all ${
              saveSuccess
                ? "border-[#2E7D5A]/40 bg-[#2E7D5A]/10 text-[#2E7D5A] dark:border-[#4EAD82]/40 dark:text-[#4EAD82]"
                : "border-[#9CA6B2]/30 bg-white/60 text-[#181A1D] hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/60 dark:text-[#F0F2F5] dark:hover:bg-[#20252D]"
            } disabled:opacity-60 disabled:cursor-not-allowed`}
          >
            {saving ? (
              <>
                <svg className="h-3.5 w-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span>Saving…</span>
              </>
            ) : saveSuccess ? (
              <>
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                <span>Saved</span>
              </>
            ) : (
              <span>Save Corrections</span>
            )}
          </button>

          {/* Proceed to analysis */}
          <button
            id="proceedToAnalysisBtn"
            type="button"
            onClick={() => onProceed(profile, analysisMode, jobDescription)}
            className="flex flex-1 items-center justify-center space-x-2 rounded-xl bg-[#5477B8] py-2.5 px-5 text-xs font-semibold text-white shadow-sm transition hover:bg-[#43629C] dark:bg-[#6E90D1] dark:hover:bg-[#85A3DC]"
          >
            <span>{modeLabel}</span>
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </button>
        </div>

        <p className="text-center text-[10px] text-[#9CA6B2] dark:text-[#64707D]">
          Changes are stored only for your active anonymous session and are automatically deleted after 24h of inactivity.
        </p>
      </div>
    </div>
  );
}
