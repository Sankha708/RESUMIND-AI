"use client";

import React, { useState } from "react";
import { ParsedResume } from "./ResumeUploadSurface";

export interface ExtractedRequirement {
  id: string;
  category: "hard_skills" | "domain_competencies" | "experience_scope" | "education_credentials";
  original_text: string;
  normalized_term: string;
  is_required: boolean;
  match_status: "matched" | "partially_supported" | "not_demonstrated";
  explanation: string;
  evidence_snippet?: string | null;
  recommendation?: string | null;
}

export interface CategoryScore {
  category: string;
  label: string;
  base_weight: number;
  normalized_weight: number;
  score: number;
  is_applicable: boolean;
  total_requirements: number;
  matched_count: number;
  partial_count: number;
  gap_count: number;
}

export interface JobMatchReportData {
  job_title?: string | null;
  overall_score?: number | null;
  score_withheld: boolean;
  withheld_reason?: string | null;
  category_scores: Record<string, CategoryScore>;
  requirements: ExtractedRequirement[];
  matched_count: number;
  partial_count: number;
  gap_count: number;
  top_recommendations: string[];
  limitations: string[];
  disclaimer: string;
}

export interface JobMatchAssessmentData {
  id: string;
  session_id: string;
  resume_id: string;
  job_title?: string | null;
  overall_score?: number | null;
  score_withheld: boolean;
  category_scores: Record<string, unknown>;
  report_data: JobMatchReportData;
  created_at: string;
  updated_at: string;
}

interface JobMatchReportViewProps {
  assessment: JobMatchAssessmentData | null;
  resume: ParsedResume;
  isLoading: boolean;
  errorMessage: string | null;
  onRetry: () => void;
  onBackToReview: () => void;
  onUploadNew: () => void;
  onSwitchToAts: () => void;
  onLaunchBuilder?: () => void;
}

const CATEGORY_ICONS: Record<string, string> = {
  hard_skills: "M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4",
  domain_competencies: "M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10",
  experience_scope: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
  education_credentials: "M12 14l9-5-9-5-9 5 9 5zm0 0l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z",
};

