"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { getApiBaseUrl } from "@/lib/api";
import { ParsedResume, StructuredProfile } from "./ResumeUploadSurface";

export interface ImprovementSuggestion {
  id: string;
  section: string;
  item_index: number | null;
  category: string;
  original_text: string;
  proposed_text: string;
  user_edited_text: string | null;
  status: "identified" | "accepted" | "rejected" | "edited";
  explanation: string;
  is_ai_generated?: boolean;
  ai_model?: string | null;
  preserved_facts?: string[];
  potential_new_claims?: string[];
  needs_user_verification?: boolean;
  created_at: string;
  updated_at: string;
}

export interface ImprovementSummary {
  total_count: number;
  accepted_count: number;
  rejected_count: number;
  pending_count: number;
  suggestions: ImprovementSuggestion[];
  disclaimer: string;
}

export interface AIProviderStatus {
  available: boolean;
  provider: string;
  model: string;
  status_message: string;
  installed_models: string[];
}

interface ImprovementStudioViewProps {
  resume: ParsedResume;
  onUpdateResumeProfile: (updated: StructuredProfile) => void;
  onBackToReview: () => void;
  onBackToAts: () => void;
  onLaunchBuilder?: () => void;
}

const API_BASE = getApiBaseUrl();

const CATEGORY_LABELS: Record<string, { label: string; color: string; badge: string }> = {
  action_verb: {
    label: "Active Verb Front-Loading",
    color: "text-[#5477B8] bg-[#5477B8]/10 border-[#5477B8]/30 dark:text-[#6E90D1]",
    badge: "Action Verb",
  },
  quantifiable_impact: {
    label: "Quantifiable Impact Placeholder",
    color: "text-emerald-700 bg-emerald-500/10 border-emerald-500/30 dark:text-emerald-400",
    badge: "Metrics & Impact",
  },
  brevity_readability: {
    label: "Brevity & Readability",
    color: "text-amber-700 bg-amber-500/10 border-amber-500/30 dark:text-amber-400",
    badge: "Brevity",
  },
  scope_clarity: {
    label: "Scope & Technology Context",
    color: "text-indigo-700 bg-indigo-500/10 border-indigo-500/30 dark:text-indigo-400",
    badge: "Scope & Tech",
  },
  repetition: {
    label: "Repetitive Phrasing",
    color: "text-rose-700 bg-rose-500/10 border-rose-500/30 dark:text-rose-400",
    badge: "Vocabulary",
  },
};

