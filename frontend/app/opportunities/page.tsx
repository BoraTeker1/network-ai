"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  Opportunity,
  OpportunityFilters,
  OpportunitySource,
} from "@/lib/api";
import {
  PageHeader,
  ErrorBanner,
  EmptyState,
  SectionLabel,
  Card,
  Button,
  WorkflowHint,
} from "@/components/ui";

const REGIONS = ["", "turkey", "remote", "europe", "global"];
const REGION_LABEL: Record<string, string> = {
  "": "All regions", turkey: "Turkey", remote: "Remote", europe: "Europe", global: "Global",
};
// Level tabs keep new-grad and internship seekers in separate lanes.
const LEVELS = ["", "new_grad", "internship", "junior"];
const LEVEL_LABEL: Record<string, string> = {
  "": "All levels", new_grad: "New grad", internship: "Internships", junior: "Junior",
};
// Field tabs serve tech and business students separately (creative/admin hidden).
const FIELDS = ["all", "software_engineering", "business"];
const FIELD_LABEL: Record<string, string> = {
  all: "All fields", software_engineering: "Engineering", business: "Business",
};
const APPLICABILITY = ["", "strong", "possible", "unclear", "no"];
const APPLICABILITY_LABEL: Record<string, string> = {
  "": "Eligible (default)", strong: "Strong fit", possible: "Possibly eligible",
  unclear: "Unclear", no: "Probably not eligible",
};
const CONFIDENCE = ["", "official_ats", "public_api", "manual_curated", "sample_demo"];
const CONFIDENCE_LABEL: Record<string, string> = {
  "": "Any source", official_ats: "Official ATS", public_api: "Public API",
  manual_curated: "Manual", sample_demo: "Sample",
};

function applicabilityStyle(label: string | null): string {
  if (label?.startsWith("Strong")) return "bg-green-100 text-green-800";
  if (label === "Possibly eligible") return "bg-amber-100 text-amber-800";
  if (label === "Unclear") return "bg-slate-100 text-slate-600";
  return "bg-rose-100 text-rose-700";
}
function confidenceStyle(c: string | null): string {
  if (c === "official_ats") return "bg-emerald-50 text-emerald-700";
  if (c === "public_api") return "bg-sky-50 text-sky-700";
  if (c === "manual_curated") return "bg-slate-100 text-slate-600";
  return "bg-amber-50 text-amber-700"; // sample
}

const chip = "rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600";
const select =
  "rounded-md border border-slate-300 bg-white px-2 py-1 text-sm focus:border-blue-500 focus:outline-none";
const tab = (active: boolean) =>
  `rounded-full px-3 py-1 text-sm font-medium ${
    active ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
  }`;

