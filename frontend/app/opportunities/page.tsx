"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  Opportunity,
  OpportunityFilters,
  OpportunitySource,
} from "@/lib/api";
import { ErrorBanner, EmptyState, Card, Button } from "@/components/ui";
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

const MATCH_TONE: Record<string, string> = {
  strong: "bg-brand-600 text-white",
  good: "bg-brand-50 text-brand-700",
  fair: "bg-amber-50 text-amber-700",
  weak: "bg-slate-100 text-slate-500",
  no: "bg-rose-50 text-rose-600",
};

function confidenceStyle(c: string | null): string {
  if (c === "official_ats") return "bg-brand-50 text-brand-700";
  if (c === "public_api") return "bg-sky-50 text-sky-700";
  if (c === "manual_curated") return "bg-slate-100 text-slate-600";
  return "bg-amber-50 text-amber-700"; // sample
}

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
  "rounded-full border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 focus:border-brand-500 focus:outline-none";
const tab = (active: boolean) =>
  `rounded-full px-3 py-1 text-sm font-medium transition-colors ${
    active ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
  }`;

/** Compact job card: one column, ~half the old height. The match score is a
 * pill whose label is derived from (and therefore consistent with) the
 * location/level/skill rows shown right under the title. */
function OpportunityCard({
  opp,
  onDraft,
}: {
  opp: Opportunity;
  onDraft: (opp: Opportunity) => void;
}) {
  const t = useT();
  const to = t.opportunities;
  const match = matchInfo(opp);
  const reasonText =
    (to.reasons as Record<string, string>)[opp.turkey_applicability_reason_code ?? ""] ??
    opp.turkey_applicability_reason ??
    "";
  const skillsText =
    opp.match.total_skills > 0
      ? to.match.skillsCount(opp.match.matched_count, opp.match.total_skills)
      : to.match.noSkillsData;
  const matchedPreview = opp.match.matched_skills.slice(0, 3).join(", ");

  return (
    <Card hover className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-400">
            {opp.date_posted && <span>{timeAgo(t, opp.date_posted)}</span>}
            {opp.source_confidence && (
              <span
                className={`rounded-full px-2 py-0.5 font-medium ${confidenceStyle(opp.source_confidence)}`}
              >
                {label(to.confidence, opp.source_confidence)}
              </span>
            )}
          </div>
          <div className="mt-0.5 text-base font-semibold leading-snug text-slate-900">
            {opp.title}
          </div>
          <div className="truncate text-sm text-slate-500">
            <span className="font-medium text-slate-700">{opp.company}</span>
            {opp.location ? <> · {opp.location}</> : null}
          </div>
        </div>
        {/* Match score — compact and consistent with the rows below. */}
        <div className="shrink-0 text-right">
          <span
            className={`inline-block rounded-full px-2.5 py-1 text-xs font-semibold ${MATCH_TONE[match.key]}`}
          >
            {to.match[match.key]}
          </span>
          {match.key !== "no" && (
            <div className="mt-0.5 text-[11px] text-slate-400">
              {to.match.scoreOf(match.score)}
            </div>
          )}
        </div>
      </div>

      {/* Why this score: location/eligibility · level · skill overlap. */}
      <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-slate-100 pt-2.5 text-xs text-slate-600">
        <span title={reasonText}>
          <span aria-hidden>📍</span> {label(to.region, opp.target_region)} —{" "}
          {(to.tier as Record<string, string>)[tierKey(opp.turkey_applicability_label)]}
        </span>
        <span>
          <span aria-hidden>🎓</span> {label(to.level, opp.seniority_level)}
        </span>
        <span title={matchedPreview}>
          <span aria-hidden>🧩</span> {skillsText}
          {matchedPreview && (
            <span className="text-slate-400"> ({matchedPreview})</span>
          )}
        </span>
      </div>
      {reasonText && (
        <p className="mt-1 text-xs leading-snug text-slate-400">{reasonText}</p>
      )}

      <div className="mt-2.5 flex flex-wrap items-center gap-2">
        <Button size="sm" onClick={() => onDraft(opp)}>
          {to.draftOutreach}
        </Button>
        {opp.is_sample ? (
          <span className="text-xs text-slate-400">{to.sampleListing}</span>
        ) : (
          opp.url && (
            <a
              href={opp.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center rounded-full border border-slate-300 px-3 py-1 text-xs font-medium text-slate-700 hover:border-slate-400 hover:bg-slate-50"
            >
              {to.openApplication}
            </a>
          )
        )}
        <span className="ml-auto">
          <LabelFeedbackControl opportunityId={opp.id} />
        </span>
      </div>
    </Card>
  );
}

export default function OpportunitiesPage() {
  const router = useRouter();
  const t = useT();
  const [items, setItems] = useState<Opportunity[]>([]);
  const [sources, setSources] = useState<OpportunitySource[]>([]);
  const [showSources, setShowSources] = useState(false);
  const [filters, setFilters] = useState<OpportunityFilters>({ function: "all" });
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [moreFilters, setMoreFilters] = useState(false);
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

  async function refresh() {
    setRefreshing(true);
    setNotice(null);
    try {
      // One click pulls everything: official ATS boards + public job APIs
      // (Arbeitnow / Remotive / Jobicy).
      const r = await api.refreshAllSources();
      setNotice(t.opportunities.importedNotice(r.created, r.succeeded, r.failed, r.skipped));
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

  const liveSources = sources.filter((s) => s.live);
  const to = t.opportunities;
  // Badge on the "more filters" toggle when hidden filters are active.
  const secondaryActive =
    Number(Boolean(filters.region)) +
    Number(Boolean(filters.applicability)) +
    Number(Boolean(filters.confidence)) +
    Number(remoteOnly);

  return (
    <div className="mx-auto max-w-4xl space-y-4 px-6 py-8">
      {/* Header: title + stat strip + refresh */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{to.title}</h1>
          <p className="mt-1 max-w-xl text-sm text-slate-600">{to.subtitle}</p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1.5">
          <Button variant="secondary" onClick={refresh} disabled={refreshing}>
            {refreshing ? to.refreshing : to.refresh}
          </Button>
          {!loading && (
            <span className="text-xs text-slate-500">
              <strong className="font-semibold text-brand-700">{items.length}</strong>{" "}
              {to.rolesLabel}
              {" · "}
              <strong className="font-semibold text-brand-700">{liveSources.length}</strong>{" "}
              {to.liveSourcesLabel}
            </span>
          )}
        </div>
      </div>

      {/* Source registry — slim disclosure line */}
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
          <span aria-hidden>{showSources ? "▴" : "▾"}</span>
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

      {/* Filter bar — sticky under the nav. Primary: level, field, posted date.
          Everything else folds under "More filters". */}
      <div className="sticky top-[57px] z-10 space-y-2 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          {LEVELS.map((lv) => (
            <button
              key={lv || "all"}
              onClick={() => setFilters((f) => ({ ...f, seniority: lv || undefined }))}
              className={tab((filters.seniority ?? "") === lv)}
            >
              {label(to.level, lv)}
            </button>
          ))}
          <span aria-hidden className="mx-1 h-4 w-px bg-slate-200" />
          {FIELDS.map((fl) => (
            <button
              key={fl}
              onClick={() => setFilters((f) => ({ ...f, function: fl }))}
              className={tab((filters.function ?? "all") === fl)}
            >
              {label(to.field, fl)}
            </button>
          ))}
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
            {POSTED.map((p) => <option key={p} value={p}>{label(to.posted, p)}</option>)}
          </select>
          <button
            onClick={() => setMoreFilters((v) => !v)}
            className="ml-auto inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-800"
          >
            {moreFilters ? to.hideFilters : to.otherFilters}
            {!moreFilters && secondaryActive > 0 && (
              <span className="rounded-full bg-brand-100 px-1.5 text-[10px] font-semibold text-brand-700">
                {secondaryActive}
              </span>
            )}
            <span aria-hidden>{moreFilters ? "▴" : "▾"}</span>
          </button>
        </div>
        {moreFilters && (
          <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 pt-2">
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
              className={tab(remoteOnly)}
            >
              {to.remoteOnly}
            </button>
          </div>
        )}
      </div>

      {notice && <p className="text-sm text-slate-600">{notice}</p>}
      <ErrorBanner message={error} />

      {loading ? (
        <p className="text-sm text-slate-500">{t.common.loading}</p>
      ) : items.length === 0 ? (
        <EmptyState
          title={to.emptyTitle}
          description={to.emptyDesc}
          ctaLabel={refreshing ? to.refreshing : to.emptyCta}
          onCta={refresh}
        />
      ) : (
        <div className="space-y-2.5">
          {items.map((opp) => (
            <OpportunityCard key={opp.id} opp={opp} onDraft={draftOutreach} />
          ))}
        </div>
      )}
    </div>
  );
}
