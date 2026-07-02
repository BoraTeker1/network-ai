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

export default function EmailsPage() {
  const [emails, setEmails] = useState<EmailDraft[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setEmails(await api.getEmails());
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load emails");
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
      <PageHeader
        title="Email approval queue"
        subtitle="AI proposes; you decide. Review why each contact and message is relevant, edit freely, then approve and send manually."
      />

      <div className="mt-4 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-800">
        🔒 Nothing is sent without your approval. No scraping, no auto-send, no
        bulk sending — Gmail sending is disabled by default.
      </div>

      <div className="mt-4">
        <LimitsWarning emailsToday={emailsToday} />
      </div>

      <ErrorBanner message={error} />

      {loading ? (
        <p className="mt-6 text-sm text-slate-500">Loading…</p>
      ) : emails.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            title="No email drafts yet"
            description="Pick an opportunity, add a contact, and draft outreach — drafts land here for review and approval."
            ctaHref="/opportunities"
            ctaLabel="Browse opportunities →"
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
