"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  api,
  EventFilters,
  EventRecommendationsResponse,
} from "@/lib/api";
import { ErrorBanner, PageHeader, scoreColor } from "@/components/ui";
import { EventCard, SearchLinkRow, providerLabel } from "@/components/EventCard";

const DAYS_OPTIONS = [7, 14, 30, 60, 90];

export default function EventsPage() {
  const [data, setData] = useState<EventRecommendationsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  // Filters (location empty => backend uses goal/job location).
  const [location, setLocation] = useState("");
  const [radius, setRadius] = useState(50);
  const [daysAhead, setDaysAhead] = useState(30);
  const [includeOnline, setIncludeOnline] = useState(true);

  const load = useCallback(
    async (filters: EventFilters) => {
      setLoading(true);
      setError(null);
      try {
        setData(await api.getEventRecommendations(filters));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load events");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    load({ days_ahead: 30, radius_miles: 50, include_online: true });
  }, [load]);

  function applyFilters() {
    load({
      location: location.trim() || undefined,
      radius_miles: radius,
      days_ahead: daysAhead,
      include_online: includeOnline,
      max_results: 20,
    });
  }

  function copyQuery(query: string) {
    navigator.clipboard?.writeText(query).then(() => {
      setCopied(query);
      setTimeout(() => setCopied(null), 1500);
    });
  }

  const match = data?.strongest_match ?? null;
  const ctx = data?.search_context;
  const recs = data?.recommendations ?? [];
  const links = data?.search_links ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Networking events"
        subtitle="Where can I meet people connected to my strongest job opportunity this week or month? Real events come from configured providers — we never invent events, and always fall back to safe manual searches."
        action={
          <Link
            href="/dashboard"
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:border-blue-400"
          >
            ← Dashboard
          </Link>
        }
      />

      {/* Strongest match context */}
      {match ? (
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Your strongest match today
              </div>
              <div className="mt-1 font-semibold text-slate-900">
                {match.title}
              </div>
              <div className="text-sm text-slate-600">
                {match.company} · {match.location || "Location N/A"}
              </div>
              {ctx && (
                <p className="mt-2 text-sm text-slate-600">
                  Searching for{" "}
                  <span className="font-medium">{ctx.role_family}</span>{" "}
                  networking opportunities
                  {ctx.city ? ` near ${ctx.city}` : ""}.
                </p>
              )}
              {ctx?.is_remote && (
                <p className="mt-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">
                  Your strongest job is remote, so we&apos;re not using
                  &quot;Remote&quot; as a city. Add a city below to find local
                  networking events.
                </p>
              )}
            </div>
            <span
              className={`shrink-0 rounded-full px-3 py-1 text-sm font-bold ${scoreColor(
                match.match_score
              )}`}
            >
              {match.match_score}
            </span>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center">
          <div className="text-sm font-semibold text-slate-800">
            No ranked job to target yet
          </div>
          <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">
            Upload a resume, ingest jobs, and rank them so events can be tailored
            to your strongest match. You can still use the manual searches below.
          </p>
          <Link
            href="/matches"
            className="mt-4 inline-block rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Go to Matches →
          </Link>
        </div>
      )}

      {/* Filters */}
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="block">
            <span className="text-xs font-medium text-slate-600">Location</span>
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder={ctx?.location || "e.g. İstanbul, Türkiye"}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-slate-600">
              Radius: {radius} mi
            </span>
            <input
              type="range"
              min={5}
              max={200}
              step={5}
              value={radius}
              onChange={(e) => setRadius(Number(e.target.value))}
              className="mt-2 w-full"
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium text-slate-600">Days ahead</span>
            <select
              value={daysAhead}
              onChange={(e) => setDaysAhead(Number(e.target.value))}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              {DAYS_OPTIONS.map((d) => (
                <option key={d} value={d}>
                  Next {d} days
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 self-end pb-2">
            <input
              type="checkbox"
              checked={includeOnline}
              onChange={(e) => setIncludeOnline(e.target.checked)}
            />
            <span className="text-sm text-slate-700">Include online</span>
          </label>
        </div>
        <button
          onClick={applyFilters}
          disabled={loading}
          className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Searching…" : "Apply filters"}
        </button>
      </div>

      <ErrorBanner message={error} />

      {data && (
        <p className="rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
          {data.message}
        </p>
      )}

      {/* Real events */}
      {loading ? (
        <p className="text-sm text-slate-500">Finding events…</p>
      ) : recs.length > 0 ? (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-900">
            Verified upcoming events
          </h2>
          {recs.map((rec) => (
            <EventCard key={rec.source_url} rec={rec} />
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          No verified upcoming events found from configured providers. Use the
          safe manual searches below — they&apos;re prefilled from your strongest
          match so you can browse real listings yourself.
        </div>
      )}

      {/* Manual search links — always available */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-900">
          Manual search links
        </h2>
        <p className="text-xs text-slate-500">
          Prefilled searches you open yourself. Nothing is scraped, registered,
          or sent on your behalf.
        </p>
        {links.map((link) => (
          <SearchLinkRow
            key={link.url}
            link={link}
            onCopyQuery={copyQuery}
            copied={copied === link.query}
          />
        ))}
      </div>

      {/* Source transparency / providers */}
      {data && (
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Providers &amp; transparency
          </div>
          <ul className="mt-3 space-y-1.5">
            {data.providers.map((p) => (
              <li
                key={p.provider}
                className="flex flex-wrap items-center gap-2 text-sm"
              >
                <span className="font-medium text-slate-800">
                  {providerLabel(p.provider)}
                </span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    p.ok
                      ? "bg-green-100 text-green-800"
                      : p.configured
                      ? "bg-amber-100 text-amber-800"
                      : "bg-slate-100 text-slate-500"
                  }`}
                >
                  {p.ok ? `ok · ${p.count}` : p.configured ? "configured" : "off"}
                </span>
                <span className="text-xs text-slate-500">{p.note}</span>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-xs text-slate-400">{data.disclaimer}</p>
        </div>
      )}
    </div>
  );
}
