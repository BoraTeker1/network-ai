"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, RankedMatch } from "@/lib/api";
import {
  EmptyState,
  ErrorBanner,
  scoreColor,
  recommendationStyle,
  NextBestAction,
  PageHeader,
} from "@/components/ui";

function Breakdown({ m }: { m: RankedMatch }) {
  if (!m.breakdown?.length) return null;
  return (
    <div className="mt-3 grid gap-2 sm:grid-cols-2">
      {m.breakdown.map((b) => (
        <div key={b.label} className="rounded-md bg-slate-50 p-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-slate-700">{b.label}</span>
            <span className="text-slate-500">
              {b.points}/{b.max}
            </span>
          </div>
          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-blue-500"
              style={{ width: `${Math.round((b.points / b.max) * 100)}%` }}
            />
          </div>
          <p className="mt-1 text-xs text-slate-500">{b.detail}</p>
        </div>
      ))}
    </div>
  );
}

export default function MatchesPage() {
  const [matches, setMatches] = useState<RankedMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [matching, setMatching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadMatches() {
    setLoading(true);
    try {
      setMatches(await api.getRankedMatches(25));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load matches");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMatches();
  }, []);

  async function handleMatchAll() {
    setMatching(true);
    setError(null);
    try {
      await api.matchAll();
      await loadMatches();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to match jobs");
    } finally {
      setMatching(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Ranked Matches"
        subtitle="Decision-oriented labels and a recommended next action for every role — not just a number."
        action={
          <button
            onClick={handleMatchAll}
            disabled={matching}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {matching ? "Matching…" : "Match All Jobs"}
          </button>
        }
      />

      <ErrorBanner message={error} />

      <div className="mt-6 space-y-3">
        {loading ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : matches.length === 0 ? (
          <EmptyState
            title="No ranked matches yet"
            description="Save your profile and ingest jobs, then click “Match All Jobs” to score every posting against your skills and target roles."
            ctaHref="/jobs"
            ctaLabel="Ingest jobs →"
          />
        ) : (
          matches.map((m) => (
            <div
              key={m.job_id}
              className="rounded-lg border border-slate-200 bg-white p-4"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="font-semibold text-slate-900">{m.title}</div>
                  <div className="text-sm text-slate-600">
                    {m.company} · {m.location || "Location N/A"}
                  </div>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1.5">
                  <span
                    className={`rounded-full px-3 py-1 text-sm font-bold ${scoreColor(
                      m.match_score
                    )}`}
                  >
                    {m.match_score}
                  </span>
                  {m.recommendation && (
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${recommendationStyle(
                        m.recommendation
                      )}`}
                    >
                      {m.recommendation}
                    </span>
                  )}
                </div>
              </div>

              {m.next_best_action && (
                <div className="mt-3">
                  <NextBestAction text={m.next_best_action} />
                </div>
              )}

              <Breakdown m={m} />

              {(m.matched_skills.length > 0 || m.missing_skills.length > 0) && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {m.matched_skills.map((s) => (
                    <span
                      key={`y-${s}`}
                      className="rounded-full bg-green-50 px-2 py-0.5 text-xs text-green-700"
                    >
                      ✓ {s}
                    </span>
                  ))}
                  {m.missing_skills.slice(0, 6).map((s) => (
                    <span
                      key={`n-${s}`}
                      className="rounded-full bg-slate-50 px-2 py-0.5 text-xs text-slate-400"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              )}

              <div className="mt-3">
                <Link
                  href={`/jobs/${m.job_id}`}
                  className="text-sm font-medium text-blue-600 hover:underline"
                >
                  Open job & outreach →
                </Link>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
