"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  api,
  Job,
  IngestResult,
  NewGradIngestResult,
} from "@/lib/api";
import { EmptyState, ErrorBanner } from "@/components/ui";

type Source = "simplify" | "newgrad-jobs";

const SOURCE_LABELS: Record<string, string> = {
  "simplify-newgrad": "SimplifyJobs",
  "newgrad-jobs.com": "newgrad-jobs.com",
};

function sourceLabel(source: string): string {
  return SOURCE_LABELS[source] ?? source;
}

/** Result panel for the newgrad-jobs.com adapter (richer summary + errors). */
function NewGradResult({ r }: { r: NewGradIngestResult }) {
  const [showErrors, setShowErrors] = useState(false);
  return (
    <div className="mt-3 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-800">
      <div className="font-medium">Ingested from newgrad-jobs.com</div>
      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-green-700">
        <span>Fetched: {r.fetched_count}</span>
        <span>Created: {r.created_count}</span>
        <span>Updated: {r.updated_count}</span>
        <span>Skipped (closed): {r.skipped_closed_count}</span>
        <span>Duplicates: {r.duplicate_count}</span>
        <span>Total in DB: {r.total_in_db}</span>
      </div>
      {r.errors.length > 0 && (
        <div className="mt-2">
          <button
            onClick={() => setShowErrors((s) => !s)}
            className="text-xs font-medium text-amber-700 underline"
          >
            {showErrors ? "Hide" : "Show"} {r.errors.length} non-fatal note
            {r.errors.length === 1 ? "" : "s"}
          </button>
          {showErrors && (
            <ul className="mt-1 list-disc space-y-0.5 pl-5 text-xs text-amber-700">
              {r.errors.slice(0, 12).map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [ingesting, setIngesting] = useState(false);
  const [source, setSource] = useState<Source>("simplify");
  const [simplifyResult, setSimplifyResult] = useState<IngestResult | null>(null);
  const [newgradResult, setNewgradResult] = useState<NewGradIngestResult | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);

  async function loadJobs() {
    setLoading(true);
    try {
      setJobs(await api.getJobs(100));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadJobs();
  }, []);

  async function handleIngest() {
    setIngesting(true);
    setError(null);
    setSimplifyResult(null);
    setNewgradResult(null);
    try {
      if (source === "newgrad-jobs") {
        setNewgradResult(await api.ingestNewGradJobs());
      } else {
        setSimplifyResult(await api.ingestJobs());
      }
      await loadJobs();
    } catch (e) {
      setError(
        e instanceof Error
          ? `Couldn't ingest jobs: ${e.message}`
          : "Couldn't ingest jobs. Please try again."
      );
    } finally {
      setIngesting(false);
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Jobs</h1>
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-sm text-slate-500">Source</label>
          <select
            value={source}
            onChange={(e) => setSource(e.target.value as Source)}
            disabled={ingesting}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none disabled:opacity-50"
          >
            <option value="simplify">SimplifyJobs (new grad)</option>
            <option value="newgrad-jobs">newgrad-jobs.com</option>
          </select>
          <button
            onClick={handleIngest}
            disabled={ingesting}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {ingesting ? "Ingesting…" : "Ingest Jobs"}
          </button>
        </div>
      </div>

      <p className="mt-2 text-xs text-slate-500">
        Permission-first: we only fetch the selected source&apos;s own pages, never
        LinkedIn/Indeed/Handshake. Requests are rate-limited and closed jobs are
        skipped.
      </p>

      {simplifyResult && (
        <p className="mt-3 rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
          Ingested {simplifyResult.ingested} new, skipped{" "}
          {simplifyResult.skipped_duplicates} duplicates.{" "}
          {simplifyResult.total_in_db} jobs in database.
        </p>
      )}
      {newgradResult && <NewGradResult r={newgradResult} />}
      <ErrorBanner message={error} />

      <div className="mt-6 space-y-3">
        {loading ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : jobs.length === 0 ? (
          <EmptyState
            title="No jobs ingested yet"
            description="Pick a source above and click “Ingest Jobs” to pull current new-grad postings into your local database."
          />
        ) : (
          jobs.map((job) => (
            <div
              key={job.id}
              className="rounded-lg border border-slate-200 bg-white p-4"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-slate-900">
                      {job.title}
                    </span>
                    {job.is_closed && (
                      <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-700">
                        Closed
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-slate-600">
                    {job.company} · {job.location || "Location N/A"}
                  </div>
                  {/* Normalized chips (only render what's present) */}
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {job.level && (
                      <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
                        {job.level}
                      </span>
                    )}
                    {job.employment_type && (
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                        {job.employment_type}
                      </span>
                    )}
                    {job.work_mode && (
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                        {job.work_mode}
                      </span>
                    )}
                    {job.salary_range && (
                      <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">
                        {job.salary_range}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 text-xs text-slate-400">
                    Source: {sourceLabel(job.source)}
                    {job.posted_at ? ` · posted ${job.posted_at}` : ""}
                  </div>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-2">
                  {job.url && (
                    <a
                      href={job.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-600 hover:underline"
                    >
                      Apply / posting ↗
                    </a>
                  )}
                  <Link
                    href={`/jobs/${job.id}`}
                    className="text-sm font-medium text-slate-700 hover:text-blue-600"
                  >
                    Details →
                  </Link>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
