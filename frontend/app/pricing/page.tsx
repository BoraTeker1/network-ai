"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, PricingPlan } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { Button, Card, PageHeader, Pill } from "@/components/ui";
import { useT } from "@/lib/i18n";

export default function PricingPage() {
  const t = useT();
  const { user } = useAuth();
  const [plans, setPlans] = useState<PricingPlan[]>([]);
  const [paymentsLive, setPaymentsLive] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .getBillingPlans()
      .then((r) => {
        setPlans(r.plans);
        setPaymentsLive(r.payments_live);
      })
      .catch(() => {});
  }, []);

  async function upgrade() {
    setBusy(true);
    setNotice(null);
    // WTP signal: the click itself is the validation metric. The backend
    // separately records checkout_link_opened / mock_checkout_viewed.
    api.trackEvent("pro_button_clicked");
    try {
      const r = await api.checkout();
      setNotice(r.message);
      if (r.url) {
        // Hosted provider checkout (new tab, so the notice stays visible).
        window.open(r.url, "_blank", "noopener,noreferrer");
      }
    } catch (e) {
      setNotice(e instanceof Error ? e.message : t.pricing.wentWrong);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <PageHeader title={t.pricing.title} subtitle={t.pricing.subtitle} />

      {paymentsLive ? (
        <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-900">
          <strong>{t.pricing.betaLabel}</strong>{t.pricing.liveText}
        </div>
      ) : (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          <strong>{t.pricing.betaLabel}</strong>{t.pricing.notLiveText}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {plans.map((p) => {
          const isPro = p.id === "pro";
          const isCurrent = user?.plan === p.id;
          return (
            <Card key={p.id} className={`p-5 ${isPro ? "border-blue-300" : ""}`}>
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900">{p.name}</h2>
                {isPro && <Pill tone="blue">{t.pricing.recommended}</Pill>}
                {isCurrent && <Pill tone="green">{t.pricing.yourPlan}</Pill>}
              </div>
              <div className="mt-2 text-3xl font-bold text-slate-900">
                ${p.price_monthly_usd}
                <span className="text-sm font-normal text-slate-500">{t.pricing.perMonth}</span>
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
                      {isCurrent ? t.pricing.onPro : busy ? t.pricing.checking : t.pricing.upgradeToPro}
                    </Button>
                  ) : (
                    <Link
                      href="/signup"
                      className="block w-full rounded-md bg-blue-600 px-4 py-2 text-center text-sm font-medium text-white hover:bg-blue-700"
                    >
                      {t.pricing.signupFirst}
                    </Link>
                  )
                ) : (
                  <Link
                    href={user ? "/opportunities" : "/signup"}
                    className="block w-full rounded-md border border-slate-300 bg-white px-4 py-2 text-center text-sm font-medium text-slate-700 hover:bg-slate-50"
                  >
                    {user ? t.pricing.youHaveFree : t.pricing.startFree}
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
        <h3 className="text-sm font-semibold text-slate-900">{t.pricing.privacyTitle}</h3>
        <ul className="mt-2 grid gap-x-6 gap-y-1 text-xs text-slate-600 sm:grid-cols-2">
          {t.pricing.privacyPoints.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
