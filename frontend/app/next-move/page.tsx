"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  api,
  ApiError,
  EmailDraft,
  Message,
  NextMoveAnalysis,
} from "@/lib/api";
import UpgradeCallout from "@/components/UpgradeCallout";
import {
  PageHeader,
  ErrorBanner,
  QualityChecklist,
  TrustLine,
  WorkflowHint,
} from "@/components/ui";
import { useT } from "@/lib/i18n";

const INTENT_STYLE: Record<string, string> = {
  positive: "bg-green-100 text-green-800",
  neutral: "bg-slate-100 text-slate-600",
  negative: "bg-rose-100 text-rose-700",
  referral_possible: "bg-emerald-100 text-emerald-800",
  interview_related: "bg-blue-100 text-blue-800",
  asks_for_resume: "bg-indigo-100 text-indigo-800",
  asks_for_work_authorization: "bg-amber-100 text-amber-800",
  needs_follow_up: "bg-purple-100 text-purple-800",
};
const URGENCY_STYLE: Record<string, string> = {
  high: "bg-rose-100 text-rose-700",
  medium: "bg-amber-100 text-amber-800",
  low: "bg-slate-100 text-slate-600",
};

function label(s: string): string {
  return s.replace(/_/g, " ");
}

export default function NextMovePage() {
  const t = useT();

  const [replyText, setReplyText] = useState("");
  const [linkedKey, setLinkedKey] = useState(""); // "message:12" | "email:3" | ""
  const [messages, setMessages] = useState<Message[]>([]);
  const [emails, setEmails] = useState<EmailDraft[]>([]);

  const [analysis, setAnalysis] = useState<NextMoveAnalysis | null>(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [shortMsg, setShortMsg] = useState("");

  const [analyzing, setAnalyzing] = useState(false);
  const [busyOutcome, setBusyOutcome] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [planLimit, setPlanLimit] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    api.getMessages().then(setMessages).catch(() => {});
    api.getEmails().then(setEmails).catch(() => {});
    // Deep link from a tracked application ("Analyze reply" on a pipeline
    // card): ?item=message:<id> preselects that item. Read from
    // window.location so the client page needs no Suspense boundary.
    const item = new URLSearchParams(window.location.search).get("item");
    if (item && /^(message|email):\d+$/.test(item)) setLinkedKey(item);
  }, []);

  const linkOptions = useMemo(() => {
    const opts: { key: string; label: string }[] = [];
    for (const m of messages) {
      opts.push({
        key: `message:${m.id}`,
        label: `${t.nextMove.messagePrefix} · ${m.company || "—"} · ${label(m.message_type)}`,
      });
    }
    for (const e of emails) {
      opts.push({
        key: `email:${e.id}`,
        label: `${t.nextMove.emailPrefix} · ${e.company || "—"} · ${e.contact_name || t.nextMove.contactFallback}`,
      });
    }
    return opts;
  }, [messages, emails, t]);

  function buildInput() {
    const input: {
      reply_text: string;
      message_id?: number;
      email_id?: number;
    } = { reply_text: replyText };
    if (linkedKey.startsWith("message:")) {
      input.message_id = Number(linkedKey.split(":")[1]);
    } else if (linkedKey.startsWith("email:")) {
      input.email_id = Number(linkedKey.split(":")[1]);
    }
    return input;
  }

  async function analyze() {
    if (!replyText.trim()) {
      setError(t.nextMove.pasteFirst);
      return;
    }
    setAnalyzing(true);
    setError(null);
    setNotice(null);
    try {
      const a = await api.analyzeNextMove(buildInput());
      setAnalysis(a);
      setSubject(a.drafted_email.subject);
      setBody(a.drafted_email.body);
      setShortMsg(a.drafted_short_message);
    } catch (e) {
      if (e instanceof ApiError && e.code === "plan_limit") {
        setPlanLimit(e.message);
      } else {
        setError(e instanceof Error ? e.message : t.nextMove.analysisFailed);
      }
    } finally {
      setAnalyzing(false);
    }
  }

  async function copy(text: string, what: string) {
    try {
      await navigator.clipboard.writeText(text);
      setNotice(t.nextMove.copiedNotice(what));
    } catch {
      setError(t.nextMove.clipboardBlocked);
    }
  }

  async function applyOutcome(outcome: string) {
    if (!analysis) return;
    const target = analysis.pipeline_target;
    if (!target.type || target.id == null) return;
    setBusyOutcome(true);
    setError(null);
    try {
      if (target.type === "message") await api.setOutcome(target.id, outcome);
      else await api.patchEmail(target.id, { outcome });
      setNotice(t.nextMove.pipelineUpdated((t.ui.outcome as Record<string, string>)[outcome] ?? label(outcome)));
    } catch (e) {
      setError(e instanceof Error ? e.message : t.nextMove.updateFailed);
    } finally {
      setBusyOutcome(false);
    }
  }

  const canLogOutcome = !!analysis?.pipeline_target.type;

  return (
    <div>
      <PageHeader title={t.nextMove.title} subtitle={t.nextMove.subtitle} />

      <div className="mt-4 space-y-3">
        <WorkflowHint>
          {t.nextMove.hintPre}
          <strong>{t.nextMove.hintStrong}</strong>
          {t.nextMove.hintPost}
        </WorkflowHint>
        <TrustLine />
      </div>

      {/* Input */}
      <section className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t.nextMove.pasteLabel}
        </label>
        <textarea
          value={replyText}
          onChange={(e) => setReplyText(e.target.value)}
          placeholder={t.nextMove.pastePh}
          className="mt-1 h-32 w-full rounded-md border border-slate-300 p-2 text-sm focus:border-brand-500 focus:outline-none"
        />
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <div className="min-w-0">
            <label className="text-xs font-medium text-slate-500">
              {t.nextMove.linkLabel}
            </label>
            {linkOptions.length === 0 ? (
              <p className="mt-1 w-72 max-w-full rounded-md border border-dashed border-slate-300 px-2 py-2 text-xs text-slate-500">
                {t.nextMove.noTrackedPre}
                <Link href="/pipeline" className="font-medium text-brand-600 hover:underline">
                  {t.nextMove.noTrackedLink}
                </Link>
                {t.nextMove.noTrackedPost}
              </p>
            ) : (
              <select
                value={linkedKey}
                onChange={(e) => setLinkedKey(e.target.value)}
                className="mt-1 block w-72 max-w-full rounded-md border border-slate-300 px-2 py-2 text-sm focus:border-brand-500 focus:outline-none"
              >
                <option value="">{t.nextMove.noLinkedItem}</option>
                {linkOptions.map((o) => (
                  <option key={o.key} value={o.key}>
                    {o.label}
                  </option>
                ))}
              </select>
            )}
          </div>
          <button
            onClick={analyze}
            disabled={analyzing}
            className="mt-5 rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {analyzing ? t.nextMove.analyzing : t.nextMove.analyzeBtn}
          </button>
        </div>
      </section>

      <ErrorBanner message={error} />
      {planLimit && <UpgradeCallout message={planLimit} />}
      {notice && (
        <p className="mt-3 rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
          {notice}
        </p>
      )}

      {analysis && (
        <div className="mt-6 space-y-4">
          {/* Summary + intent */}
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t.nextMove.replySummary}
              </div>
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  analysis.llm_used
                    ? "bg-violet-100 text-violet-700"
                    : "bg-slate-100 text-slate-600"
                }`}
              >
                {analysis.llm_used ? t.nextMove.analyzedByAI : t.nextMove.deterministic}
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-700">{analysis.summary}</p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  INTENT_STYLE[analysis.intent] ?? "bg-slate-100 text-slate-600"
                }`}
              >
                {(t.nextMove.intent as Record<string, string>)[analysis.intent] ?? label(analysis.intent)}
              </span>
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  URGENCY_STYLE[analysis.urgency] ?? "bg-slate-100 text-slate-600"
                }`}
              >
                {t.nextMove.urgencyLabel((t.nextMove.urgency as Record<string, string>)[analysis.urgency] ?? analysis.urgency)}
              </span>
              {analysis.signals
                .filter((s) => s !== analysis.intent)
                .map((s) => (
                  <span
                    key={s}
                    className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500"
                  >
                    {(t.nextMove.intent as Record<string, string>)[s] ?? label(s)}
                  </span>
                ))}
            </div>
          </section>

          {/* Recommended next move */}
          <section className="rounded-lg border border-brand-100 bg-brand-50 p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-brand-700">
              {t.nextMove.recommendedNext}
            </div>
            <p className="mt-1 text-sm text-slate-700">
              {analysis.recommended_next_action}
            </p>
            {analysis.risk_notes && (
              <p className="mt-2 text-xs text-slate-500">
                <span className="font-medium">{t.nextMove.riskNotes}</span>{" "}
                {analysis.risk_notes}
              </p>
            )}
          </section>

          {/* Drafted response */}
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t.nextMove.draftedResponse}
            </div>

            <div className="mt-3 grid gap-4 lg:grid-cols-2">
              {/* Email-style */}
              <div>
                <div className="text-xs font-medium text-slate-500">{t.nextMove.emailStyle}</div>
                <input
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                />
                <textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  className="mt-2 h-44 w-full rounded-md border border-slate-300 p-2 text-sm focus:border-brand-500 focus:outline-none"
                />
                <button
                  onClick={() => copy(`Subject: ${subject}\n\n${body}`, t.nextMove.whatEmail)}
                  className="mt-2 rounded-full bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
                >
                  {t.nextMove.copyEmail}
                </button>
              </div>

              {/* Short-message style */}
              <div>
                <div className="text-xs font-medium text-slate-500">
                  {t.nextMove.linkedinStyle}
                </div>
                <textarea
                  value={shortMsg}
                  onChange={(e) => setShortMsg(e.target.value)}
                  className="mt-1 h-44 w-full rounded-md border border-slate-300 p-2 text-sm focus:border-brand-500 focus:outline-none"
                />
                <button
                  onClick={() => copy(shortMsg, t.nextMove.whatMessage)}
                  className="mt-2 rounded-full bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
                >
                  {t.nextMove.copyMessage}
                </button>
              </div>
            </div>

            <div className="mt-4 grid gap-2 sm:grid-cols-2">
              <QualityChecklist checklist={analysis.quality_checklist} />
              <QualityChecklist checklist={analysis.safety_checklist} />
            </div>
          </section>

          {/* Log outcome */}
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t.nextMove.logOutcome}
              </div>
              {analysis.suggested_pipeline_update && (
                <span className="text-xs text-slate-500">
                  {t.nextMove.suggestedLabel}{" "}
                  <span className="font-medium text-slate-700">
                    {(t.ui.outcome as Record<string, string>)[analysis.suggested_pipeline_update] ?? label(analysis.suggested_pipeline_update)}
                  </span>
                </span>
              )}
            </div>

            {!canLogOutcome ? (
              <p className="mt-2 text-sm text-slate-500">
                {t.nextMove.linkToLog}
              </p>
            ) : (
              <div className="mt-2 flex flex-wrap gap-2">
                {([
                  { outcome: "replied", label: t.nextMove.markReplied },
                  { outcome: "referral_received", label: t.nextMove.markReferral },
                  { outcome: "interview_received", label: t.nextMove.markInterview },
                ] as { outcome: string; label: string }[]).map((b) => {
                  const suggested =
                    analysis.suggested_pipeline_update === b.outcome;
                  return (
                    <button
                      key={b.outcome}
                      disabled={busyOutcome}
                      onClick={() => applyOutcome(b.outcome)}
                      className={`rounded-md px-3 py-1.5 text-sm font-medium disabled:opacity-50 ${
                        suggested
                          ? "bg-green-600 text-white hover:bg-green-700"
                          : "border border-slate-300 text-slate-700 hover:border-brand-400"
                      }`}
                    >
                      {b.label}
                    </button>
                  );
                })}
              </div>
            )}
            <p className="mt-3 text-xs text-slate-400">
              {t.nextMove.loggingNote}
            </p>
          </section>
        </div>
      )}
    </div>
  );
}
