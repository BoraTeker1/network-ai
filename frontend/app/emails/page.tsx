"use client";

import { useEffect, useState } from "react";
import { api, EmailDraft } from "@/lib/api";
import {
  PageHeader,
  ErrorBanner,
  EmptyState,
  WhyNotSpam,
  LimitsWarning,
} from "@/components/ui";
import EmailDraftCard from "@/components/EmailDraftCard";
import { useT } from "@/lib/i18n";

export default function EmailsPage() {
  const t = useT();
  const [emails, setEmails] = useState<EmailDraft[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setEmails(await api.getEmails());
      } catch (e) {
        setError(e instanceof Error ? e.message : t.emails.loadFailed);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  function replace(updated: EmailDraft) {
    setEmails((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
  }

  const today = new Date().toISOString().slice(0, 10);
  const emailsToday = emails.filter((e) =>
    (e.created_at ?? "").startsWith(today)
  ).length;

  return (
    <div>
      <PageHeader title={t.emails.title} subtitle={t.emails.subtitle} />

      <div className="mt-4 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-800">
        {t.emails.lockNote}
      </div>

      <div className="mt-4">
        <LimitsWarning emailsToday={emailsToday} />
      </div>

      <ErrorBanner message={error} />

      {loading ? (
        <p className="mt-6 text-sm text-slate-500">{t.common.loading}</p>
      ) : emails.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            title={t.emails.emptyTitle}
            description={t.emails.emptyDesc}
            ctaHref="/opportunities"
            ctaLabel={t.pipeline.emptyCta}
          />
        </div>
      ) : (
        <div className="mt-6 space-y-4">
          {emails.map((e) => (
            <EmailDraftCard key={e.id} email={e} onUpdated={replace} />
          ))}
        </div>
      )}

      <section className="mt-10">
        <WhyNotSpam />
      </section>
    </div>
  );
}
