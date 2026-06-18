"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, Mission } from "@/lib/api";
import {
  ErrorBanner,
  NextBestAction,
  recommendationStyle,
  scoreColor,
} from "@/components/ui";
import MomentumCard from "@/components/MomentumCard";

/** Small labeled stat tile that deep-links somewhere useful. */
function StatTile({
  value,
  label,
  href,
  accent,
}: {
  value: number | string;
  label: string;
  href: string;
  accent?: boolean;
}) {
  return (
    <Link
      href={href}
      className={`rounded-lg border p-4 transition hover:border-blue-400 ${
        accent ? "border-blue-200 bg-blue-50" : "border-slate-200 bg-white"
      }`}
    >
      <div className="text-2xl font-bold text-slate-900">{value}</div>
      <div className="mt-1 text-xs font-medium text-slate-500">{label}</div>
    </Link>
  );
}

/** The setup checklist — shown until the user has a real mission. Never blank. */
function SetupChecklist({ mission }: { mission: Mission }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <h2 className="text-lg font-semibold text-slate-900">
        Let&apos;s get your networking set up
      </h2>
      <p className="mt-1 text-sm text-slate-500">
        Finish these steps and your daily mission appears here automatically.
      </p>
      <ol className="mt-4 space-y-2">
        {mission.setup_steps.map((s, i) => (
          <li
            key={s.key}
            className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3 ${
              s.done
                ? "border-green-100 bg-green-50"
                : "border-slate-200 bg-white"
            }`}
          >
            <div className="flex min-w-0 items-start gap-3">
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  s.done
                    ? "bg-green-600 text-white"
                    : "bg-slate-100 text-slate-600"
                }`}
              >
                {s.done ? "✓" : i + 1}
              </span>
              <div className="min-w-0">
                <div className="text-sm font-medium text-slate-800">
                  {s.title}
                </div>
                <p className="text-xs text-slate-500">{s.description}</p>
              </div>
            </div>
            {!s.done && (
              <Link
                href={s.cta_href}
                className="shrink-0 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
              >
                {s.cta_label} →
              </Link>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

export default function DashboardPage() {
  const [mission, setMission] = useState<Mission | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setMission(await api.getMission());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load your mission");
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

  if (loading) {
    return <p className="text-sm text-slate-500">Loading today&apos;s mission…</p>;
  }
  if (!mission) {
    return <ErrorBanner message={error || "Could not load your mission."} />;
  }

  const best = mission.best_job;

  return (
    <div className="space-y-6">
      {/* Header + quick setup actions */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Today&apos;s Networking Mission
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-600">
            One focused plan for what to do right now — AI proposes, you approve
            and send everything yourself.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() =>
              runAction("ingest", api.ingestJobs, "Ingested the latest new-grad jobs.")
            }
            disabled={busy !== null}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:border-blue-400 disabled:opacity-50"
          >
            {busy === "ingest" ? "Ingesting…" : "Ingest Jobs"}
          </button>
          <button
            onClick={() =>
              runAction("match", api.matchAll, "Re-ranked all jobs against your profile.")
            }
            disabled={busy !== null}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:border-blue-400 disabled:opacity-50"
          >
            {busy === "match" ? "Matching…" : "Match Jobs"}
          </button>
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
      </div>

      {notice && (
        <p className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
          {notice}
        </p>
      )}
      <ErrorBanner message={error} />

      {/* Hero: the one thing to do today */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="h-1.5 w-full bg-gradient-to-r from-blue-500 via-indigo-500 to-violet-600" />
        <div className="p-6">
          <div className="text-xs font-semibold uppercase tracking-wide text-blue-700">
            {mission.ready ? "Your mission today" : "Next step to unlock your mission"}
          </div>
          <h2 className="mt-1 text-2xl font-bold text-slate-900">
            {mission.headline}
          </h2>
          {mission.focus && (
            <p className="mt-2 max-w-2xl text-sm text-slate-600">{mission.focus}</p>
          )}
          <div className="mt-4 flex flex-wrap gap-3">
            {mission.ready && best && (
              <Link
                href={`/jobs/${best.job_id}`}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
              >
                Network for this job →
              </Link>
            )}
            <Link
              href="/vibe"
              className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-blue-400"
            >
              ⏱️ Start 25-min networking sprint
            </Link>
          </div>
        </div>
      </div>

      {/* When not ready, show the setup checklist so the page is never blank. */}
      {!mission.ready && <SetupChecklist mission={mission} />}

      {/* Today's numbers */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile
          value={mission.drafts.pending_review}
          label="Drafts ready for approval"
          href="/messages"
          accent={mission.drafts.pending_review > 0}
        />
        <StatTile
          value={mission.follow_ups.due}
          label="Follow-ups due"
          href="/pipeline"
          accent={mission.follow_ups.due > 0}
        />
        <StatTile
          value={mission.momentum.points_today}
          label="Momentum points today"
          href="/vibe"
        />
        <StatTile
          value={mission.momentum.streak > 0 ? `🔥 ${mission.momentum.streak}` : "—"}
          label="Day streak"
          href="/vibe"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Best job to target today */}
        <div className="lg:col-span-2 space-y-6">
          {best ? (
            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Best job to target today
                  </div>
                  <div className="mt-1 font-semibold text-slate-900">
                    {best.title}
                  </div>
                  <div className="text-sm text-slate-600">
                    {best.company} · {best.location || "Location N/A"}
                  </div>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1.5">
                  <span
                    className={`rounded-full px-3 py-1 text-sm font-bold ${scoreColor(
                      best.match_score
                    )}`}
                  >
                    {best.match_score}
                  </span>
                  {mission.match_label && (
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${recommendationStyle(
                        mission.match_label
                      )}`}
                    >
                      {mission.match_label}
                    </span>
                  )}
                </div>
              </div>

              {mission.match_explanation && (
                <div className="mt-3 rounded-md bg-slate-50 p-3">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Why this job is worth networking for
                  </div>
                  <p className="mt-1 text-sm text-slate-700">
                    {mission.match_explanation}
                  </p>
                  {best.matched_skills.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {best.matched_skills.slice(0, 8).map((s) => (
                        <span
                          key={s}
                          className="rounded-full bg-green-50 px-2 py-0.5 text-xs text-green-700"
                        >
                          ✓ {s}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {mission.recommended_next_action && (
                <div className="mt-3">
                  <NextBestAction text={mission.recommended_next_action} />
                </div>
              )}

              <div className="mt-4">
                <Link
                  href={`/jobs/${best.job_id}`}
                  className="inline-block rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
                >
                  Network for this job →
                </Link>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center">
              <div className="text-sm font-semibold text-slate-800">
                No ranked job to target yet
              </div>
              <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">
                Once you upload a resume, ingest jobs, and rank them, your best
                target appears here with a ready-to-run contact plan.
              </p>
              <Link
                href="/matches"
                className="mt-4 inline-block rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Go to Matches →
              </Link>
            </div>
          )}

          {/* Contact plan */}
          {mission.contact_plan && (
            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Your contact plan
              </div>
              <p className="mt-1 text-sm text-slate-700">
                {mission.contact_plan.who_first}
              </p>
              <p className="mt-0.5 text-xs text-slate-500">
                {mission.contact_plan.contact_count} ·{" "}
                <span className="capitalize">{mission.contact_plan.tone}</span> tone
                · ask for{" "}
                <span className="font-medium">{mission.contact_plan.ask_type}</span>
              </p>

              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {mission.contact_plan.recommended_contact_types.map((c) => (
                  <div
                    key={c.contact_type}
                    className="rounded-md border border-slate-100 bg-slate-50 p-3"
                  >
                    <div className="text-sm font-medium text-slate-800">
                      {c.label}
                    </div>
                    <p className="mt-0.5 text-xs text-slate-500">{c.why}</p>
                  </div>
                ))}
              </div>

              {best && (
                <Link
                  href={`/jobs/${best.job_id}`}
                  className="mt-4 inline-block text-sm font-medium text-blue-600 hover:underline"
                >
                  Find &amp; add these contacts →
                </Link>
              )}
            </div>
          )}
        </div>

        {/* Right rail: momentum + funnel */}
        <div className="space-y-6">
          <MomentumCard />

          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Your funnel
            </div>
            <ul className="mt-3 space-y-2">
              {mission.pipeline.funnel.map((stage) => (
                <li
                  key={stage.label}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-slate-600">{stage.label}</span>
                  <span className="font-semibold text-slate-900">
                    {stage.value}
                  </span>
                </li>
              ))}
            </ul>
            <Link
              href="/pipeline"
              className="mt-3 inline-block text-sm font-medium text-blue-600 hover:underline"
            >
              Open pipeline →
            </Link>
          </div>

          {/* Follow-ups due */}
          {mission.follow_ups.due > 0 && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-5">
              <div className="text-xs font-semibold uppercase tracking-wide text-amber-700">
                Follow-ups due
              </div>
              <ul className="mt-2 space-y-1.5">
                {mission.follow_ups.items.map((f) => (
                  <li key={`${f.kind}-${f.id}`} className="text-sm text-amber-900">
                    {f.company || "Unknown company"}
                    {f.role ? ` · ${f.role}` : ""}
                    {f.due_date ? ` · due ${f.due_date}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      <p className="text-xs text-slate-400">
        Safety: no scraping, no auto-send, no bulk sending. Network AI proposes
        drafts and manual search links — you review, edit, copy, and send
        everything yourself.
      </p>
    </div>
  );
}