export default function OpportunitiesPage() {
  const router = useRouter();
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
      setNotice(
        `Imported ${r.created} new listings · ${r.succeeded} ATS boards live, ` +
          `${r.failed} failed, ${r.skipped} skipped (manual/disabled).`
      );
      await load();
    } catch {
      setNotice("Couldn't refresh live sources; the curated feed still works.");
    } finally {
      setRefreshing(false);
    }
  }

  function draftOutreach(opp: Opportunity) {
    sessionStorage.setItem("outreach_prefill", JSON.stringify(opp.outreach_prefill));
    router.push("/outreach");
  }

  const liveSources = sources.filter((s) => s.live);

  return (
    <div className="mx-auto max-w-4xl space-y-5 px-6 py-8">
      <PageHeader
        title="Opportunities for Turkish junior engineers"
        subtitle="Turkey-based, remote, European, and global roles a Turkey-based junior can realistically apply to — each flows into the bilingual outreach copilot."
        action={
          <Button onClick={refresh} disabled={refreshing}>
            {refreshing ? "Refreshing…" : "Refresh live sources"}
          </Button>
        }
      />

      <WorkflowHint>
        Pick a realistic role → <strong>draft outreach</strong> → save it to your pipeline.
      </WorkflowHint>

      <p className="text-xs text-slate-500">
        Sourced from companies&apos; official public ATS APIs, public job feeds &amp; manual
        import — <strong>no scraping</strong>. Eligibility labels are conservative guesses;
        always verify on the company page before applying.
      </p>

      {/* Source registry status */}
      <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
        <button
          onClick={() => setShowSources((s) => !s)}
          className="flex w-full items-center justify-between text-left"
        >
          <span className="font-medium text-slate-800">
            Live sources: {liveSources.map((s) => s.company_name).join(", ") || "—"}
          </span>
          <span className="text-xs text-slate-500">{showSources ? "hide" : "show all"}</span>
        </button>
        {showSources && (
          <ul className="mt-2 space-y-1 border-t border-slate-100 pt-2">
            {sources.map((s) => (
              <li key={s.id} className="flex flex-wrap items-center gap-2 text-xs">
                <span className={s.live ? "text-emerald-700" : "text-slate-400"}>
                  {s.live ? "● live" : "○ manual"}
                </span>
                <span className="font-medium text-slate-700">{s.company_name}</span>
                <span className="text-slate-400">
                  {s.ats_provider} · {s.country_scope} · {s.company_category}
                </span>
                {!s.live && (
                  <a href={s.careers_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                    careers ↗
                  </a>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Level + Field lanes: new-grad vs internship, and engineering vs business */}
      <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-12 text-xs font-medium uppercase tracking-wide text-slate-400">Level</span>
          {LEVELS.map((lv) => (
            <button
              key={lv || "all"}
              onClick={() => setFilters((f) => ({ ...f, seniority: lv || undefined }))}
              className={tab((filters.seniority ?? "") === lv)}
            >
              {LEVEL_LABEL[lv]}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-12 text-xs font-medium uppercase tracking-wide text-slate-400">Field</span>
          {FIELDS.map((fl) => (
            <button
              key={fl}
              onClick={() => setFilters((f) => ({ ...f, function: fl }))}
              className={tab((filters.function ?? "all") === fl)}
            >
              {FIELD_LABEL[fl]}
            </button>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white p-3">
        <select className={select} value={filters.region ?? ""} onChange={(e) => setFilters((f) => ({ ...f, region: e.target.value || undefined }))}>
          {REGIONS.map((r) => <option key={r} value={r}>{REGION_LABEL[r]}</option>)}
        </select>
        <select className={select} value={filters.applicability ?? ""} onChange={(e) => setFilters((f) => ({ ...f, applicability: e.target.value || undefined }))}>
          {APPLICABILITY.map((a) => <option key={a} value={a}>{APPLICABILITY_LABEL[a]}</option>)}
        </select>
        <select className={select} value={filters.confidence ?? ""} onChange={(e) => setFilters((f) => ({ ...f, confidence: e.target.value || undefined }))}>
          {CONFIDENCE.map((c) => <option key={c} value={c}>{CONFIDENCE_LABEL[c]}</option>)}
        </select>
        <label className="flex items-center gap-1.5 text-sm text-slate-700">
          <input type="checkbox" checked={remoteOnly} onChange={(e) => setRemoteOnly(e.target.checked)} />
          Remote only
        </label>
        {!loading && <span className="ml-auto text-xs text-slate-500">{items.length} roles</span>}
      </div>

      {notice && <p className="text-sm text-slate-600">{notice}</p>}
      <ErrorBanner message={error} />

      {loading ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : items.length === 0 ? (
        <EmptyState title="No matching opportunities" description="Try clearing filters or refreshing live sources." />
      ) : (
        <div className="space-y-3">
          {items.map((opp) => (
            <Card key={opp.id} hover className="p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-base font-semibold leading-tight text-slate-900">{opp.title}</div>
                  <div className="mt-0.5 text-sm text-slate-600">
                    <span className="font-medium text-slate-700">{opp.company}</span>
                    {opp.location ? ` · ${opp.location}` : ""}
                  </div>
                </div>
                <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${applicabilityStyle(opp.turkey_applicability_label)}`}>
                  {opp.turkey_applicability_label}
                </span>
              </div>

              <p className="mt-1.5 text-xs text-slate-500">{opp.turkey_applicability_reason}</p>

              {opp.match.reason && (
                <div className="mt-2 rounded-md bg-slate-50 px-2.5 py-1.5">
                  <p className="text-xs font-medium text-slate-700">{opp.match.reason}</p>
                  {opp.match.matched_skills.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {opp.match.matched_skills.map((s) => (
                        <span key={s} className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                          {s}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div className="mt-2 flex flex-wrap gap-1.5">
                <span className={chip}>{REGION_LABEL[opp.target_region] ?? opp.target_region}</span>
                <span className={chip}>{opp.seniority_level.replace("_", " ")}</span>
                <span className={chip}>{opp.remote_policy}</span>
                {opp.source_confidence && (
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${confidenceStyle(opp.source_confidence)}`}>
                    {CONFIDENCE_LABEL[opp.source_confidence] ?? opp.source_confidence}
                  </span>
                )}
                {opp.source_provider && <span className={chip}>{opp.source_provider}</span>}
                {opp.language_expectation && <span className={chip}>{opp.language_expectation}</span>}
                {opp.tags.slice(0, 5).map((t) => (
                  <span key={t} className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700">{t}</span>
                ))}
              </div>

              {opp.work_auth_note && (
                <p className="mt-2 text-xs text-slate-500">
                  <SectionLabel>Work authorization</SectionLabel> {opp.work_auth_note}
                </p>
              )}

              <div className="mt-3 flex flex-wrap items-center gap-4 border-t border-slate-100 pt-3">
                <Button onClick={() => draftOutreach(opp)}>Draft outreach</Button>
                {opp.is_sample ? (
                  <span className="text-xs text-slate-400">
                    Sample listing — refresh live sources for real links
                  </span>
                ) : (
                  opp.url && (
                    <a href={opp.url} target="_blank" rel="noopener noreferrer" className="text-sm font-medium text-blue-600 hover:underline">
                      Open application ↗
                    </a>
                  )
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
