"use client";

// Small shared UI primitives used across pages — kept deliberately tiny.

import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import type { Checklist } from "@/lib/api";
import { useT } from "@/lib/i18n";

/** Standard surface card — soft border + subtle shadow for a calm SaaS feel. */
export function Card({
  children,
  className = "",
  hover = false,
}: {
  children: ReactNode;
  className?: string;
  hover?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border border-slate-200 bg-white shadow-sm ${
        hover ? "transition-colors hover:border-slate-300 hover:shadow-md" : ""
      } ${className}`}
    >
      {children}
    </div>
  );
}

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary: "rounded-full bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50",
  secondary:
    "rounded-full border border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50 disabled:opacity-50",
  ghost: "rounded-md text-slate-600 hover:bg-slate-100 hover:text-slate-900 disabled:opacity-50",
  danger: "rounded-md border border-rose-200 bg-white text-rose-700 hover:bg-rose-50 disabled:opacity-50",
};

/** Consistent button. `size="sm"` for inline card actions. */
export function Button({
  variant = "primary",
  size = "md",
  className = "",
  ...props
}: {
  variant?: ButtonVariant;
  size?: "sm" | "md";
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  const sizing = size === "sm" ? "px-2.5 py-1 text-xs" : "px-4 py-2 text-sm";
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-1.5 font-medium transition-colors ${sizing} ${BUTTON_VARIANTS[variant]} ${className}`}
    />
  );
}

type PillTone = "neutral" | "blue" | "green" | "amber" | "rose" | "violet";
const PILL_TONES: Record<PillTone, string> = {
  neutral: "bg-slate-100 text-slate-600",
  blue: "bg-brand-50 text-brand-700",
  green: "bg-green-100 text-green-800",
  amber: "bg-amber-100 text-amber-800",
  rose: "bg-rose-100 text-rose-700",
  violet: "bg-violet-100 text-violet-800",
};

/** Generic rounded pill/badge for chips and labels. */
export function Pill({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: PillTone;
}) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PILL_TONES[tone]}`}>
      {children}
    </span>
  );
}

/** Small section header used to group content within a page. */
export function SectionHeader({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <h2 className="text-base font-semibold text-slate-900">{title}</h2>
      {hint && <span className="text-xs text-slate-500">{hint}</span>}
      {action}
    </div>
  );
}

/** Slim, one-line hint that makes the core loop obvious at the top of a page. */
export function WorkflowHint({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-brand-100 bg-brand-50/60 px-3 py-2 text-sm text-brand-900">
      <span aria-hidden className="text-brand-500">
        →
      </span>
      <span>{children}</span>
    </div>
  );
}

/** Compact one-line trust note — the anti-spam promise without dominating a page. */
export function TrustLine() {
  const t = useT();
  return (
    <p className="flex items-center gap-1.5 text-xs text-slate-500">
      <span className="text-green-600">🛡️</span>
      {t.ui.trustLine}
    </p>
  );
}

/** Friendly empty state with one clear call-to-action (link or button). */
export function EmptyState({
  title,
  description,
  ctaHref,
  ctaLabel,
  onCta,
}: {
  title: string;
  description: string;
  ctaHref?: string;
  ctaLabel?: string;
  onCta?: () => void;
}) {
  const ctaClass =
    "mt-4 inline-block rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700";
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center">
      <div className="text-base font-semibold text-slate-800">{title}</div>
      <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">{description}</p>
      {onCta && ctaLabel ? (
        <button onClick={onCta} className={ctaClass}>
          {ctaLabel}
        </button>
      ) : ctaHref && ctaLabel ? (
        <Link href={ctaHref} className={ctaClass}>
          {ctaLabel}
        </Link>
      ) : null}
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
  copied: "bg-panel-100 text-panel-800",
  sent_manually: "bg-purple-100 text-purple-800",
  sent_manual: "bg-purple-100 text-purple-800",
  sent_via_gmail: "bg-purple-100 text-purple-800",
};

export function StatusBadge({ status }: { status: string }) {
  const t = useT();
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
        STATUS_STYLES[status] ?? "bg-slate-100 text-slate-600"
      }`}
    >
      {(t.ui.status as Record<string, string>)[status] ?? status.replace(/_/g, " ")}
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
  const t = useT();
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
        OUTCOME_STYLES[outcome] ?? "bg-slate-100 text-slate-600"
      }`}
    >
      {(t.ui.outcome as Record<string, string>)[outcome] ?? outcome.replace(/_/g, " ")}
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
  followed_up: "bg-panel-100 text-panel-800",
  no_response: "bg-slate-100 text-slate-500",
};

export function FollowUpBadge({
  status,
  dueDate,
}: {
  status: string | null;
  dueDate?: string | null;
}) {
  const t = useT();
  if (!status) {
    return (
      <span className="rounded-full bg-slate-50 px-2 py-0.5 text-xs text-slate-400">
        {t.ui.noFollowUp}
      </span>
    );
  }
  const label =
    (t.ui.followUp as Record<string, string>)[status] ?? status.replace(/_/g, " ");
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
        FOLLOW_UP_STYLES[status] ?? "bg-slate-100 text-slate-600"
      }`}
    >
      {label}
      {status === "follow_up_needed" && dueDate ? t.ui.dueDate(dueDate) : ""}
    </span>
  );
}

