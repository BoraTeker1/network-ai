"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  api,
  Job,
  MatchResult,
  ContactSearch,
  Message,
  OutreachStrategy,
} from "@/lib/api";
import {
  recommendationStyle,
  NextBestAction,
  ToneBadge,
  SectionLabel,
} from "@/components/ui";

export default function JobDetailPage() {
  const params = useParams();
  const jobId = Number(params.id);

  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [match, setMatch] = useState<MatchResult | null>(null);
  const [matching, setMatching] = useState(false);

  const [searches, setSearches] = useState<ContactSearch[]>([]);
  const [strategy, setStrategy] = useState<OutreachStrategy | null>(null);

  const [contactName, setContactName] = useState("");
  const [contactTitle, setContactTitle] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState<Message[]>([]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [j, cs, st] = await Promise.all([
          api.getJob(jobId),
          api.getContactSearches(jobId).catch(() => []),
          api.getStrategy(jobId).catch(() => null),
        ]);
        setJob(j);
        setSearches(cs);
        setStrategy(st);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load job");
      } finally {
        setLoading(false);
      }
    }
    if (!Number.isNaN(jobId)) load();
  }, [jobId]);

  async function handleMatch() {
    setMatching(true);
    setError(null);
    try {
      setMatch(await api.matchJob(jobId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate match");
    } finally {
      setMatching(false);
    }
  }

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    try {
      const msgs = await api.generateMessages(
        jobId,
        contactName,
        contactTitle
      );
      setGenerated(msgs);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate drafts");
    } finally {
      setGenerating(false);
    }
  }

  if (loading) return <p className="text-sm text-slate-500">Loading...</p>;
  if (!job)
    return (
      <div>
        <p className="text-sm text-red-600">{error || "Job not found."}</p>
        <Link href="/jobs" className="text-sm text-blue-600 hover:underline">
          ← Back to jobs
        </Link>
      </div>
    );

  return (
    <div className="space-y-8">
      <div>
        <Link href="/jobs" className="text-sm text-blue-600 hover:underline">
          ← Back to jobs
        </Link>
        <h1 className="mt-2 text-2xl font-bold">{job.title}</h1>
        <div className="text-slate-600">
          {job.company} · {job.location || "Location N/A"}
        </div>
        {job.url && (
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-1 inline-block text-sm text-blue-600 hover:underline"
          >
            Open job posting ↗
          </a>
        )}
      </div>

      {error && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {/* Match */}
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Match</h2>
          <button
            onClick={handleMatch}
            disabled={matching}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {matching ? "Scoring..." : "Generate Match"}
          </button>
        </div>
        {match ? (
          <div className="mt-3">
            <div className="flex items-center gap-3">
              <div className="text-3xl font-bold">{match.match_score}/100</div>
              {match.recommendation && (
                <span
                  className={`rounded-full px-2.5 py-1 text-xs font-medium ${recommendationStyle(
                    match.recommendation
                  )}`}
                >
                  {match.recommendation}
                </span>
              )}
            </div>

            {match.breakdown?.length > 0 && (
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {match.breakdown.map((b) => (
                  <div key={b.label} className="rounded-md bg-slate-50 p-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-slate-700">
                        {b.label}
                      </span>
                      <span className="text-slate-500">
                        {b.points}/{b.max}
                      </span>
                    </div>
                    <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-200">
                      <div
                        className="h-full rounded-full bg-blue-500"
                        style={{
                          width: `${Math.round((b.points / b.max) * 100)}%`,
                        }}
                      />
                    </div>
                    <p className="mt-1 text-xs text-slate-500">{b.detail}</p>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-3 flex flex-wrap gap-2">
              {match.matched_skills.map((s) => (
                <span
                  key={`y-${s}`}
                  className="rounded-full bg-green-50 px-2 py-0.5 text-xs text-green-700"
                >
                  ✓ {s}
                </span>
              ))}
              {match.missing_skills.slice(0, 6).map((s) => (
                <span
                  key={`n-${s}`}
                  className="rounded-full bg-slate-50 px-2 py-0.5 text-xs text-slate-400"
                >
                  {s}
                </span>
              ))}
            </div>

            {match.next_best_action && (
              <div className="mt-4">
                <NextBestAction text={match.next_best_action} />
              </div>
            )}
          </div>
        ) : (
          <p className="mt-3 text-sm text-slate-500">
            Click “Generate Match” to score this job against your profile.
          </p>
        )}
      </section>

      {/* Outreach strategy */}
      {strategy && (
        <section className="rounded-lg border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Outreach Strategy</h2>
            <span
              className={`rounded-full px-2.5 py-1 text-xs font-medium ${recommendationStyle(
                strategy.label
              )}`}
            >
              {strategy.label}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            A deterministic plan based on this role&apos;s fit — advice-first, never
            a referral ask as the opener.
          </p>

          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <div className="rounded-md bg-slate-50 p-3">
              <SectionLabel>Who to contact first</SectionLabel>
              <p className="mt-1 text-sm text-slate-700">{strategy.who_first}</p>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <SectionLabel>How many people</SectionLabel>
              <p className="mt-1 text-sm text-slate-700">{strategy.contact_count}</p>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <SectionLabel>Tone &amp; ask</SectionLabel>
              <p className="mt-1 text-sm text-slate-700">
                <span className="capitalize">{strategy.tone}</span> tone · ask for{" "}
                <span className="font-medium">{strategy.ask_type}</span>
              </p>
            </div>
          </div>

          <div className="mt-4">
            <SectionLabel>Suggested sequence</SectionLabel>
            <ol className="mt-2 space-y-2">
              {strategy.sequence.map((s) => (
                <li key={s.step} className="flex gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">
                    {s.step}
                  </span>
                  <div>
                    <div className="text-sm font-medium text-slate-800">
                      {s.title}
                    </div>
                    <p className="text-xs text-slate-500">{s.detail}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>
      )}

      {/* Contact searches */}
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-lg font-semibold">Contact Search Suggestions</h2>
        <p className="mt-1 text-xs text-slate-500">
          Manual searches only — Network AI never scrapes LinkedIn. Open a
          search and find people yourself.
        </p>
        <div className="mt-4 space-y-3">
          {searches.length === 0 ? (
            <p className="text-sm text-slate-500">No suggestions available.</p>
          ) : (
            searches.map((s) => (
              <div
                key={s.label}
                className="rounded-md border border-slate-100 bg-slate-50 p-3"
              >
                <div className="font-medium text-slate-800">{s.label}</div>
                <code className="mt-1 block text-xs text-slate-500">
                  {s.query}
                </code>
                <div className="mt-2 flex gap-2">
                  <a
                    href={s.google_search_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded border border-slate-300 bg-white px-2 py-1 text-xs hover:border-blue-400"
                  >
                    Open Google Search ↗
                  </a>
                  <a
                    href={s.linkedin_search_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded border border-slate-300 bg-white px-2 py-1 text-xs hover:border-blue-400"
                  >
                    Open LinkedIn Search ↗
                  </a>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      {/* Generate drafts */}
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-lg font-semibold">Generate Outreach Drafts</h2>
        <p className="mt-1 text-xs text-slate-500">
          Optional: add a contact name/title to personalize the greeting.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <input
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            placeholder="Contact name (optional)"
            value={contactName}
            onChange={(e) => setContactName(e.target.value)}
          />
          <input
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            placeholder="Contact title (optional)"
            value={contactTitle}
            onChange={(e) => setContactTitle(e.target.value)}
          />
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="mt-3 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {generating ? "Generating..." : "Generate Outreach Drafts"}
        </button>

        {generated.length > 0 && (
          <div className="mt-4 space-y-3">
            <p className="text-sm text-green-700">
              Generated {generated.length} drafts.{" "}
              <Link href="/messages" className="font-medium underline">
                Review them in Messages →
              </Link>
            </p>
            {generated.map((m) => (
              <div
                key={m.id}
                className="rounded-md border border-slate-100 bg-slate-50 p-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="text-xs font-semibold uppercase text-slate-500">
                    {m.message_type.replace(/_/g, " ")}
                  </div>
                  <ToneBadge tone={m.tone} />
                </div>
                <p className="mt-1 text-sm text-slate-700">{m.draft_text}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
