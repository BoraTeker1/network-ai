"use client";

// Rendered when the API returns a 402 plan_limit error — a tasteful upgrade
// nudge instead of a generic red error.

import Link from "next/link";
import { useT } from "@/lib/i18n";

export default function UpgradeCallout({ message }: { message: string }) {
  const t = useT();
  return (
    <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-brand-200 bg-brand-50 px-4 py-3">
      <div className="min-w-0">
        <p className="text-sm font-medium text-slate-900">{t.upgrade.limitTitle}</p>
        <p className="mt-0.5 text-xs text-slate-600">{message}</p>
      </div>
      <Link
        href="/pricing"
        className="shrink-0 rounded-full bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
      >
        {t.upgrade.seePlans}
      </Link>
    </div>
  );
}
