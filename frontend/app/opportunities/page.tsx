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
// Level tabs keep new-grad and internship seekers in separate lanes.
const LEVELS = ["", "new_grad", "internship", "junior"];
// Field tabs serve tech and business students separately (creative/admin hidden).
const FIELDS = ["all", "software_engineering", "business"];
const APPLICABILITY = ["", "strong", "possible", "unclear", "no"];
const CONFIDENCE = ["", "official_ats", "public_api", "manual_curated", "sample_demo"];

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

// 4-tier Turkey-applicability meta for the match panel (dark surface, so light text tones).
function tierMeta(t: Dict, label_: string | null): { short: string; tone: string } {
  if (label_?.startsWith("Strong"))
    return { short: t.opportunities.tier.strong, tone: "text-brand-300" };
  if (label_ === "Possibly eligible")
    return { short: t.opportunities.tier.possible, tone: "text-amber-300" };
  if (label_ === "Unclear")
    return { short: t.opportunities.tier.unclear, tone: "text-slate-300" };
  return { short: t.opportunities.tier.no, tone: "text-rose-300" };
}
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

const chip = "rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600";
const select =
  "rounded-full border border-slate-300 bg-white px-3 py-1 text-sm text-slate-700 focus:border-brand-500 focus:outline-none";
const tab = (active: boolean) =>
  `rounded-full px-3 py-1 text-sm font-medium transition-colors ${
    active ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
  }`;

/** One glyph + label cell in the card's metadata grid. */
function MetaCell({ glyph, label: text }: { glyph: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-sm text-slate-600">
      <span aria-hidden className="text-slate-400">{glyph}</span>
      <span className="capitalize">{text}</span>
    </span>
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

  return (
    <div className="mx-auto max-w-4xl space-y-4 px-6 py-8">
      {/* Header: title + stat strip + refresh */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{to.title}</h1>
          <p className="mt-1 max-w-xl text-sm text-slate-600">
            {to.subtitlePre}
            <strong className="font-semibold text-slate-800">{to.subtitleStrong}</strong>
            {to.subtitlePost}
          </p>
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

      <p className="text-xs text-slate-500">
        {to.sourcedPre}
        <strong>{to.noScraping}</strong>
        {to.sourcedPost}
      </p>

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

      {/* Filter bar — sticky under the nav: level/field chips + pill filters */}
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
        </div>
        <div className="flex flex-wrap items-center gap-2">
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
      </div>

      {notice && <p className="text-sm text-slate-600">{notice}</p>}
      <ErrorBanner message={error} />

      {loading ? (
        <p className="text-sm text-slate-500">{t.common.loading}</p>
      ) : items.length === 0 ? (
        <EmptyState title={to.emptyTitle} description={to.emptyDesc} />
      ) : (
        <div className="space-y-3">
          {items.map((opp) => {
            const tier = tierMeta(t, opp.turkey_applicability_label);
            return (
              <Card key={opp.id} hover className="overflow-hidden">
                <div className="md:grid md:grid-cols-[1fr,220px]">
                  {/* Main zone */}
                  <div className="p-4">
                    <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-400">
                      {opp.date_posted && <span>{timeAgo(t, opp.date_posted)}</span>}
                      {opp.source_confidence && (
                        <span className={`rounded-full px-2 py-0.5 font-medium ${confidenceStyle(opp.source_confidence)}`}>
                          {label(to.confidence, opp.source_confidence)}
                        </span>
                      )}
                      {opp.source_provider && <span>{opp.source_provider}</span>}
                    </div>

                    <div className="mt-1 text-lg font-semibold leading-tight text-slate-900">
                      {opp.title}
                    </div>
                    <div className="mt-0.5 text-sm text-slate-500">
                      <span className="font-medium text-slate-700">{opp.company}</span>
                      {opp.location ? <> / {opp.location}</> : null}
                    </div>

                    <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 border-t border-slate-100 pt-3 sm:max-w-md">
                      <MetaCell glyph="🌍" label={label(to.region, opp.target_region)} />
                      <MetaCell glyph="🏠" label={opp.remote_policy} />
                      <MetaCell glyph="🎓" label={label(to.level, opp.seniority_level)} />
                      {opp.language_expectation && <MetaCell glyph="💬" label={opp.language_expectation} />}
                    </div>

                    {opp.tags.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {opp.tags.slice(0, 5).map((tag) => (
                          <span key={tag} className={chip}>{tag}</span>
                        ))}
                      </div>
                    )}

                    {opp.work_auth_note && (
                      <p className="mt-2 text-xs text-slate-500">
                        <span className="font-semibold uppercase tracking-wide text-slate-400">
                          {to.workAuth}
                        </span>{" "}
                        {opp.work_auth_note}
                      </p>
                    )}

                    <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-slate-100 pt-3">
                      <Button onClick={() => draftOutreach(opp)}>{to.draftOutreach}</Button>
                      {opp.is_sample ? (
                        <span className="text-xs text-slate-400">{to.sampleListing}</span>
                      ) : (
                        opp.url && (
                          <a
                            href={opp.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 rounded-full border border-slate-300 px-3.5 py-1.5 text-sm font-medium text-slate-700 hover:border-slate-400 hover:bg-slate-50"
                          >
                            {to.openApplication}
                          </a>
                        )
                      )}
                      <span className="ml-auto">
                        <LabelFeedbackControl opportunityId={opp.id} />
                      </span>
                    </div>
                  </div>

                  {/* Match panel — Turkey-applicability tier + skill overlap (no invented %) */}
                  <div className="bg-panel-900 p-4 text-white md:flex md:flex-col md:justify-center">
                    <div className={`text-[11px] font-semibold uppercase tracking-widest ${tier.tone}`}>
                      {to.turkeyFit}
                    </div>
                    <div className={`mt-1 text-lg font-bold leading-tight ${tier.tone}`}>
                      {tier.short}
                    </div>
                    {opp.turkey_applicability_reason && (
                      <p className="mt-1.5 text-xs leading-relaxed text-panel-100/90">
                        {opp.turkey_applicability_reason}
                      </p>
                    )}
                    {opp.match.reason && (
                      <div className="mt-3 border-t border-panel-700/60 pt-3">
                        {opp.match.matched_skills.length > 0 ? (
                          <ul className="space-y-1">
                            {opp.match.matched_skills.slice(0, 4).map((s) => (
                              <li key={s} className="flex items-center gap-1.5 text-xs text-panel-100">
                                <span aria-hidden className="text-brand-300">✓</span>
                                {s}
                              </li>
                            ))}
                            {opp.match.matched_skills.length > 4 && (
                              <li className="text-xs text-panel-300">
                                {to.moreSkills(opp.match.matched_skills.length - 4)}
                              </li>
                            )}
                          </ul>
                        ) : (
                          <p className="text-xs text-panel-200">{opp.match.reason}</p>
                        )}
                        {opp.match.total_skills > 0 && (
                          <p className="mt-2 text-[11px] font-medium uppercase tracking-wide text-panel-300">
                            {to.skillsOfYours(opp.match.matched_count, opp.match.total_skills)}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
