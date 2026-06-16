"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, DashboardStats, Goal } from "@/lib/api";
import {
  EmptyState,
  ErrorBanner,
  StatusBadge,
  ToneBadge,
  scoreColor,
  recommendationStyle,
  WhyNotSpam,
} from "@/components/ui";
import VibeModeCard from "@/components/VibeModeCard";
import MomentumCard from "@/components/MomentumCard";

/** One stage of the "Your Networking Funnel" strip. */
function FunnelStrip({ stages }: { stages: { label: string; value: number }[] }) {
  return (
    <div className="flex flex-wrap items-stretch gap-2">
      {stages.map((s, i) => (
        <div key={s.label} className="flex items-center gap-2">
          <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-center">
            <div className="text-xl font-bold text-slate-900">{s.value}</div>
            <div className="mt-0.5 text-[11px] font-medium uppercase tracking-wide text-slate-500">
              {s.label}
            </div>
          </div>
          {i < stages.length - 1 && (
            <span className="text-slate-300">→</span>
          )}
        </div>
      ))}
    </div>
  );
}

/** A single "today's plan" metric with a deep link. */
function PlanItem({
  value,
  label,
  href,
}: {
  value: number;
  label: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="rounded-lg border border-slate-200 bg-white p-4 transition hover:border-blue-400"
    >
      <div className="text-2xl font-bold text-slate-900">{value}</div>
      <div className="mt-1 text-xs font-medium text-slate-500">{label}</div>
    </Link>
  );
}

