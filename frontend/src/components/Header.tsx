"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSession } from "@/context/SessionContext";

interface HeaderProps {
  onFreshStart?: () => void;
}

export function Header({ onFreshStart }: HeaderProps) {
  const router = useRouter();
  const { resetSession } = useSession();
  const [freshStartError, setFreshStartError] = useState<string | null>(null);
  const [isStartingFresh, setIsStartingFresh] = useState(false);

  const handleFreshStart = async (event: React.MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    if (isStartingFresh) return;

    setFreshStartError(null);
    setIsStartingFresh(true);

    try {
      const resetSucceeded = await resetSession();
      if (!resetSucceeded) {
        setFreshStartError("Could not confirm a fresh session. Please try again.");
        return;
      }

      onFreshStart?.();
      router.replace("/");
    } finally {
      setIsStartingFresh(false);
    }
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-[#9CA6B2]/20 bg-[#F3F5F6]/80 backdrop-blur-md dark:border-[#9CA6B2]/15 dark:bg-[#0E1013]/80">
      <div className="mx-auto flex h-16 max-w-7xl items-center px-4 sm:px-6 lg:px-8">
        <Link
          href="/"
          onClick={handleFreshStart}
          aria-label="RESUMIND AI — start a fresh resume session"
          title={isStartingFresh ? "Starting a fresh session" : "Start a fresh resume session"}
          aria-disabled={isStartingFresh}
          className={`inline-flex items-center space-x-3 rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5477B8] dark:focus-visible:ring-[#6E90D1] ${isStartingFresh ? "opacity-60" : ""}`}
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-[#9CA6B2]/30 bg-white/70 shadow-sm backdrop-blur-sm dark:border-[#9CA6B2]/20 dark:bg-[#1A1E24]/70">
            {/* Abstract Document-to-Signal Brand Mark */}
            <svg
              className="h-5 w-5 text-[#5477B8] dark:text-[#6E90D1]"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <rect x="4" y="3" width="12" height="18" rx="2" strokeOpacity="0.8" />
              <line x1="8" y1="8" x2="12" y2="8" strokeOpacity="0.5" />
              <line x1="8" y1="12" x2="12" y2="12" strokeOpacity="0.5" />
              <path
                d="M14 14l3 3 5-5"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-base font-bold tracking-tight text-[#181A1D] dark:text-[#F0F2F5]">
                RESUMIND
              </span>
              <span className="rounded bg-[#5477B8]/15 px-1.5 py-0.5 text-[10px] font-semibold tracking-wider text-[#5477B8] dark:text-[#6E90D1]">
                AI
              </span>
            </div>
          </div>
        </Link>
      </div>
      {freshStartError && (
        <p role="alert" className="border-t border-[#9CA6B2]/20 px-4 py-2 text-center text-xs text-red-700 dark:border-[#9CA6B2]/15 dark:text-red-300">
          {freshStartError}
        </p>
      )}
    </header>
  );
}
