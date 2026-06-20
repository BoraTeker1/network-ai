"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  api,
  Mission,
  Meeting,
  EventRecommendationsResponse,
} from "@/lib/api";
import {
  ErrorBanner,
  NextBestAction,
  recommendationStyle,
  scoreColor,
} from "@/components/ui";
import MomentumCard from "@/components/MomentumCard";
import { useMomentum } from "@/components/MomentumProvider";
import { EventCard, SearchLinkRow } from "@/components/EventCard";

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

/** A numbered pillar section: SHOW UP / MEET / FOLLOW UP. */
function Pillar({
  step,
  title,
  subtitle,
  accent,
  children,
}: {
  step: number;
  title: string;
  subtitle: string;
  accent: string; // tailwind gradient classes for the number chip
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex items-start gap-3">
        <span
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br ${accent} text-sm font-bold text-white`}
        >
          {step}
        </span>
        <div className="min-w-0">
          <h2 className="text-base font-bold tracking-tight text-slate-900">
            {title}
          </h2>
          <p className="text-xs text-slate-500">{subtitle}</p>
        </div>
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}

/** The setup checklist — shown until the user has a real target. Never blank. */
function SetupChecklist({ mission }: { mission: Mission }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <h2 className="text-lg font-semibold text-slate-900">
        Let&apos;s set up your presence plan
      </h2>
      <p className="mt-1 text-sm text-slate-500">
        Finish these steps and your weekly &quot;where to show up&quot; plan
        appears here automatically.
      </p>
      <ol className="mt-4 space-y-2">
        {mission.setup_steps.map((s, i) => (
          <li
            key={s.key}
            className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3 ${
              s.done ? "border-green-100 bg-green-50" : "border-slate-200 bg-white"
            }`}
          >
            <div className="flex min-w-0 items-start gap-3">
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  s.done ? "bg-green-600 text-white" : "bg-slate-100 text-slate-600"
                }`}
              >
                {s.done ? "✓" : i + 1}
              </span>
              <div className="min-w-0">
                <div className="text-sm font-medium text-slate-800">{s.title}</div>
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
  const { celebrate } = useMomentum();
  const [mission, setMission] = useState<Mission | null>(null);
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [events, setEvents] = useState<EventRecommendationsResponse | null>(null);
  const [eventsLoading, setEventsLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  // "Met someone? Log it" inline form.
  const [metName, setMetName] = useState("");
  const [metWhere, setMetWhere] = useState("");
  const [logging, setLogging] = useState(false);

  const load = useCallback(async () => {
    try {
      const [m, mt] = await Promise.all([api.getMission(), api.getMeetings()]);
      setMission(m);
      setMeetings(mt);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load your plan");
    } finally {
      setLoading(false);
    }
  }, []);

  // Events come from a network provider (confs.tech) — load them progressively
  // so the rest of the plan renders instantly.
  const loadEvents = useCallback(async () => {
    setEventsLoading(true);
    try {
      setEvents(await api.getEventRecommendations({ max_results: 3 }));
    } catch {
      setEvents(null);
    } finally {
      setEventsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    loadEvents();
  }, [load, loadEvents]);

  async function runAction(name: string, fn: () => Promise<unknown>, msg: string) {
    setBusy(name);
    setError(null);
    setNotice(null);
    try {
      await fn();
      setNotice(msg);
      await load();
      await loadEvents();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  function copyQuery(query: string) {
    navigator.clipboard?.writeText(query).then(() => {
      setCopied(query);
      setTimeout(() => setCopied(null), 1500);
    });
  }

  async function logMeeting() {
    const name = metName.trim();
    if (!name) return;
    setLogging(true);
    setError(null);
    try {
      const created = await api.logMeeting({
        name,
        where_met: metWhere.trim() || undefined,
        job_id: mission?.best_job?.job_id ?? undefined,
      });
      celebrate(created.momentum); // toast + chime for "Person met"
      setMetName("");
      setMetWhere("");
      await load(); // refresh meetings list + presence funnel
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not log that meeting");
    } finally {
      setLogging(false);
    }
  }

  async function toggleFollowedUp(m: Meeting) {
    try {
      await api.updateMeeting(m.id, { followed_up: !m.followed_up });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update that meeting");
    }
  }

  if (loading) {
    return <p className="text-sm text-slate-500">Loading this week&apos;s plan…</p>;
  }
  if (!mission) {
    return <ErrorBanner message={error || "Could not load your plan."} />;
  }

  const best = mission.best_job;
  const recs = events?.recommendations ?? [];
  const links = (events?.search_links ?? []).slice(0, 3);
  const isRemote = events?.search_context.is_remote ?? false;
  const contacts = mission.contact_plan?.recommended_contact_types ?? [];
  const followUps = mission.follow_ups.items;
  const pendingDrafts = mission.drafts.pending_review;

  // Honest presence funnel: every value maps to a real tracked number.
  const presenceFunnel = [
    { label: "Opportunities", value: mission.pipeline.strong_matches },
    { label: "Events to attend", value: recs.length },
    { label: "People met", value: mission.pipeline.people_met },
    { label: "Outreach started", value: mission.pipeline.drafts },
    { label: "Replies", value: mission.pipeline.replies },
    { label: "Interviews", value: mission.pipeline.interviews },
  ];

  return (
    <div className="space-y-6">
      {/* Header + secondary data actions */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            This Week&apos;s Presence Plan
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-600">
            Where to show up, who to meet, and how to follow up — to turn your
            strongest opportunity into a referral. No bots, no spam.
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

      {/* This week's target — the spine everything hangs off */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="h-1.5 w-full bg-gradient-to-r from-fuchsia-500 via-purple-500 to-indigo-600" />
        <div className="p-6">
          <div className="text-xs font-semibold uppercase tracking-wide text-purple-700">
            {mission.ready ? "This week's target" : "Set your target to unlock the plan"}
          </div>
          {mission.ready && best ? (
            <>
              <div className="mt-1 flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="text-2xl font-bold text-slate-900">
                    {best.title}
                  </h2>
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
                <p className="mt-3 max-w-2xl text-sm text-slate-600">
                  {mission.match_explanation}
                </p>
              )}
              <div className="mt-4 flex flex-wrap gap-3">
                <Link
                  href={`/jobs/${best.job_id}`}
                  className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
                >
                  Open this opportunity →
                </Link>
                <Link
                  href="/matches"
                  className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-blue-400"
                >
                  Change target
                </Link>
              </div>
            </>
          ) : (
            <h2 className="mt-1 text-2xl font-bold text-slate-900">
              {mission.headline}
            </h2>
          )}
        </div>
      </div>

      {/* Not ready → setup checklist so the page is never blank. */}
      {!mission.ready && <SetupChecklist mission={mission} />}

      {/* This week's numbers, reframed around presence */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile
          value={eventsLoading ? "…" : recs.length || links.length}
          label={recs.length ? "Events to attend" : "Places to search"}
          href="/events"
          accent={recs.length > 0}
        />
        <StatTile
          value={mission.pipeline.people_met}
          label="People met"
          href="/pipeline"
          accent={mission.pipeline.people_met > 0}
        />
        <StatTile
          value={mission.follow_ups.due}
          label="Follow-ups due"
          href="/pipeline"
          accent={mission.follow_ups.due > 0}
        />
        <StatTile
          value={mission.momentum.streak > 0 ? `🔥 ${mission.momentum.streak}` : "—"}
          label="Day streak"
          href="/vibe"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* The three pillars */}
        <div className="space-y-6 lg:col-span-2">
          {/* 1 · SHOW UP */}
          <Pillar
            step={1}
            title="Show up"
            subtitle="Where the people connected to this opportunity gather this week"
            accent="from-fuchsia-500 to-purple-600"
          >
            {eventsLoading ? (
              <p className="text-sm text-slate-500">Finding events…</p>
            ) : recs.length > 0 ? (
              <div className="space-y-3">
                {recs.map((rec) => (
                  <EventCard key={rec.source_url} rec={rec} compact />
                ))}
                <Link
                  href="/events"
                  className="inline-block text-sm font-medium text-blue-600 hover:underline"
                >
                  See all events →
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">
                  {isRemote
                    ? "Your target is remote, so there's no local city to search. Pick a city on the Events page, or use these safe searches (online events included)."
                    : "No verified events from providers yet — here are safe searches built from your target."}
                </p>
                {links.map((link) => (
                  <SearchLinkRow
                    key={link.url}
                    link={link}
                    onCopyQuery={copyQuery}
                    copied={copied === link.query}
                  />
                ))}
                <Link
                  href="/events"
                  className="inline-block text-sm font-medium text-blue-600 hover:underline"
                >
                  Open Events →
                </Link>
              </div>
            )}
          </Pillar>

          {/* 2 · MEET */}
          <Pillar
            step={2}
            title="Meet"
            subtitle={
              best
                ? `Who to look for at ${best.company} (and at those events)`
                : "Who to look for once you've set a target"
            }
            accent="from-purple-500 to-indigo-600"
          >
            {contacts.length > 0 ? (
              <>
                <div className="grid gap-2 sm:grid-cols-2">
                  {contacts.map((c) => (
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
                {mission.contact_plan && (
                  <p className="mt-3 text-xs text-slate-500">
                    {mission.contact_plan.who_first} ·{" "}
                    <span className="capitalize">{mission.contact_plan.tone}</span>{" "}
                    tone · ask for{" "}
                    <span className="font-medium">
                      {mission.contact_plan.ask_type}
                    </span>
                  </p>
                )}
                {best && (
                  <Link
                    href={`/jobs/${best.job_id}`}
                    className="mt-4 inline-block text-sm font-medium text-blue-600 hover:underline"
                  >
                    Find &amp; add these people →
                  </Link>
                )}
              </>
            ) : (
              <p className="text-sm text-slate-500">
                Set this week&apos;s target and your contact plan — who to look
                for and why — appears here.
              </p>
            )}

            {/* Log who you met — the core presence signal. */}
            <div className="mt-5 border-t border-slate-100 pt-4">
              <div className="flex items-center justify-between">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  People you&apos;ve met
                </div>
                {meetings.length > 0 && (
                  <span className="text-xs text-slate-400">
                    {meetings.length} logged
                  </span>
                )}
              </div>

              {meetings.length > 0 && (
                <ul className="mt-2 space-y-1.5">
                  {meetings.slice(0, 4).map((m) => (
                    <li
                      key={m.id}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-slate-100 bg-slate-50 px-3 py-2"
                    >
                      <div className="min-w-0 text-sm text-slate-700">
                        <span className="font-medium">{m.name}</span>
                        {m.where_met ? (
                          <span className="text-slate-500"> · {m.where_met}</span>
                        ) : null}
                        {m.company ? (
                          <span className="text-slate-400"> · {m.company}</span>
                        ) : null}
                      </div>
                      <button
                        onClick={() => toggleFollowedUp(m)}
                        className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                          m.followed_up
                            ? "bg-green-100 text-green-800"
                            : "bg-amber-100 text-amber-800 hover:bg-amber-200"
                        }`}
                      >
                        {m.followed_up ? "✓ followed up" : "mark followed up"}
                      </button>
                    </li>
                  ))}
                </ul>
              )}

              <div className="mt-3 flex flex-wrap items-end gap-2">
                <label className="min-w-0 flex-1">
                  <span className="text-xs font-medium text-slate-600">
                    Who did you meet?
                  </span>
                  <input
                    value={metName}
                    onChange={(e) => setMetName(e.target.value)}
                    placeholder="e.g. Priya Patel"
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  />
                </label>
                <label className="min-w-0 flex-1">
                  <span className="text-xs font-medium text-slate-600">
                    Where? (optional)
                  </span>
                  <input
                    value={metWhere}
                    onChange={(e) => setMetWhere(e.target.value)}
                    placeholder="e.g. JS Conf NY"
                    onKeyDown={(e) => e.key === "Enter" && logMeeting()}
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                  />
                </label>
                <button
                  onClick={logMeeting}
                  disabled={logging || !metName.trim()}
                  className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {logging ? "Logging…" : "Log it (+15)"}
                </button>
              </div>
              <p className="mt-1.5 text-xs text-slate-400">
                Logged by you — never auto-detected. Earns Momentum and feeds your
                presence funnel.
              </p>
            </div>
          </Pillar>

          {/* 3 · FOLLOW UP */}
          <Pillar
            step={3}
            title="Follow up"
            subtitle="Turn the people you've met into warm, human follow-ups"
            accent="from-indigo-500 to-blue-600"
          >
            {mission.recommended_next_action && (
              <div className="mb-3">
                <NextBestAction text={mission.recommended_next_action} />
              </div>
            )}
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-md border border-slate-100 bg-slate-50 p-3">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Drafts ready for you
                </div>
                <div className="mt-1 text-2xl font-bold text-slate-900">
                  {pendingDrafts}
                </div>
                <Link
                  href="/messages"
                  className="mt-1 inline-block text-xs font-medium text-blue-600 hover:underline"
                >
                  Review &amp; approve →
                </Link>
              </div>
              <div className="rounded-md border border-slate-100 bg-slate-50 p-3">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Got a reply?
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  Paste it and get your next move + a drafted response.
                </p>
                <Link
                  href="/next-move"
                  className="mt-1 inline-block text-xs font-medium text-blue-600 hover:underline"
                >
                  Plan my next move →
                </Link>
              </div>
            </div>

            {followUps.length > 0 && (
              <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3">
                <div className="text-xs font-semibold uppercase tracking-wide text-amber-700">
                  Follow-ups due
                </div>
                <ul className="mt-1.5 space-y-1">
                  {followUps.map((f) => (
                    <li key={`${f.kind}-${f.id}`} className="text-sm text-amber-900">
                      {f.company || "Unknown company"}
                      {f.role ? ` · ${f.role}` : ""}
                      {f.due_date ? ` · due ${f.due_date}` : ""}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Pillar>
        </div>

        {/* Right rail: momentum + presence funnel */}
        <div className="space-y-6">
          <MomentumCard />

          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Your presence funnel
            </div>
            <ul className="mt-3 space-y-2">
              {presenceFunnel.map((stage) => (
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

          <Link
            href="/vibe"
            className="block rounded-xl border border-slate-200 bg-white p-5 transition hover:border-blue-400"
          >
            <div className="text-sm font-semibold text-slate-900">
              ⏱️ 25-min networking sprint
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Focus block to knock out today&apos;s show-up + follow-up steps.
            </p>
          </Link>
        </div>
      </div>

      <p className="text-xs text-slate-400">
        Safety: no scraping, no auto-send, no auto-register. Network AI shows you
        where to be and drafts human follow-ups — you review, edit, and send
        everything yourself.
      </p>
    </div>
  );
}