export function ImprovementStudioView({
  resume,
  onUpdateResumeProfile,
  onBackToReview,
  onBackToAts,
  onLaunchBuilder,
}: ImprovementStudioViewProps) {
  const [suggestions, setSuggestions] = useState<ImprovementSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeStatusFilter, setActiveStatusFilter] = useState<"all" | "pending" | "accepted" | "rejected">("all");
  const [activeSectionFilter, setActiveSectionFilter] = useState<string>("all");
  const [editedDrafts, setEditedDrafts] = useState<Record<string, string>>({});
  const [actionInProgress, setActionInProgress] = useState<Record<string, boolean>>({});
  const [aiRewriteInProgress, setAiRewriteInProgress] = useState<Record<string, boolean>>({});
  const [aiRewriteErrors, setAiRewriteErrors] = useState<Record<string, string>>({});
  const [aiRewriteRateLimited, setAiRewriteRateLimited] = useState<Record<string, boolean>>({});
  const [aiRewriteCooldownSeconds, setAiRewriteCooldownSeconds] = useState<number>(0);
  const [customPromptOpen, setCustomPromptOpen] = useState<Record<string, boolean>>({});
  const [customPromptInputs, setCustomPromptInputs] = useState<Record<string, string>>({});
  const [batchInProgress, setBatchInProgress] = useState<boolean>(false);
  const [batchNotification, setBatchNotification] = useState<string | null>(null);

  // AI Provider status
  const [providerStatus, setProviderStatus] = useState<AIProviderStatus | null>(null);
  const [isCheckingProvider, setIsCheckingProvider] = useState<boolean>(false);

  // Keyboard navigation & focused card
  const [focusedSuggestionId, setFocusedSuggestionId] = useState<string | null>(null);
  const textareaRefs = useRef<Record<string, HTMLTextAreaElement | null>>({});

  useEffect(() => {
    if (aiRewriteCooldownSeconds <= 0) return;

    const timer = window.setTimeout(() => {
      setAiRewriteCooldownSeconds((seconds) => Math.max(0, seconds - 1));
    }, 1000);

    return () => window.clearTimeout(timer);
  }, [aiRewriteCooldownSeconds]);

  // ── Load Provider Status ───────────────────────────────────────────────────
  const checkProviderStatus = useCallback(async () => {
    setIsCheckingProvider(true);
    try {
      const response = await fetch(`${API_BASE}/api/improvement/provider/status`, {
        credentials: "include",
      });
      if (response.ok) {
        const data: AIProviderStatus = await response.json();
        setProviderStatus(data);
      }
    } catch {
      setProviderStatus({
        available: false,
        provider: "ollama",
        model: "llama3.2",
        status_message: "Local Ollama server connection offline.",
        installed_models: [],
      });
    } finally {
      setIsCheckingProvider(false);
    }
  }, []);

  // ── Load Suggestions ───────────────────────────────────────────────────────
  const loadSuggestions = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const response = await fetch(`${API_BASE}/api/improvement/generate`, {
        method: "POST",
        credentials: "include",
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to load suggestions (${response.status})`);
      }

      const data: ImprovementSummary = await response.json();
      setSuggestions(data.suggestions);

      const initialDrafts: Record<string, string> = {};
      data.suggestions.forEach((s) => {
        initialDrafts[s.id] = s.user_edited_text || s.proposed_text;
      });
      setEditedDrafts(initialDrafts);

      if (data.suggestions.length > 0 && !focusedSuggestionId) {
        setFocusedSuggestionId(data.suggestions[0].id);
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to load improvement opportunities.");
    } finally {
      setIsLoading(false);
    }
  }, [focusedSuggestionId]);

  useEffect(() => {
    let ignore = false;
    async function init() {
      try {
        const pRes = await fetch(`${API_BASE}/api/improvement/provider/status`, { credentials: "include" });
        if (pRes.ok && !ignore) {
          const data: AIProviderStatus = await pRes.json();
          setProviderStatus(data);
        }
      } catch {
        if (!ignore) {
          setProviderStatus({
            available: false,
            provider: "ollama",
            model: "llama3.2",
            status_message: "Local Ollama server connection offline.",
            installed_models: [],
          });
        }
      } finally {
        if (!ignore) {
          setIsCheckingProvider(false);
        }
      }

      try {
        const response = await fetch(`${API_BASE}/api/improvement/generate`, {
          method: "POST",
          credentials: "include",
        });

        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(err.detail || `Failed to load suggestions (${response.status})`);
        }

        const data: ImprovementSummary = await response.json();
        if (!ignore) {
          setSuggestions(data.suggestions);

          const initialDrafts: Record<string, string> = {};
          data.suggestions.forEach((s) => {
            initialDrafts[s.id] = s.user_edited_text || s.proposed_text;
          });
          setEditedDrafts(initialDrafts);

          if (data.suggestions.length > 0) {
            setFocusedSuggestionId(data.suggestions[0].id);
          }
        }
      } catch (err: unknown) {
        if (!ignore) {
          setErrorMessage(err instanceof Error ? err.message : "Failed to load improvement opportunities.");
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    init();
    return () => {
      ignore = true;
    };
  }, []);

  // ── Sync canonical resume changes from backend ────────────────────────────
  const refreshCanonicalResume = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/resume`, { credentials: "include" });
      if (res.ok) {
        const updatedResume: ParsedResume = await res.json();
        onUpdateResumeProfile(updatedResume.structured_data);
      }
    } catch {
      // Non-fatal background sync
    }
  }, [onUpdateResumeProfile]);

  // ── Update Suggestion (Accept / Reject / Edit) ─────────────────────────────
  const handleUpdateSuggestion = useCallback(
    async (
      suggestionId: string,
      action: "accept" | "reject" | "edit",
      customText?: string
    ) => {
      setActionInProgress((prev) => ({ ...prev, [suggestionId]: true }));
      try {
        const response = await fetch(`${API_BASE}/api/improvement/${suggestionId}`, {
          method: "PUT",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action,
            user_edited_text: customText !== undefined ? customText : editedDrafts[suggestionId],
          }),
        });

        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(err.detail || `Failed to update suggestion (${response.status})`);
        }

        const updatedItem: ImprovementSuggestion = await response.json();
        setSuggestions((prev) => prev.map((s) => (s.id === suggestionId ? updatedItem : s)));

        if (action === "accept") {
          await refreshCanonicalResume();
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Failed to update suggestion.";
        alert(`Error updating suggestion: ${msg}`);
      } finally {
        setActionInProgress((prev) => ({ ...prev, [suggestionId]: false }));
      }
    },
    [editedDrafts, refreshCanonicalResume]
  );

  // ── Restore Suggestion ────────────────────────────────────────────────────
  const handleRestoreSuggestion = async (suggestionId: string) => {
    setActionInProgress((prev) => ({ ...prev, [suggestionId]: true }));
    try {
      const response = await fetch(`${API_BASE}/api/improvement/${suggestionId}/restore`, {
        method: "POST",
        credentials: "include",
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to restore original text.");
      }

      const restoredItem: ImprovementSuggestion = await response.json();
      setSuggestions((prev) => prev.map((s) => (s.id === suggestionId ? restoredItem : s)));
      setEditedDrafts((prev) => ({ ...prev, [suggestionId]: restoredItem.proposed_text }));

      await refreshCanonicalResume();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to restore original text.";
      alert(`Error restoring original text: ${msg}`);
    } finally {
      setActionInProgress((prev) => ({ ...prev, [suggestionId]: false }));
    }
  };

  // ── AI Rewrite with Ollama (Phase 8) ──────────────────────────────────────
  const handleTriggerAIRewrite = async (suggestionId: string) => {
    setAiRewriteInProgress((prev) => ({ ...prev, [suggestionId]: true }));
    setAiRewriteErrors((prev) => ({ ...prev, [suggestionId]: "" }));
    setAiRewriteRateLimited((prev) => ({ ...prev, [suggestionId]: false }));
    const customPrompt = customPromptInputs[suggestionId]?.trim() || undefined;

    try {
      const response = await fetch(`${API_BASE}/api/improvement/${suggestionId}/rewrite`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          custom_instruction: customPrompt,
        }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        if (response.status === 429) {
          const retryAfter = Number.parseInt(response.headers.get("Retry-After") || "", 10);
          const waitSeconds = Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter : 60;
          setAiRewriteCooldownSeconds(waitSeconds);
          setAiRewriteRateLimited((prev) => ({ ...prev, [suggestionId]: true }));
          throw new Error(err.detail || "Request rate limit exceeded. Please retry later.");
        }
        throw new Error(err.detail || `AI rewrite request failed (${response.status})`);
      }

      const updatedItem: ImprovementSuggestion = await response.json();
      setSuggestions((prev) => prev.map((s) => (s.id === suggestionId ? updatedItem : s)));
      setEditedDrafts((prev) => ({ ...prev, [suggestionId]: updatedItem.proposed_text }));
      setCustomPromptOpen((prev) => ({ ...prev, [suggestionId]: false }));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "AI rewrite failed.";
      const model = providerStatus?.model || "the configured Ollama model";
      const guidance = /local ai provider unavailable|ollama.*offline|ollama.*unreachable|model.*not installed/i.test(msg)
        ? ` Start Ollama and confirm ${model} is available. The suggestion is unchanged, and you can still edit the heuristic version.`
        : /rate limit exceeded/i.test(msg)
        ? " The suggestion is unchanged. Wait for the retry timer before trying again."
        : " The suggestion is unchanged; you can retry after the issue is resolved.";
      setAiRewriteErrors((prev) => ({ ...prev, [suggestionId]: `${msg}${guidance}` }));
    } finally {
      setAiRewriteInProgress((prev) => ({ ...prev, [suggestionId]: false }));
    }
  };

  // ── Batch Accept High-Confidence Suggestions ──────────────────────────────
  const handleBatchAccept = async () => {
    setBatchInProgress(true);
    setBatchNotification(null);
    try {
      const response = await fetch(`${API_BASE}/api/improvement/batch-accept`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          only_without_placeholders: true,
        }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to batch accept suggestions.");
      }

      const result = await response.json();
      setSuggestions(result.suggestions);

      // Re-populate draft text
      const newDrafts: Record<string, string> = {};
      result.suggestions.forEach((s: ImprovementSuggestion) => {
        newDrafts[s.id] = s.user_edited_text || s.proposed_text;
      });
      setEditedDrafts(newDrafts);

      await refreshCanonicalResume();
      setBatchNotification(
        `Batch optimization applied: ${result.accepted_count} suggestions accepted to your active resume (${result.skipped_count} skipped requiring manual input).`
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to batch accept suggestions.";
      alert(`Batch accept failed: ${msg}`);
    } finally {
      setBatchInProgress(false);
    }
  };

  // ── Keyboard Shortcuts (A = Accept, R = Reject, E = Edit) ──────────────────
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't intercept when user is actively typing in textarea or input
      const activeTag = document.activeElement?.tagName.toLowerCase();
      if (activeTag === "textarea" || activeTag === "input") {
        return;
      }

      if (!focusedSuggestionId) return;
      const targetSuggestion = suggestions.find((s) => s.id === focusedSuggestionId);
      if (!targetSuggestion) return;

      const key = e.key.toUpperCase();
      if (key === "A") {
        e.preventDefault();
        const currentDraft = editedDrafts[targetSuggestion.id] ?? targetSuggestion.proposed_text;
        handleUpdateSuggestion(targetSuggestion.id, "accept", currentDraft);
      } else if (key === "R") {
        e.preventDefault();
        handleUpdateSuggestion(targetSuggestion.id, "reject");
      } else if (key === "E") {
        e.preventDefault();
        const el = textareaRefs.current[targetSuggestion.id];
        if (el) {
          el.focus();
          el.select();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [focusedSuggestionId, suggestions, editedDrafts, handleUpdateSuggestion]);

  // Counts
  const acceptedCount = suggestions.filter((s) => s.status === "accepted").length;
  const pendingCount = suggestions.filter((s) => s.status === "identified" || s.status === "edited").length;
  const rejectedCount = suggestions.filter((s) => s.status === "rejected").length;
  const batchEligibleCount = suggestions.filter(
    (s) =>
      (s.status === "identified" || s.status === "edited") &&
      !s.proposed_text.includes("[") &&
      !s.proposed_text.includes("]")
  ).length;

  // Filtered list
  const filteredSuggestions = suggestions.filter((s) => {
    if (activeStatusFilter === "pending" && s.status !== "identified" && s.status !== "edited") return false;
    if (activeStatusFilter === "accepted" && s.status !== "accepted") return false;
    if (activeStatusFilter === "rejected" && s.status !== "rejected") return false;
    if (activeSectionFilter !== "all" && s.section !== activeSectionFilter) return false;
    return true;
  });
  const anyAIRewriteInProgress = Object.values(aiRewriteInProgress).some(Boolean);

  // ── Loading state ──────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex w-full flex-col items-center justify-center py-24 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-[#5477B8]/40 bg-white/80 shadow-lg shadow-[#5477B8]/10 backdrop-blur-md dark:border-[#6E90D1]/30 dark:bg-[#1A1E24]/90">
          <svg className="h-8 w-8 animate-spin text-[#5477B8] dark:text-[#6E90D1]" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
        <h3 className="mt-8 text-xl font-bold text-[#181A1D] dark:text-[#F0F2F5]">
          Analyzing Opportunities & Connecting Local AI...
        </h3>
        <p className="mt-2 max-w-md text-sm text-[#58616D] dark:text-[#A0ABB8]">
          Reviewing bullet clarity, action verbs, and checking Ollama local generative rewriting availability.
        </p>
      </div>
    );
  }

  // ── Error state ────────────────────────────────────────────────────────────
  if (errorMessage) {
    return (
      <div className="mx-auto flex w-full max-w-xl flex-col items-center justify-center rounded-2xl border border-red-500/20 bg-white/70 p-8 text-center shadow-lg backdrop-blur-md dark:border-red-500/20 dark:bg-[#1A1E24]/70">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-red-100 text-red-600 dark:bg-red-950/50 dark:text-red-400">
          <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h3 className="mt-4 text-lg font-bold text-[#181A1D] dark:text-[#F0F2F5]">
          Improvement Studio Error
        </h3>
        <p className="mt-2 text-sm text-[#58616D] dark:text-[#A0ABB8]">{errorMessage}</p>
        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={loadSuggestions}
            className="rounded-xl bg-[#5477B8] px-5 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-[#43629C] dark:bg-[#6E90D1]"
          >
            Retry Loading
          </button>
          <button
            type="button"
            onClick={onBackToReview}
            className="rounded-xl border border-[#9CA6B2]/30 bg-white/60 px-5 py-2.5 text-xs font-semibold text-[#181A1D] transition hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/60 dark:text-[#F0F2F5]"
          >
            Back to Review
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full space-y-8">
      {/* ── Top Header & Actions ───────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-[#181A1D] sm:text-3xl dark:text-[#F0F2F5]">
            Targeted Bullet Rewriting
          </h2>
          <p className="text-xs text-[#58616D] dark:text-[#A0ABB8]">
            Document: <span className="font-semibold text-[#181A1D] dark:text-[#F0F2F5]">{resume.filename}</span> — All proposed revisions remain strictly grounded in verified facts.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            id="backToAtsButton"
            type="button"
            onClick={onBackToAts}
            className="inline-flex items-center space-x-1.5 rounded-xl border border-[#9CA6B2]/30 bg-white/70 px-4 py-2 text-xs font-semibold text-[#5477B8] shadow-sm transition hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/70 dark:text-[#6E90D1] dark:hover:bg-[#20252D]"
          >
            <span>View ATS Score</span>
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
            <span>Review Full Resume</span>
          </button>
        </div>
      </div>

      {/* ── Local AI Engine Status Banner (Ollama & Grounding) ────────────── */}
      <div className="rounded-2xl border border-[#5477B8]/25 bg-gradient-to-r from-white/80 via-[#F3F5F6]/70 to-white/80 p-4.5 backdrop-blur-md shadow-xs dark:border-[#6E90D1]/25 dark:from-[#1A1E24]/80 dark:via-[#14171C]/70 dark:to-[#1A1E24]/80">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start space-x-3">
            <div
              className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-white ${
                providerStatus?.available
                  ? "bg-emerald-600 shadow-xs shadow-emerald-500/50"
                  : "bg-amber-500"
              }`}
            >
              {providerStatus?.available ? (
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              )}
            </div>
            <div className="space-y-0.5 text-xs text-[#181A1D] dark:text-[#F0F2F5]">
              <div className="flex items-center space-x-2">
                <span className="font-bold">
                  {providerStatus?.available
                    ? `Local Ollama AI Connected (${providerStatus.model})`
                    : "Local Ollama Offline — Heuristic Optimization Active"}
                </span>
                <span className="rounded-full bg-black/5 dark:bg-white/10 px-2 py-0.5 text-[10px] font-mono text-[#58616D] dark:text-[#A0ABB8]">
                  Zero Cloud Data Leakage
                </span>
              </div>
              <p className="text-[11px] text-[#58616D] dark:text-[#A0ABB8] leading-relaxed">
                {providerStatus?.available
                  ? "Local generative rewrite engine is operational. Bullet rewrites run completely on your machine with strict action verb front-loading."
                  : "Start Ollama with 'ollama serve' and pull 'ollama run llama3.2' to enable on-device generative rewriting. Rule-based ATS optimization remains active."}
              </p>
            </div>
          </div>

          <div className="flex shrink-0 items-center space-x-2">
            <button
              type="button"
              disabled={isCheckingProvider}
              onClick={checkProviderStatus}
              className="rounded-lg border border-[#9CA6B2]/30 bg-white/60 px-3 py-1.5 text-[11px] font-semibold text-[#5477B8] transition hover:bg-[#F3F5F6] disabled:opacity-50 dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/60 dark:text-[#6E90D1]"
            >
              {isCheckingProvider ? "Checking..." : "Refresh Provider Status"}
            </button>
          </div>
        </div>
      </div>

      {/* ── Batch Controls Bar ──────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4 backdrop-blur-md dark:border-emerald-500/20 dark:bg-emerald-950/15">
        <div className="space-y-0.5">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold text-emerald-800 dark:text-emerald-300">
              Batch Quick-Action
            </span>
            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300">
              {batchEligibleCount} Ready
            </span>
          </div>
          <p className="text-[11px] text-[#58616D] dark:text-[#A0ABB8]">
            Apply all high-confidence active verb enhancements that do not require missing metric placeholders.
          </p>
        </div>

        <button
          type="button"
          disabled={batchInProgress || batchEligibleCount === 0}
          onClick={handleBatchAccept}
          className="inline-flex items-center space-x-2 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:opacity-50 dark:bg-emerald-500 dark:hover:bg-emerald-600"
        >
          {batchInProgress ? (
            <span>Applying Batch...</span>
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span>Accept All High-Confidence Grammar Enhancements</span>
            </>
          )}
        </button>
      </div>

      {batchNotification && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs font-medium text-emerald-900 dark:text-emerald-200">
          {batchNotification}
        </div>
      )}

      {/* ── Summary Metrics Bar ────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: "Total Opportunities", count: suggestions.length, color: "text-[#181A1D] dark:text-[#F0F2F5]" },
          { label: "Pending Review", count: pendingCount, color: "text-[#5477B8] dark:text-[#6E90D1]" },
          { label: "Applied to Resume", count: acceptedCount, color: "text-emerald-600 dark:text-emerald-400" },
          { label: "Dismissed / Rejected", count: rejectedCount, color: "text-[#838F9E] dark:text-[#64707D]" },
        ].map(({ label, count, color }) => (
          <div
            key={label}
            className="rounded-xl border border-[#9CA6B2]/20 bg-white/60 p-3.5 backdrop-blur-sm dark:border-[#9CA6B2]/15 dark:bg-[#14171C]/60"
          >
            <p className={`text-2xl font-extrabold ${color}`}>{count}</p>
            <p className="text-[11px] font-medium text-[#58616D] dark:text-[#A0ABB8]">{label}</p>
          </div>
        ))}
      </div>

      {/* ── Filter Controls & Keyboard Hint ─────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[#9CA6B2]/30 pb-3 dark:border-[#9CA6B2]/20">
        {/* Status Filters */}
        <div className="flex flex-wrap gap-2">
          {(
            [
              { key: "all", label: `All (${suggestions.length})` },
              { key: "pending", label: `Pending (${pendingCount})` },
              { key: "accepted", label: `Accepted (${acceptedCount})` },
              { key: "rejected", label: `Dismissed (${rejectedCount})` },
            ] as const
          ).map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveStatusFilter(tab.key)}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                activeStatusFilter === tab.key
                  ? "bg-[#5477B8] text-white shadow-sm dark:bg-[#6E90D1]"
                  : "border border-[#9CA6B2]/25 bg-white/60 text-[#58616D] hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/15 dark:bg-[#1A1E24]/60 dark:text-[#A0ABB8] dark:hover:bg-[#20252D]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Section Filter & Shortcuts Hint */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="hidden md:inline-flex items-center space-x-1.5 text-[11px] text-[#838F9E] dark:text-[#64707D]">
            <span>Hotkeys:</span>
            <kbd className="rounded border border-[#9CA6B2]/30 bg-white/60 px-1 py-0.5 text-[10px] font-mono dark:bg-[#1A1E24]">A</kbd>
            <span>Accept</span>
            <kbd className="rounded border border-[#9CA6B2]/30 bg-white/60 px-1 py-0.5 text-[10px] font-mono dark:bg-[#1A1E24]">R</kbd>
            <span>Reject</span>
            <kbd className="rounded border border-[#9CA6B2]/30 bg-white/60 px-1 py-0.5 text-[10px] font-mono dark:bg-[#1A1E24]">E</kbd>
            <span>Edit</span>
          </div>

          <div className="flex items-center space-x-2">
            <label htmlFor="sectionFilter" className="text-xs font-semibold text-[#838F9E] dark:text-[#64707D]">
              Section:
            </label>
            <select
              id="sectionFilter"
              value={activeSectionFilter}
              onChange={(e) => setActiveSectionFilter(e.target.value)}
              className="rounded-lg border border-[#9CA6B2]/30 bg-white/70 px-2.5 py-1 text-xs text-[#181A1D] dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/70 dark:text-[#F0F2F5]"
            >
              <option value="all">All Sections</option>
              <option value="experience">Experience</option>
              <option value="projects">Projects</option>
              <option value="summary">Summary</option>
            </select>
          </div>
        </div>
      </div>

      {/* ── Revision Cards List ─────────────────────────────────────────────── */}
      <div className="space-y-6">
        {filteredSuggestions.length === 0 ? (
          <div className="rounded-2xl border border-[#9CA6B2]/20 bg-white/40 p-12 text-center text-xs text-[#838F9E] dark:border-[#9CA6B2]/10 dark:bg-[#14171C]/40">
            No improvement opportunities matching the selected filter.
          </div>
        ) : (
          filteredSuggestions.map((suggestion) => {
            const catMeta = CATEGORY_LABELS[suggestion.category] || {
              label: suggestion.category.replace("_", " "),
              color: "text-[#5477B8] bg-[#5477B8]/10 border-[#5477B8]/30",
              badge: suggestion.category,
            };
            const isPending = suggestion.status === "identified" || suggestion.status === "edited";
            const isAccepted = suggestion.status === "accepted";
            const isRejected = suggestion.status === "rejected";
            const inProgress = Boolean(actionInProgress[suggestion.id]);
            const isRewriting = Boolean(aiRewriteInProgress[suggestion.id]);
            const currentDraft = editedDrafts[suggestion.id] ?? suggestion.proposed_text;
            const hasCustomEdits = currentDraft.trim() !== suggestion.proposed_text.trim();
            const hasPlaceholders = currentDraft.includes("[") && currentDraft.includes("]");
            const isFocused = focusedSuggestionId === suggestion.id;
            const isAi = Boolean(suggestion.is_ai_generated);

            return (
              <div
                key={suggestion.id}
                onClick={() => setFocusedSuggestionId(suggestion.id)}
                className={`relative rounded-2xl border p-5 shadow-xs backdrop-blur-md transition ${
                  isFocused
                    ? "ring-2 ring-[#5477B8] dark:ring-[#6E90D1]"
                    : "hover:border-[#5477B8]/40"
                } ${
                  isAccepted
                    ? "border-emerald-500/40 bg-emerald-500/5 dark:border-emerald-500/30 dark:bg-emerald-950/15"
                    : isRejected
                    ? "border-[#9CA6B2]/20 bg-white/30 opacity-70 dark:border-[#9CA6B2]/10 dark:bg-[#14171C]/30"
                    : "border-[#9CA6B2]/30 bg-white/60 dark:border-[#9CA6B2]/20 dark:bg-[#14171C]/60"
                }`}
              >
                {/* Header row: category, section tag, and status badge */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#9CA6B2]/15 pb-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-md border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${catMeta.color}`}>
                      {catMeta.label}
                    </span>
                    <span className="rounded bg-black/5 dark:bg-white/5 px-2 py-0.5 text-[10px] font-semibold text-[#838F9E] uppercase dark:text-[#64707D]">
                      {suggestion.section}
                    </span>
                    {isAi && (
                      <span className="inline-flex items-center space-x-1 rounded-md border border-[#5477B8]/40 bg-[#5477B8]/15 px-2 py-0.5 text-[10px] font-bold text-[#5477B8] dark:text-[#6E90D1]">
                        <span className="h-1.5 w-1.5 rounded-full bg-[#5477B8] dark:bg-[#6E90D1]" />
                        <span>AI Synthesized ({suggestion.ai_model || "llama3.2"})</span>
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-2">
                    {isAccepted && (
                      <span className="inline-flex items-center space-x-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-[10px] font-bold text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                        <span>✓ Applied to Active Resume</span>
                      </span>
                    )}
                    {isRejected && (
                      <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-[10px] font-bold text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                        Dismissed
                      </span>
                    )}
                    {isPending && (
                      <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-[10px] font-bold text-[#5477B8] dark:bg-blue-950/40 dark:text-[#6E90D1]">
                        Ready for Review
                      </span>
                    )}
                  </div>
                </div>

                {/* Explanation text */}
                <p className="mt-3 text-xs text-[#58616D] dark:text-[#A0ABB8] leading-relaxed">
                  <span className="font-semibold text-[#181A1D] dark:text-[#F0F2F5]">Optimization Rationale:</span> {suggestion.explanation}
                </p>

                {/* Grounding & Truthfulness provenance tags */}
                {isAi && suggestion.preserved_facts && suggestion.preserved_facts.length > 0 && (
                  <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#838F9E] dark:text-[#64707D]">
                      Preserved Facts:
                    </span>
                    {suggestion.preserved_facts.map((fact, idx) => (
                      <span
                        key={idx}
                        className="rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] text-emerald-800 dark:text-emerald-300"
                      >
                        ✓ {fact}
                      </span>
                    ))}
                  </div>
                )}

                {/* Candidate Verification Warning if model added potential new claims */}
                {suggestion.needs_user_verification && (
                  <div className="mt-2.5 flex items-start space-x-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-2 text-[11px] text-amber-900 dark:text-amber-300">
                    <svg className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <span>
                      <strong>Candidate Verification Required:</strong> Please review any tools, metrics, or technical scopes proposed by the model to ensure they precisely reflect your verified background.
                    </span>
                  </div>
                )}

                {/* Comparison Diff Box: Original vs Proposed (Editable) */}
                <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
                  {/* Left: Original Text */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-[#838F9E] dark:text-[#64707D]">
                        Original Resume Statement
                      </span>
                    </div>
                    <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-3 text-xs text-[#181A1D] dark:border-red-500/20 dark:bg-red-950/20 dark:text-[#F0F2F5]">
                      <blockquote className="border-l-2 border-red-400 pl-2 font-mono text-[11px] leading-relaxed">
                        &ldquo;{suggestion.original_text}&rdquo;
                      </blockquote>
                    </div>
                  </div>

                  {/* Right: Proposed / Editable Text */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
                        Proposed Replacement (Editable)
                      </span>
                      {hasPlaceholders && (
                        <span className="text-[10px] font-semibold text-amber-600 dark:text-amber-400">
                          Replace [...] with verified figures
                        </span>
                      )}
                    </div>

                    <textarea
                      ref={(el) => {
                        textareaRefs.current[suggestion.id] = el;
                      }}
                      rows={3}
                      disabled={isAccepted || inProgress || isRewriting}
                      value={currentDraft}
                      onChange={(e) => {
                        const val = e.target.value;
                        setEditedDrafts((prev) => ({ ...prev, [suggestion.id]: val }));
                      }}
                      className="w-full rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-3 font-mono text-[11px] text-[#181A1D] leading-relaxed transition focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600 disabled:opacity-80 dark:border-emerald-500/20 dark:bg-emerald-950/20 dark:text-[#F0F2F5]"
                    />
                  </div>
                </div>

                {/* Custom Instruction Box for AI Rewrite */}
                {customPromptOpen[suggestion.id] && (
                  <div className="mt-3 rounded-xl border border-[#5477B8]/30 bg-[#5477B8]/5 p-3 space-y-2 dark:border-[#6E90D1]/30 dark:bg-[#6E90D1]/5">
                    <label className="text-[11px] font-semibold text-[#181A1D] dark:text-[#F0F2F5]">
                      Directive for Local AI (e.g., &ldquo;Emphasize cloud architecture&rdquo;, &ldquo;Front-load metrics&rdquo;):
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="e.g. Focus on microservices and latency optimization"
                        value={customPromptInputs[suggestion.id] || ""}
                        onChange={(e) =>
                          setCustomPromptInputs((prev) => ({ ...prev, [suggestion.id]: e.target.value }))
                        }
                        className="flex-1 rounded-lg border border-[#9CA6B2]/30 bg-white px-3 py-1.5 text-xs text-[#181A1D] focus:outline-none focus:ring-1 focus:ring-[#5477B8] dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24] dark:text-[#F0F2F5]"
                      />
                      <button
                        type="button"
                        onClick={() => handleTriggerAIRewrite(suggestion.id)}
                        disabled={isRewriting || anyAIRewriteInProgress || aiRewriteCooldownSeconds > 0}
                        className="rounded-lg bg-[#5477B8] px-3 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-[#43629C] disabled:opacity-50 dark:bg-[#6E90D1]"
                      >
                        {aiRewriteCooldownSeconds > 0
                          ? `Retry in ${aiRewriteCooldownSeconds}s`
                          : "Run Rewrite"}
                      </button>
                    </div>
                  </div>
                )}

                {aiRewriteErrors[suggestion.id] && (
                  <div
                    role="alert"
                    className="mt-3 rounded-xl border border-amber-500/35 bg-amber-500/10 p-3 text-xs leading-relaxed text-amber-950 dark:text-amber-200"
                  >
                    <p className="font-semibold">
                      {aiRewriteRateLimited[suggestion.id]
                        ? "Rewrite temporarily rate limited"
                        : "Local AI rewrite unavailable"}
                    </p>
                    <p className="mt-1">
                      {aiRewriteErrors[suggestion.id]}
                      {aiRewriteRateLimited[suggestion.id] && (
                        <> Retry in {aiRewriteCooldownSeconds > 0 ? `${aiRewriteCooldownSeconds} seconds` : "a moment"}.</>
                      )}
                    </p>
                  </div>
                )}

                {/* Action buttons bar */}
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-[#9CA6B2]/15 pt-3">
                  <div className="flex items-center space-x-2">
                    {/* AI Rewrite Button */}
                    {!isAccepted && (
                      <button
                        type="button"
                        disabled={isRewriting || inProgress || anyAIRewriteInProgress || aiRewriteCooldownSeconds > 0}
                        onClick={() => {
                          if (customPromptOpen[suggestion.id]) {
                            handleTriggerAIRewrite(suggestion.id);
                          } else {
                            handleTriggerAIRewrite(suggestion.id);
                          }
                        }}
                        className="inline-flex items-center space-x-1.5 rounded-xl border border-[#5477B8]/40 bg-white/70 px-3.5 py-1.5 text-xs font-semibold text-[#5477B8] shadow-xs transition hover:bg-[#5477B8]/10 disabled:opacity-50 dark:border-[#6E90D1]/30 dark:bg-[#1A1E24]/70 dark:text-[#6E90D1]"
                      >
                        {isRewriting ? (
                          <>
                            <svg className="h-3.5 w-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                            </svg>
                            <span>Rewriting with Ollama...</span>
                          </>
                        ) : (
                          <>
                            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                            <span>
                              {aiRewriteCooldownSeconds > 0
                                ? `Retry in ${aiRewriteCooldownSeconds}s`
                                : "Rewrite with Local AI"}
                            </span>
                          </>
                        )}
                      </button>
                    )}

                    {!isAccepted && (
                      <button
                        type="button"
                        onClick={() =>
                          setCustomPromptOpen((prev) => ({ ...prev, [suggestion.id]: !prev[suggestion.id] }))
                        }
                        className="text-[11px] text-[#58616D] hover:underline dark:text-[#A0ABB8]"
                      >
                        {customPromptOpen[suggestion.id] ? "Hide Custom Directive" : "+ Add Directive"}
                      </button>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {isAccepted ? (
                      <button
                        type="button"
                        disabled={inProgress}
                        onClick={() => handleRestoreSuggestion(suggestion.id)}
                        className="inline-flex items-center space-x-1.5 rounded-xl border border-[#9CA6B2]/30 bg-white/70 px-4 py-2 text-xs font-semibold text-[#181A1D] shadow-xs transition hover:bg-[#F3F5F6] disabled:opacity-50 dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/70 dark:text-[#F0F2F5] dark:hover:bg-[#20252D]"
                      >
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h10a5 5 0 015 5v2m0 0l-4-4m4 4l4-4" />
                        </svg>
                        <span>Restore Original Statement</span>
                      </button>
                    ) : (
                      <>
                        <button
                          type="button"
                          disabled={inProgress}
                          onClick={() => handleUpdateSuggestion(suggestion.id, "reject")}
                          className="rounded-xl border border-[#9CA6B2]/30 bg-white/60 px-4 py-2 text-xs font-semibold text-[#58616D] transition hover:bg-[#F3F5F6] disabled:opacity-50 dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/60 dark:text-[#A0ABB8] dark:hover:bg-[#20252D]"
                        >
                          {isRejected ? "Rejected" : "Reject"}
                        </button>

                        <button
                          type="button"
                          disabled={inProgress}
                          onClick={() => handleUpdateSuggestion(suggestion.id, "accept", currentDraft)}
                          className="inline-flex items-center space-x-1.5 rounded-xl bg-[#5477B8] px-5 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-[#43629C] disabled:opacity-50 dark:bg-[#6E90D1] dark:hover:bg-[#85A3DC]"
                        >
                          {inProgress ? (
                            <span>Saving...</span>
                          ) : (
                            <>
                              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                              </svg>
                              <span>{hasCustomEdits ? "Accept Custom Revision" : "Accept Suggestion"}</span>
                            </>
                          )}
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* ── Bottom Navigation & Re-analysis CTA ────────────────────────────── */}
      <div className="rounded-2xl border border-[#5477B8]/20 bg-gradient-to-r from-[#5477B8]/5 via-[#9CA6B2]/5 to-[#5477B8]/5 p-6 backdrop-blur-md dark:border-[#6E90D1]/20">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="space-y-1">
            <h4 className="text-sm font-bold text-[#181A1D] dark:text-[#F0F2F5]">
              Finished Reviewing Improvements?
            </h4>
            <p className="text-xs text-[#58616D] dark:text-[#A0ABB8]">
              Accepted changes have updated your active resume. You can inspect your updated profile in the Review Studio or re-run the ATS Readiness Assessment.
            </p>
          </div>

          <div className="flex gap-2.5">
            <button
              type="button"
              onClick={onBackToReview}
              className="rounded-xl border border-[#9CA6B2]/30 bg-white/70 px-4 py-2 text-xs font-semibold text-[#181A1D] shadow-xs transition hover:bg-[#F3F5F6] dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/70 dark:text-[#F0F2F5]"
            >
              Inspect Active Resume
            </button>
            <button
              type="button"
              onClick={onBackToAts}
              className="rounded-xl border border-[#5477B8]/40 bg-[#5477B8]/10 px-4 py-2 text-xs font-semibold text-[#5477B8] shadow-xs transition hover:bg-[#5477B8]/20 dark:text-[#6E90D1]"
            >
              Re-evaluate ATS Score
            </button>
            {onLaunchBuilder && (
              <button
                type="button"
                onClick={onLaunchBuilder}
                className="rounded-xl bg-[#5477B8] px-5 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-[#43629C] dark:bg-[#6E90D1] flex items-center space-x-1.5"
              >
                <span>Continue to Resume Builder</span>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