export default function Home() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [goal, setGoal] = useState<Goal | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [s, goals] = await Promise.all([
        api.getStats(),
        api.getGoals().catch(() => []),
      ]);
      setStats(s);
      setGoal(goals[0] ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function runAction(name: string, fn: () => Promise<unknown>, msg: string) {
    setBusy(name);
    setError(null);
    setNotice(null);
    try {
      await fn();
      setNotice(msg);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  const draftsWaiting = stats?.status_counts.draft ?? 0;
  const jobsWorthNetworking = stats
    ? stats.total_matches - (stats.strong_targets ?? 0)
    : 0;
  const isEmpty =
    !!stats &&
    stats.total_jobs === 0 &&
    stats.total_messages === 0 &&
    stats.total_matches === 0;

  return (
    <div>
      {/* Hero */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-2xl">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            Turn new job postings into working actions
          </h1>
          <p className="mt-2 text-slate-600">
            Network AI finds relevant new-grad roles, suggests who to contact,
            drafts permission-based outreach, and tracks outcomes — so you network
            with intent instead of spraying applications.
          </p>
        </div>
        <button
          onClick={() =>
            runAction("seed", api.seedDemo, "Loaded demo profile, jobs & drafts.")
          }
          disabled={busy !== null}
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:border-blue-400 disabled:opacity-50"
        >
          {busy === "seed" ? "Loading…" : "Load demo data"}
        </button>
      </div>

      {notice && (
        <p className="mt-3 rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
          {notice}
        </p>
      )}
      <ErrorBanner message={error} />

      {/* CTA row */}
      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <Link
          href="/profile"
          className="rounded-md bg-blue-600 px-4 py-3 text-center text-sm font-medium text-white hover:bg-blue-700"
        >
          Save Profile
        </Link>
        <button
          onClick={() =>
            runAction("ingest", api.ingestJobs, "Ingested the latest new-grad jobs.")
          }
          disabled={busy !== null}
          className="rounded-md border border-slate-300 bg-white px-4 py-3 text-sm font-medium text-slate-700 hover:border-blue-400 disabled:opacity-50"
        >
          {busy === "ingest" ? "Ingesting…" : "Ingest Jobs"}
        </button>
        <button
          onClick={() =>
            runAction("match", api.matchAll, "Re-ranked all jobs against your profile.")
          }
          disabled={busy !== null}
          className="rounded-md border border-slate-300 bg-white px-4 py-3 text-sm font-medium text-slate-700 hover:border-blue-400 disabled:opacity-50"
        >
          {busy === "match" ? "Matching…" : "Match Jobs"}
        </button>
        <Link
          href="/messages"
          className="rounded-md border border-slate-300 bg-white px-4 py-3 text-center text-sm font-medium text-slate-700 hover:border-blue-400"
        >
          Review Drafts
        </Link>
        <Link
          href="/pipeline"
          className="rounded-md border border-slate-300 bg-white px-4 py-3 text-center text-sm font-medium text-slate-700 hover:border-blue-400"
        >
          Open Pipeline
        </Link>
      </div>

      {/* Vibe Mode + Momentum */}
      <div className="mt-6 grid gap-3 lg:grid-cols-2">
        <VibeModeCard />
        <MomentumCard />
      </div>

      {/* Current goal summary */}
      {!loading && (
        <div className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Current job-search goal
            </div>
            <Link
              href="/goals"
              className="text-sm font-medium text-blue-600 hover:underline"
            >
              {goal ? "Edit goal →" : "Set a goal →"}
            </Link>
          </div>
          {goal ? (
            <p className="mt-1 text-sm text-slate-700">
              <span className="font-medium">
                {goal.target_role || "Role TBD"}
              </span>
              {goal.target_location ? ` · ${goal.target_location}` : ""} · outreach
              goal: <span className="font-medium">{goal.outreach_goal || "advice"}</span>
              {goal.preferred_contact_types.length > 0
                ? ` · contacts: ${goal.preferred_contact_types
                    .map((t) => t.replace(/_/g, " "))
                    .join(", ")}`
                : ""}
            </p>
          ) : (
            <p className="mt-1 text-sm text-slate-500">
              No goal set yet — add one so the AI email copilot can personalize
              drafts honestly.
            </p>
          )}
        </div>
      )}

      {loading ? (
        <p className="mt-8 text-sm text-slate-500">Loading dashboard…</p>
      ) : isEmpty ? (
        <div className="mt-8">
          <EmptyState
            title="Let's get your pipeline started"
            description="Save your resume profile, ingest new-grad jobs, then match them — or click “Load demo data” above to populate everything instantly."
            ctaHref="/profile"
            ctaLabel="Save your profile →"
          />
        </div>
      ) : (
        stats && (
          <>
            {/* Today's networking plan */}
            <section className="mt-10">
              <h2 className="text-lg font-semibold text-slate-900">
                Today&apos;s networking plan
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Where to spend your effort right now.
              </p>
              <div className="mt-3 grid gap-3 grid-cols-2 lg:grid-cols-4">
                <PlanItem
                  value={stats.strong_targets ?? 0}
                  label="Strong targets to act on"
                  href="/matches"
                />
                <PlanItem
                  value={Math.max(0, jobsWorthNetworking)}
                  label="Jobs worth networking"
                  href="/matches"
                />
                <PlanItem
                  value={draftsWaiting}
                  label="Drafts waiting for review"
                  href="/messages"
                />
                <PlanItem
                  value={stats.follow_ups_due ?? 0}
                  label="Follow-ups / outcomes to update"
                  href="/pipeline"
                />
              </div>
            </section>

            {/* Networking funnel */}
            <section className="mt-10">
              <h2 className="text-lg font-semibold text-slate-900">
                Your networking funnel
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Every number comes straight from your local data — no estimates.
              </p>
              <div className="mt-3">
                <FunnelStrip stages={stats.funnel ?? []} />
              </div>
            </section>

            {/* Top matches */}
            <section className="mt-10">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">
                  Top 5 recommended jobs
                </h2>
                <Link
                  href="/matches"
                  className="text-sm font-medium text-blue-600 hover:underline"
                >
                  View all →
                </Link>
              </div>
              <div className="mt-3 space-y-2">
                {stats.top_matches.length === 0 ? (
                  <EmptyState
                    title="No matches yet"
                    description="Ingest jobs and click “Match Jobs” to rank them against your profile."
                  />
                ) : (
                  stats.top_matches.map((m) => (
                    <Link
                      key={m.job_id}
                      href={`/jobs/${m.job_id}`}
                      className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white p-3 hover:border-blue-400"
                    >
                      <div className="min-w-0">
                        <div className="truncate font-medium text-slate-900">
                          {m.title}
                        </div>
                        <div className="truncate text-sm text-slate-500">
                          {m.company} · {m.location || "Location N/A"}
                        </div>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        {m.recommendation && (
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${recommendationStyle(
                              m.recommendation
                            )}`}
                          >
                            {m.recommendation}
                          </span>
                        )}
                        <span
                          className={`rounded-full px-2.5 py-1 text-sm font-bold ${scoreColor(
                            m.match_score
                          )}`}
                        >
                          {m.match_score}
                        </span>
                      </div>
                    </Link>
                  ))
                )}
              </div>
            </section>

            {/* Recent outreach activity */}
            <section className="mt-10">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">
                  Recent outreach activity
                </h2>
                <Link
                  href="/messages"
                  className="text-sm font-medium text-blue-600 hover:underline"
                >
                  Review all →
                </Link>
              </div>
              <div className="mt-3 space-y-2">
                {stats.recent_messages.length === 0 ? (
                  <EmptyState
                    title="No drafts yet"
                    description="Open a job and click “Generate Outreach Drafts” to create your first messages."
                  />
                ) : (
                  stats.recent_messages.map((m) => (
                    <div
                      key={m.id}
                      className="rounded-lg border border-slate-200 bg-white p-3"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0 text-sm">
                          <span className="font-medium text-slate-900">
                            {m.company || "Unknown company"}
                          </span>{" "}
                          <span className="text-slate-400">
                            · {m.message_type.replace(/_/g, " ")}
                          </span>
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          <ToneBadge tone={m.tone} />
                          <StatusBadge status={m.status} />
                        </div>
                      </div>
                      <p className="mt-1 truncate text-sm text-slate-600">
                        {m.draft_text}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </section>

            {/* Trust / safety */}
            <section className="mt-10">
              <WhyNotSpam />
            </section>
          </>
        )
      )}

      <p className="mt-10 text-xs text-slate-400">
        Safety note: No scraping. No auto-send. Every message requires user
        approval. Network AI proposes drafts and manual search links — you review,
        edit, copy, and send everything yourself.
      </p>
    </div>
  );
}
