"use client";

import React, { useState } from "react";
import { ParsedResume } from "./ResumeUploadSurface";

export interface ATSFinding {
  severity: "critical" | "warning" | "positive";
  title: string;
  message: string;
  evidence?: string | null;
}

export interface DimensionResult {
  score: number;
  weight: number;
  weighted_score: number;
  strengths: string[];
  findings: ATSFinding[];
}

export interface ATSReport {
  overall_score: number;
  subscores: {
    file_integrity: DimensionResult;
    section_taxonomy: DimensionResult;
    contact: DimensionResult;
    bullet_impact: DimensionResult;
    length_hygiene: DimensionResult;
  };
  top_strengths: string[];
  prioritized_findings: ATSFinding[];
  limitations: string[];
  disclaimer: string;
}

export interface ATSAssessmentData {
  id: string;
  session_id: string;
  resume_id: string;
  overall_score: number;
  dimension_scores: Record<string, { score: number; weight: number; weighted_score: number }>;
  report_data: ATSReport;
  created_at: string;
  updated_at: string;
}

interface ATSReportViewProps {
  assessment: ATSAssessmentData | null;
  resume: ParsedResume;
  isLoading: boolean;
  errorMessage: string | null;
  onRetry: () => void;
  onBackToReview: () => void;
  onUploadNew: () => void;
  onProceedToImprovement?: () => void;
  onLaunchBuilder?: () => void;
}

const DIMENSION_CONFIG: Record<
  string,
  { label: string; weightLabel: string; description: string; icon: string }
> = {
  file_integrity: {
    label: "File & Text Integrity",
    weightLabel: "25% Weight",
    description: "Evaluates mechanical text extraction, layer clarity, and binary density.",
    icon: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  },
  section_taxonomy: {
    label: "Section Taxonomy",
    weightLabel: "20% Weight",
    description: "Evaluates recognizable standard headings (Experience, Education, Skills).",
    icon: "M4 6h16M4 10h16M4 14h16M4 18h16",
  },
  contact: {
    label: "Contact Information",
    weightLabel: "15% Weight",
    description: "Evaluates completeness and RFC compliance of email, phone, and links.",
    icon: "M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
  },
  bullet_impact: {
    label: "Bullet Construction & Impact",
    weightLabel: "25% Weight",
    description: "Evaluates action-verb front-loading, quantifiable metrics, and statement length.",
    icon: "M13 10V3L4 14h7v7l9-11h-7z",
  },
  length_hygiene: {
    label: "Length & Hygiene",
    weightLabel: "15% Weight",
    description: "Evaluates document volume, duplicate lines, and paragraph density.",
    icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2",
  },
};

