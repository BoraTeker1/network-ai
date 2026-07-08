"use client";

import { useState } from "react";
import {
  api,
  EmailDraft,
  OUTCOMES,
  FOLLOW_UP_STATUSES,
} from "@/lib/api";
import { useT } from "@/lib/i18n";
import {
  StatusBadge,
  OutcomeBadge,
  FollowUpBadge,
  QualityChecklist,
} from "@/components/ui";

function defaultDueDate(): string {
  const d = new Date();
  d.setDate(d.getDate() + 7);
  return d.toISOString().slice(0, 10);
}

/** A single AI-proposed email, rendered Cursor-style: proposal + why + review.
 *  Nothing here can auto-send — Gmail is intentionally disabled. */
export default function EmailDraftCard({
  email,
  onUpdated,
}: {
  email: EmailDraft;
  onUpdated: (e: EmailDraft) => void;
}) {
  const t = useT();
  const [subject, setSubject] = useState(email.subject ?? "");
  const [body, setBody] = useState(email.body ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [gmailMsg, setGmailMsg] = useState<string | null>(null);

  // LinkedIn drafts are stored as EmailDraft rows but render differently: no
  // subject line, a character counter (LinkedIn caps connection notes at 300),
  // and copy/send chrome tuned for pasting into LinkedIn yourself.
  const isLinkedIn = (email.message_type ?? "").startsWith("linkedin");
  const isConnection = email.message_type === "linkedin_connection";
  const charLimit = isConnection ? 300 : 600;
  const overLimit = isLinkedIn && body.length > charLimit;
  const channelLabel = isConnection
    ? t.emailCard.channelConnection
    : isLinkedIn
    ? t.emailCard.channelMessage
    : t.emailCard.channelEmail;

  async function run(fn: () => Promise<EmailDraft>) {
    setBusy(true);
    setError(null);
    try {
      const updated = await fn();
      onUpdated(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : t.emailCard.actionFailed);
    } finally {
      setBusy(false);
    }
  }

  async function handleCopy() {
    // LinkedIn has no subject — copy the body alone so it pastes cleanly.
    const clip = isLinkedIn ? body : `Subject: ${subject}\n\n${body}`;
    try {
      await navigator.clipboard.writeText(clip);
    } catch {
      /* clipboard may be blocked; still record the copy */
    }
    await run(() => api.markEmailCopied(email.id));
  }

  async function handleGmail() {
    setBusy(true);
    try {
      const r = await api.sendEmailGmail(email.id, true);
      setGmailMsg(r.message);
    } catch (e) {
      setGmailMsg(e instanceof Error ? e.message : t.emailCard.gmailUnavailable);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      {/* Proposal header */}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-xs font-semibold uppercase tracking-wide text-brand-700">
            {isLinkedIn
              ? t.emailCard.proposesChannel(channelLabel)
              : t.emailCard.proposesEmail}
          </div>
          <div className="mt-0.5 text-sm font-semibold text-slate-900">
            {email.contact_name || t.emailCard.unknownContact}
            {email.contact_title ? ` · ${email.contact_title}` : ""}
          </div>
          <div className="text-xs text-slate-500">
            {email.company || "—"}
            {email.role ? ` · ${email.role}` : ""}
            {email.contact_email ? ` · ${email.contact_email}` : ""}
          </div>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1.5">
          <div className="flex items-center gap-2">
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                email.llm_used
                  ? "bg-violet-100 text-violet-700"
                  : "bg-slate-100 text-slate-600"
              }`}
            >
              {email.llm_used ? t.emailCard.writtenByAI : t.emailCard.template}
            </span>
            <StatusBadge status={email.status} />
          </div>
          {email.outcome && <OutcomeBadge outcome={email.outcome} />}
          <FollowUpBadge
            status={email.follow_up_status}
            dueDate={email.follow_up_due_date}
          />
        </div>
      </div>

      {/* Why this contact */}
      {email.contact_why_relevant && (
        <p className="mt-2 rounded-md bg-slate-50 p-2 text-xs text-slate-600">
          <span className="font-medium">{t.emailCard.whyContact}</span>{" "}
          {email.contact_why_relevant}
        </p>
      )}

      {/* Subject + body (editable). LinkedIn drafts have no subject. */}
      {!isLinkedIn && (
        <div className="mt-3">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t.emailCard.subject}
          </label>
          <input
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
          />
        </div>
      )}
      <div className="mt-2">
        <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {isLinkedIn ? (
            <>
              {t.emailCard.message}{" "}
              <span className={overLimit ? "text-red-600" : "text-slate-400"}>
                {t.emailCard.chars(body.length, charLimit)}
              </span>
            </>
          ) : (
            <>{t.emailCard.bodyWords(body.split(/\s+/).filter(Boolean).length)}</>
          )}
        </label>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          className={`mt-1 h-40 w-full rounded-md border p-2 text-sm focus:outline-none ${
            overLimit
              ? "border-red-400 focus:border-red-500"
              : "border-slate-300 focus:border-brand-500"
          }`}
        />
        {overLimit && (
          <p className="mt-1 text-xs text-red-600">
            {isConnection
              ? t.emailCard.overLimitConnection
              : t.emailCard.overLimitMessage}
          </p>
        )}
      </div>

      {email.personalization_notes && (
        <p className="mt-2 text-xs text-slate-500">
          <span className="font-medium">{t.emailCard.personalizationNotes}</span>{" "}
          {email.personalization_notes}
        </p>
      )}

      {/* Why this is safe + what to do next */}
      {(email.why_safe || email.suggested_next_step) && (
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {email.why_safe && (
            <p className="rounded-md bg-green-50 p-2 text-xs text-green-800">
              <span className="font-medium">{t.emailCard.whySafe}</span>{" "}
              {email.why_safe}
            </p>
          )}
          {email.suggested_next_step && (
            <p className="rounded-md bg-brand-50 p-2 text-xs text-brand-800">
              <span className="font-medium">{t.emailCard.suggestedNext}</span>{" "}
              {email.suggested_next_step}
            </p>
          )}
        </div>
      )}

      {/* Checklists */}
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        <QualityChecklist checklist={email.quality_checklist} />
        <QualityChecklist checklist={email.risk_checklist} />
      </div>

      {error && (
        <p className="mt-2 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {/* Actions */}
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          disabled={busy}
          onClick={() => run(() => api.patchEmail(email.id, { subject, body }))}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm hover:border-brand-400 disabled:opacity-50"
        >
          {t.emailCard.saveEdit}
        </button>
        <button
          disabled={busy}
          onClick={() => run(() => api.approveEmail(email.id))}
          className="rounded bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
        >
          {t.emailCard.approve}
        </button>
        <button
          disabled={busy}
          onClick={() => run(() => api.rejectEmail(email.id))}
          className="rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
        >
          {t.emailCard.reject}
        </button>
        <button
          disabled={busy}
          onClick={handleCopy}
          className="rounded-full bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {isLinkedIn ? (isConnection ? t.emailCard.copyNote : t.emailCard.copyMessage) : t.emailCard.copyEmail}
        </button>
        <button
          disabled={busy}
          onClick={() => run(() => api.markEmailSentManual(email.id))}
          className="rounded bg-purple-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
        >
          {isLinkedIn ? t.emailCard.markSentLinkedIn : t.emailCard.markSentManually}
        </button>
        {/* Gmail send only applies to email drafts. */}
        {!isLinkedIn && (
          <button
            onClick={handleGmail}
            title={t.emailCard.gmailTooltip}
            className="cursor-not-allowed rounded border border-dashed border-slate-300 px-3 py-1.5 text-sm text-slate-400"
          >
            {t.emailCard.gmailDisabled}
          </button>
        )}
      </div>
      {gmailMsg && (
        <p className="mt-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-700">
          {gmailMsg}
        </p>
      )}

      {/* Outcome + follow-up tracking */}
      <div className="mt-3 border-t border-slate-100 pt-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t.emailCard.trackHeader}
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          {OUTCOMES.map((o) => (
            <button
              key={o}
              disabled={busy}
              onClick={() => run(() => api.patchEmail(email.id, { outcome: o }))}
              className={`rounded-full border px-3 py-1 text-xs disabled:opacity-50 ${
                email.outcome === o
                  ? "border-brand-500 bg-brand-50 font-medium text-brand-700"
                  : "border-slate-300 text-slate-600 hover:border-brand-400"
              }`}
            >
              {(t.ui.outcome as Record<string, string>)[o] ?? o.replace(/_/g, " ")}
            </button>
          ))}
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          {FOLLOW_UP_STATUSES.map((s) => (
            <button
              key={s}
              disabled={busy}
              onClick={() =>
                run(() =>
                  api.patchEmail(email.id, {
                    follow_up_status: s,
                    follow_up_due_date:
                      s === "follow_up_needed" ? defaultDueDate() : null,
                  })
                )
              }
              className={`rounded-full border px-3 py-1 text-xs disabled:opacity-50 ${
                email.follow_up_status === s
                  ? "border-amber-500 bg-amber-50 font-medium text-amber-700"
                  : "border-slate-300 text-slate-600 hover:border-amber-400"
              }`}
            >
              {(t.ui.followUp as Record<string, string>)[s] ?? s.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
