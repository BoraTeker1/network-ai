"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Message, OUTCOMES } from "@/lib/api";
import {
  EmptyState,
  ErrorBanner,
  OutcomeBadge,
  FollowUpBadge,
  StatusBadge,
  PageHeader,
  Card,
  Button,
} from "@/components/ui";
import { useT } from "@/lib/i18n";
import type { Dict } from "@/lib/i18n/en";

const chip = "rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600";

function relativeTime(t: Dict, iso: string | null): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const mins = Math.round((Date.now() - then) / 60000);
  if (mins < 1) return t.pipeline.justNow;
  if (mins < 60) return t.pipeline.minsAgo(mins);
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return t.pipeline.hrsAgo(hrs);
  return t.pipeline.daysAgoShort(Math.round(hrs / 24));
}

function channelLabel(t: Dict, m: Message): string {
  if (m.channel === "linkedin") return t.outreach.channel.linkedin;
  if (m.channel === "email") return t.outreach.channel.email;
  return m.message_type.replace(/_/g, " ");
}

function OutreachCard({
  m,
  onUpdated,
  onError,
}: {
  m: Message;
  onUpdated: (updated: Message) => void;
  onError: (msg: string) => void;
}) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  async function act(fn: () => Promise<Message>) {
    setBusy(true);
    try {
      onUpdated(await fn());
    } catch (e) {
      onError(e instanceof Error ? e.message : t.pipeline.actionFailed);
    } finally {
      setBusy(false);
    }
  }

  async function copyDraft() {
    const text = m.subject ? `Subject: ${m.subject}\n\n${m.draft_text ?? ""}` : m.draft_text ?? "";
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      onError(t.pipeline.clipboardBlocked);
    }
  }

  const preview = (m.draft_text ?? "").slice(0, 140);
  const updated = relativeTime(t, m.updated_at);

  return (
    <Card hover className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-base font-semibold leading-tight text-slate-900">
            {m.title || t.pipeline.outreachDraft}
          </div>
          <div className="mt-0.5 text-sm text-slate-600">
            <span className="font-medium text-slate-700">{m.company || t.pipeline.unknownCompany}</span>
            {m.contact_name ? t.pipeline.toContact(m.contact_name) : ""}
          </div>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <div className="flex flex-wrap items-center justify-end gap-1.5">
            <StatusBadge status={m.status} />
            {m.outcome && <OutcomeBadge outcome={m.outcome} />}
          </div>
          {updated && <span className="text-xs text-slate-400">{t.pipeline.updatedAgo(updated)}</span>}
        </div>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <span className={chip}>{channelLabel(t, m)}</span>
        {m.language && <span className={chip}>{m.language === "tr" ? "Türkçe" : "English"}</span>}
        {m.follow_up_status && (
          <FollowUpBadge status={m.follow_up_status} dueDate={m.follow_up_due_date} />
        )}
        {m.job_url && (
          <a
            href={m.job_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-brand-600 hover:underline"
          >
            {t.pipeline.openRole}
          </a>
        )}
      </div>

      {/* Draft preview / full view */}
      {preview && (
        <div className="mt-2 rounded-md bg-slate-50 px-3 py-2">
          {open ? (
            <>
              {m.subject && (
                <p className="text-xs font-medium text-slate-700">{t.pipeline.subjectPrefix} {m.subject}</p>
              )}
              <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{m.draft_text}</p>
            </>
          ) : (
            <p className="text-sm text-slate-500">
              {preview}
              {(m.draft_text ?? "").length > 140 ? "…" : ""}
            </p>
          )}
        </div>
      )}

      {/* Actions — all manual, nothing is ever sent for you */}
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
        <Button variant="secondary" size="sm" onClick={() => setOpen((v) => !v)}>
          {open ? t.pipeline.hideDraft : t.pipeline.viewDraft}
        </Button>
        <Button variant="secondary" size="sm" onClick={copyDraft}>
          {copied ? t.common.copied : t.pipeline.copyDraft}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          disabled={busy}
          onClick={() => act(() => api.markSentManually(m.id))}
        >
          {t.pipeline.markSent}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          disabled={busy}
          onClick={() => act(() => api.setOutcome(m.id, "replied"))}
        >
          {t.pipeline.markReplied}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          disabled={busy}
          onClick={() => act(() => api.setFollowUp(m.id, "follow_up_needed"))}
        >
          {t.pipeline.needsFollowUp}
        </Button>
      </div>
    </Card>
  );
}

export default function PipelinePage() {
  const t = useT();
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getMessages()
      .then(setMessages)
      .catch((e) => setError(e instanceof Error ? e.message : t.pipeline.loadFailed))
      .finally(() => setLoading(false));
  }, []);

  function applyUpdate(updated: Message) {
    setMessages((prev) => prev.map((m) => (m.id === updated.id ? { ...m, ...updated } : m)));
  }

  if (loading) return <p className="text-sm text-slate-500">{t.common.loading}</p>;

  const followUpsDue = messages.filter((m) => m.follow_up_status === "follow_up_needed");
  const byOutcome = (outcome: string) => messages.filter((m) => m.outcome === outcome);

  return (
    <div>
      <PageHeader title={t.pipeline.title} subtitle={t.pipeline.subtitle} />

      <ErrorBanner message={error} />

      {messages.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            title={t.pipeline.emptyTitle}
            description={t.pipeline.emptyDesc}
            ctaHref="/opportunities"
            ctaLabel={t.pipeline.emptyCta}
          />
        </div>
      ) : (
        <>
          {/* Follow-ups due band */}
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3">
            <div className="text-xs font-semibold uppercase tracking-wide text-amber-700">
              {t.pipeline.followUpsDue(followUpsDue.length)}
            </div>
            {followUpsDue.length === 0 ? (
              <p className="mt-1 text-sm text-amber-700">
                {t.pipeline.noFollowUpsYet}
              </p>
            ) : (
              <div className="mt-2 flex flex-wrap gap-2">
                {followUpsDue.map((m) => (
                  <span
                    key={m.id}
                    className="rounded-md border border-amber-300 bg-white px-2.5 py-1 text-xs text-slate-700"
                  >
                    {m.company || t.pipeline.unknown}
                    {m.follow_up_due_date ? t.ui.dueDate(m.follow_up_due_date) : ""}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Outreach tracker */}
          <div className="mt-6 space-y-3">
            {messages.map((m) => (
              <OutreachCard
                key={m.id}
                m={m}
                onUpdated={applyUpdate}
                onError={setError}
              />
            ))}
          </div>

          {/* Got a reply? */}
          <div className="mt-6 rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600">
            {t.pipeline.gotReplyPre}
            <Link href="/next-move" className="font-medium text-brand-600 hover:underline">
              {t.pipeline.gotReplyLink}
            </Link>
            {t.pipeline.gotReplyPost}
          </div>

          {/* Outcomes summary */}
          <h2 className="mt-10 text-lg font-semibold text-slate-900">{t.pipeline.outcomesTitle}</h2>
          <p className="mt-1 text-sm text-slate-500">
            {t.pipeline.outcomesSubtitle}
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {OUTCOMES.map((o) => {
              const items = byOutcome(o);
              return (
                <div key={o} className="rounded-lg border border-slate-200 bg-white p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium capitalize text-slate-600">
                      {(t.ui.outcome as Record<string, string>)[o] ?? o.replace(/_/g, " ")}
                    </span>
                    <span className="text-sm font-bold text-slate-900">{items.length}</span>
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
