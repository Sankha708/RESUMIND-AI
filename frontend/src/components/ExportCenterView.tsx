"use client";

import React, { useState, useEffect, useCallback } from "react";
import { getApiBaseUrl } from "@/lib/api";
import { ParsedResume } from "./ResumeUploadSurface";

export interface ExportStatusData {
  has_builder_document: boolean;
  candidate_name: string;
  builder_version: number;
  template_id: string;
  builder_updated_at: string | null;
  has_ats_assessment: boolean;
  ats_score: number | null;
  has_job_match: boolean;
  job_match_title: string | null;
  job_match_score: number | null;
  suggestions_count: number;
  accepted_suggestions_count: number;
}

interface ReanalysisSectionDiff {
  key: string;
  label: string;
  before: string;
  after: string;
  change: string;
  visible_before: boolean;
  visible_after: boolean;
}

interface ReanalysisDimensionDelta {
  label: string;
  weight: number;
  baseline_score: number;
  revised_score: number;
  delta: number;
}

interface ReanalysisData {
  available: boolean;
  reason: string | null;
  builder_version: number | null;
  ats: {
    baseline_score: number;
    revised_score: number;
    delta: number;
    dimensions: Record<string, ReanalysisDimensionDelta>;
  } | null;
  job_match: {
    job_title: string | null;
    baseline_score: number | null;
    revised_score: number | null;
    delta: number | null;
    unavailable_reason: string | null;
    matched_before: number;
    matched_after: number;
    partially_supported_before: number;
    partially_supported_after: number;
    not_demonstrated_before: number;
    not_demonstrated_after: number;
  } | null;
  changed_sections: ReanalysisSectionDiff[];
  resolved_findings: string[];
  limitations: string[];
}

interface ExportCenterViewProps {
  resume: ParsedResume | null;
  onBackToBuilder: () => void;
  onBackToAssessments: () => void;
  onUploadNew: () => void;
}

const API_BASE = getApiBaseUrl();

const TEMPLATE_META = {
  name: "ATS Professional",
  style: "Single-column layout • Clear headings • Selectable text",
};

function serviceErrorMessage(error: unknown, connectionMessage: string, fallbackMessage: string): string {
  if (error instanceof TypeError) return connectionMessage;
  if (error instanceof Error) {
    if (/failed to fetch|networkerror|network request failed|load failed/i.test(error.message)) {
      return connectionMessage;
    }
    return error.message;
  }
  return fallbackMessage;
}

