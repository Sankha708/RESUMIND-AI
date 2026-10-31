"use client";

import React, { useState, useCallback, useEffect } from "react";
import { getApiBaseUrl } from "@/lib/api";
import { useSession } from "@/context/SessionContext";
import { Header } from "@/components/Header";
import { SignatureIllustration } from "@/components/SignatureIllustration";
import { ResumeUploadSurface, ParsedResume, StructuredProfile } from "@/components/ResumeUploadSurface";
import { ResumeReviewScreen } from "@/components/ResumeReviewScreen";
import { AnalysisModeSelector, AnalysisMode } from "@/components/AnalysisModeSelector";
import { ATSReportView, ATSAssessmentData } from "@/components/ATSReportView";
import { JobMatchReportView, JobMatchAssessmentData } from "@/components/JobMatchReportView";
import { ImprovementStudioView } from "@/components/ImprovementStudioView";
import { ResumeBuilderView } from "@/components/ResumeBuilderView";
import { ExportCenterView } from "@/components/ExportCenterView";

type AppView = "upload" | "review" | "ats_report" | "job_match_report" | "improvement_studio" | "builder" | "export";

const API_BASE = getApiBaseUrl();

export default function Home() {
  const { loading: sessionLoading, backendOnline } = useSession();
  const [appView, setAppView] = useState<AppView>("upload");
  const [isRestoringSession, setIsRestoringSession] = useState<boolean>(true);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>("ats_readiness");
  const [jobDescription, setJobDescription] = useState<string>("");
  const [parsedResume, setParsedResume] = useState<ParsedResume | null>(null);

  // ATS Assessment state
  const [assessmentData, setAssessmentData] = useState<ATSAssessmentData | null>(null);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);
  const [evaluationError, setEvaluationError] = useState<string | null>(null);

  // Job Match state
  const [jobMatchData, setJobMatchData] = useState<JobMatchAssessmentData | null>(null);
  const [isJobMatching, setIsJobMatching] = useState<boolean>(false);
  const [jobMatchError, setJobMatchError] = useState<string | null>(null);

  useEffect(() => {
    if (sessionLoading) return;

    let cancelled = false;

    async function restoreActiveSession() {
      try {
        if (!backendOnline) return;

        const resumeResponse = await fetch(`${API_BASE}/api/resume`, {
          credentials: "include",
        });
        if (!resumeResponse.ok) return;

        const resume: ParsedResume = await resumeResponse.json();
        if (cancelled) return;
        setParsedResume(resume);

        const statusResponse = await fetch(`${API_BASE}/api/export/status`, {
          credentials: "include",
        });
        if (!statusResponse.ok) {
          setAppView("review");
          return;
        }

        const exportStatus: { has_builder_document: boolean } = await statusResponse.json();
        if (!cancelled) {
          setAppView(exportStatus.has_builder_document ? "builder" : "review");
        }
      } catch {
        // Keep the upload screen available if session restoration cannot reach the API.
      } finally {
        if (!cancelled) setIsRestoringSession(false);
      }
    }

    void restoreActiveSession();
    return () => {
      cancelled = true;
    };
  }, [sessionLoading, backendOnline]);

  // ── Derived readiness for upload CTA ──────────────────────────────────────
  const isReady =
    Boolean(selectedFile) &&
    (analysisMode === "ats_readiness" || jobDescription.trim().length >= 20);

  const getCtaLabel = (): string => {
    if (!selectedFile) return "Select Resume Document to Begin";
    if (analysisMode === "ats_readiness") return "Upload & Extract Resume";
    if (jobDescription.trim().length < 20) return "Provide Job Description to Continue";
    return "Upload & Extract Resume";
  };

  // ── Callbacks ──────────────────────────────────────────────────────────────
  const handleUploadSuccess = useCallback((result: ParsedResume) => {
    setParsedResume(result);
    setAssessmentData(null);
    setEvaluationError(null);
    setJobMatchData(null);
    setJobMatchError(null);
    setAppView("review");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const handleSaveCorrections = useCallback(
    async (updatedProfile: StructuredProfile) => {
      if (!parsedResume) throw new Error("No active resume to update.");

      const response = await fetch(`${API_BASE}/api/resume`, {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ structured_data: updatedProfile }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to save corrections.");
      }

      const updated: ParsedResume = await response.json();
      setParsedResume(updated);
      // Invalidate existing assessments so subsequent runs re-evaluate
      setAssessmentData(null);
      setJobMatchData(null);
    },
    [parsedResume]
  );

  const handleReset = useCallback(() => {
    setSelectedFile(null);
    setAnalysisMode("ats_readiness");
    setJobDescription("");
    setParsedResume(null);
    setAssessmentData(null);
    setEvaluationError(null);
    setIsEvaluating(false);
    setJobMatchData(null);
    setJobMatchError(null);
    setIsJobMatching(false);
    setAppView("upload");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const runAssessment = useCallback(async (recalculate: boolean = false) => {
    setIsEvaluating(true);
    setEvaluationError(null);
    window.scrollTo({ top: 0, behavior: "smooth" });

    try {
      const url = recalculate
        ? `${API_BASE}/api/assessment?recalculate=true`
        : `${API_BASE}/api/assessment`;

      const response = await fetch(url, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `Assessment request failed (${response.status})`);
      }

      const data: ATSAssessmentData = await response.json();
      setAssessmentData(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "An unexpected error occurred while scoring the resume.";
      setEvaluationError(msg);
    } finally {
      setIsEvaluating(false);
    }
  }, []);

  const runJobMatch = useCallback(async (recalculate: boolean = false, overrideJd?: string) => {
    const jdToUse = (overrideJd !== undefined ? overrideJd : jobDescription).trim();
    if (!jdToUse) {
      setJobMatchError("Job description text is required to evaluate Job Match.");
      return;
    }

    setIsJobMatching(true);
    setJobMatchError(null);
    window.scrollTo({ top: 0, behavior: "smooth" });

    try {
      const response = await fetch(`${API_BASE}/api/job-match`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_description: jdToUse,
          recalculate,
        }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `Job match request failed (${response.status})`);
      }

      const data: JobMatchAssessmentData = await response.json();
      setJobMatchData(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "An error occurred while evaluating job description match.";
      setJobMatchError(msg);
    } finally {
      setIsJobMatching(false);
    }
  }, [jobDescription]);

  const handleProceedToAnalysis = useCallback(
    (
      _profile: StructuredProfile,
      mode: "ats_readiness" | "job_match",
      jobDesc: string
    ) => {
      if (mode === "job_match") {
        setAppView("job_match_report");
        runJobMatch(false, jobDesc);
      } else {
        setAppView("ats_report");
        runAssessment(false);
      }
    },
    [runAssessment, runJobMatch]
  );

  const handleRetryAssessment = useCallback(() => {
    runAssessment(true);
  }, [runAssessment]);

  const handleRetryJobMatch = useCallback(() => {
    runJobMatch(true);
  }, [runJobMatch]);

  const handleBackToReview = useCallback(() => {
    setAppView("review");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const handleSwitchToAts = useCallback(() => {
    setAnalysisMode("ats_readiness");
    setAppView("ats_report");
    if (!assessmentData) {
      runAssessment(false);
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [assessmentData, runAssessment]);

  const handleLaunchImprovementStudio = useCallback(() => {
    setAppView("improvement_studio");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const handleLaunchBuilder = useCallback(() => {
    setAppView("builder");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const handleLaunchExport = useCallback(() => {
    setAppView("export");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const handleUpdateResumeProfile = useCallback((updatedProfile: StructuredProfile) => {
    setParsedResume((prev) => (prev ? { ...prev, structured_data: updatedProfile } : prev));
    // Invalidate cached assessment scores so re-evaluating reflects the updated resume
    setAssessmentData(null);
    setJobMatchData(null);
  }, []);

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="flex min-h-screen flex-col bg-[#F3F5F6] text-[#181A1D] transition-colors duration-200 dark:bg-[#0E1013] dark:text-[#F0F2F5]">
      {/* Sticky Header */}
      <Header onFreshStart={handleReset} />

      <main className="mx-auto flex w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 lg:px-8 lg:py-12">
        {isRestoringSession ? (
          <div className="flex min-h-[360px] w-full items-center justify-center">
            <p role="status" className="text-sm font-medium text-[#58616D] dark:text-[#A0ABB8]">
              Restoring your private workspace...
            </p>
          </div>
        ) : (
          <>

        {/* ── VIEW: Upload ── */}
        {appView === "upload" && (
          <div className="grid w-full grid-cols-1 items-center gap-12 lg:grid-cols-12 lg:gap-8">
            {/* Left Column */}
            <div className="flex flex-col space-y-6 lg:col-span-7">
              <div className="space-y-3">
                <h1 className="text-3xl font-extrabold tracking-tight text-[#181A1D] sm:text-4xl lg:text-5xl dark:text-[#F0F2F5]">
                  Your experience. <br className="hidden sm:inline" />
                  Your next possibility.
                </h1>

                <p className="max-w-xl text-sm leading-relaxed text-[#58616D] sm:text-base dark:text-[#A0ABB8]">
                  Understand your resume, discover what a role requires, and present
                  your real strengths with greater clarity.
                </p>
              </div>

              {/* Analysis Mode Selector */}
              <div className="max-w-xl">
                <AnalysisModeSelector
                  mode={analysisMode}
                  onModeChange={setAnalysisMode}
                  jobDescription={jobDescription}
                  onJobDescriptionChange={setJobDescription}
                />
              </div>

              {/* Resume Upload Surface */}
              <div className="max-w-xl">
                <ResumeUploadSurface
                  selectedFile={selectedFile}
                  onFileSelect={setSelectedFile}
                  onUploadSuccess={handleUploadSuccess}
                  analysisMode={analysisMode}
                  isReady={isReady}
                  ctaLabel={getCtaLabel()}
                />
              </div>
            </div>

            {/* Right Column: Illustration */}
            <div className="flex items-center justify-center lg:col-span-5">
              <SignatureIllustration />
            </div>
          </div>
        )}

        {/* ── VIEW: Extraction Review ── */}
        {appView === "review" && parsedResume && (
          <div className="w-full max-w-3xl mx-auto">
            <ResumeReviewScreen
              resume={parsedResume}
              onSaveCorrections={handleSaveCorrections}
              onReset={handleReset}
              onProceed={handleProceedToAnalysis}
              analysisMode={analysisMode}
              jobDescription={jobDescription}
            />
          </div>
        )}

        {/* ── VIEW: Real ATS Report View (Phase 5) ── */}
        {appView === "ats_report" && parsedResume && (
          <div className="w-full max-w-4xl mx-auto">
            <ATSReportView
              assessment={assessmentData}
              resume={parsedResume}
              isLoading={isEvaluating}
              errorMessage={evaluationError}
              onRetry={handleRetryAssessment}
              onBackToReview={handleBackToReview}
              onUploadNew={handleReset}
              onProceedToImprovement={handleLaunchImprovementStudio}
              onLaunchBuilder={handleLaunchBuilder}
            />
          </div>
        )}

        {/* ── VIEW: Real Job Match Report View (Phase 6) ── */}
        {appView === "job_match_report" && parsedResume && (
          <div className="w-full max-w-4xl mx-auto">
            <JobMatchReportView
              assessment={jobMatchData}
              resume={parsedResume}
              isLoading={isJobMatching}
              errorMessage={jobMatchError}
              onRetry={handleRetryJobMatch}
              onBackToReview={handleBackToReview}
              onUploadNew={handleReset}
              onSwitchToAts={handleSwitchToAts}
              onLaunchBuilder={handleLaunchBuilder}
            />
          </div>
        )}

        {/* ── VIEW: AI Resume Improvement Studio (Phase 7 & 8) ── */}
        {appView === "improvement_studio" && parsedResume && (
          <div className="w-full max-w-4xl mx-auto">
            <ImprovementStudioView
              resume={parsedResume}
              onBackToAts={() => {
                setAppView("ats_report");
                if (!assessmentData) {
                  runAssessment(false);
                }
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
              onBackToReview={handleBackToReview}
              onUpdateResumeProfile={handleUpdateResumeProfile}
              onLaunchBuilder={handleLaunchBuilder}
            />
          </div>
        )}

        {/* ── VIEW: Resume Builder & Template Studio ── */}
        {appView === "builder" && (
          <div className="w-full max-w-7xl mx-auto">
            <ResumeBuilderView
              resume={parsedResume}
              onBackToAssessments={() => {
                setAppView(analysisMode === "job_match" ? "job_match_report" : "ats_report");
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
              onBackToReview={handleBackToReview}
              onProceedToExport={handleLaunchExport}
            />
          </div>
        )}

        {/* ── VIEW: Export Center ── */}
        {appView === "export" && (
          <div className="w-full max-w-5xl mx-auto">
            <ExportCenterView
              resume={parsedResume}
              onBackToBuilder={() => {
                setAppView("builder");
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
              onBackToAssessments={() => {
                setAppView(analysisMode === "job_match" ? "job_match_report" : "ats_report");
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
              onUploadNew={handleReset}
            />
          </div>
        )}
          </>
        )}
      </main>

    </div>
  );
}