export function ATSReportView({
  assessment,
  resume,
  isLoading,
  errorMessage,
  onRetry,
  onBackToReview,
  onUploadNew,
  onProceedToImprovement,
  onLaunchBuilder,
}: ATSReportViewProps) {
  const [activeTab, setActiveTab] = useState<"overview" | "dimensions" | "findings">("overview");

  // ── Loading State ─────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex w-full flex-col items-center justify-center py-24 text-center">
        <div className="relative flex h-24 w-24 items-center justify-center">
          <div className="absolute h-full w-full animate-ping rounded-full bg-[#5477B8]/20 dark:bg-[#6E90D1]/20" />
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-[#5477B8]/40 bg-white/80 shadow-lg shadow-[#5477B8]/10 backdrop-blur-md dark:border-[#6E90D1]/30 dark:bg-[#1A1E24]/90">
            <svg
              className="h-8 w-8 animate-spin text-[#5477B8] dark:text-[#6E90D1]"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="3"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
          </div>
        </div>

        <h3 className="mt-8 text-xl font-bold text-[#181A1D] dark:text-[#F0F2F5]">
          Calculating Heuristic ATS Readiness...
        </h3>
        <p className="mt-2 max-w-md text-sm text-[#58616D] dark:text-[#A0ABB8]">
          Executing deterministic algorithmic checks across File Integrity, Section Taxonomy,
          Contact Completeness, Bullet Construction, and Length Hygiene.
        </p>
      </div>
    );
  }

  // ── Error State ───────────────────────────────────────────────────────────
  if (errorMessage || !assessment) {
    return (
      <div className="mx-auto flex w-full max-w-xl flex-col items-center justify-center rounded-2xl border border-red-500/20 bg-white/70 p-8 text-center shadow-lg backdrop-blur-md dark:border-red-500/20 dark:bg-[#1A1E24]/70">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-red-100 text-red-600 dark:bg-red-950/50 dark:text-red-400">
          <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h3 className="mt-4 text-lg font-bold text-[#181A1D] dark:text-[#F0F2F5]">
          Assessment Evaluation Error
        </h3>
        <p className="mt-2 text-sm text-[#58616D] dark:text-[#A0ABB8]">
          {errorMessage || "Unable to retrieve ATS assessment report for the active session."}
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={onRetry}
            className="rounded-xl bg-[#5477B8] px-5 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-[#43629C] dark:bg-[#6E90D1] dark:hover:bg-[#85A3DC]"
          >
            Retry Assessment
          </button>
          <button
            type="button"
            onClick={onBackToReview}
            className="rounded-xl border border-[#9CA6B2]/30 bg-white/60 px-5 py-2.5 text-xs font-semibold text-[#181A1D] transition hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/60 dark:text-[#F0F2F5] dark:hover:bg-[#20252D]"
          >
            Back to Review
          </button>
        </div>
      </div>
    );
  }

  const report = assessment.report_data;
  const overall = report.overall_score;

  // Grade tier helper
  const getScoreTier = (score: number) => {
    if (score >= 85) {
      return {
        label: "Optimal ATS Readiness",
        colorClass: "text-emerald-600 dark:text-emerald-400",
        bgClass: "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300",
        barClass: "bg-emerald-500",
        message: "Your resume exhibits strong mechanical parseability and clean taxonomy.",
      };
    }
    if (score >= 70) {
      return {
        label: "Good Machine Readability",
        colorClass: "text-[#5477B8] dark:text-[#6E90D1]",
        bgClass: "bg-[#5477B8]/10 border-[#5477B8]/30 text-[#5477B8] dark:text-[#6E90D1]",
        barClass: "bg-[#5477B8] dark:bg-[#6E90D1]",
        message: "Parses cleanly across most modern ATS engines with minor optimization opportunities.",
      };
    }
    if (score >= 55) {
      return {
        label: "Moderate Formatting Risk",
        colorClass: "text-amber-600 dark:text-amber-400",
        bgClass: "bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-300",
        barClass: "bg-amber-500",
        message: "Noticeable structural or bullet phrasing gaps detected that may limit ATS indexing.",
      };
    }
    return {
      label: "Critical Action Needed",
      colorClass: "text-rose-600 dark:text-rose-400",
      bgClass: "bg-rose-500/10 border-rose-500/30 text-rose-700 dark:text-rose-300",
      barClass: "bg-rose-500",
      message: "Unreadable layers or missing core sections identified. High risk of ATS drop-off.",
    };
  };

  const tier = getScoreTier(overall);

  return (
    <div className="w-full space-y-8">
      {/* ── Top Navigation & Meta Header ───────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="inline-flex items-center space-x-2 rounded-full border border-[#9CA6B2]/30 bg-white/60 px-3 py-1 text-[11px] font-semibold tracking-wider text-[#5477B8] uppercase backdrop-blur-sm dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/60 dark:text-[#6E90D1]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#5477B8] dark:bg-[#6E90D1]" />
            <span>Standalone Diagnostic Report</span>
          </div>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-[#181A1D] sm:text-3xl dark:text-[#F0F2F5]">
            ATS Readiness Assessment
          </h2>
          <p className="text-xs text-[#58616D] dark:text-[#A0ABB8]">
            Document: <span className="font-semibold text-[#181A1D] dark:text-[#F0F2F5]">{resume.filename}</span> ({resume.file_type.toUpperCase()}, {(resume.file_size / 1024).toFixed(1)} KB)
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            id="backToReviewButton"
            type="button"
            onClick={onBackToReview}
            className="inline-flex items-center space-x-1.5 rounded-xl border border-[#9CA6B2]/30 bg-white/70 px-4 py-2 text-xs font-semibold text-[#181A1D] shadow-sm transition hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/70 dark:text-[#F0F2F5] dark:hover:bg-[#20252D]"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M11 17l-5-5m0 0l5-5m-5 5h12" />
            </svg>
            <span>Edit Extracted Data</span>
          </button>
          <button
            id="uploadNewResumeBtn"
            type="button"
            onClick={onUploadNew}
            className="inline-flex items-center space-x-1.5 rounded-xl border border-[#9CA6B2]/30 bg-white/70 px-4 py-2 text-xs font-semibold text-[#58616D] shadow-sm transition hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/70 dark:text-[#A0ABB8] dark:hover:bg-[#20252D]"
          >
            <span>Upload Another</span>
          </button>
        </div>
      </div>

      {/* ── Hero Scorecard (Liquid Glass Frost & Chrome) ───────────────────── */}
      <div className="relative overflow-hidden rounded-2xl border border-[#9CA6B2]/30 bg-white/60 p-6 shadow-xl backdrop-blur-md sm:p-8 dark:border-[#9CA6B2]/20 dark:bg-[#14171C]/70">
        <div className="grid grid-cols-1 items-center gap-8 lg:grid-cols-12">
          {/* Left: Overall Circular Progress & Tier */}
          <div className="flex flex-col items-center justify-center text-center lg:col-span-5">
            <div className="relative flex h-40 w-40 items-center justify-center sm:h-44 sm:w-44">
              {/* SVG Circular Progress Bar */}
              <svg className="h-full w-full -rotate-90 transform" viewBox="0 0 160 160">
                <circle
                  cx="80"
                  cy="80"
                  r="68"
                  className="stroke-[#9CA6B2]/20 dark:stroke-[#9CA6B2]/10"
                  strokeWidth="12"
                  fill="transparent"
                />
                <circle
                  cx="80"
                  cy="80"
                  r="68"
                  className={tier.barClass}
                  strokeWidth="12"
                  strokeDasharray={427}
                  strokeDashoffset={427 - (427 * overall) / 100}
                  strokeLinecap="round"
                  stroke="currentColor"
                  fill="transparent"
                  style={{ transition: "stroke-dashoffset 1s ease-in-out" }}
                />
              </svg>

              {/* Central Score readout */}
              <div className="absolute flex flex-col items-center justify-center">
                <span className="text-4xl font-extrabold tracking-tight text-[#181A1D] sm:text-5xl dark:text-[#F0F2F5]">
                  {overall}
                </span>
                <span className="text-[11px] font-semibold text-[#838F9E] uppercase tracking-wider dark:text-[#64707D]">
                  out of 100
                </span>
              </div>
            </div>

            <div className="mt-4">
              <span className={`inline-block rounded-full border px-3 py-1 text-xs font-bold ${tier.bgClass}`}>
                {tier.label}
              </span>
              <p className="mt-2 text-xs text-[#58616D] max-w-xs dark:text-[#A0ABB8]">
                {tier.message}
              </p>
            </div>
          </div>

          {/* Right: Quick Subscore Bars (The 5 Dimensions) */}
          <div className="space-y-3.5 lg:col-span-7">
            <div className="flex items-center justify-between border-b border-[#9CA6B2]/20 pb-2">
              <span className="text-xs font-bold tracking-wider uppercase text-[#838F9E] dark:text-[#64707D]">
                Approved Scoring Framework Breakdown
              </span>
              <span className="text-[11px] text-[#838F9E] dark:text-[#64707D]">
                Weighted Formula
              </span>
            </div>

            {Object.entries(DIMENSION_CONFIG).map(([dimKey, config]) => {
              const sub = report.subscores[dimKey as keyof typeof report.subscores];
              if (!sub) return null;
              const subTier = getScoreTier(sub.score);

              return (
                <div key={dimKey} className="group">
                  <div className="flex items-center justify-between text-xs font-medium">
                    <span className="text-[#181A1D] font-semibold dark:text-[#F0F2F5]">
                      {config.label}{" "}
                      <span className="text-[10px] text-[#838F9E] font-normal dark:text-[#64707D]">
                        ({config.weightLabel})
                      </span>
                    </span>
                    <span className={`font-bold ${subTier.colorClass}`}>
                      {sub.score} / 100
                    </span>
                  </div>
                  <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-[#9CA6B2]/20 dark:bg-[#9CA6B2]/10">
                    <div
                      className={`h-full rounded-full ${subTier.barClass}`}
                      style={{ width: `${Math.max(5, sub.score)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── View Filter Tabs ────────────────────────────────────────────────── */}
      <div className="flex border-b border-[#9CA6B2]/30 dark:border-[#9CA6B2]/20">
        {(
          [
            { key: "overview", label: "Overview & Strengths" },
            { key: "dimensions", label: "5-Dimension Deep Dive" },
            { key: "findings", label: `Prioritized Findings (${report.prioritized_findings.length})` },
          ] as const
        ).map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`border-b-2 px-5 py-2.5 text-xs font-semibold transition-colors ${
              activeTab === tab.key
                ? "border-[#5477B8] text-[#5477B8] dark:border-[#6E90D1] dark:text-[#6E90D1]"
                : "border-transparent text-[#58616D] hover:text-[#181A1D] dark:text-[#A0ABB8] dark:hover:text-[#F0F2F5]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── TAB: Overview & Strengths ──────────────────────────────────────── */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Strengths Card */}
          <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-6 backdrop-blur-sm dark:border-emerald-500/20 dark:bg-emerald-500/5">
            <div className="flex items-center space-x-2 text-emerald-700 dark:text-emerald-300">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h3 className="text-base font-bold">Identified Structural Strengths</h3>
            </div>
            <ul className="mt-4 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
              {report.top_strengths.map((str, idx) => (
                <li
                  key={idx}
                  className="flex items-start space-x-2 text-xs text-[#181A1D] dark:text-[#E2E8F0]"
                >
                  <span className="mt-0.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
                  <span>{str}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Top Priority Action Cards */}
          <div className="space-y-3">
            <h3 className="text-sm font-bold uppercase tracking-wider text-[#838F9E] dark:text-[#64707D]">
              Highest Priority Optimization Items
            </h3>
            {report.prioritized_findings.slice(0, 3).map((f, idx) => (
              <div
                key={idx}
                className="rounded-xl border border-[#9CA6B2]/20 bg-white/60 p-4 backdrop-blur-sm dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/50"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-block rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                          f.severity === "critical"
                            ? "bg-rose-500/10 text-rose-600 border border-rose-500/20 dark:text-rose-400"
                            : "bg-amber-500/10 text-amber-600 border border-amber-500/20 dark:text-amber-400"
                        }`}
                      >
                        {f.severity === "critical" ? "Critical Risk" : "Optimization"}
                      </span>
                      <h4 className="text-sm font-bold text-[#181A1D] dark:text-[#F0F2F5]">
                        {f.title}
                      </h4>
                    </div>
                    <p className="text-xs text-[#58616D] dark:text-[#A0ABB8]">
                      {f.message}
                    </p>
                    {f.evidence && (
                      <p className="mt-1 font-mono text-[11px] text-[#838F9E] dark:text-[#64707D] bg-black/5 dark:bg-white/5 rounded px-2 py-1 inline-block">
                        {f.evidence}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── TAB: 5-Dimension Deep Dive ──────────────────────────────────────── */}
      {activeTab === "dimensions" && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {Object.entries(DIMENSION_CONFIG).map(([dimKey, config]) => {
            const sub = report.subscores[dimKey as keyof typeof report.subscores];
            if (!sub) return null;
            const subTier = getScoreTier(sub.score);

            return (
              <div
                key={dimKey}
                className="flex flex-col justify-between rounded-2xl border border-[#9CA6B2]/30 bg-white/60 p-6 shadow-sm backdrop-blur-md dark:border-[#9CA6B2]/20 dark:bg-[#14171C]/60"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#5477B8]/10 text-[#5477B8] dark:bg-[#6E90D1]/10 dark:text-[#6E90D1]">
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                          <path strokeLinecap="round" strokeLinejoin="round" d={config.icon} />
                        </svg>
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-[#181A1D] dark:text-[#F0F2F5]">
                          {config.label}
                        </h4>
                        <span className="text-[10px] text-[#838F9E] dark:text-[#64707D]">
                          {config.weightLabel}
                        </span>
                      </div>
                    </div>
                    <span className={`text-base font-extrabold ${subTier.colorClass}`}>
                      {sub.score} <span className="text-[10px] font-normal text-[#838F9E]">/ 100</span>
                    </span>
                  </div>

                  <p className="mt-3 text-xs text-[#58616D] dark:text-[#A0ABB8]">
                    {config.description}
                  </p>

                  {/* Dimension Strengths */}
                  {sub.strengths.length > 0 && (
                    <div className="mt-4 space-y-1">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                        Passed Checks
                      </p>
                      {sub.strengths.map((str, idx) => (
                        <p key={idx} className="text-xs text-[#181A1D] dark:text-[#E2E8F0] flex items-center space-x-1.5">
                          <span className="text-emerald-500">✓</span>
                          <span>{str}</span>
                        </p>
                      ))}
                    </div>
                  )}

                  {/* Dimension Findings */}
                  {sub.findings.length > 0 && (
                    <div className="mt-4 space-y-2 border-t border-[#9CA6B2]/20 pt-3">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400">
                        Areas for Improvement
                      </p>
                      {sub.findings.map((f, idx) => (
                        <div key={idx} className="rounded-lg bg-black/5 dark:bg-white/5 p-2 text-xs">
                          <p className="font-semibold text-[#181A1D] dark:text-[#F0F2F5]">{f.title}</p>
                          <p className="mt-0.5 text-[#58616D] dark:text-[#A0ABB8]">{f.message}</p>
                          {f.evidence && (
                            <p className="mt-1 font-mono text-[10px] text-[#838F9E] dark:text-[#64707D]">
                              {f.evidence}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── TAB: Prioritized Findings ───────────────────────────────────────── */}
      {activeTab === "findings" && (
        <div className="space-y-4">
          {report.prioritized_findings.length === 0 ? (
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-8 text-center">
              <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">
                Zero critical or warning findings detected! Your resume formatting aligns closely with consensus parsing standards.
              </p>
            </div>
          ) : (
            report.prioritized_findings.map((finding, idx) => (
              <div
                key={idx}
                className={`rounded-xl border p-4.5 backdrop-blur-sm transition ${
                  finding.severity === "critical"
                    ? "border-rose-500/30 bg-rose-500/5 dark:border-rose-500/20 dark:bg-rose-950/20"
                    : "border-amber-500/30 bg-amber-500/5 dark:border-amber-500/20 dark:bg-amber-950/20"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                          finding.severity === "critical"
                            ? "bg-rose-500/20 text-rose-700 dark:text-rose-300"
                            : "bg-amber-500/20 text-amber-700 dark:text-amber-300"
                        }`}
                      >
                        {finding.severity === "critical" ? "Critical Risk" : "Optimization"}
                      </span>
                      <h4 className="text-sm font-bold text-[#181A1D] dark:text-[#F0F2F5]">
                        {finding.title}
                      </h4>
                    </div>
                    <p className="text-xs text-[#58616D] dark:text-[#A0ABB8] leading-relaxed">
                      {finding.message}
                    </p>
                    {finding.evidence && (
                      <div className="mt-2 rounded bg-black/5 dark:bg-white/5 p-2 font-mono text-[11px] text-[#4A5568] dark:text-[#CBD5E1]">
                        <span className="font-sans font-semibold text-[10px] text-[#838F9E] uppercase tracking-wider block">
                          Identified Resume Evidence:
                        </span>
                        {finding.evidence}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* ── Next Phase Notice & Action Bar ──────────────────────────────────── */}
      <div className="rounded-2xl border border-[#5477B8]/20 bg-gradient-to-r from-[#5477B8]/5 via-[#9CA6B2]/5 to-[#5477B8]/5 p-6 backdrop-blur-md dark:border-[#6E90D1]/20">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="space-y-1">
            <div className="inline-flex items-center space-x-1.5 text-[10px] font-bold uppercase tracking-wider text-[#5477B8] dark:text-[#6E90D1]">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span>Resume Improvement Studio Active</span>
            </div>
            <h4 className="text-sm font-bold text-[#181A1D] dark:text-[#F0F2F5]">
              Resume Improvement Studio
            </h4>
            <p className="text-xs text-[#58616D] dark:text-[#A0ABB8] max-w-xl">
              Inspect grounded improvement opportunities derived from your actual resume content.
              Compare original text with proposed revisions, insert verified metrics, and accept or reject individual suggestions.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {onProceedToImprovement && (
              <button
                id="launchImprovementStudioBtn"
                type="button"
                onClick={onProceedToImprovement}
                className="rounded-xl bg-[#5477B8] px-5 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-[#43629C] dark:bg-[#6E90D1] dark:hover:bg-[#85A3DC] flex items-center space-x-2"
              >
                <span>Launch Improvement Studio</span>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </button>
            )}
            {onLaunchBuilder && (
              <button
                id="launchResumeBuilderBtn"
                type="button"
                onClick={onLaunchBuilder}
                className="rounded-xl border border-[#5477B8]/40 bg-[#5477B8]/10 px-4 py-2.5 text-xs font-semibold text-[#5477B8] transition hover:bg-[#5477B8]/20 dark:text-[#6E90D1] flex items-center space-x-2"
              >
                <span>Open in Resume Builder</span>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
            )}
            <button
              id="correctResumeCtaBtn"
              type="button"
              onClick={onBackToReview}
              className="rounded-xl border border-[#9CA6B2]/30 bg-white/60 dark:bg-[#1A1E24]/60 px-4 py-2.5 text-xs font-semibold text-[#181A1D] dark:text-[#F0F2F5] transition hover:bg-white dark:hover:bg-[#20252D]"
            >
              Adjust In Review Studio
            </button>
          </div>
        </div>
      </div>

      {/* ── Honest Disclaimer & Heuristic Limits ────────────────────────────── */}
      <div className="rounded-xl border border-[#9CA6B2]/20 bg-white/40 p-4 text-xs text-[#838F9E] dark:border-[#9CA6B2]/10 dark:bg-[#14171C]/40 dark:text-[#64707D]">
        <p className="font-semibold text-[#181A1D] dark:text-[#A0ABB8] mb-1">
          Algorithmic Assessment Disclaimer
        </p>
        <p>{report.disclaimer}</p>
        {report.limitations.length > 0 && (
          <ul className="mt-2 list-disc pl-4 space-y-0.5">
            {report.limitations.map((lim, idx) => (
              <li key={idx}>{lim}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