export function JobMatchReportView({
  assessment,
  resume,
  isLoading,
  errorMessage,
  onRetry,
  onBackToReview,
  onUploadNew,
  onSwitchToAts,
  onLaunchBuilder,
}: JobMatchReportViewProps) {
  const [statusFilter, setStatusFilter] = useState<"all" | "matched" | "partial" | "gap">("all");
  const [expandedSnippets, setExpandedSnippets] = useState<Record<string, boolean>>({});

  const toggleSnippet = (reqId: string) => {
    setExpandedSnippets((prev) => ({
      ...prev,
      [reqId]: !prev[reqId],
    }));
  };

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
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
          </div>
        </div>

        <h3 className="mt-8 text-xl font-bold text-[#181A1D] dark:text-[#F0F2F5]">
          Extracting Requirements & Grounding Citations...
        </h3>
        <p className="mt-2 max-w-md text-sm text-[#58616D] dark:text-[#A0ABB8]">
          Cross-referencing technical skills, domain competencies, experience scope, and credentials
          against your reviewed resume text with verbatim verification.
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
          Job Match Evaluation Error
        </h3>
        <p className="mt-2 text-sm text-[#58616D] dark:text-[#A0ABB8]">
          {errorMessage || "Unable to retrieve job match assessment report for the active session."}
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={onRetry}
            className="rounded-xl bg-[#5477B8] px-5 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-[#43629C] dark:bg-[#6E90D1] dark:hover:bg-[#85A3DC]"
          >
            Retry Matching
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
  const getMatchTier = (score: number | null) => {
    if (score === null) {
      return {
        label: "Score Withheld",
        colorClass: "text-[#838F9E] dark:text-[#64707D]",
        bgClass: "bg-[#9CA6B2]/10 border-[#9CA6B2]/30 text-[#58616D] dark:text-[#A0ABB8]",
        barClass: "bg-[#9CA6B2]",
        message: "Insufficient requirement structure extracted from job posting.",
      };
    }
    if (score >= 80) {
      return {
        label: "Strong Role Alignment",
        colorClass: "text-emerald-600 dark:text-emerald-400",
        bgClass: "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300",
        barClass: "bg-emerald-500",
        message: "Extensive grounded textual evidence found for core technical requirements.",
      };
    }
    if (score >= 60) {
      return {
        label: "Moderate Role Alignment",
        colorClass: "text-[#5477B8] dark:text-[#6E90D1]",
        bgClass: "bg-[#5477B8]/10 border-[#5477B8]/30 text-[#5477B8] dark:text-[#6E90D1]",
        barClass: "bg-[#5477B8] dark:bg-[#6E90D1]",
        message: "Key requirements supported; tailoring experience bullets will strengthen alignment.",
      };
    }
    return {
      label: "Significant Gaps Detected",
      colorClass: "text-amber-600 dark:text-amber-400",
      bgClass: "bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-300",
      barClass: "bg-amber-500",
      message: "Multiple required skills or competencies lack explicit evidence in your resume.",
    };
  };

  const tier = getMatchTier(overall ?? null);

  // Filter requirements
  const filteredRequirements = report.requirements.filter((req) => {
    if (statusFilter === "matched") return req.match_status === "matched";
    if (statusFilter === "partial") return req.match_status === "partially_supported";
    if (statusFilter === "gap") return req.match_status === "not_demonstrated";
    return true;
  });

  return (
    <div className="w-full space-y-8">
      {/* ── Top Navigation & Meta Header ───────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="inline-flex items-center space-x-2 rounded-full border border-[#9CA6B2]/30 bg-white/60 px-3 py-1 text-[11px] font-semibold tracking-wider text-[#5477B8] uppercase backdrop-blur-sm dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/60 dark:text-[#6E90D1]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#5477B8] dark:bg-[#6E90D1]" />
            <span>Target Role Alignment Report</span>
          </div>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-[#181A1D] sm:text-3xl dark:text-[#F0F2F5]">
            {report.job_title ? `Target Role: ${report.job_title}` : "Job Description Requirement Match"}
          </h2>
          <p className="text-xs text-[#58616D] dark:text-[#A0ABB8]">
            Evaluated against: <span className="font-semibold text-[#181A1D] dark:text-[#F0F2F5]">{resume.filename}</span>
          </p>
        </div>

        <div className="flex items-center gap-2">
          {onLaunchBuilder && (
            <button
              id="launchBuilderFromJobMatchBtn"
              type="button"
              onClick={onLaunchBuilder}
              className="inline-flex items-center space-x-1.5 rounded-xl bg-[#5477B8] px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-[#43629C] dark:bg-[#6E90D1]"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              <span>Open in Resume Builder</span>
            </button>
          )}
          <button
            id="switchToAtsBtn"
            type="button"
            onClick={onSwitchToAts}
            className="inline-flex items-center space-x-1.5 rounded-xl border border-[#9CA6B2]/30 bg-white/70 px-4 py-2 text-xs font-semibold text-[#5477B8] shadow-sm transition hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/70 dark:text-[#6E90D1] dark:hover:bg-[#20252D]"
          >
            <span>View ATS Readiness</span>
          </button>
          <button
            id="backToReviewButton"
            type="button"
            onClick={onBackToReview}
            className="inline-flex items-center space-x-1.5 rounded-xl border border-[#9CA6B2]/30 bg-white/70 px-4 py-2 text-xs font-semibold text-[#181A1D] shadow-sm transition hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/70 dark:text-[#F0F2F5] dark:hover:bg-[#20252D]"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M11 17l-5-5m0 0l5-5m-5 5h12" />
            </svg>
            <span>Edit Resume / JD</span>
          </button>
          <button
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
            {report.score_withheld ? (
              <div className="flex flex-col items-center justify-center p-6 text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-amber-500/10 text-amber-600 dark:bg-amber-950/40 dark:text-amber-400">
                  <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <h3 className="mt-3 text-base font-bold text-[#181A1D] dark:text-[#F0F2F5]">
                  Score Withheld
                </h3>
                <p className="mt-1 max-w-xs text-xs text-[#58616D] dark:text-[#A0ABB8]">
                  {report.withheld_reason || "The provided job description did not contain enough identifiable requirements to compute a grounded match score."}
                </p>
                <button
                  type="button"
                  onClick={onBackToReview}
                  className="mt-4 rounded-xl bg-[#5477B8] px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-[#43629C] dark:bg-[#6E90D1]"
                >
                  Provide More Detailed JD
                </button>
              </div>
            ) : (
              <>
                <div className="relative flex h-40 w-40 items-center justify-center sm:h-44 sm:w-44">
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
                      strokeDashoffset={427 - (427 * (overall ?? 0)) / 100}
                      strokeLinecap="round"
                      stroke="currentColor"
                      fill="transparent"
                      style={{ transition: "stroke-dashoffset 1s ease-in-out" }}
                    />
                  </svg>

                  <div className="absolute flex flex-col items-center justify-center">
                    <span className="text-4xl font-extrabold tracking-tight text-[#181A1D] sm:text-5xl dark:text-[#F0F2F5]">
                      {overall}
                    </span>
                    <span className="text-[11px] font-semibold text-[#838F9E] uppercase tracking-wider dark:text-[#64707D]">
                      Match Score
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
              </>
            )}
          </div>

          {/* Right: Category Breakdown Cards */}
          <div className="space-y-3 lg:col-span-7">
            <div className="flex items-center justify-between border-b border-[#9CA6B2]/20 pb-2">
              <span className="text-xs font-bold tracking-wider uppercase text-[#838F9E] dark:text-[#64707D]">
                Approved Job-Match Dimensions
              </span>
              <span className="text-[11px] text-[#838F9E] dark:text-[#64707D]">
                Grounded Requirement Satisfaction
              </span>
            </div>

            {Object.entries(report.category_scores).map(([catKey, cat]) => {
              const icon = CATEGORY_ICONS[catKey] || CATEGORY_ICONS["hard_skills"];
              return (
                <div key={catKey} className="rounded-xl border border-[#9CA6B2]/20 bg-white/40 p-3 backdrop-blur-sm dark:border-[#9CA6B2]/10 dark:bg-[#1A1E24]/40">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-2">
                      <div className="flex h-6 w-6 items-center justify-center rounded-md bg-[#5477B8]/10 text-[#5477B8] dark:bg-[#6E90D1]/10 dark:text-[#6E90D1]">
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                          <path strokeLinecap="round" strokeLinejoin="round" d={icon} />
                        </svg>
                      </div>
                      <span className="font-semibold text-[#181A1D] dark:text-[#F0F2F5]">
                        {cat.label}{" "}
                        <span className="text-[10px] text-[#838F9E] font-normal dark:text-[#64707D]">
                          ({Math.round(cat.normalized_weight * 100)}% Weight)
                        </span>
                      </span>
                    </div>

                    {cat.is_applicable ? (
                      <span className="font-bold text-[#181A1D] dark:text-[#F0F2F5]">
                        {cat.score} <span className="text-[10px] text-[#838F9E]">/ 100</span>
                      </span>
                    ) : (
                      <span className="rounded bg-black/5 dark:bg-white/5 px-2 py-0.5 text-[10px] font-semibold text-[#838F9E]">
                        Not in Job Posting
                      </span>
                    )}
                  </div>

                  {cat.is_applicable && (
                    <div className="mt-2">
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#9CA6B2]/20 dark:bg-[#9CA6B2]/10">
                        <div
                          className="h-full rounded-full bg-[#5477B8] dark:bg-[#6E90D1]"
                          style={{ width: `${Math.max(4, cat.score)}%` }}
                        />
                      </div>
                      <div className="mt-1 flex items-center justify-between text-[10px] text-[#838F9E] dark:text-[#64707D]">
                        <span>{cat.matched_count} Matched</span>
                        <span>{cat.partial_count} Partial</span>
                        <span>{cat.gap_count} Gaps</span>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── Requirement Matrix Filters ─────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-[#9CA6B2]/30 pb-3 dark:border-[#9CA6B2]/20">
        <div className="flex flex-wrap gap-2">
          {(
            [
              { key: "all", label: `All Requirements (${report.requirements.length})` },
              { key: "matched", label: `Matched (${report.matched_count})`, countClass: "text-emerald-600" },
              { key: "partial", label: `Partially Supported (${report.partial_count})`, countClass: "text-amber-600" },
              { key: "gap", label: `Unsubstantiated Gaps (${report.gap_count})`, countClass: "text-rose-600" },
            ] as const
          ).map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setStatusFilter(tab.key)}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                statusFilter === tab.key
                  ? "bg-[#5477B8] text-white shadow-sm dark:bg-[#6E90D1]"
                  : "border border-[#9CA6B2]/25 bg-white/60 text-[#58616D] hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/15 dark:bg-[#1A1E24]/60 dark:text-[#A0ABB8] dark:hover:bg-[#20252D]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <span className="text-[11px] text-[#838F9E] dark:text-[#64707D]">
          Click citations to inspect verbatim resume evidence
        </span>
      </div>

      {/* ── Requirements Detailed List ──────────────────────────────────────── */}
      <div className="space-y-4">
        {filteredRequirements.length === 0 ? (
          <div className="rounded-xl border border-[#9CA6B2]/20 bg-white/40 p-8 text-center text-xs text-[#838F9E] dark:border-[#9CA6B2]/10 dark:bg-[#14171C]/40">
            No requirements found matching this filter.
          </div>
        ) : (
          filteredRequirements.map((req) => {
            const isExpanded = Boolean(expandedSnippets[req.id]);
            return (
              <div
                key={req.id}
                className="rounded-xl border border-[#9CA6B2]/25 bg-white/60 p-4 shadow-sm backdrop-blur-sm transition dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/60"
              >
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                  <div className="space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {/* Match Status Badge */}
                      <span
                        className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                          req.match_status === "matched"
                            ? "bg-emerald-500/15 text-emerald-700 border border-emerald-500/30 dark:text-emerald-300"
                            : req.match_status === "partially_supported"
                            ? "bg-amber-500/15 text-amber-700 border border-amber-500/30 dark:text-amber-300"
                            : "bg-rose-500/15 text-rose-700 border border-rose-500/30 dark:text-rose-300"
                        }`}
                      >
                        {req.match_status === "matched"
                          ? "✓ Supported"
                          : req.match_status === "partially_supported"
                          ? "◐ Partially Supported"
                          : "✕ Not Demonstrated"}
                      </span>

                      {/* Required vs Preferred */}
                      <span className="rounded bg-black/5 dark:bg-white/5 px-2 py-0.5 text-[10px] font-semibold text-[#838F9E] dark:text-[#64707D]">
                        {req.is_required ? "Must-Have Requirement" : "Preferred / Bonus"}
                      </span>

                      <span className="text-[10px] font-mono text-[#838F9E] uppercase dark:text-[#64707D]">
                        {req.category.replace("_", " ")}
                      </span>
                    </div>

                    <h4 className="text-sm font-bold text-[#181A1D] dark:text-[#F0F2F5]">
                      {req.original_text}
                    </h4>

                    <p className="text-xs text-[#58616D] dark:text-[#A0ABB8] leading-relaxed">
                      {req.explanation}
                    </p>

                    {/* Recommendation for gap */}
                    {req.recommendation && (
                      <p className="mt-1 text-xs text-[#5477B8] dark:text-[#6E90D1] flex items-center space-x-1">
                        <span>💡 Tip:</span>
                        <span>{req.recommendation}</span>
                      </p>
                    )}
                  </div>

                  {/* Verbatim Evidence Toggle Button */}
                  {req.evidence_snippet && (
                    <button
                      type="button"
                      onClick={() => toggleSnippet(req.id)}
                      className="self-start inline-flex items-center space-x-1 rounded-lg border border-[#9CA6B2]/30 bg-white/80 px-2.5 py-1 text-[11px] font-semibold text-[#5477B8] shadow-xs transition hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/80 dark:text-[#6E90D1] dark:hover:bg-[#20252D]"
                    >
                      <span>{isExpanded ? "Hide Evidence" : "View Verbatim Citation"}</span>
                      <svg
                        className={`h-3 w-3 transform transition-transform ${isExpanded ? "rotate-180" : ""}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                  )}
                </div>

                {/* Expandable Verbatim Evidence Snippet */}
                {req.evidence_snippet && isExpanded && (
                  <div className="mt-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 text-xs dark:border-emerald-500/20 dark:bg-emerald-950/20">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400 mb-1 flex items-center space-x-1">
                      <span>✓ Verbatim Resume Evidence:</span>
                    </p>
                    <blockquote className="border-l-2 border-emerald-500 pl-2.5 font-mono text-[11px] text-[#181A1D] dark:text-[#E2E8F0]">
                      &ldquo;{req.evidence_snippet}&rdquo;
                    </blockquote>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* ── Top Tailoring Recommendations ──────────────────────────────────── */}
      {report.top_recommendations.length > 0 && (
        <div className="rounded-2xl border border-[#5477B8]/20 bg-gradient-to-r from-[#5477B8]/5 via-[#9CA6B2]/5 to-[#5477B8]/5 p-6 backdrop-blur-md dark:border-[#6E90D1]/20">
          <div className="flex items-center space-x-2 text-[#5477B8] dark:text-[#6E90D1]">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <h3 className="text-sm font-bold uppercase tracking-wider">
              Priority Resume Tailoring Recommendations
            </h3>
          </div>
          <ul className="mt-3 space-y-2 text-xs text-[#181A1D] dark:text-[#F0F2F5]">
            {report.top_recommendations.map((rec, idx) => (
              <li key={idx} className="flex items-start space-x-2">
                <span className="mt-0.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-[#5477B8] dark:bg-[#6E90D1]" />
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Disclaimer & Heuristic Guardrails ──────────────────────────────── */}
      <div className="rounded-xl border border-[#9CA6B2]/20 bg-white/40 p-4 text-xs text-[#838F9E] dark:border-[#9CA6B2]/10 dark:bg-[#14171C]/40 dark:text-[#64707D]">
        <p className="font-semibold text-[#181A1D] dark:text-[#A0ABB8] mb-1">
          Job Match Alignment Disclaimer
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
