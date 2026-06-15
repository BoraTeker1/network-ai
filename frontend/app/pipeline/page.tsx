"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Message, RankedMatch, OUTCOMES } from "@/lib/api";
import {
  EmptyState,
  ErrorBanner,
  OutcomeBadge,
  FollowUpBadge,
  PageHeader,
} from "@/components/ui";

// Outreach status columns, in funnel order.
const STATUS_COLUMNS: { status: string; label: string }[] = [
  { status: "draft", label: "Drafted" },
  { status: "approved", label: "Approved" },
  { status: "copied", label: "Copied" },
  { status: "sent_manually", label: "Sent Manually" },
  { status: "rejected", label: "Rejected" },
];

function MessageCard({ m }: { m: Message }) {
  return (
    <Link
      href={m.job_id ? `/jobs/${m.job_id}` : "/messages"}
      className="block rounded-md border border-slate-200 bg-white p-2.5 hover:border-blue-400"
    >
      <div className="truncate text-sm font-medium text-slate-900">
        {m.company || "Unknown company"}
      </div>
      <div className="truncate text-xs text-slate-500">{m.title || ""}</div>
      <div className="mt-1 flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-wide text-slate-400">
          {m.message_type.replace(/_/g, " ")}
        </span>
        {m.outcome && <OutcomeBadge outcome={m.outcome} />}
      </div>
      {m.follow_up_status && (
        <div className="mt-1.5">
          <FollowUpBadge
            status={m.follow_up_status}
            dueDate={m.follow_up_due_date}
          />
        </div>
      )}
    </Link>
  );
}

export default function PipelinePage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [matches, setMatches] = useState<RankedMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [msgs, ranked] = await Promise.all([
          api.getMessages(),
          api.getRankedMatches(100),
        ]);
        setMessages(msgs);
        setMatches(ranked);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load pipeline");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <p className="text-sm text-slate-500">Loading…</p>;

  const jobsWithDrafts = new Set(
    messages.map((m) => m.job_id).filter((id): id is number => id != null)
  );
  const notStarted = matches.filter((m) => !jobsWithDrafts.has(m.job_id));

  const byStatus = (status: string) =>
    messages.filter((m) => m.status === status);
  const byOutcome = (outcome: string) =>
    messages.filter((m) => m.outcome === outcome);

  const followUpsDue = messages.filter(
    (m) => m.follow_up_status === "follow_up_needed"
  );

  const isEmpty = messages.length === 0 && matches.length === 0;

  return (
    <div>
      <PageHeader
        title="Networking Pipeline"
        subtitle="A lightweight CRM for your job-search outreach. Track every contact from an untouched match through drafting, approval, manual send, follow-up, and the real outcome."
      />

      <ErrorBanner message={error} />

      {!isEmpty && (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-amber-700">
            Follow-ups due ({followUpsDue.length})
          </div>
          {followUpsDue.length === 0 ? (
            <p className="mt-1 text-sm text-amber-700">
              No follow-up needed yet. Mark one on the Messages page after you
              reach out.
            </p>
          ) : (
            <div className="mt-2 flex flex-wrap gap-2">
              {followUpsDue.map((m) => (
                <Link
                  key={m.id}
                  href={m.job_id ? `/jobs/${m.job_id}` : "/messages"}
                  className="rounded-md border border-amber-300 bg-white px-2.5 py-1 text-xs text-slate-700 hover:border-amber-500"
                >
                  {m.company || "Unknown"}
                  {m.follow_up_due_date ? ` · due ${m.follow_up_due_date}` : ""}
                </Link>
              ))}
            </div>
          )}
        </div>
      )}

      {isEmpty ? (
        <div className="mt-6">
          <EmptyState
            title="Your pipeline is empty"
            description="Match jobs and generate outreach drafts to start tracking them here. From the dashboard you can also load demo data instantly."
            ctaHref="/matches"
            ctaLabel="Go to matches →"
          />
        </div>
      ) : (
        <>
          {/* Outreach status board */}
          <div className="mt-6 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
            {/* Not Started — matched jobs with no drafts yet */}
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-700">
                  Not Started
                </span>
                <span className="text-xs text-slate-400">
                  {notStarted.length}
                </span>
              </div>
              <div className="mt-2 space-y-2">
                {notStarted.length === 0 ? (
                  <p className="text-xs text-slate-400">
                    Every matched job has drafts.
                  </p>
                ) : (
                  notStarted.slice(0, 8).map((m) => (
                    <Link
                      key={m.job_id}
                      href={`/jobs/${m.job_id}`}
                      className="block rounded-md border border-slate-200 bg-white p-2.5 hover:border-blue-400"
                    >
                      <div className="truncate text-sm font-medium text-slate-900">
                        {m.company}
                      </div>
                      <div className="truncate text-xs text-slate-500">
                        {m.title}
                      </div>
                    </Link>
                  ))
                )}
              </div>
            </div>

            {STATUS_COLUMNS.map((col) => {
              const items = byStatus(col.status);
              return (
                <div
                  key={col.status}
                  className="rounded-lg border border-slate-200 bg-slate-50 p-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-slate-700">
                      {col.label}
                    </span>
                    <span className="text-xs text-slate-400">
                      {items.length}
                    </span>
                  </div>
                  <div className="mt-2 space-y-2">
                    {items.length === 0 ? (
                      <p className="text-xs text-slate-400">—</p>
                    ) : (
                      items.map((m) => <MessageCard key={m.id} m={m} />)
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Outcomes band */}
          <h2 className="mt-10 text-lg font-semibold text-slate-900">
            Outcomes
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Real-world results you reported after reaching out manually.
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {OUTCOMES.map((o) => {
              const items = byOutcome(o);
              return (
                <div
                  key={o}
                  className="rounded-lg border border-slate-200 bg-white p-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium capitalize text-slate-600">
                      {o.replace(/_/g, " ")}
                    </span>
                    <span className="text-sm font-bold text-slate-900">
                      {items.length}
                    </span>
                  </div>
                  <div className="mt-2 space-y-1">
                    {items.length === 0 ? (
                      <p className="text-xs text-slate-300">No events yet</p>
                    ) : (
                      items.slice(0, 5).map((m) => (
                        <div
                          key={m.id}
                          className="truncate text-xs text-slate-500"
                        >
                          {m.company}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
