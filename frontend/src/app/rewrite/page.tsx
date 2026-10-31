"use client";

import React, { useState, useEffect, useCallback } from "react";
import { getApiBaseUrl } from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Header } from "@/components/Header";
import { ImprovementStudioView } from "@/components/ImprovementStudioView";
import { ParsedResume, StructuredProfile } from "@/components/ResumeUploadSurface";

const API_BASE = getApiBaseUrl();

export default function RewritePage() {
  const router = useRouter();
  const [resume, setResume] = useState<ParsedResume | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;
    async function loadSession() {
      try {
        const response = await fetch(`${API_BASE}/api/resume`, {
          credentials: "include",
        });

        if (response.status === 401 || response.status === 404) {
          if (!ignore) setResume(null);
          return;
        }

        if (!response.ok) {
          throw new Error(`Failed to load active resume session (${response.status})`);
        }

        const data: ParsedResume = await response.json();
        if (!ignore) {
          setResume(data);
        }
      } catch (err: unknown) {
        if (!ignore) {
          const msg = err instanceof Error ? err.message : "Failed to load active resume.";
          setError(msg);
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }
    loadSession();
    return () => {
      ignore = true;
    };
  }, []);

  const handleUpdateResumeProfile = useCallback((updatedProfile: StructuredProfile) => {
    setResume((prev) => (prev ? { ...prev, structured_data: updatedProfile } : prev));
  }, []);

  return (
    <div className="flex min-h-screen flex-col bg-[#F3F5F6] text-[#181A1D] transition-colors duration-200 dark:bg-[#0E1013] dark:text-[#F0F2F5]">
      <Header />

      <main className="mx-auto flex w-full max-w-4xl flex-1 px-4 py-8 sm:px-6 lg:px-8 lg:py-12">
        {isLoading && (
          <div className="flex w-full flex-col items-center justify-center py-24 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-[#5477B8]/40 bg-white/80 shadow-lg shadow-[#5477B8]/10 backdrop-blur-md dark:border-[#6E90D1]/30 dark:bg-[#1A1E24]/90">
              <svg className="h-8 w-8 animate-spin text-[#5477B8] dark:text-[#6E90D1]" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
            <h3 className="mt-6 text-lg font-bold text-[#181A1D] dark:text-[#F0F2F5]">
              Loading Active Session...
            </h3>
          </div>
        )}

        {!isLoading && error && (
          <div className="mx-auto flex w-full max-w-xl flex-col items-center justify-center rounded-2xl border border-red-500/20 bg-white/70 p-8 text-center shadow-lg backdrop-blur-md dark:border-red-500/20 dark:bg-[#1A1E24]/70">
            <h3 className="text-lg font-bold text-[#181A1D] dark:text-[#F0F2F5]">Session Error</h3>
            <p className="mt-2 text-sm text-[#58616D] dark:text-[#A0ABB8]">{error}</p>
            <Link
              href="/"
              className="mt-6 rounded-xl bg-[#5477B8] px-5 py-2.5 text-xs font-semibold text-white shadow-xs hover:bg-[#43629C] dark:bg-[#6E90D1]"
            >
              Return to Upload
            </Link>
          </div>
        )}

        {!isLoading && !error && !resume && (
          <div className="mx-auto flex w-full max-w-xl flex-col items-center justify-center rounded-2xl border border-[#9CA6B2]/30 bg-white/60 p-10 text-center shadow-lg backdrop-blur-md dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/60">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[#5477B8]/10 text-[#5477B8] dark:text-[#6E90D1]">
              <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="mt-4 text-xl font-bold text-[#181A1D] dark:text-[#F0F2F5]">
              No Active Resume Found
            </h3>
            <p className="mt-2 text-sm text-[#58616D] dark:text-[#A0ABB8]">
              Upload a resume document first to analyze weak bullets, active verbs, and launch the AI Rewrite Studio.
            </p>
            <Link
              href="/"
              className="mt-6 inline-flex items-center space-x-2 rounded-xl bg-[#5477B8] px-6 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-[#43629C] dark:bg-[#6E90D1]"
            >
              <span>Upload Resume Document</span>
            </Link>
          </div>
        )}

        {!isLoading && !error && resume && (
          <ImprovementStudioView
            resume={resume}
            onUpdateResumeProfile={handleUpdateResumeProfile}
            onBackToReview={() => {
              router.push("/");
            }}
            onBackToAts={() => {
              router.push("/");
            }}
          />
        )}
      </main>

    </div>
  );
}
