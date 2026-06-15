"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Job, IngestResult } from "@/lib/api";
import { EmptyState, ErrorBanner } from "@/components/ui";

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [ingesting, setIngesting] = useState(false);
  const [result, setResult] = useState<IngestResult | null>(null);
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
    try {
      const r = await api.ingestJobs();
      setResult(r);
      await loadJobs();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to ingest jobs");
    } finally {
      setIngesting(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Jobs</h1>
        <button
          onClick={handleIngest}
          disabled={ingesting}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {ingesting ? "Ingesting..." : "Ingest Latest New Grad Jobs"}
        </button>
      </div>

      {result && (
        <p className="mt-3 rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
          Ingested {result.ingested} new, skipped {result.skipped_duplicates}{" "}
          duplicates. {result.total_in_db} jobs in database.
        </p>
      )}
      <ErrorBanner message={error} />

      <div className="mt-6 space-y-3">
        {loading ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : jobs.length === 0 ? (
          <EmptyState
            title="No jobs ingested yet"
            description="Click “Ingest Latest New Grad Jobs” above to pull the current SimplifyJobs new-grad postings into your local database."
          />
        ) : (
          jobs.map((job) => (
            <div
              key={job.id}
              className="rounded-lg border border-slate-200 bg-white p-4"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="font-semibold text-slate-900">
                    {job.title}
                  </div>
                  <div className="text-sm text-slate-600">
                    {job.company} · {job.location || "Location N/A"}
                  </div>
                  <div className="mt-1 text-xs text-slate-400">
                    Source: {job.source}
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
                      Job posting ↗
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
