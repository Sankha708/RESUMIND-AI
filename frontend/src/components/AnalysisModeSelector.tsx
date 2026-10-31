"use client";

import React from "react";

export type AnalysisMode = "ats_readiness" | "job_match";

interface AnalysisModeSelectorProps {
  mode: AnalysisMode;
  onModeChange: (mode: AnalysisMode) => void;
  jobDescription: string;
  onJobDescriptionChange: (text: string) => void;
}

export function AnalysisModeSelector({
  mode,
  onModeChange,
  jobDescription,
  onJobDescriptionChange,
}: AnalysisModeSelectorProps) {
  const isJobMatch = mode === "job_match";

  return (
    <div className="space-y-4">
      {/* Mode Selection Label */}
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold uppercase tracking-wider text-[#58616D] dark:text-[#A0ABB8]">
          Analysis Mode
        </label>
        <span className="text-[11px] text-[#838F9E] dark:text-[#64707D]">
          {isJobMatch ? "Evaluates role-specific requirements" : "Evaluates format & parser hygiene"}
        </span>
      </div>

      {/* Segmented Control */}
      <div
        role="radiogroup"
        aria-label="Analysis Mode"
        className="grid grid-cols-2 gap-1.5 rounded-xl border border-[#9CA6B2]/25 bg-[#F3F5F6]/60 p-1 backdrop-blur-md dark:border-[#9CA6B2]/15 dark:bg-[#1A1E24]/60"
      >
        {/* ATS Readiness Choice */}
        <button
          type="button"
          role="radio"
          aria-checked={mode === "ats_readiness"}
          onClick={() => onModeChange("ats_readiness")}
          className={`flex items-center justify-center space-x-2 rounded-lg px-3 py-2 text-xs font-medium transition-all ${
            mode === "ats_readiness"
              ? "border border-[#9CA6B2]/30 bg-white text-[#181A1D] shadow-sm dark:border-[#9CA6B2]/20 dark:bg-[#222831] dark:text-[#F0F2F5]"
              : "text-[#58616D] hover:text-[#181A1D] dark:text-[#A0ABB8] dark:hover:text-[#F0F2F5]"
          }`}
        >
          <svg
            className={`h-3.5 w-3.5 ${
              mode === "ats_readiness"
                ? "text-[#5477B8] dark:text-[#6E90D1]"
                : "text-[#9CA6B2]"
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>ATS Readiness</span>
        </button>

        {/* Job Match Choice */}
        <button
          type="button"
          role="radio"
          aria-checked={mode === "job_match"}
          onClick={() => onModeChange("job_match")}
          className={`flex items-center justify-center space-x-2 rounded-lg px-3 py-2 text-xs font-medium transition-all ${
            mode === "job_match"
              ? "border border-[#9CA6B2]/30 bg-white text-[#181A1D] shadow-sm dark:border-[#9CA6B2]/20 dark:bg-[#222831] dark:text-[#F0F2F5]"
              : "text-[#58616D] hover:text-[#181A1D] dark:text-[#A0ABB8] dark:hover:text-[#F0F2F5]"
          }`}
        >
          <svg
            className={`h-3.5 w-3.5 ${
              mode === "job_match"
                ? "text-[#5477B8] dark:text-[#6E90D1]"
                : "text-[#9CA6B2]"
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <span>Job Match</span>
        </button>
      </div>

      {/* Conditional Job Description Input Drawer */}
      {isJobMatch && (
        <div className="space-y-2 rounded-xl border border-[#9CA6B2]/20 bg-white/40 p-3.5 backdrop-blur-sm dark:border-[#9CA6B2]/15 dark:bg-[#1A1E24]/40">
          <div className="flex items-center justify-between">
            <label
              htmlFor="jobDescriptionInput"
              className="text-xs font-medium text-[#181A1D] dark:text-[#F0F2F5]"
            >
              Target Job Posting
            </label>
            <span className="text-[10px] text-[#838F9E] dark:text-[#64707D]">
              {jobDescription.length} / 10,000 characters
            </span>
          </div>

          <textarea
            id="jobDescriptionInput"
            rows={3}
            value={jobDescription}
            onChange={(e) => onJobDescriptionChange(e.target.value.slice(0, 10000))}
            placeholder="Paste target job responsibilities, skills, or role requirements..."
            className="w-full rounded-lg border border-[#9CA6B2]/25 bg-white/70 p-2.5 text-xs text-[#181A1D] placeholder-[#9CA6B2] transition focus:border-[#5477B8] focus:outline-none focus:ring-1 focus:ring-[#5477B8] dark:border-[#9CA6B2]/20 dark:bg-[#0E1013]/60 dark:text-[#F0F2F5] dark:placeholder-[#64707D]"
          />
          <p className="text-[11px] text-[#58616D] dark:text-[#A0ABB8]">
            Requirements will be cross-referenced against your resume with verbatim citations.
          </p>
        </div>
      )}
    </div>
  );
}
