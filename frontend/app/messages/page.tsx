"use client";

import { useEffect, useState } from "react";
import { api, Message, OUTCOMES, FOLLOW_UP_STATUSES } from "@/lib/api";
import {
  EmptyState,
  ErrorBanner,
  StatusBadge,
  OutcomeBadge,
  ToneBadge,
  FollowUpBadge,
  QualityChecklist,
  WhyNotSpam,
  PageHeader,
} from "@/components/ui";

const CONNECTION_LIMIT = 280;

// Default a "follow up needed" reminder to one week out (client-side only).
function defaultDueDate(): string {
  const d = new Date();
  d.setDate(d.getDate() + 7);
  return d.toISOString().slice(0, 10);
}

export default function MessagesPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function load() {
    setLoading(true);
    try {
      const msgs = await api.getMessages();
      setMessages(msgs);
      setDrafts(Object.fromEntries(msgs.map((m) => [m.id, m.draft_text ?? ""])));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load messages");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function replace(updated: Message) {
    setMessages((prev) => prev.map((m) => (m.id === updated.id ? updated : m)));
  }

  async function run(id: number, fn: () => Promise<Message>) {
    setBusyId(id);
    setError(null);
    try {
      replace(await fn());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusyId(null);
    }
  }

  async function handleCopy(m: Message) {
    const text = drafts[m.id] ?? m.draft_text ?? "";
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Clipboard may be blocked; still mark copied so the workflow proceeds.
    }
    await run(m.id, () => api.markCopied(m.id));
  }

  if (loading) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <div>
      <PageHeader
        title="Messages"
        subtitle="AI proposed these drafts. Review, edit, approve, copy, then send manually on LinkedIn. Nothing is auto-sent."
      />

      <div className="mt-4">
        <WhyNotSpam compact />
      </div>

      <ErrorBanner message={error} />

      {messages.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            title="No outreach drafts yet"
            description="Open a job from your matches and click “Generate Outreach Drafts” to create connection, recruiter, engineer, and alumni-style messages."
            ctaHref="/matches"
            ctaLabel="Go to matches →"
          />
        </div>
      ) : (
        <div className="mt-6 space-y-4">
          {messages.map((m) => {
            const text = drafts[m.id] ?? "";
            const isConnection = m.message_type === "connection_request";
            const overLimit = isConnection && text.length > CONNECTION_LIMIT;
            return (
              <div
                key={m.id}
                className="rounded-lg border border-slate-200 bg-white p-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm">
                    <span className="font-semibold text-slate-900">
                      {m.company || "Unknown company"}
                    </span>{" "}
                    <span className="text-slate-500">— {m.title || ""}</span>
                    <div className="mt-1 flex items-center gap-2">
                      <span className="text-xs uppercase tracking-wide text-slate-400">
                        {m.message_type.replace(/_/g, " ")}
                      </span>
                      <ToneBadge tone={m.tone} />
                    </div>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1.5">
                    <div className="flex items-center gap-2">
                      {m.outcome && <OutcomeBadge outcome={m.outcome} />}
                      <StatusBadge status={m.status} />
                    </div>
                    <FollowUpBadge
                      status={m.follow_up_status}
                      dueDate={m.follow_up_due_date}
                    />
                  </div>
                </div>

                <textarea
                  className="mt-3 h-28 w-full rounded-md border border-slate-300 p-2 text-sm focus:border-blue-500 focus:outline-none"
                  value={text}
                  onChange={(e) =>
                    setDrafts((d) => ({ ...d, [m.id]: e.target.value }))
                  }
                />
                <div
                  className={`mt-1 text-right text-xs ${
                    overLimit ? "font-medium text-red-600" : "text-slate-400"
                  }`}
                >
                  {text.length}
                  {isConnection ? ` / ${CONNECTION_LIMIT}` : ""} chars
                </div>

                <div className="mt-3">
                  <QualityChecklist checklist={m.checklist} />
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    disabled={busyId === m.id}
                    onClick={() => run(m.id, () => api.patchMessage(m.id, text))}
                    className="rounded border border-slate-300 px-3 py-1.5 text-sm hover:border-blue-400 disabled:opacity-50"
                  >
                    Save Edit
                  </button>
                  <button
                    disabled={busyId === m.id}
                    onClick={() => run(m.id, () => api.approveMessage(m.id))}
                    className="rounded bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
                  >
                    Approve
                  </button>
                  <button
                    disabled={busyId === m.id}
                    onClick={() => run(m.id, () => api.rejectMessage(m.id))}
                    className="rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                  >
                    Reject
                  </button>
                  <button
                    disabled={busyId === m.id}
                    onClick={() => handleCopy(m)}
                    className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    Copy
                  </button>
                  <button
                    disabled={busyId === m.id}
                    onClick={() => run(m.id, () => api.markSentManually(m.id))}
                    className="rounded bg-purple-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
                  >
                    Mark Sent Manually
                  </button>
                </div>

                {/* Outcome tracking — what happened after you reached out */}
                <div className="mt-3 border-t border-slate-100 pt-3">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    After you sent it — track the outcome
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {OUTCOMES.map((o) => (
                      <button
                        key={o}
                        disabled={busyId === m.id}
                        onClick={() => run(m.id, () => api.setOutcome(m.id, o))}
                        className={`rounded-full border px-3 py-1 text-xs disabled:opacity-50 ${
                          m.outcome === o
                            ? "border-blue-500 bg-blue-50 font-medium text-blue-700"
                            : "border-slate-300 text-slate-600 hover:border-blue-400"
                        }`}
                      >
                        {o.replace(/_/g, " ")}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Follow-up tracking */}
                <div className="mt-3 border-t border-slate-100 pt-3">
                  <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Follow-up
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    {FOLLOW_UP_STATUSES.map((s) => (
                      <button
                        key={s}
                        disabled={busyId === m.id}
                        onClick={() =>
                          run(m.id, () =>
                            api.setFollowUp(
                              m.id,
                              s,
                              s === "follow_up_needed" ? defaultDueDate() : null
                            )
                          )
                        }
                        className={`rounded-full border px-3 py-1 text-xs disabled:opacity-50 ${
                          m.follow_up_status === s
                            ? "border-amber-500 bg-amber-50 font-medium text-amber-700"
                            : "border-slate-300 text-slate-600 hover:border-amber-400"
                        }`}
                      >
                        {s.replace(/_/g, " ")}
                      </button>
                    ))}
                    {m.follow_up_status && (
                      <button
                        disabled={busyId === m.id}
                        onClick={() => run(m.id, () => api.setFollowUp(m.id, "none"))}
                        className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-400 hover:border-slate-400 disabled:opacity-50"
                      >
                        clear
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