/** Prominent "next best action" callout used on match cards / job detail. */
export function NextBestAction({ text }: { text: string | null | undefined }) {
  const t = useT();
  if (!text) return null;
  return (
    <div className="flex items-start gap-2 rounded-md border border-brand-100 bg-brand-50 p-3">
      <span className="mt-0.5 text-brand-600">→</span>
      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-brand-700">
          {t.ui.nextBestAction}
        </div>
        <p className="mt-0.5 text-sm text-slate-700">{text}</p>
      </div>
    </div>
  );
}

/** The trust panel — why Network AI is a copilot, not a spam tool. */
export function WhyNotSpam({ compact = false }: { compact?: boolean }) {
  const t = useT();
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-2">
        <span className="text-base">🛡️</span>
        <h3 className="text-sm font-semibold text-slate-900">
          {t.ui.whyNotSpamTitle}
        </h3>
      </div>
      <ul
        className={`mt-3 grid gap-x-6 gap-y-1.5 ${
          compact ? "" : "sm:grid-cols-2"
        }`}
      >
        {t.ui.spamPoints.map((p) => (
          <li key={p} className="flex items-start gap-1.5 text-xs text-slate-600">
            <span className="mt-0.5 text-green-600">✓</span>
            <span>{p}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// Suggested MVP outreach limits (UI nudges — quality over volume).
export const MAX_CONTACTS_PER_COMPANY = 3;
export const MAX_EMAILS_PER_DAY = 5;

/** Soft warning when the user exceeds suggested outreach limits. */
export function LimitsWarning({
  contactsForCompany,
  emailsToday,
}: {
  contactsForCompany?: number;
  emailsToday?: number;
}) {
  const t = useT();
  const warnings: string[] = [];
  if ((contactsForCompany ?? 0) > MAX_CONTACTS_PER_COMPANY) {
    warnings.push(t.ui.tooManyContacts(MAX_CONTACTS_PER_COMPANY));
  }
  if ((emailsToday ?? 0) > MAX_EMAILS_PER_DAY) {
    warnings.push(t.ui.tooManyEmails(MAX_EMAILS_PER_DAY));
  }
  if (warnings.length === 0) return null;
  return (
    <div className="rounded-md border border-amber-300 bg-amber-50 p-3">
      <div className="text-xs font-semibold uppercase tracking-wide text-amber-700">
        {t.ui.headsUp}
      </div>
      <ul className="mt-1 space-y-1">
        {warnings.map((w) => (
          <li key={w} className="text-sm text-amber-800">
            {w}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Renders the deterministic message-quality checklist. */
export function QualityChecklist({ checklist }: { checklist: Checklist }) {
  const t = useT();
  const allPassed = checklist.passed === checklist.total;
  return (
    <div className="rounded-md border border-slate-100 bg-slate-50 p-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t.ui.qualityChecklist}
        </span>
        <span
          className={`text-xs font-medium ${
            allPassed ? "text-green-700" : "text-amber-700"
          }`}
        >
          {t.ui.checklistPassed(checklist.passed, checklist.total)}
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