export function ExportCenterView({
  resume,
  onBackToBuilder,
  onBackToAssessments,
  onUploadNew,
}: ExportCenterViewProps) {
  const [statusData, setStatusData] = useState<ExportStatusData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Download states for each button: "idle" | "downloading" | "success" | "error"
  const [pdfState, setPdfState] = useState<"idle" | "downloading" | "success" | "error">("idle");
  const [docxState, setDocxState] = useState<"idle" | "downloading" | "success" | "error">("idle");
  const [reportState, setReportState] = useState<"idle" | "downloading" | "success" | "error">("idle");

  const [downloadNotice, setDownloadNotice] = useState<string | null>(null);
  const [reanalysis, setReanalysis] = useState<ReanalysisData | null>(null);
  const [reanalysisLoading, setReanalysisLoading] = useState<boolean>(true);
  const [reanalysisError, setReanalysisError] = useState<string | null>(null);

  // ── Load Export Status ───────────────────────────────────────────────────────
  const fetchExportStatus = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const response = await fetch(`${API_BASE}/api/export/status`, {
        credentials: "include",
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to fetch export metadata (${response.status})`);
      }

      const data: ExportStatusData = await response.json();
      setStatusData(data);
    } catch (err: unknown) {
      setErrorMessage(serviceErrorMessage(
        err,
        "Backend connection failed. Export status is unavailable; check that the API is running, then retry.",
        "Failed to connect to export service.",
      ));
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchReanalysis = useCallback(async () => {
    setReanalysisLoading(true);
    setReanalysisError(null);
    try {
      const response = await fetch(`${API_BASE}/api/reanalysis`, { credentials: "include" });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to load resume comparison (${response.status})`);
      }
      setReanalysis(await response.json());
    } catch (err: unknown) {
      setReanalysisError(serviceErrorMessage(
        err,
        "Backend connection failed. Differential comparison is unavailable; check that the API is running, then retry.",
        "Failed to load resume comparison.",
      ));
    } finally {
      setReanalysisLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    async function loadStatus() {
      try {
        const response = await fetch(`${API_BASE}/api/export/status`, {
          credentials: "include",
        });

        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(err.detail || `Failed to fetch export metadata (${response.status})`);
        }

        const data: ExportStatusData = await response.json();
        if (!ignore) {
          setStatusData(data);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setErrorMessage(serviceErrorMessage(
            err,
            "Backend connection failed. Export status is unavailable; check that the API is running, then retry.",
            "Failed to connect to export service.",
          ));
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }
    async function loadReanalysis() {
      try {
        const response = await fetch(`${API_BASE}/api/reanalysis`, { credentials: "include" });
        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(err.detail || `Failed to load resume comparison (${response.status})`);
        }
        const data: ReanalysisData = await response.json();
        if (!ignore) setReanalysis(data);
      } catch (err: unknown) {
        if (!ignore) {
          setReanalysisError(serviceErrorMessage(
            err,
            "Backend connection failed. Differential comparison is unavailable; check that the API is running, then retry.",
            "Failed to load resume comparison.",
          ));
        }
      } finally {
        if (!ignore) setReanalysisLoading(false);
      }
    }
    loadStatus();
    loadReanalysis();
    return () => {
      ignore = true;
    };
  }, [fetchReanalysis]);

  // ── File Download Trigger Helper ───────────────────────────────────────────
  const triggerDownload = async (
    endpoint: string,
    defaultFilename: string,
    stateSetter: React.Dispatch<React.SetStateAction<"idle" | "downloading" | "success" | "error">>
  ) => {
    stateSetter("downloading");
    setDownloadNotice(null);
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        credentials: "include",
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `Server returned error (${response.status})`);
      }

      // Resolve filename from Content-Disposition header if present
      let filename = defaultFilename;
      const disposition = response.headers.get("content-disposition");
      if (disposition && disposition.includes("filename=")) {
        const match = disposition.match(/filename="?([^";]+)"?/);
        if (match && match[1]) {
          filename = match[1];
        }
      }

      const blob = await response.blob();
      const objectUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(objectUrl);

      stateSetter("success");
      setDownloadNotice(`Successfully downloaded: ${filename}`);
      setTimeout(() => stateSetter("idle"), 4000);
    } catch (err: unknown) {
      stateSetter("error");
      const msg = err instanceof Error ? err.message : "Unexpected download failure.";
      setDownloadNotice(`Download failed: ${msg}`);
      setTimeout(() => stateSetter("idle"), 5000);
    }
  };

  if (isLoading) {
    return (
      <div className="flex min-h-[450px] flex-col items-center justify-center space-y-4">
        <div className="h-10 w-10 animate-spin rounded-full border-3 border-[#5477B8]/20 border-t-[#5477B8] dark:border-[#6E90D1]/20 dark:border-t-[#6E90D1]" />
        <p className="text-sm font-medium text-[#58616D] dark:text-[#A0ABB8]">
          Preparing Export Center & verifying document artifacts...
        </p>
      </div>
    );
  }

  if (errorMessage && !statusData) {
    return (
      <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-8 text-center backdrop-blur-md">
        <h3 className="text-base font-bold text-red-600 dark:text-red-400">Export Center Unavailable</h3>
        <p className="mt-2 text-xs text-[#58616D] dark:text-[#A0ABB8]">{errorMessage}</p>
        <button
          onClick={fetchExportStatus}
          className="mt-4 rounded-xl bg-[#5477B8] px-4 py-2 text-xs font-semibold text-white hover:bg-[#43629C]"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  const hasDoc = statusData?.has_builder_document;
  const templateMeta = TEMPLATE_META;

  return (
    <div className="flex flex-col space-y-8">
      {/* ── Top Header & Navigation ─────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-[#181A1D] sm:text-3xl dark:text-[#F0F2F5]">
            Multi-Format Export & Diagnostic Hub
          </h2>
          <p className="text-xs text-[#58616D] dark:text-[#A0ABB8]">
            Download an ATS-oriented, text-based PDF and editable Word DOCX resume, plus a separate diagnostic audit report.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={onBackToBuilder}
            className="flex items-center space-x-1.5 rounded-xl border border-[#9CA6B2]/30 bg-white/70 px-4 py-2 text-xs font-semibold text-[#181A1D] shadow-xs transition hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/70 dark:text-[#F0F2F5]"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
            <span>Resume Builder</span>
          </button>
          <button
            type="button"
            onClick={onBackToAssessments}
            className="flex items-center space-x-1.5 rounded-xl border border-[#9CA6B2]/30 bg-white/70 px-4 py-2 text-xs font-semibold text-[#58616D] shadow-xs transition hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/70 dark:text-[#A0ABB8]"
          >
            <span>Assessments</span>
          </button>
          <button
            type="button"
            onClick={onUploadNew}
            className="flex items-center space-x-1.5 rounded-xl border border-[#9CA6B2]/30 bg-white/70 px-4 py-2 text-xs font-semibold text-[#58616D] shadow-xs transition hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/70 dark:text-[#A0ABB8]"
          >
            <span>Upload New</span>
          </button>
        </div>
      </div>

      {/* ── Document Metadata Banner ────────────────────────────────────────── */}
      <div className="rounded-2xl border border-[#9CA6B2]/20 bg-white/70 p-5 shadow-xs backdrop-blur-md dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/70">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-bold text-[#181A1D] dark:text-[#F0F2F5]">
                {statusData?.candidate_name || resume?.structured_data?.contact?.name || resume?.filename || "Active Resume Draft"}
              </span>
              <span className="rounded-md bg-[#5477B8]/10 px-2 py-0.5 text-[10px] font-bold text-[#5477B8] dark:bg-[#6E90D1]/15 dark:text-[#6E90D1]">
                v{statusData?.builder_version || 1} • Saved
              </span>
              <span className="rounded-md bg-[#9CA6B2]/10 px-2 py-0.5 text-[10px] font-medium text-[#58616D] dark:text-[#A0ABB8]">
                {templateMeta.name}
              </span>
            </div>
            <p className="text-xs text-[#58616D] dark:text-[#A0ABB8]">
              {templateMeta.style}
              {statusData?.builder_updated_at && (
                <span> • Last saved {new Date(statusData.builder_updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
              )}
            </p>
          </div>

          <div className="flex items-center space-x-3 text-xs">
            {statusData?.has_ats_assessment && (
              <div className="flex items-center space-x-1.5 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-2.5 py-1 text-emerald-700 dark:text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                <span className="font-semibold">ATS Score: {statusData.ats_score}/100</span>
              </div>
            )}
            {statusData?.has_job_match && (
              <div className="flex items-center space-x-1.5 rounded-lg border border-[#5477B8]/20 bg-[#5477B8]/5 px-2.5 py-1 text-[#5477B8] dark:text-[#6E90D1]">
                <span className="h-1.5 w-1.5 rounded-full bg-[#5477B8]" />
                <span className="font-semibold">Job Match: {statusData.job_match_score ? `${statusData.job_match_score}/100` : "Evaluated"}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Status Toast Notice ──────────────────────────────────────────────── */}
      <section
        aria-labelledby="differential-reanalysis-heading"
        className="rounded-2xl border border-[#5477B8]/25 bg-white/70 p-5 shadow-xs backdrop-blur-md dark:border-[#6E90D1]/20 dark:bg-[#14171C]/70"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#5477B8] dark:text-[#6E90D1]">
              Saved revision comparison
            </span>
            <h3 id="differential-reanalysis-heading" className="mt-1 text-lg font-bold text-[#181A1D] dark:text-[#F0F2F5]">
              Differential Reanalysis
            </h3>
            <p className="mt-1 max-w-2xl text-xs leading-relaxed text-[#58616D] dark:text-[#A0ABB8]">
              Compares the saved ATS baseline with the current Builder PDF. Typography and template-only changes are excluded.
            </p>
          </div>
          <button
            type="button"
            onClick={fetchReanalysis}
            disabled={reanalysisLoading}
            className="rounded-xl border border-[#9CA6B2]/30 bg-white/70 px-3 py-2 text-xs font-semibold text-[#181A1D] transition hover:bg-[#F3F5F6] disabled:opacity-50 dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/70 dark:text-[#F0F2F5]"
          >
            {reanalysisLoading ? "Comparing..." : "Refresh comparison"}
          </button>
        </div>

        {reanalysisLoading && !reanalysis ? (
          <p className="mt-4 text-xs text-[#58616D] dark:text-[#A0ABB8]">Checking for a saved baseline and Builder revision...</p>
        ) : reanalysisError ? (
          <p role="alert" className="mt-4 rounded-xl border border-red-500/25 bg-red-500/5 p-3 text-xs text-red-700 dark:text-red-400">
            {reanalysisError}
          </p>
        ) : reanalysis && !reanalysis.available ? (
          <div className="mt-4 rounded-xl border border-[#9CA6B2]/25 bg-[#F3F5F6]/70 p-4 dark:bg-[#0E1013]/60">
            <p className="text-sm font-semibold text-[#181A1D] dark:text-[#F0F2F5]">Comparison unavailable</p>
            <p className="mt-1 text-xs leading-relaxed text-[#58616D] dark:text-[#A0ABB8]">{reanalysis.reason}</p>
            <p className="mt-2 text-[11px] leading-relaxed text-[#838F9E] dark:text-[#84909E]">
              Run ATS Readiness to save the baseline, make and save a content change in Resume Builder, then refresh this comparison.
            </p>
          </div>
        ) : reanalysis?.ats ? (
          <div className="mt-5 space-y-5">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {[
                { label: "Saved baseline", value: reanalysis.ats.baseline_score },
                { label: "Current Builder PDF", value: reanalysis.ats.revised_score },
                { label: "ATS Readiness change", value: reanalysis.ats.delta, delta: true },
              ].map((item) => (
                <div key={item.label} className="rounded-xl border border-[#9CA6B2]/20 bg-white/70 p-4 dark:bg-[#0E1013]/50">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-[#838F9E]">{item.label}</p>
                  <p className={`mt-1 text-2xl font-bold ${item.delta ? (item.value > 0 ? "text-emerald-700 dark:text-emerald-400" : item.value < 0 ? "text-amber-700 dark:text-amber-400" : "text-[#181A1D] dark:text-[#F0F2F5]") : "text-[#181A1D] dark:text-[#F0F2F5]"}`}>
                    {item.delta && item.value > 0 ? "+" : ""}{item.value.toFixed(1)}<span className="ml-1 text-xs font-medium text-[#838F9E]">/100</span>
                  </p>
                </div>
              ))}
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#58616D] dark:text-[#A0ABB8]">ATS dimensions</h4>
              <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {Object.entries(reanalysis.ats.dimensions).map(([key, dimension]) => (
                  <div key={key} className="rounded-xl border border-[#9CA6B2]/20 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-xs font-semibold text-[#181A1D] dark:text-[#F0F2F5]">{dimension.label}</span>
                      <span className={`text-xs font-bold ${dimension.delta > 0 ? "text-emerald-700 dark:text-emerald-400" : dimension.delta < 0 ? "text-amber-700 dark:text-amber-400" : "text-[#58616D] dark:text-[#A0ABB8]"}`}>
                        {dimension.delta > 0 ? "+" : ""}{dimension.delta.toFixed(1)}
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] text-[#838F9E]">
                      {dimension.baseline_score.toFixed(1)} → {dimension.revised_score.toFixed(1)} · {Math.round(dimension.weight * 100)}% weight
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {reanalysis.job_match && (
              <div className="rounded-xl border border-[#5477B8]/20 bg-[#5477B8]/5 p-4 dark:bg-[#5477B8]/10">
                <h4 className="text-xs font-bold text-[#254B78] dark:text-[#9DB8EB]">
                  Job Match{reanalysis.job_match.job_title ? ` · ${reanalysis.job_match.job_title}` : ""}
                </h4>
                {reanalysis.job_match.delta === null ? (
                  <p className="mt-1 text-xs text-[#58616D] dark:text-[#A0ABB8]">{reanalysis.job_match.unavailable_reason}</p>
                ) : (
                  <>
                    <p className="mt-1 text-sm font-semibold text-[#181A1D] dark:text-[#F0F2F5]">
                      {reanalysis.job_match.baseline_score?.toFixed(1)} → {reanalysis.job_match.revised_score?.toFixed(1)}
                      <span className="ml-2 text-[#5477B8] dark:text-[#9DB8EB]">({reanalysis.job_match.delta > 0 ? "+" : ""}{reanalysis.job_match.delta.toFixed(1)})</span>
                    </p>
                    <p className="mt-1 text-[11px] text-[#58616D] dark:text-[#A0ABB8]">
                      Textual matches: {reanalysis.job_match.matched_before} → {reanalysis.job_match.matched_after}; partial support: {reanalysis.job_match.partially_supported_before} → {reanalysis.job_match.partially_supported_after}; no text found: {reanalysis.job_match.not_demonstrated_before} → {reanalysis.job_match.not_demonstrated_after}.
                    </p>
                  </>
                )}
              </div>
            )}

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#58616D] dark:text-[#A0ABB8]">Changed sections</h4>
              <div className="mt-2 space-y-2">
                {reanalysis.changed_sections.map((section) => (
                  <details key={section.key} className="rounded-xl border border-[#9CA6B2]/20 p-3">
                    <summary className="cursor-pointer text-xs font-semibold text-[#181A1D] dark:text-[#F0F2F5]">
                      {section.label} · {section.change}
                    </summary>
                    <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-wider text-[#838F9E]">Uploaded baseline</p>
                        <pre className="mt-1 whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-[#58616D] dark:text-[#A0ABB8]">{section.before || "(empty)"}</pre>
                      </div>
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-wider text-[#5477B8] dark:text-[#9DB8EB]">Saved Builder revision</p>
                        <pre className="mt-1 whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-[#181A1D] dark:text-[#F0F2F5]">{section.after || "(empty)"}</pre>
                      </div>
                    </div>
                  </details>
                ))}
              </div>
            </div>

            {reanalysis.resolved_findings.length > 0 && (
              <div className="rounded-xl border border-emerald-600/20 bg-emerald-600/5 p-4">
                <h4 className="text-xs font-bold text-emerald-800 dark:text-emerald-300">Findings absent from the revised report</h4>
                <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-[#58616D] dark:text-[#A0ABB8]">
                  {reanalysis.resolved_findings.map((finding) => <li key={finding}>{finding}</li>)}
                </ul>
              </div>
            )}

            <ul className="space-y-1 border-t border-[#9CA6B2]/20 pt-3 text-[10px] leading-relaxed text-[#838F9E]">
              {reanalysis.limitations.map((limitation) => <li key={limitation}>• {limitation}</li>)}
            </ul>
          </div>
        ) : null}
      </section>

      {downloadNotice && (
        <div className={`flex items-center justify-between rounded-xl border p-3 text-xs shadow-xs transition ${
          downloadNotice.includes("failed")
            ? "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-400"
            : "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
        }`}>
          <span>{downloadNotice}</span>
          <button
            type="button"
            onClick={() => setDownloadNotice(null)}
            className="font-bold underline ml-2"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ── Empty State: When no document is saved yet ───────────────────────── */}
      {!hasDoc && (
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-8 text-center backdrop-blur-md">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h3 className="mt-4 text-base font-bold text-[#181A1D] dark:text-[#F0F2F5]">
            No Saved Resume Document Found
          </h3>
          <p className="mt-1 text-xs text-[#58616D] dark:text-[#A0ABB8] max-w-md mx-auto">
            You must open the Resume Builder to review, configure, and save your resume content before downloading.
          </p>
          <button
            type="button"
            onClick={onBackToBuilder}
            className="mt-4 rounded-xl bg-[#5477B8] px-5 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-[#43629C] dark:bg-[#6E90D1]"
          >
            Open Resume Builder
          </button>
        </div>
      )}

      {/* ── Download Action Cards Grid ───────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* ── Card 1: Vector PDF Resume ──────────────────────────────────────── */}
        <div className="flex flex-col justify-between rounded-2xl border border-[#9CA6B2]/25 bg-white/70 p-6 shadow-sm backdrop-blur-md dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/70">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-red-500/20 bg-red-500/10 text-red-600 dark:text-red-400">
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              </div>
              <span className="rounded-full bg-red-500/10 px-2.5 py-0.5 text-[10px] font-bold text-red-600 dark:text-red-400">
                Vector PDF
              </span>
            </div>

            <div>
              <h3 className="text-base font-bold text-[#181A1D] dark:text-[#F0F2F5]">
                ATS-Oriented PDF Resume
              </h3>
              <p className="mt-1 text-xs text-[#58616D] dark:text-[#A0ABB8] leading-relaxed">
                Single-column, vector-rendered A4 document with 100% extractable text layer, standard universal typography, and clean hierarchy.
              </p>
            </div>

            <div className="space-y-1.5 pt-2 border-t border-[#9CA6B2]/15 text-[11px] text-[#58616D] dark:text-[#A0ABB8]">
              <div className="flex items-center space-x-1.5">
                <span className="text-emerald-500">✓</span>
                <span>Zero multi-column parsing traps</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <span className="text-emerald-500">✓</span>
                <span>Active template: {templateMeta.name}</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <span className="text-emerald-500">✓</span>
                <span>Embedded hyperlinks for email & profiles</span>
              </div>
            </div>
          </div>

          <button
            id="downloadPdfResumeBtn"
            type="button"
            onClick={() =>
              triggerDownload(
                `/api/export/resume/pdf${statusData?.builder_version ? `?version=${statusData.builder_version}` : ""}`,
                "RESUMIND_Resume.pdf",
                setPdfState
              )
            }
            disabled={!hasDoc || pdfState === "downloading"}
            className="mt-6 flex w-full items-center justify-center space-x-2 rounded-xl bg-[#181A1D] py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-[#2B3037] disabled:opacity-50 dark:bg-[#F0F2F5] dark:text-[#181A1D] dark:hover:bg-white"
          >
            {pdfState === "downloading" ? (
              <>
                <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/20 border-t-white" />
                <span>Generating Vector PDF...</span>
              </>
            ) : pdfState === "success" ? (
              <>
                <span>Downloaded Successfully</span>
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                <span>Download Resume PDF</span>
              </>
            )}
          </button>
        </div>

        {/* ── Card 2: Editable Word DOCX Resume ──────────────────────────────── */}
        <div className="flex flex-col justify-between rounded-2xl border border-[#9CA6B2]/25 bg-white/70 p-6 shadow-sm backdrop-blur-md dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/70">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-blue-500/20 bg-blue-500/10 text-blue-600 dark:text-blue-400">
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <span className="rounded-full bg-blue-500/10 px-2.5 py-0.5 text-[10px] font-bold text-blue-600 dark:text-blue-400">
                Word DOCX
              </span>
            </div>

            <div>
              <h3 className="text-base font-bold text-[#181A1D] dark:text-[#F0F2F5]">
                Editable Microsoft Word DOCX
              </h3>
              <p className="mt-1 text-xs text-[#58616D] dark:text-[#A0ABB8] leading-relaxed">
                Native OpenXML Word document with genuine headings, paragraphs, and bullet points. 100% editable in Word, Google Docs, and LibreOffice.
              </p>
            </div>

            <div className="space-y-1.5 pt-2 border-t border-[#9CA6B2]/15 text-[11px] text-[#58616D] dark:text-[#A0ABB8]">
              <div className="flex items-center space-x-1.5">
                <span className="text-emerald-500">✓</span>
                <span>Native formatting, no image screenshots</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <span className="text-emerald-500">✓</span>
                <span>Standard heading & bullet hierarchy</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <span className="text-emerald-500">✓</span>
                <span>Full offline editing capability</span>
              </div>
            </div>
          </div>

          <button
            id="downloadDocxResumeBtn"
            type="button"
            onClick={() =>
              triggerDownload(
                `/api/export/resume/docx${statusData?.builder_version ? `?version=${statusData.builder_version}` : ""}`,
                "RESUMIND_Resume.docx",
                setDocxState
              )
            }
            disabled={!hasDoc || docxState === "downloading"}
            className="mt-6 flex w-full items-center justify-center space-x-2 rounded-xl border border-[#5477B8]/40 bg-[#5477B8]/10 py-2.5 text-xs font-semibold text-[#5477B8] shadow-sm transition hover:bg-[#5477B8]/20 disabled:opacity-50 dark:text-[#6E90D1]"
          >
            {docxState === "downloading" ? (
              <>
                <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-[#5477B8]/20 border-t-[#5477B8]" />
                <span>Compiling Word DOCX...</span>
              </>
            ) : docxState === "success" ? (
              <>
                <span>Downloaded Successfully</span>
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                <span>Download Editable DOCX</span>
              </>
            )}
          </button>
        </div>

        {/* ── Card 3: Diagnostic Improvement Report PDF ──────────────────────── */}
        <div className="flex flex-col justify-between rounded-2xl border border-[#5477B8]/30 bg-gradient-to-b from-[#5477B8]/5 via-white/70 to-white/70 p-6 shadow-sm backdrop-blur-md dark:from-[#6E90D1]/10 dark:via-[#14171C]/70 dark:to-[#14171C]/70">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-[#5477B8]/30 bg-[#5477B8]/10 text-[#5477B8] dark:text-[#6E90D1]">
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <span className="rounded-full bg-[#5477B8]/15 px-2.5 py-0.5 text-[10px] font-bold text-[#5477B8] dark:text-[#6E90D1]">
                Audit Report
              </span>
            </div>

            <div>
              <h3 className="text-base font-bold text-[#181A1D] dark:text-[#F0F2F5]">
                Diagnostic Audit Report PDF
              </h3>
              <p className="mt-1 text-xs text-[#58616D] dark:text-[#A0ABB8] leading-relaxed">
                Comprehensive executive PDF report detailing your 5-dimension ATS readiness score, grounded requirement match findings, and accepted revisions.
              </p>
            </div>

            <div className="space-y-1.5 pt-2 border-t border-[#9CA6B2]/15 text-[11px] text-[#58616D] dark:text-[#A0ABB8]">
              <div className="flex items-center space-x-1.5">
                <span className="text-emerald-500">✓</span>
                <span>ATS Readiness score & dimension weights</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <span className="text-emerald-500">✓</span>
                <span>Target role match breakdown (if assessed)</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <span className="text-emerald-500">✓</span>
                <span>{statusData?.accepted_suggestions_count || 0} accepted bullet revisions logged</span>
              </div>
            </div>
          </div>

          <button
            id="downloadAuditReportBtn"
            type="button"
            onClick={() =>
              triggerDownload(
                "/api/export/report/pdf",
                "RESUMIND_Audit_Report.pdf",
                setReportState
              )
            }
            disabled={reportState === "downloading"}
            className="mt-6 flex w-full items-center justify-center space-x-2 rounded-xl bg-[#5477B8] py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-[#43629C] disabled:opacity-50 dark:bg-[#6E90D1]"
          >
            {reportState === "downloading" ? (
              <>
                <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/20 border-t-white" />
                <span>Generating Diagnostic Audit...</span>
              </>
            ) : reportState === "success" ? (
              <>
                <span>Downloaded Successfully</span>
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>Download Diagnostic Audit PDF</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── ATS Safety & Ethical Boundaries Notice ──────────────────────────── */}
      <div className="rounded-xl border border-[#9CA6B2]/20 bg-white/40 p-4 text-xs text-[#838F9E] dark:border-[#9CA6B2]/10 dark:bg-[#14171C]/40 dark:text-[#64707D]">
        <p className="font-semibold text-[#181A1D] dark:text-[#A0ABB8] mb-1">
          ATS Compliance Architecture & Ethical Notice
        </p>
        <p>
          Exports use a conventional single-column layout and native text where possible. The generated files are tested on representative fixtures, but no software can guarantee parsing or ranking behavior in every employer&apos;s ATS.
        </p>
      </div>
    </div>
  );
}
