"use client";

import Link from "next/link";
import { Card, PageHeader, TrustLine } from "@/components/ui";
import { useT } from "@/lib/i18n";

const STEP_HREFS = ["/profile", "/opportunities", "/outreach", "/pipeline"];

export default function WelcomePage() {
  const t = useT();
  // Auth is enforced by the layout-level RouteGuard (/welcome is private).
  return (
    <div className="mx-auto max-w-3xl space-y-5">
        <PageHeader title={t.welcome.title} subtitle={t.welcome.subtitle} />

        <div className="grid gap-3 sm:grid-cols-2">
          {t.welcome.steps.map((s, i) => (
            <Card key={STEP_HREFS[i]} hover className="p-4">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-semibold text-blue-700">
                  {i + 1}
                </span>
                <h2 className="font-semibold text-slate-900">{s.title}</h2>
              </div>
              <p className="mt-2 text-sm text-slate-600">{s.body}</p>
              <Link
                href={STEP_HREFS[i]}
                className="mt-3 inline-block text-sm font-medium text-blue-600 hover:underline"
              >
                {s.cta}
              </Link>
            </Card>
          ))}
        </div>

        <div className="flex items-center justify-between">
          <TrustLine />
          <Link
            href="/opportunities"
            className="shrink-0 text-sm text-slate-500 hover:text-slate-700"
          >
            {t.welcome.skip}
          </Link>
        </div>
      </div>
  );
}
