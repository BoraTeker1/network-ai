"use client";

import Link from "next/link";
import { Card, PageHeader, TrustLine } from "@/components/ui";

const STEPS = [
  {
    n: 1,
    title: "Add your résumé",
    body: "Paste or upload it — we extract your skills locally. They power role ranking and personalize every draft.",
    href: "/profile",
    cta: "Add résumé →",
  },
  {
    n: 2,
    title: "Browse realistic roles",
    body: "Türkiye + remote/EU listings from official company APIs, each labeled for whether you can actually apply.",
    href: "/opportunities",
    cta: "See opportunities →",
  },
  {
    n: 3,
    title: "Draft your first outreach",
    body: "Pick a role, find the right person, and get an honest TR/EN draft. You edit, copy, and send it yourself.",
    href: "/outreach",
    cta: "Open the copilot →",
  },
  {
    n: 4,
    title: "Track it in your pipeline",
    body: "Save the draft, mark it sent, log replies, and let Next Move AI help when someone writes back.",
    href: "/pipeline",
    cta: "View pipeline →",
  },
];

export default function WelcomePage() {
  // Auth is enforced by the layout-level RouteGuard (/welcome is private).
  return (
    <div className="mx-auto max-w-3xl space-y-5">
        <PageHeader
          title="Welcome — here's the whole loop"
          subtitle="Four steps from résumé to a tracked conversation. Most people get their first draft out in under five minutes."
        />

        <div className="grid gap-3 sm:grid-cols-2">
          {STEPS.map((s) => (
            <Card key={s.n} hover className="p-4">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-semibold text-blue-700">
                  {s.n}
                </span>
                <h2 className="font-semibold text-slate-900">{s.title}</h2>
              </div>
              <p className="mt-2 text-sm text-slate-600">{s.body}</p>
              <Link
                href={s.href}
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
            Skip for now →
          </Link>
        </div>
      </div>
  );
}
