"use client";

import React, { useRef, useState } from "react";
import { getApiBaseUrl } from "@/lib/api";

export interface StructuredProfile {
  contact: {
    name: string | null;
    email: string | null;
    phone: string | null;
    headline?: string | null;
    urls: string[];
    location: string | null;
    uncertainty: Record<string, boolean>;
  };
  summary: string | null;
  experience: string[];
  education: string[];
  skills: string[];
  skill_categories?: { category: string; skills: string[] }[];
  projects: string[];
  certifications: string[];
  other: string[];
  warnings: string[];
}

export interface ParsedResume {
  id: string;
  session_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  raw_text: string;
  structured_data: StructuredProfile;
  created_at: string;
  updated_at: string;
}

interface ResumeUploadSurfaceProps {
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
  onUploadSuccess: (result: ParsedResume) => void;
  analysisMode: "ats_readiness" | "job_match";
  isReady: boolean;
  ctaLabel: string;
}

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ALLOWED_EXTENSIONS = [".pdf", ".docx"];
const API_BASE = getApiBaseUrl();

type UploadState = "idle" | "uploading" | "error";

export function ResumeUploadSurface({
  selectedFile,
  onFileSelect,
  onUploadSuccess,
  isReady,
  ctaLabel,
}: ResumeUploadSurfaceProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateAndSetFile = (file: File) => {
    setValidationError(null);
    setUploadError(null);
    setUploadState("idle");

    if (file.size > MAX_FILE_SIZE) {
      setValidationError("File exceeds maximum allowable size of 10MB.");
      onFileSelect(null);
      return;
    }

    const fileName = file.name.toLowerCase();
    const hasValidExt = ALLOWED_EXTENSIONS.some((ext) => fileName.endsWith(ext));
    if (!hasValidExt) {
      setValidationError("Invalid file type. Please select a .pdf or .docx document.");
      onFileSelect(null);
      return;
    }

    onFileSelect(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleRemoveFile = () => {
    onFileSelect(null);
    setValidationError(null);
    setUploadError(null);
    setUploadState("idle");
    setUploadProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleAnalyzeTrigger = async () => {
    if (!selectedFile || !isReady) return;

    setUploadState("uploading");
    setUploadError(null);
    setUploadProgress(10);

    let progressTimer: ReturnType<typeof setInterval> | undefined;
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      // Simulate early progress tick while waiting for server response
      progressTimer = setInterval(() => {
        setUploadProgress((prev) => Math.min(prev + 8, 88));
      }, 300);

      const response = await fetch(`${API_BASE}/api/resume/upload`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });

      clearInterval(progressTimer);
      progressTimer = undefined;
      setUploadProgress(95);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Upload failed. Please try again." }));
        const message =
          response.status === 413
            ? "File is too large. Maximum upload size is 10MB."
            : response.status === 400
            ? errorData.detail || "Document is invalid or unsupported."
            : response.status === 422
            ? errorData.detail || "Document could not be parsed. Try a different file."
            : errorData.detail || "Upload failed. Please check your connection and try again.";

        setUploadError(message);
        setUploadState("error");
        setUploadProgress(0);
        return;
      }

      const result: ParsedResume = await response.json();
      setUploadProgress(100);

      // Short pause at 100% before transitioning
      setTimeout(() => {
        setUploadState("idle");
        setUploadProgress(0);
        onUploadSuccess(result);
      }, 400);
    } catch (err: unknown) {
      if (progressTimer) clearInterval(progressTimer);
      const detail = err instanceof Error ? err.message : "Unknown network error";
      const msg =
        err instanceof TypeError && /fetch|network/i.test(err.message)
          ? `Could not reach the API at ${API_BASE}. Keep the backend running on port 8000 and open the frontend using the matching host (for example, http://127.0.0.1:3000). Browser detail: ${detail}`
          : `Upload failed: ${detail}`;
      setUploadError(msg);
      setUploadState("error");
      setUploadProgress(0);
    }
  };

  const isUploading = uploadState === "uploading";

  return (
    <div className="rounded-2xl border border-[#9CA6B2]/30 bg-white/70 p-6 shadow-sm backdrop-blur-md dark:border-[#9CA6B2]/20 dark:bg-[#14171C]/75">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        onChange={handleFileInputChange}
        className="hidden"
        id="resumeFileInput"
      />

      {!selectedFile ? (
        // Empty State: Drag & Drop Dropzone
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              fileInputRef.current?.click();
            }
          }}
          tabIndex={0}
          role="button"
          aria-label="Upload resume: drag and drop PDF or DOCX file, or press to browse"
          className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition-all cursor-pointer ${
            isDragging
              ? "border-[#5477B8] bg-[#5477B8]/10 dark:border-[#6E90D1] dark:bg-[#6E90D1]/10"
              : "border-[#9CA6B2]/40 bg-[#F3F5F6]/40 hover:border-[#5477B8]/60 hover:bg-[#F3F5F6]/70 dark:border-[#9CA6B2]/25 dark:bg-[#1A1E24]/40 dark:hover:border-[#6E90D1]/50"
          }`}
        >
          <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-full border border-[#9CA6B2]/30 bg-white/80 text-[#5477B8] shadow-sm dark:border-[#9CA6B2]/20 dark:bg-[#20252D] dark:text-[#6E90D1]">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
          </div>

          <h3 className="text-sm font-semibold text-[#181A1D] dark:text-[#F0F2F5]">
            Select or drag your resume here
          </h3>
          <p className="mt-1 text-xs text-[#58616D] dark:text-[#A0ABB8]">
            Accepts PDF or DOCX format (up to 10MB)
          </p>

          <button
            type="button"
            className="mt-4 inline-flex items-center space-x-1.5 rounded-lg border border-[#9CA6B2]/30 bg-white px-3.5 py-1.5 text-xs font-medium text-[#181A1D] shadow-sm transition hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/20 dark:bg-[#20252D] dark:text-[#F0F2F5] dark:hover:bg-[#282F3A]"
          >
            <span>Browse Documents</span>
          </button>
        </div>
      ) : (
        // Selected File State
        <div className="rounded-xl border border-[#9CA6B2]/30 bg-white/50 p-4 backdrop-blur-sm dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/50">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#9CA6B2]/30 bg-[#5477B8]/10 text-[#5477B8] dark:border-[#9CA6B2]/20 dark:bg-[#6E90D1]/15 dark:text-[#6E90D1]">
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>

              <div>
                <p className="text-xs font-semibold text-[#181A1D] dark:text-[#F0F2F5]">
                  {selectedFile.name}
                </p>
                <div className="flex items-center space-x-2 text-[11px] text-[#58616D] dark:text-[#A0ABB8]">
                  <span>{formatFileSize(selectedFile.size)}</span>
                  <span>•</span>
                  <span className="text-[#2E7D5A] dark:text-[#4EAD82] font-medium">
                    Verified Valid Format
                  </span>
                </div>
              </div>
            </div>

            {!isUploading && (
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="text-xs font-medium text-[#5477B8] hover:underline dark:text-[#6E90D1]"
                >
                  Replace
                </button>
                <button
                  type="button"
                  onClick={handleRemoveFile}
                  className="rounded p-1 text-[#838F9E] hover:bg-[#F3F5F6] hover:text-[#B33939] dark:text-[#64707D] dark:hover:bg-[#20252D] dark:hover:text-[#D9534F]"
                  aria-label="Remove selected resume"
                  title="Remove selected resume"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}
          </div>

          {/* Upload progress bar */}
          {isUploading && (
            <div className="mt-3">
              <div className="flex items-center justify-between text-[10px] text-[#58616D] dark:text-[#A0ABB8] mb-1">
                <span>Extracting document…</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="h-1 w-full rounded-full bg-[#9CA6B2]/20 dark:bg-[#9CA6B2]/10 overflow-hidden">
                <div
                  className="h-full rounded-full bg-[#5477B8] dark:bg-[#6E90D1] transition-all duration-300 ease-out"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Client-side validation error */}
      {validationError && (
        <div className="mt-3 flex items-center space-x-2 rounded-lg border border-[#B33939]/30 bg-[#B33939]/10 p-2.5 text-xs text-[#B33939] dark:border-[#D9534F]/30 dark:bg-[#D9534F]/10 dark:text-[#D9534F]">
          <svg className="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span>{validationError}</span>
        </div>
      )}

      {/* Backend upload error */}
      {uploadError && (
        <div className="mt-3 flex items-start space-x-2 rounded-lg border border-[#B33939]/30 bg-[#B33939]/10 p-2.5 text-xs text-[#B33939] dark:border-[#D9534F]/30 dark:bg-[#D9534F]/10 dark:text-[#D9534F]">
          <svg className="h-4 w-4 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <span className="font-semibold">Upload failed: </span>
            <span>{uploadError}</span>
          </div>
        </div>
      )}

      {/* Primary Action Button */}
      <div className="mt-5">
        <button
          id="analyzeResumeBtn"
          type="button"
          onClick={handleAnalyzeTrigger}
          disabled={!isReady || isUploading}
          className={`flex w-full items-center justify-center space-x-2 rounded-xl py-3 px-4 text-xs font-semibold tracking-wide transition-all shadow-sm ${
            isReady && !isUploading
              ? "bg-[#5477B8] text-white hover:bg-[#43629C] dark:bg-[#6E90D1] dark:hover:bg-[#85A3DC] cursor-pointer"
              : "bg-[#9CA6B2]/20 text-[#838F9E] cursor-not-allowed dark:bg-[#9CA6B2]/10 dark:text-[#64707D]"
          }`}
          aria-label={ctaLabel}
        >
          {isUploading ? (
            <>
              <svg className="h-3.5 w-3.5 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span>Parsing document…</span>
            </>
          ) : (
            <>
              <span>{ctaLabel}</span>
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </>
          )}
        </button>

        <p className="mt-2 text-center text-[10px] text-[#838F9E] dark:text-[#64707D]">
          No login required · Documents are stored only for your active session
        </p>
      </div>
    </div>
  );
}
