// Small shared UI primitives used across pages — kept deliberately tiny.

import Link from "next/link";
import type { ReactNode } from "react";
import type { Checklist } from "@/lib/api";

/** Friendly empty state with an optional call-to-action. */
export function EmptyState({
  title,
  description,
  ctaHref,
  ctaLabel,
}: {
  title: string;
  description: string;
  ctaHref?: string;
  ctaLabel?: string;
}) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center">
      <div className="text-base font-semibold text-slate-800">{title}</div>
      <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">{description}</p>
      {ctaHref && ctaLabel && (
        <Link
          href={ctaHref}
          className="mt-4 inline-block rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          {ctaLabel}
        </Link>
      )}
    </div>
  );
}

/** Inline error banner. Renders nothing when `message` is falsy. */
export function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
      {message}
    </p>
  );
}

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-slate-100 text-slate-600",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-700",
  copied: "bg-blue-100 text-blue-800",
  sent_manually: "bg-purple-100 text-purple-800",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
        STATUS_STYLES[status] ?? "bg-slate-100 text-slate-600"
      }`}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}

const OUTCOME_STYLES: Record<string, string> = {
  connected: "bg-sky-100 text-sky-800",
  replied: "bg-teal-100 text-teal-800",
  referral_received: "bg-emerald-100 text-emerald-800",
  interview_received: "bg-green-100 text-green-800",
  ignored: "bg-slate-100 text-slate-500",
  rejected: "bg-rose-100 text-rose-700",
};

export function OutcomeBadge({ outcome }: { outcome: string }) {
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
        OUTCOME_STYLES[outcome] ?? "bg-slate-100 text-slate-600"
      }`}
    >
      {outcome.replace(/_/g, " ")}
    </span>
  );
}

// 4-tier thresholds, matching the backend strategy labels.
export function scoreColor(score: number): string {
  if (score >= 75) return "bg-green-100 text-green-800";
  if (score >= 50) return "bg-amber-100 text-amber-800";
  if (score >= 25) return "bg-slate-100 text-slate-600";
  return "bg-rose-50 text-rose-600";
}

export function recommendationStyle(rec: string | null): string {
  if (rec === "Strong Target") return "bg-green-100 text-green-800";
  if (rec === "Worth Networking") return "bg-amber-100 text-amber-800";
  if (rec === "Low Priority") return "bg-slate-100 text-slate-500";
  if (rec === "Poor Fit") return "bg-rose-50 text-rose-600";
  return "bg-slate-100 text-slate-500";
}

/** Consistent page header with title + optional subtitle and right-side action. */
export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 pb-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          {title}
        </h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-slate-600">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

/** Small uppercase section label. */
export function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
      {children}
    </div>
  );
}

const TONE_STYLES: Record<string, string> = {
  concise: "bg-indigo-50 text-indigo-700",
  warm: "bg-orange-50 text-orange-700",
  direct: "bg-sky-50 text-sky-700",
  "low-pressure": "bg-emerald-50 text-emerald-700",
};

export function ToneBadge({ tone }: { tone: string }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
        TONE_STYLES[tone] ?? "bg-slate-100 text-slate-600"
      }`}
    >
      {tone}
    </span>
  );
}

const FOLLOW_UP_STYLES: Record<string, string> = {
  follow_up_needed: "bg-amber-100 text-amber-800",
  followed_up: "bg-blue-100 text-blue-800",
  no_response: "bg-slate-100 text-slate-500",
};

export function FollowUpBadge({
  status,
  dueDate,
}: {
  status: string | null;
  dueDate?: string | null;
}) {
  if (!status) {
    return (
      <span className="rounded-full bg-slate-50 px-2 py-0.5 text-xs text-slate-400">
        No follow-up yet
      </span>
    );
  }
  const label = status.replace(/_/g, " ");
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
        FOLLOW_UP_STYLES[status] ?? "bg-slate-100 text-slate-600"
      }`}
    >
      {label}
      {status === "follow_up_needed" && dueDate ? ` · due ${dueDate}` : ""}
    </span>
  );
}

/** Prominent "next best action" callout used on match cards / job detail. */
export function NextBestAction({ text }: { text: string | null | undefined }) {
  if (!text) return null;
  return (
    <div className="flex items-start gap-2 rounded-md border border-blue-100 bg-blue-50 p-3">
      <span className="mt-0.5 text-blue-600">→</span>
      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-blue-700">
          Next best action
        </div>
        <p className="mt-0.5 text-sm text-slate-700">{text}</p>
      </div>
    </div>
  );
}

const SPAM_POINTS = [
  "Every message requires your explicit approval before it's used.",
  "Manual copy & send only — nothing is ever sent on your behalf.",
  "No LinkedIn scraping; contact search links are opened by you.",
  "No bulk sending and no browser automation.",
  "A quality checklist flags fake personalization and weak asks.",
  "Outcome + follow-up tracking rewards quality over volume.",
];

/** The trust panel — why Network AI is a copilot, not a spam tool. */
export function WhyNotSpam({ compact = false }: { compact?: boolean }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-2">
        <span className="text-base">🛡️</span>
        <h3 className="text-sm font-semibold text-slate-900">
          Why this is not a spam tool
        </h3>
      </div>
      <ul
        className={`mt-3 grid gap-x-6 gap-y-1.5 ${
          compact ? "" : "sm:grid-cols-2"
        }`}
      >
        {SPAM_POINTS.map((p) => (
          <li key={p} className="flex items-start gap-1.5 text-xs text-slate-600">
            <span className="mt-0.5 text-green-600">✓</span>
            <span>{p}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Renders the deterministic message-quality checklist. */
export function QualityChecklist({ checklist }: { checklist: Checklist }) {
  const allPassed = checklist.passed === checklist.total;
  return (
    <div className="rounded-md border border-slate-100 bg-slate-50 p-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Quality checklist
        </span>
        <span
          className={`text-xs font-medium ${
            allPassed ? "text-green-700" : "text-amber-700"
          }`}
        >
          {checklist.passed}/{checklist.total} passed
        </span>
      </div>
      <ul className="mt-2 grid gap-1 sm:grid-cols-2">
        {checklist.items.map((item) => (
          <li
            key={item.key}
            className={`flex items-center gap-1.5 text-xs ${
              item.passed ? "text-slate-600" : "text-slate-400"
            }`}
          >
            <span>{item.passed ? "✓" : "○"}</span>
            <span>{item.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
