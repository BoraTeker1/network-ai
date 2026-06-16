"use client";

import { useState } from "react";
import {
  api,
  EmailDraft,
  OUTCOMES,
  FOLLOW_UP_STATUSES,
} from "@/lib/api";
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
  const [subject, setSubject] = useState(email.subject ?? "");
  const [body, setBody] = useState(email.body ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [gmailMsg, setGmailMsg] = useState<string | null>(null);

  async function run(fn: () => Promise<EmailDraft>) {
    setBusy(true);
    setError(null);
    try {
      onUpdated(await fn());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`);
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
      setGmailMsg(e instanceof Error ? e.message : "Gmail unavailable");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      {/* Proposal header */}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-xs font-semibold uppercase tracking-wide text-blue-700">
            AI proposes emailing this person
          </div>
          <div className="mt-0.5 text-sm font-semibold text-slate-900">
            {email.contact_name || "Unknown contact"}
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
              {email.llm_used ? "✨ Written by AI" : "Template (no LLM)"}
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
          <span className="font-medium">Why this contact:</span>{" "}
          {email.contact_why_relevant}
        </p>
      )}

      {/* Subject + body (editable) */}
      <div className="mt-3">
        <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Subject
        </label>
        <input
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        />
      </div>
      <div className="mt-2">
        <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Body ({body.split(/\s+/).filter(Boolean).length} words)
        </label>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          className="mt-1 h-40 w-full rounded-md border border-slate-300 p-2 text-sm focus:border-blue-500 focus:outline-none"
        />
      </div>

      {email.personalization_notes && (
        <p className="mt-2 text-xs text-slate-500">
          <span className="font-medium">Personalization notes:</span>{" "}
          {email.personalization_notes}
        </p>
      )}

      {/* Why this is safe + what to do next */}
      {(email.why_safe || email.suggested_next_step) && (
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {email.why_safe && (
            <p className="rounded-md bg-green-50 p-2 text-xs text-green-800">
              <span className="font-medium">🛡️ Why this is safe:</span>{" "}
              {email.why_safe}
            </p>
          )}
          {email.suggested_next_step && (
            <p className="rounded-md bg-blue-50 p-2 text-xs text-blue-800">
              <span className="font-medium">→ Suggested next step:</span>{" "}
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
          className="rounded border border-slate-300 px-3 py-1.5 text-sm hover:border-blue-400 disabled:opacity-50"
        >
          Save Edit
        </button>
        <button
          disabled={busy}
          onClick={() => run(() => api.approveEmail(email.id))}
          className="rounded bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
        >
          Approve
        </button>
        <button
          disabled={busy}
          onClick={() => run(() => api.rejectEmail(email.id))}
          className="rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
        >
          Reject
        </button>
        <button
          disabled={busy}
          onClick={handleCopy}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          Copy Email
        </button>
        <button
          disabled={busy}
          onClick={() => run(() => api.markEmailSentManual(email.id))}
          className="rounded bg-purple-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
        >
          Mark Sent Manually
        </button>
        <button
          onClick={handleGmail}
          title="Gmail sending requires OAuth configuration. Manual copy is available."
          className="cursor-not-allowed rounded border border-dashed border-slate-300 px-3 py-1.5 text-sm text-slate-400"
        >
          Send via Gmail (disabled)
        </button>
      </div>
      {gmailMsg && (
        <p className="mt-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-700">
          {gmailMsg}
        </p>
      )}

      {/* Outcome + follow-up tracking */}
      <div className="mt-3 border-t border-slate-100 pt-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          After you reach out — track it
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          {OUTCOMES.map((o) => (
            <button
              key={o}
              disabled={busy}
              onClick={() => run(() => api.patchEmail(email.id, { outcome: o }))}
              className={`rounded-full border px-3 py-1 text-xs disabled:opacity-50 ${
                email.outcome === o
                  ? "border-blue-500 bg-blue-50 font-medium text-blue-700"
                  : "border-slate-300 text-slate-600 hover:border-blue-400"
              }`}
            >
              {o.replace(/_/g, " ")}
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
              {s.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
