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
import { useMomentum } from "@/components/MomentumProvider";

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

// The outcomes Next Move can confirm into the pipeline.
const OUTCOME_BUTTONS: { outcome: string; label: string }[] = [
  { outcome: "replied", label: "Mark Replied" },
  { outcome: "referral_received", label: "Mark Referral Received" },
  { outcome: "interview_received", label: "Mark Interview Received" },
];

function label(s: string): string {
  return s.replace(/_/g, " ");
}

export default function NextMovePage() {
  const { celebrate } = useMomentum();

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
  }, []);

  const linkOptions = useMemo(() => {
    const opts: { key: string; label: string }[] = [];
    for (const m of messages) {
      opts.push({
        key: `message:${m.id}`,
        label: `Message · ${m.company || "—"} · ${label(m.message_type)}`,
      });
    }
    for (const e of emails) {
      opts.push({
        key: `email:${e.id}`,
        label: `Email · ${e.company || "—"} · ${e.contact_name || "contact"}`,
      });
    }
    return opts;
  }, [messages, emails]);

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
      setError("Paste the reply you received first.");
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
        setError(e instanceof Error ? e.message : "Analysis failed");
      }
    } finally {
      setAnalyzing(false);
    }
  }

  async function copy(text: string, what: string) {
    try {
      await navigator.clipboard.writeText(text);
      setNotice(`${what} copied to your clipboard.`);
    } catch {
      setError("Clipboard blocked by the browser — select and copy manually.");
    }
  }

  async function applyOutcome(outcome: string) {
    if (!analysis) return;
    const target = analysis.pipeline_target;
    if (!target.type || target.id == null) return;
    setBusyOutcome(true);
    setError(null);
    try {
      const updated =
        target.type === "message"
          ? await api.setOutcome(target.id, outcome)
          : await api.patchEmail(target.id, { outcome });
      celebrate(updated.momentum);
      setNotice(`Pipeline updated → ${label(outcome)}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update outcome");
    } finally {
      setBusyOutcome(false);
    }
  }

  const canLogOutcome = !!analysis?.pipeline_target.type;

  return (
    <div>
      <PageHeader
        title="Next Move AI"
        subtitle="Got a reply from a recruiter, engineer, alumnus, or hiring manager? Paste it in. Next Move AI reads only what you paste — it never auto-reads your inbox — then summarizes the reply, detects intent, and drafts a response you review, edit, and send yourself."
      />

      <div className="mt-4 space-y-3">
        <WorkflowHint>
          Paste a reply, <strong>link it to a tracked outreach item</strong>, and get your next
          response drafted.
        </WorkflowHint>
        <TrustLine />
      </div>

      {/* Input */}
      <section className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Paste the reply you received
        </label>
        <textarea
          value={replyText}
          onChange={(e) => setReplyText(e.target.value)}
          placeholder="e.g. “Thanks for reaching out! Your background looks great — are you free for a quick call this week?”"
          className="mt-1 h-32 w-full rounded-md border border-slate-300 p-2 text-sm focus:border-blue-500 focus:outline-none"
        />
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <div className="min-w-0">
            <label className="text-xs font-medium text-slate-500">
              Link a pipeline item (optional — enables outcome + Momentum)
            </label>
            {linkOptions.length === 0 ? (
              <p className="mt-1 w-72 max-w-full rounded-md border border-dashed border-slate-300 px-2 py-2 text-xs text-slate-500">
                No tracked outreach yet.{" "}
                <Link href="/pipeline" className="font-medium text-blue-600 hover:underline">
                  Save a draft to your pipeline
                </Link>{" "}
                to link replies here.
              </p>
            ) : (
              <select
                value={linkedKey}
                onChange={(e) => setLinkedKey(e.target.value)}
                className="mt-1 block w-72 max-w-full rounded-md border border-slate-300 px-2 py-2 text-sm focus:border-blue-500 focus:outline-none"
              >
                <option value="">No linked item</option>
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
            className="mt-5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {analyzing ? "Analyzing…" : "Analyze reply"}
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
                Reply summary
              </div>
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  analysis.llm_used
                    ? "bg-violet-100 text-violet-700"
                    : "bg-slate-100 text-slate-600"
                }`}
              >
                {analysis.llm_used ? "✨ Analyzed by AI" : "Deterministic analysis"}
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-700">{analysis.summary}</p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  INTENT_STYLE[analysis.intent] ?? "bg-slate-100 text-slate-600"
                }`}
              >
                {label(analysis.intent)}
              </span>
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  URGENCY_STYLE[analysis.urgency] ?? "bg-slate-100 text-slate-600"
                }`}
              >
                urgency: {analysis.urgency}
              </span>
              {analysis.signals
                .filter((s) => s !== analysis.intent)
                .map((s) => (
                  <span
                    key={s}
                    className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500"
                  >
                    {label(s)}
                  </span>
                ))}
            </div>
          </section>

          {/* Recommended next move */}
          <section className="rounded-lg border border-blue-100 bg-blue-50 p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-blue-700">
              Recommended next move
            </div>
            <p className="mt-1 text-sm text-slate-700">
              {analysis.recommended_next_action}
            </p>
            {analysis.risk_notes && (
              <p className="mt-2 text-xs text-slate-500">
                <span className="font-medium">Risk notes:</span>{" "}
                {analysis.risk_notes}
              </p>
            )}
          </section>

          {/* Drafted response */}
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Drafted response — review &amp; edit before sending
            </div>

            <div className="mt-3 grid gap-4 lg:grid-cols-2">
              {/* Email-style */}
              <div>
                <div className="text-xs font-medium text-slate-500">Email style</div>
                <input
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                />
                <textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  className="mt-2 h-44 w-full rounded-md border border-slate-300 p-2 text-sm focus:border-blue-500 focus:outline-none"
                />
                <button
                  onClick={() => copy(`Subject: ${subject}\n\n${body}`, "Email")}
                  className="mt-2 rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
                >
                  Copy email
                </button>
              </div>

              {/* Short-message style */}
              <div>
                <div className="text-xs font-medium text-slate-500">
                  LinkedIn / chat style
                </div>
                <textarea
                  value={shortMsg}
                  onChange={(e) => setShortMsg(e.target.value)}
                  className="mt-1 h-44 w-full rounded-md border border-slate-300 p-2 text-sm focus:border-blue-500 focus:outline-none"
                />
                <button
                  onClick={() => copy(shortMsg, "Message")}
                  className="mt-2 rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
                >
                  Copy message
                </button>
              </div>
            </div>

            <div className="mt-4 grid gap-2 sm:grid-cols-2">
              <QualityChecklist checklist={analysis.quality_checklist} />
              <QualityChecklist checklist={analysis.safety_checklist} />
            </div>
          </section>

          {/* Log outcome + Momentum */}
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                After you send your reply — log the outcome
              </div>
              {analysis.suggested_pipeline_update && (
                <span className="text-xs text-slate-500">
                  Suggested:{" "}
                  <span className="font-medium text-slate-700">
                    {label(analysis.suggested_pipeline_update)}
                  </span>
                  {analysis.suggested_momentum
                    ? ` · Momentum +${analysis.suggested_momentum.points}`
                    : ""}
                </span>
              )}
            </div>

            {!canLogOutcome ? (
              <p className="mt-2 text-sm text-slate-500">
                Link a pipeline item above (a message or email) to log the outcome
                and earn Momentum. Without a linked item you can still copy and send
                the draft manually.
              </p>
            ) : (
              <div className="mt-2 flex flex-wrap gap-2">
                {OUTCOME_BUTTONS.map((b) => {
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
                          : "border border-slate-300 text-slate-700 hover:border-blue-400"
                      }`}
                    >
                      {b.label}
                    </button>
                  );
                })}
              </div>
            )}
            <p className="mt-3 text-xs text-slate-400">
              Logging an outcome updates your pipeline and awards Momentum once —
              re-clicking the same outcome never double-counts. Nothing is sent for
              you; you send your reply manually.
            </p>
          </section>
        </div>
      )}
    </div>
  );
}
