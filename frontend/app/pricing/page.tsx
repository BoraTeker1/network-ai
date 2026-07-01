"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, PricingPlan } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { Button, Card, PageHeader, Pill } from "@/components/ui";

export default function PricingPage() {
  const { user } = useAuth();
  const [plans, setPlans] = useState<PricingPlan[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.getBillingPlans().then((r) => setPlans(r.plans)).catch(() => {});
  }, []);

  async function upgrade() {
    setBusy(true);
    setNotice(null);
    try {
      const r = await api.checkout();
      setNotice(r.message); // honest: payments aren't live in the beta
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <PageHeader
        title="Pricing"
        subtitle="Try the whole loop free. Upgrade when the limits get in your way."
      />

      <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
        <strong>Early-access beta:</strong> payments aren&apos;t live yet. Pro is
        granted manually to beta users — the button below tells you exactly that.
        No card fields, no fake checkout.
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {plans.map((p) => {
          const isPro = p.id === "pro";
          const isCurrent = user?.plan === p.id;
          return (
            <Card key={p.id} className={`p-5 ${isPro ? "border-blue-300" : ""}`}>
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">{p.name}</h2>
                {isPro && <Pill tone="blue">Recommended</Pill>}
                {isCurrent && <Pill tone="green">Your plan</Pill>}
              </div>
              <div className="mt-2 text-3xl font-bold text-slate-900">
                ${p.price_monthly_usd}
                <span className="text-sm font-normal text-slate-500"> / month</span>
              </div>
              <ul className="mt-4 space-y-1.5">
                {p.features.map((f) => (
                  <li key={f} className="flex items-start gap-1.5 text-sm text-slate-600">
                    <span className="mt-0.5 text-green-600">✓</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-5">
                {isPro ? (
                  user ? (
                    <Button onClick={upgrade} disabled={busy || isCurrent} className="w-full">
                      {isCurrent ? "You're on Pro" : busy ? "Checking…" : "Upgrade to Pro"}
                    </Button>
                  ) : (
                    <Link
                      href="/signup"
                      className="block w-full rounded-md bg-blue-600 px-4 py-2 text-center text-sm font-medium text-white hover:bg-blue-700"
                    >
                      Sign up first
                    </Link>
                  )
                ) : (
                  <Link
                    href={user ? "/opportunities" : "/signup"}
                    className="block w-full rounded-md border border-slate-300 bg-white px-4 py-2 text-center text-sm font-medium text-slate-700 hover:bg-slate-50"
                  >
                    {user ? "You have Free" : "Start free"}
                  </Link>
                )}
              </div>
            </Card>
          );
        })}
      </div>

      {notice && (
        <p className="rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-900">{notice}</p>
      )}

      {/* Privacy & trust — the promise that differentiates the product. */}
      <Card className="p-4">
        <h3 className="text-sm font-semibold text-slate-900">Privacy &amp; trust</h3>
        <ul className="mt-2 grid gap-x-6 gap-y-1 text-xs text-slate-600 sm:grid-cols-2">
          <li>· Your résumé, drafts, and pipeline are private to your account.</li>
          <li>· No scraping — roles come from official public company APIs.</li>
          <li>· No auto-send, ever. You review, copy, and send everything.</li>
          <li>· No guarantees of jobs or interviews — a copilot, not a promise.</li>
        </ul>
      </Card>
    </div>
  );
}
