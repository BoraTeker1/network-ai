"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  Opportunity,
  OpportunityFilters,
  OpportunitySource,
} from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { useFeedSearch } from "@/components/AppShell";
import CompanyLogo from "@/components/CompanyLogo";
import { ErrorBanner, EmptyState, Card, Button } from "@/components/ui";
import {
  ArrowUpRight,
  Bookmark,
  Briefcase,
  ChevronDown,
  FileText,
  GraduationCap,
  Refresh,
  Send,
  ShieldCheck,
  Sliders,
  SortDesc,
  Target,
  X,
} from "@/components/icons";
import { useSavedOpportunities } from "@/lib/saved";
import { useT } from "@/lib/i18n";
import type { Dict } from "@/lib/i18n/en";

const REGIONS = ["", "turkey", "remote", "europe", "global"];
// "entry_level" groups new-grad + junior (each applies to the other's roles);
// internships stay a separate lane.
const LEVELS = ["", "entry_level", "internship"];
// Field tabs serve tech and business students separately (creative/admin hidden).
const FIELDS = ["all", "software_engineering", "business"];
const APPLICABILITY = ["", "strong", "possible", "unclear", "no"];
const CONFIDENCE = ["", "official_ats", "public_api", "manual_curated", "sample_demo"];
// Freshness windows in days ("" = any time).
const POSTED = ["", "1", "7", "30", "90"];

const JUNIOR_LEVELS = ["new_grad", "junior", "internship"];

const REFRESHED_AT_KEY = "network_ai_opps_refreshed_at";

type SortKey = "best" | "newest";

// Look up a filter value in a dict map, treating "" as "all".
function label(map: Record<string, string>, key: string | null | undefined): string {
  return map[key || "all"] ?? key ?? "";
}

// "3 days ago" style label for the feed's meta row; falls back to the raw string.
function timeAgo(t: Dict, dateStr: string): string {
  const ts = Date.parse(dateStr);
  if (Number.isNaN(ts)) return dateStr;
  const days = Math.floor((Date.now() - ts) / 86_400_000);
  if (days <= 0) return t.opportunities.today;
  if (days === 1) return t.opportunities.yesterday;
  if (days < 30) return t.opportunities.daysAgo(days);
  return t.opportunities.monthsAgo(Math.floor(days / 30));
}

// Minute-granularity sibling of timeAgo, for "updated 12 min ago".
function shortAgo(t: Dict, ts: number): string {
  const mins = Math.floor((Date.now() - ts) / 60_000);
  if (mins < 1) return t.opportunities.justNow;
  if (mins < 60) return t.opportunities.minutesAgo(mins);
  const hours = Math.floor(mins / 60);
  if (hours < 24) return t.opportunities.hoursAgo(hours);
  return timeAgo(t, new Date(ts).toISOString());
}

function tierKey(label_: string | null): "strong" | "possible" | "unclear" | "no" {
  if (label_?.startsWith("Strong")) return "strong";
  if (label_ === "Possibly eligible") return "possible";
  if (label_ === "Unclear") return "unclear";
  return "no";
}

/**
 * Explainable match score from the three signals the card shows: eligibility
 * (max 45), level (max 20), and skill overlap (max 35). The overall label is
 * derived from the score, so it can never contradict its own components —
 * a strong-eligibility role with 0 matched skills tops out at "good".
 */
function matchInfo(opp: Opportunity): {
  score: number;
  key: "strong" | "good" | "fair" | "weak" | "no";
} {
  const tier = tierKey(opp.turkey_applicability_label);
  if (tier === "no") return { score: 0, key: "no" };
  const eligibility = { strong: 45, possible: 28, unclear: 12, no: 0 }[tier];
  const level = JUNIOR_LEVELS.includes(opp.seniority_level)
    ? 20
    : opp.seniority_level === "mid"
      ? 10
      : opp.seniority_level === "unknown"
        ? 8
        : 0;
  const { matched_count: matched, total_skills: total } = opp.match;
  // Cap the denominator so long skill lists don't drown a real overlap.
  const skills = total > 0 ? Math.round(35 * Math.min(1, matched / Math.min(total, 8))) : 0;
  const score = eligibility + level + skills;
  const key = score >= 80 ? "strong" : score >= 60 ? "good" : score >= 35 ? "fair" : "weak";
  return { score, key };
}

// Score rail colors, keyed to the same tiers the label uses.
const SCORE_TONE: Record<string, string> = {
  strong: "text-brand-700",
  good: "text-brand-600",
  fair: "text-amber-600",
  weak: "text-slate-400",
  no: "text-rose-500",
};

function confidenceStyle(c: string | null): string {
  if (c === "official_ats") return "bg-brand-50 text-brand-700";
  if (c === "public_api") return "bg-sky-50 text-sky-700";
  if (c === "manual_curated") return "bg-slate-100 text-slate-600";
  return "bg-amber-50 text-amber-700"; // sample
}

// Eligibility line tone — green when Türkiye can actually apply.
const TIER_TONE: Record<string, string> = {
  strong: "text-brand-700",
  possible: "text-brand-600",
  unclear: "text-slate-500",
  no: "text-rose-600",
};

// Tiny per-card feedback on the eligibility label — the signal that tells us
// whether the Turkey-applicability classifier is actually right for real users.
function LabelFeedbackControl({ opportunityId }: { opportunityId: number }) {
  const t = useT();
  const [state, setState] = useState<"idle" | "reason" | "done">("idle");
  const [reason, setReason] = useState("");

  async function send(verdict: "right" | "wrong", withReason?: string) {
    try {
      await api.sendLabelFeedback(opportunityId, verdict, withReason);
      setState("done");
    } catch {
      setState("done"); // feedback is best-effort; never nag the user about it
    }
  }

  if (state === "done") {
    return <span className="text-xs text-slate-400">{t.opportunities.labelThanks}</span>;
  }
  if (state === "reason") {
    return (
      <span className="inline-flex flex-wrap items-center gap-1.5">
        <input
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder={t.opportunities.labelWrongPlaceholder}
          className="rounded-full border border-slate-300 px-2 py-0.5 text-xs focus:border-brand-500 focus:outline-none"
        />
        <button
          onClick={() => send("wrong", reason.trim() || undefined)}
          className="text-xs font-medium text-brand-700 hover:underline"
        >
          {t.opportunities.labelSend}
        </button>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-slate-400">
      {t.opportunities.labelRight}
      <button
        onClick={() => send("right")}
        title={t.opportunities.labelRightTitle}
        className="rounded px-1 hover:bg-brand-50 hover:text-brand-700"
      >
        ✓
      </button>
      <button
        onClick={() => setState("reason")}
        title={t.opportunities.labelWrongTitle}
        className="rounded px-1 hover:bg-rose-50 hover:text-rose-700"
      >
        ✗
      </button>
    </span>
  );
}

const select =
  "appearance-none rounded-lg border border-slate-200 bg-white py-2 pl-3 pr-8 text-sm text-slate-700 focus:border-brand-500 focus:outline-none";

/** Bordered segmented control — one group of mutually exclusive filter tabs. */
function Segmented({
  options,
  value,
  onChange,
  labels,
}: {
  options: string[];
  value: string;
  onChange: (v: string) => void;
  labels: Record<string, string>;
}) {
  return (
    <div className="inline-flex items-center rounded-lg border border-slate-200 bg-white p-1">
      {options.map((opt) => {
        const active = value === opt;
        return (
          <button
            key={opt || "all"}
            onClick={() => onChange(opt)}
            aria-pressed={active}
            className={`whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              active
                ? "bg-brand-600 text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
            }`}
          >
            {label(labels, opt)}
          </button>
        );
      })}
    </div>
  );
}

/** One dismissible chip in the active-filter row. */
function FilterChip({ text, onClear }: { text: string; onClear: () => void }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 py-1 pl-2.5 pr-1.5 text-xs font-medium text-brand-700">
      {text}
      <button
        onClick={onClear}
        aria-label={`${text} ✕`}
        className="rounded-full p-0.5 hover:bg-brand-100"
      >
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}

function StatTile({
  Icon,
  value,
  caption,
}: {
  Icon: (p: { className?: string }) => JSX.Element;
  value: number;
  caption: string;
}) {
  return (
    <div className="flex items-center gap-3 px-2 py-1">
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-600">
        <Icon className="h-5 w-5" />
      </span>
      <div className="min-w-0">
        <div className="text-2xl font-bold leading-tight text-slate-900">{value}</div>
        <div className="truncate text-xs text-slate-500">{caption}</div>
      </div>
    </div>
  );
}

/** Job card: logo, title + eligibility evidence, the match score in its own
 * rail, and the two actions. The score's label is derived from (and therefore
 * consistent with) the eligibility/level/skill row shown under the title. */
function OpportunityCard({
  opp,
  onDraft,
  saved,
  onToggleSave,
  careersUrl,
}: {
  opp: Opportunity;
  onDraft: (opp: Opportunity) => void;
  saved: boolean;
  onToggleSave: (id: number) => void;
  careersUrl?: string;
}) {
  const t = useT();
  const to = t.opportunities;
  const match = matchInfo(opp);
  const tier = tierKey(opp.turkey_applicability_label);
  const reasonText =
    (to.reasons as Record<string, string>)[opp.turkey_applicability_reason_code ?? ""] ??
    opp.turkey_applicability_reason ??
    "";
  const skills = opp.match.matched_skills.slice(0, 3);

  return (
    <Card hover className="p-4">
      <div className="flex flex-wrap items-start gap-4">
        <CompanyLogo
          company={opp.company}
          url={opp.url ?? opp.source_url}
          careersUrl={careersUrl}
        />

        {/* Title, company, and the evidence behind the score */}
        <div className="min-w-0 flex-1 basis-64">
          <h3 className="text-base font-semibold leading-snug text-slate-900">{opp.title}</h3>
          <div className="mt-0.5 truncate text-sm">
            <span className="font-medium text-brand-700">{opp.company}</span>
            {opp.location ? <span className="text-slate-500"> · {opp.location}</span> : null}
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-slate-500">
            {opp.source_confidence && (
              <span
                className={`rounded-full px-2 py-0.5 font-medium ${confidenceStyle(opp.source_confidence)}`}
              >
                {label(to.confidence, opp.source_confidence)}
              </span>
            )}
            {opp.date_posted && <span>{timeAgo(t, opp.date_posted)}</span>}
            <span className={`inline-flex items-center gap-1 font-medium ${TIER_TONE[tier]}`}>
              <ShieldCheck className="h-3.5 w-3.5" />
              {tier === "strong" ? to.eligibleFromTurkey : (to.tier as Record<string, string>)[tier]}
            </span>
            <span className="inline-flex items-center gap-1">
              <GraduationCap className="h-3.5 w-3.5 text-slate-400" />
              {label(to.level, opp.seniority_level)}
            </span>
            {skills.length > 0 && (
              <span className="text-slate-400">{skills.join(" · ")}</span>
            )}
          </div>

          {reasonText && (
            <p className="mt-2 inline-flex items-start gap-1.5 text-xs leading-snug text-slate-400">
              <FileText className="mt-px h-3.5 w-3.5 shrink-0" />
              {reasonText}
            </p>
          )}
        </div>

        {/* Match score rail */}
        <div className="w-24 shrink-0 text-center">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
            {to.matchScoreLabel}
          </div>
          <div className={`text-3xl font-bold leading-tight ${SCORE_TONE[match.key]}`}>
            {match.score}
          </div>
          <div className="text-xs font-medium text-slate-500">{to.match[match.key]}</div>
        </div>

        {/* Save + the two actions */}
        <div className="flex shrink-0 items-start gap-2">
          <button
            onClick={() => onToggleSave(opp.id)}
            aria-pressed={saved}
            title={saved ? to.savedRole : to.saveRole}
            aria-label={saved ? to.savedRole : to.saveRole}
            className={`rounded-lg p-1.5 transition-colors ${
              saved
                ? "text-brand-600 hover:bg-brand-50"
                : "text-slate-300 hover:bg-slate-100 hover:text-slate-500"
            }`}
          >
            <Bookmark className="h-5 w-5" filled={saved} />
          </button>

          <div className="flex w-44 flex-col gap-2">
            {opp.is_sample ? (
              <span className="rounded-lg bg-slate-50 px-3 py-2 text-center text-xs text-slate-400">
                {to.sampleListing}
              </span>
            ) : (
              opp.url && (
                <a
                  href={opp.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700"
                >
                  {to.openApplication}
                  <ArrowUpRight className="h-4 w-4" />
                </a>
              )
            )}
            <button
              onClick={() => onDraft(opp)}
              className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-slate-400 hover:bg-slate-50"
            >
              {to.draftOutreach}
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      <div className="mt-2 flex justify-end">
        <LabelFeedbackControl opportunityId={opp.id} />
      </div>
    </Card>
  );
}

export default function OpportunitiesPage() {
  const router = useRouter();
  const t = useT();
  const { user, loading: authLoading } = useAuth();
  const { query } = useFeedSearch();
  const { has: isSaved, toggle: toggleSaved } = useSavedOpportunities();
  const autoRefreshTried = useRef(false);
  const [items, setItems] = useState<Opportunity[]>([]);
  const [sources, setSources] = useState<OpportunitySource[]>([]);
  const [showSources, setShowSources] = useState(false);
  const [filters, setFilters] = useState<OpportunityFilters>({ function: "all" });
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [moreFilters, setMoreFilters] = useState(false);
  const [sort, setSort] = useState<SortKey>("best");
  const [refreshedAt, setRefreshedAt] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getOpportunities({ ...filters, remote: remoteOnly });
      setItems(res.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load opportunities.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    api.getOpportunitySources().then((r) => setSources(r.sources)).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, remoteOnly]);

  // Read the last refresh after mount so the server render stays deterministic.
  useEffect(() => {
    const stored = Number(window.localStorage.getItem(REFRESHED_AT_KEY));
    if (stored) setRefreshedAt(stored);
  }, []);

  // First-visit auto-refresh: when a logged-in user lands on an empty or
  // sample-only feed, pull the live sources once so the first screen shows
  // real listings instead of demo rows. One shot per browser session; the
  // backend's opps_refresh rate limit (2/min) guards against loops anyway.
  useEffect(() => {
    if (authLoading || !user || loading || refreshing || autoRefreshTried.current) return;
    autoRefreshTried.current = true;
    if (sessionStorage.getItem("opps_auto_refreshed")) return;
    const feedIsPlaceholder = items.length === 0 || items.every((i) => i.is_sample);
    if (!feedIsPlaceholder) return;
    sessionStorage.setItem("opps_auto_refreshed", "1");
    setNotice(t.opportunities.autoRefreshing);
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, user, loading, items]);

  async function refresh() {
    setRefreshing(true);
    setNotice(null);
    try {
      // One click pulls everything: official ATS boards + public job APIs
      // (Arbeitnow / Remotive / Jobicy).
      const r = await api.refreshAllSources();
      setNotice(t.opportunities.importedNotice(r.created, r.succeeded, r.failed, r.skipped));
      const now = Date.now();
      setRefreshedAt(now);
      try {
        window.localStorage.setItem(REFRESHED_AT_KEY, String(now));
      } catch {
        /* private mode — the timestamp just won't survive a reload */
      }
      await load();
    } catch {
      setNotice(t.opportunities.refreshFailed);
    } finally {
      setRefreshing(false);
    }
  }

  function draftOutreach(opp: Opportunity) {
    sessionStorage.setItem("outreach_prefill", JSON.stringify(opp.outreach_prefill));
    router.push("/outreach");
  }

  const to = t.opportunities;
  const liveSources = sources.filter((s) => s.live);

  // The top-bar query and the sort control are applied in the browser — the API
  // has no search or ordering params, and the feed is capped at 100 rows anyway.
  const visible = useMemo(() => {
    const q = query.trim().toLocaleLowerCase("tr");
    const matched = q
      ? items.filter((o) =>
          `${o.company ?? ""} ${o.title ?? ""}`.toLocaleLowerCase("tr").includes(q),
        )
      : items;
    return [...matched].sort((a, b) =>
      sort === "newest"
        ? Date.parse(b.date_posted ?? "") - Date.parse(a.date_posted ?? "") || 0
        : matchInfo(b).score - matchInfo(a).score,
    );
  }, [items, query, sort]);

  const strongMatches = useMemo(
    () => items.filter((o) => matchInfo(o).key === "strong").length,
    [items],
  );

  // Company → its own careers page, so a card's logo can come from the company's
  // domain rather than from whichever ATS board the listing was imported off.
  const careersByCompany = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of sources) {
      if (s.careers_url) map.set(s.company_name.toLocaleLowerCase("tr"), s.careers_url);
    }
    return map;
  }, [sources]);

  // Badge on the "more filters" toggle when hidden filters are active.
  const secondaryActive =
    Number(Boolean(filters.region)) +
    Number(Boolean(filters.applicability)) +
    Number(Boolean(filters.confidence)) +
    Number(remoteOnly);

  // Every filter that's off its default gets a dismissible chip.
  const chips: { text: string; clear: () => void }[] = [];
  if (filters.seniority) {
    chips.push({
      text: label(to.level, filters.seniority),
      clear: () => setFilters((f) => ({ ...f, seniority: undefined })),
    });
  }
  if (filters.function && filters.function !== "all") {
    chips.push({
      text: label(to.field, filters.function),
      clear: () => setFilters((f) => ({ ...f, function: "all" })),
    });
  }
  if (filters.posted_within_days) {
    chips.push({
      text: label(to.posted, String(filters.posted_within_days)),
      clear: () => setFilters((f) => ({ ...f, posted_within_days: undefined })),
    });
  }
  if (filters.region) {
    chips.push({
      text: label(to.region, filters.region),
      clear: () => setFilters((f) => ({ ...f, region: undefined })),
    });
  }
  if (filters.applicability) {
    chips.push({
      text: label(to.applicability, filters.applicability),
      clear: () => setFilters((f) => ({ ...f, applicability: undefined })),
    });
  }
  if (filters.confidence) {
    chips.push({
      text: label(to.confidence, filters.confidence),
      clear: () => setFilters((f) => ({ ...f, confidence: undefined })),
    });
  }
  if (remoteOnly) {
    chips.push({ text: to.remoteOnly, clear: () => setRemoteOnly(false) });
  }

  function clearAll() {
    setFilters({ function: "all" });
    setRemoteOnly(false);
  }

  return (
    <div className="space-y-4">
      {/* Header: title + refresh + last-updated */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{to.title}</h1>
          <p className="mt-1 max-w-xl text-sm text-slate-600">{to.subtitle}</p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1.5">
          <Button variant="secondary" onClick={refresh} disabled={refreshing}>
            <Refresh className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            {refreshing ? to.refreshing : to.refresh}
          </Button>
          {refreshedAt && (
            <span className="text-xs text-slate-400">
              {to.lastUpdated(shortAgo(t, refreshedAt))}
            </span>
          )}
        </div>
      </div>

      {/* What the feed is made of, at a glance */}
      <Card className="grid gap-2 p-4 sm:grid-cols-3 sm:divide-x sm:divide-slate-100">
        <StatTile Icon={Briefcase} value={items.length} caption={to.statActiveRoles} />
        <div className="sm:pl-6">
          <StatTile
            Icon={ShieldCheck}
            value={liveSources.length}
            caption={to.statVerifiedSources}
          />
        </div>
        <div className="sm:pl-6">
          <StatTile Icon={Target} value={strongMatches} caption={to.statStrongMatches} />
        </div>
      </Card>

      {/* Source registry — the "no scraping, here's where this came from" proof */}
      <div className="text-sm">
        <button
          onClick={() => setShowSources((s) => !s)}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-800"
        >
          <span aria-hidden className="text-brand-600">●</span>
          {liveSources.length} {to.liveSourcesLabel}
          {liveSources.length > 0 &&
            `: ${liveSources.slice(0, 6).map((s) => s.company_name).join(", ")}${
              liveSources.length > 6 ? ", …" : ""
            }`}
          <ChevronDown className={`h-3.5 w-3.5 ${showSources ? "rotate-180" : ""}`} />
        </button>
        {showSources && (
          <ul className="mt-2 space-y-1 rounded-xl border border-slate-200 bg-white p-3">
            {sources.map((s) => (
              <li key={s.id} className="flex flex-wrap items-center gap-2 text-xs">
                <span className={s.live ? "text-brand-700" : "text-slate-400"}>
                  {s.live ? `● ${to.live}` : `○ ${to.manualSource}`}
                </span>
                <span className="font-medium text-slate-700">{s.company_name}</span>
                <span className="text-slate-400">
                  {s.ats_provider} · {s.country_scope} · {s.company_category}
                </span>
                {!s.live && (
                  <a href={s.careers_url} target="_blank" rel="noopener noreferrer" className="text-brand-700 hover:underline">
                    {to.careers}
                  </a>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Filters. Primary: level, field, posted date. The rest folds away. */}
      <Card className="space-y-3 p-3">
        <div className="flex flex-wrap items-center gap-2">
          <Segmented
            options={LEVELS}
            value={filters.seniority ?? ""}
            onChange={(v) => setFilters((f) => ({ ...f, seniority: v || undefined }))}
            labels={to.level}
          />
          <Segmented
            options={FIELDS}
            value={filters.function ?? "all"}
            onChange={(v) => setFilters((f) => ({ ...f, function: v }))}
            labels={to.field}
          />

          <div className="relative ml-auto">
            <select
              className={select}
              value={filters.posted_within_days ? String(filters.posted_within_days) : ""}
              onChange={(e) =>
                setFilters((f) => ({
                  ...f,
                  posted_within_days: e.target.value ? Number(e.target.value) : undefined,
                }))
              }
            >
              {POSTED.map((p) => (
                <option key={p} value={p}>
                  {label(to.posted, p)}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          </div>

          <button
            onClick={() => setMoreFilters((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900"
          >
            <Sliders className="h-4 w-4" />
            {moreFilters ? to.hideFilters : to.otherFilters}
            {!moreFilters && secondaryActive > 0 && (
              <span className="rounded-full bg-brand-100 px-1.5 text-[10px] font-semibold text-brand-700">
                {secondaryActive}
              </span>
            )}
          </button>
        </div>

        {moreFilters && (
          <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
            <select className={select} value={filters.region ?? ""} onChange={(e) => setFilters((f) => ({ ...f, region: e.target.value || undefined }))}>
              {REGIONS.map((r) => <option key={r} value={r}>{label(to.region, r)}</option>)}
            </select>
            <select className={select} value={filters.applicability ?? ""} onChange={(e) => setFilters((f) => ({ ...f, applicability: e.target.value || undefined }))}>
              {APPLICABILITY.map((a) => <option key={a} value={a}>{label(to.applicability, a)}</option>)}
            </select>
            <select className={select} value={filters.confidence ?? ""} onChange={(e) => setFilters((f) => ({ ...f, confidence: e.target.value || undefined }))}>
              {CONFIDENCE.map((c) => <option key={c} value={c}>{label(to.confidence, c)}</option>)}
            </select>
            <button
              onClick={() => setRemoteOnly((v) => !v)}
              aria-pressed={remoteOnly}
              className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                remoteOnly
                  ? "border-brand-600 bg-brand-600 text-white"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              {to.remoteOnly}
            </button>
          </div>
        )}

        {chips.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
            <span className="text-xs text-slate-500">{to.activeFilters}</span>
            {chips.map((c) => (
              <FilterChip key={c.text} text={c.text} onClear={c.clear} />
            ))}
            <button
              onClick={clearAll}
              className="ml-auto text-xs font-medium text-brand-700 hover:underline"
            >
              {to.clearFilters}
            </button>
          </div>
        )}
      </Card>

      {notice && <p className="text-sm text-slate-600">{notice}</p>}
      {!authLoading && !user && !loading &&
        (items.length === 0 || items.every((i) => i.is_sample)) && (
          <p className="text-sm text-slate-500">{to.loginToRefresh}</p>
        )}
      <ErrorBanner message={error} />

      {/* Results */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-slate-900">
          {to.resultsTitle}{" "}
          {!loading && (
            <span className="text-sm font-normal text-slate-400">
              {to.resultsCount(visible.length)}
            </span>
          )}
        </h2>
        <div className="relative">
          <SortDesc className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <select
            aria-label={to.sortBest}
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            className={`${select} pl-9`}
          >
            <option value="best">{to.sortBest}</option>
            <option value="newest">{to.sortNewest}</option>
          </select>
          <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-slate-500">{t.common.loading}</p>
      ) : items.length === 0 ? (
        <EmptyState
          title={to.emptyTitle}
          description={to.emptyDesc}
          ctaLabel={refreshing ? to.refreshing : to.emptyCta}
          onCta={refresh}
        />
      ) : visible.length === 0 ? (
        <EmptyState title={to.emptyTitle} description={to.noSearchResults(query.trim())} />
      ) : (
        <div className="space-y-2.5">
          {visible.map((opp) => (
            <OpportunityCard
              key={opp.id}
              opp={opp}
              onDraft={draftOutreach}
              saved={isSaved(opp.id)}
              onToggleSave={toggleSaved}
              careersUrl={careersByCompany.get((opp.company ?? "").toLocaleLowerCase("tr"))}
            />
          ))}
        </div>
      )}
    </div>
  );
}
