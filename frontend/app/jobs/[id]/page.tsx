"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  api,
  Job,
  MatchResult,
  ContactSearch,
  Message,
  OutreachStrategy,
  Contact,
  DiscoverResponse,
  EmailDraft,
  Goal,
  CONTACT_TYPES,
} from "@/lib/api";
import {
  recommendationStyle,
  NextBestAction,
  ToneBadge,
  SectionLabel,
  LimitsWarning,
} from "@/components/ui";
import EmailDraftCard from "@/components/EmailDraftCard";

export default function JobDetailPage() {
  const params = useParams();
  const jobId = Number(params.id);

  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [match, setMatch] = useState<MatchResult | null>(null);
  const [matching, setMatching] = useState(false);

  const [searches, setSearches] = useState<ContactSearch[]>([]);
  const [strategy, setStrategy] = useState<OutreachStrategy | null>(null);

  const [contactName, setContactName] = useState("");
  const [contactTitle, setContactTitle] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState<Message[]>([]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [j, cs, st] = await Promise.all([
          api.getJob(jobId),
          api.getContactSearches(jobId).catch(() => []),
          api.getStrategy(jobId).catch(() => null),
        ]);
        setJob(j);
        setSearches(cs);
        setStrategy(st);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load job");
      } finally {
        setLoading(false);
      }
    }
    if (!Number.isNaN(jobId)) load();
  }, [jobId]);

  async function handleMatch() {
    setMatching(true);
    setError(null);
    try {
      setMatch(await api.matchJob(jobId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate match");
    } finally {
      setMatching(false);
    }
  }

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    try {
      const msgs = await api.generateMessages(
        jobId,
        contactName,
        contactTitle
      );
      setGenerated(msgs);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate drafts");
    } finally {
      setGenerating(false);
    }
  }

  if (loading) return <p className="text-sm text-slate-500">Loading...</p>;
  if (!job)
    return (
      <div>
        <p className="text-sm text-red-600">{error || "Job not found."}</p>
        <Link href="/jobs" className="text-sm text-blue-600 hover:underline">
          ← Back to jobs
        </Link>
      </div>
    );

  return (
    <div className="space-y-8">
      <div>
        <Link href="/jobs" className="text-sm text-blue-600 hover:underline">
          ← Back to jobs
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold">{job.title}</h1>
          {job.is_closed && (
            <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-700">
              Closed
            </span>
          )}
        </div>
        <div className="text-slate-600">
          {job.company} · {job.location || "Location N/A"}
        </div>
        <div className="mt-1 flex flex-wrap gap-1.5">
          {job.level && (
            <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
              {job.level}
            </span>
          )}
          {job.employment_type && (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
              {job.employment_type}
            </span>
          )}
          {job.work_mode && (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
              {job.work_mode}
            </span>
          )}
          {job.salary_range && (
            <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">
              {job.salary_range}
            </span>
          )}
        </div>
        <div className="mt-1 text-xs text-slate-400">
          Source: {job.source}
          {job.posted_at ? ` · posted ${job.posted_at}` : ""}
        </div>
        {job.url && (
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-1 inline-block text-sm text-blue-600 hover:underline"
          >
            Open apply / job posting ↗
          </a>
        )}
        {job.source === "newgrad-jobs.com" && job.external_apply_url && (
          <p className="mt-1 text-xs text-slate-400">
            Apply link is provided as-is and may route through an aggregator —
            verify it points to the company before applying.
          </p>
        )}
      </div>

      {(job.description ||
        (job.responsibilities?.length ?? 0) > 0 ||
        (job.qualifications?.length ?? 0) > 0 ||
        (job.benefits?.length ?? 0) > 0) && (
        <section className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="text-lg font-semibold">Role details</h2>
          {job.description && (
            <p className="mt-2 text-sm text-slate-700">{job.description}</p>
          )}
          {(
            [
              ["Responsibilities", job.responsibilities],
              ["Qualifications", job.qualifications],
              ["Benefits", job.benefits],
            ] as const
          ).map(([label, items]) =>
            items && items.length > 0 ? (
              <div key={label} className="mt-3">
                <SectionLabel>{label}</SectionLabel>
                <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-slate-600">
                  {items.map((it, i) => (
                    <li key={i}>{it}</li>
                  ))}
                </ul>
              </div>
            ) : null
          )}
        </section>
      )}

      <NetworkSteps />

      {error && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {/* Match */}
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Match</h2>
          <button
            onClick={handleMatch}
            disabled={matching}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {matching ? "Scoring..." : "Generate Match"}
          </button>
        </div>
        {match ? (
          <div className="mt-3">
            <div className="flex items-center gap-3">
              <div className="text-3xl font-bold">{match.match_score}/100</div>
              {match.recommendation && (
                <span
                  className={`rounded-full px-2.5 py-1 text-xs font-medium ${recommendationStyle(
                    match.recommendation
                  )}`}
                >
                  {match.recommendation}
                </span>
              )}
            </div>

            {match.breakdown?.length > 0 && (
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {match.breakdown.map((b) => (
                  <div key={b.label} className="rounded-md bg-slate-50 p-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-slate-700">
                        {b.label}
                      </span>
                      <span className="text-slate-500">
                        {b.points}/{b.max}
                      </span>
                    </div>
                    <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-200">
                      <div
                        className="h-full rounded-full bg-blue-500"
                        style={{
                          width: `${Math.round((b.points / b.max) * 100)}%`,
                        }}
                      />
                    </div>
                    <p className="mt-1 text-xs text-slate-500">{b.detail}</p>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-3 flex flex-wrap gap-2">
              {match.matched_skills.map((s) => (
                <span
                  key={`y-${s}`}
                  className="rounded-full bg-green-50 px-2 py-0.5 text-xs text-green-700"
                >
                  ✓ {s}
                </span>
              ))}
              {match.missing_skills.slice(0, 6).map((s) => (
                <span
                  key={`n-${s}`}
                  className="rounded-full bg-slate-50 px-2 py-0.5 text-xs text-slate-400"
                >
                  {s}
                </span>
              ))}
            </div>

            {match.next_best_action && (
              <div className="mt-4">
                <NextBestAction text={match.next_best_action} />
              </div>
            )}
          </div>
        ) : (
          <p className="mt-3 text-sm text-slate-500">
            Click “Generate Match” to score this job against your profile.
          </p>
        )}
      </section>

      {/* Outreach strategy */}
      {strategy && (
        <section className="rounded-lg border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Outreach Strategy</h2>
            <span
              className={`rounded-full px-2.5 py-1 text-xs font-medium ${recommendationStyle(
                strategy.label
              )}`}
            >
              {strategy.label}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            A deterministic plan based on this role&apos;s fit — advice-first, never
            a referral ask as the opener.
          </p>

          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <div className="rounded-md bg-slate-50 p-3">
              <SectionLabel>Who to contact first</SectionLabel>
              <p className="mt-1 text-sm text-slate-700">{strategy.who_first}</p>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <SectionLabel>How many people</SectionLabel>
              <p className="mt-1 text-sm text-slate-700">{strategy.contact_count}</p>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <SectionLabel>Tone &amp; ask</SectionLabel>
              <p className="mt-1 text-sm text-slate-700">
                <span className="capitalize">{strategy.tone}</span> tone · ask for{" "}
                <span className="font-medium">{strategy.ask_type}</span>
              </p>
            </div>
          </div>

          <div className="mt-4">
            <SectionLabel>Suggested sequence</SectionLabel>
            <ol className="mt-2 space-y-2">
              {strategy.sequence.map((s) => (
                <li key={s.step} className="flex gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">
                    {s.step}
                  </span>
                  <div>
                    <div className="text-sm font-medium text-slate-800">
                      {s.title}
                    </div>
                    <p className="text-xs text-slate-500">{s.detail}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>
      )}

      {/* Contacts & AI email outreach */}
      <ContactsOutreach jobId={jobId} company={job.company} />

      {/* Contact searches */}
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-lg font-semibold">Contact Search Suggestions</h2>
        <p className="mt-1 text-xs text-slate-500">
          Manual searches only — Network AI never scrapes LinkedIn. Open a
          search and find people yourself.
        </p>
        <div className="mt-4 space-y-3">
          {searches.length === 0 ? (
            <p className="text-sm text-slate-500">No suggestions available.</p>
          ) : (
            searches.map((s) => (
              <div
                key={s.label}
                className="rounded-md border border-slate-100 bg-slate-50 p-3"
              >
                <div className="font-medium text-slate-800">{s.label}</div>
                <code className="mt-1 block text-xs text-slate-500">
                  {s.query}
                </code>
                <div className="mt-2 flex gap-2">
                  <a
                    href={s.google_search_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded border border-slate-300 bg-white px-2 py-1 text-xs hover:border-blue-400"
                  >
                    Open Google Search ↗
                  </a>
                  <a
                    href={s.linkedin_search_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded border border-slate-300 bg-white px-2 py-1 text-xs hover:border-blue-400"
                  >
                    Open LinkedIn Search ↗
                  </a>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      {/* Generate drafts */}
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-lg font-semibold">Generate Outreach Drafts</h2>
        <p className="mt-1 text-xs text-slate-500">
          Optional: add a contact name/title to personalize the greeting.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <input
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            placeholder="Contact name (optional)"
            value={contactName}
            onChange={(e) => setContactName(e.target.value)}
          />
          <input
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            placeholder="Contact title (optional)"
            value={contactTitle}
            onChange={(e) => setContactTitle(e.target.value)}
          />
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="mt-3 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {generating ? "Generating..." : "Generate Outreach Drafts"}
        </button>

        {generated.length > 0 && (
          <div className="mt-4 space-y-3">
            <p className="text-sm text-green-700">
              Generated {generated.length} drafts.{" "}
              <Link href="/messages" className="font-medium underline">
                Review them in Messages →
              </Link>
            </p>
            {generated.map((m) => (
              <div
                key={m.id}
                className="rounded-md border border-slate-100 bg-slate-50 p-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="text-xs font-semibold uppercase text-slate-500">
                    {m.message_type.replace(/_/g, " ")}
                  </div>
                  <ToneBadge tone={m.tone} />
                </div>
                <p className="mt-1 text-sm text-slate-700">{m.draft_text}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

// ---- Guided "Network for this job" steps (just a map of the page below) ----

const NETWORK_STEPS = [
  { title: "Review the match reason", detail: "See the transparent score and why this role is worth your effort." },
  { title: "Plan who to contact", detail: "Use the deterministic outreach strategy — who first, how many, what tone." },
  { title: "Add a contact", detail: "Find people yourself (no scraping) and add them manually." },
  { title: "Draft messages", detail: "Generate permission-based drafts — AI proposes, you decide." },
  { title: "Approve & copy", detail: "Edit, approve, copy — nothing is ever sent for you." },
  { title: "Update your pipeline", detail: "Mark sent and log the outcome to keep momentum honest." },
];

function NetworkSteps() {
  return (
    <section className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div className="h-1.5 w-full bg-gradient-to-r from-blue-500 via-indigo-500 to-violet-600" />
      <div className="p-4">
        <h2 className="text-sm font-semibold text-slate-900">
          Network for this job — your guided flow
        </h2>
        <p className="mt-1 text-xs text-slate-500">
          Work top to bottom. Everything below is a copilot step: you approve,
          copy, and send each message yourself.
        </p>
        <ol className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {NETWORK_STEPS.map((s, i) => (
            <li
              key={s.title}
              className="flex items-start gap-2 rounded-md border border-slate-100 bg-slate-50 p-2.5"
            >
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-100 text-[11px] font-bold text-blue-700">
                {i + 1}
              </span>
              <div className="min-w-0">
                <div className="text-xs font-medium text-slate-800">{s.title}</div>
                <p className="text-[11px] text-slate-500">{s.detail}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

// ---- Contacts & AI email outreach (manual-first, compliant discovery) ----

const EMPTY_CONTACT = {
  name: "",
  title: "",
  email: "",
  linkedin_url: "",
  contact_type: "recruiter",
  source_note: "",
};

function ContactsOutreach({
  jobId,
  company,
}: {
  jobId: number;
  company: string | null;
}) {
  const [goal, setGoal] = useState<Goal | null>(null);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [drafts, setDrafts] = useState<EmailDraft[]>([]);
  const [discovery, setDiscovery] = useState<DiscoverResponse | null>(null);
  const [discoverType, setDiscoverType] = useState("technical_recruiter");
  const [form, setForm] = useState({ ...EMPTY_CONTACT });
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const [goals, cs] = await Promise.all([
        api.getGoals().catch(() => []),
        api.getContacts(jobId).catch(() => []),
      ]);
      setGoal(goals[0] ?? null);
      setContacts(cs);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load contacts");
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  async function handleDiscover() {
    setBusy("discover");
    setError(null);
    try {
      setDiscovery(
        await api.discoverContacts({
          job_id: jobId,
          goal_id: goal?.id,
          contact_type: discoverType,
          max_results: 5,
        })
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Discovery failed");
    } finally {
      setBusy(null);
    }
  }

  async function handleAddManual() {
    if (!form.name.trim()) {
      setError("Contact name is required.");
      return;
    }
    setBusy("add");
    setError(null);
    try {
      await api.addManualContact({
        name: form.name,
        title: form.title || undefined,
        email: form.email || undefined,
        linkedin_url: form.linkedin_url || undefined,
        contact_type: form.contact_type,
        source_note: form.source_note || undefined,
        job_id: jobId,
      });
      setForm({ ...EMPTY_CONTACT });
      setShowForm(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add contact");
    } finally {
      setBusy(null);
    }
  }

  // One handler for all three channels — email, a LinkedIn connection note, or
  // a LinkedIn DM. They all return an EmailDraft that the same card renders.
  async function handleDraft(
    contactId: number,
    channel: "email" | "connection" | "dm"
  ) {
    setBusy(`draft-${channel}-${contactId}`);
    setError(null);
    try {
      const common = {
        job_id: jobId,
        contact_id: contactId,
        goal_id: goal?.id ?? null,
        tone: goal?.tone_preference ?? "warm_low_pressure",
      };
      const draft =
        channel === "email"
          ? await api.draftEmail(common)
          : await api.draftLinkedIn({ ...common, kind: channel });
      setDrafts((prev) => [draft, ...prev.filter((d) => d.id !== draft.id)]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to draft outreach");
    } finally {
      setBusy(null);
    }
  }

  function replaceDraft(updated: EmailDraft) {
    setDrafts((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
  }

  const field =
    "mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none";

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">Contacts &amp; AI Outreach</h2>
        {!goal && (
          <a href="/goals" className="text-xs font-medium text-blue-600 hover:underline">
            Set a job-search goal to personalize drafts →
          </a>
        )}
      </div>
      <p className="mt-1 text-xs text-slate-500">
        Add contacts you found yourself, or run compliant discovery. No scraping,
        no invented emails — and nothing is ever sent without your approval.
      </p>

      {error && (
        <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="mt-3">
        <LimitsWarning contactsForCompany={contacts.length} />
      </div>

      {/* Discover */}
      <div className="mt-4 flex flex-wrap items-end gap-2">
        <div>
          <SectionLabel>Discover contact type</SectionLabel>
          <select
            className={field}
            value={discoverType}
            onChange={(e) => setDiscoverType(e.target.value)}
          >
            {CONTACT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={handleDiscover}
          disabled={busy === "discover"}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {busy === "discover" ? "Discovering…" : "Discover Contacts"}
        </button>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:border-blue-400"
        >
          {showForm ? "Cancel" : "Add Contact Manually"}
        </button>
      </div>

      {discovery && (
        <div className="mt-3 rounded-md border border-slate-100 bg-slate-50 p-3">
          <p className="text-xs text-slate-600">{discovery.message}</p>
          <p className="mt-1 text-[11px] text-slate-400">
            Providers available: {discovery.providers_available.join(", ")}
          </p>
        </div>
      )}

      {/* Manual add form */}
      {showForm && (
        <div className="mt-4 grid gap-3 rounded-md border border-slate-100 bg-slate-50 p-4 sm:grid-cols-2">
          <div>
            <SectionLabel>Name *</SectionLabel>
            <input
              className={field}
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </div>
          <div>
            <SectionLabel>Title</SectionLabel>
            <input
              className={field}
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
          </div>
          <div>
            <SectionLabel>Email</SectionLabel>
            <input
              className={field}
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </div>
          <div>
            <SectionLabel>LinkedIn URL (optional)</SectionLabel>
            <input
              className={field}
              value={form.linkedin_url}
              onChange={(e) =>
                setForm({ ...form, linkedin_url: e.target.value })
              }
            />
          </div>
          <div>
            <SectionLabel>Contact type</SectionLabel>
            <select
              className={field}
              value={form.contact_type}
              onChange={(e) =>
                setForm({ ...form, contact_type: e.target.value })
              }
            >
              {CONTACT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </div>
          <div>
            <SectionLabel>Source note</SectionLabel>
            <input
              className={field}
              placeholder="e.g. company careers page"
              value={form.source_note}
              onChange={(e) =>
                setForm({ ...form, source_note: e.target.value })
              }
            />
          </div>
          <div className="sm:col-span-2">
            <button
              onClick={handleAddManual}
              disabled={busy === "add"}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {busy === "add" ? "Adding…" : "Save Contact"}
            </button>
          </div>
        </div>
      )}

      {/* Contact list */}
      <div className="mt-4 space-y-2">
        {contacts.length === 0 ? (
          <p className="text-sm text-slate-500">
            No contacts yet for this company. Add one manually or run discovery.
          </p>
        ) : (
          contacts.map((c) => (
            <div
              key={c.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-200 p-3"
            >
              <div className="min-w-0">
                <div className="text-sm font-medium text-slate-900">
                  {c.name}
                  {c.title ? ` · ${c.title}` : ""}
                </div>
                <div className="text-xs text-slate-500">
                  {c.email || "no email"}
                  {c.email_confidence != null
                    ? ` · ${c.email_confidence}% confidence`
                    : ""}{" "}
                  · source: {c.source}
                </div>
                {c.why_relevant && (
                  <div className="mt-0.5 text-xs text-slate-400">
                    {c.why_relevant}
                  </div>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => handleDraft(c.id, "email")}
                  disabled={busy === `draft-email-${c.id}`}
                  className="rounded-md bg-violet-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50"
                >
                  {busy === `draft-email-${c.id}` ? "Drafting…" : "Draft Email"}
                </button>
                <button
                  onClick={() => handleDraft(c.id, "connection")}
                  disabled={busy === `draft-connection-${c.id}`}
                  className="rounded-md border border-[#0a66c2] px-3 py-1.5 text-sm font-medium text-[#0a66c2] hover:bg-[#0a66c2]/5 disabled:opacity-50"
                  title="A LinkedIn connection-request note (300-char cap)"
                >
                  {busy === `draft-connection-${c.id}`
                    ? "Drafting…"
                    : "LinkedIn Note"}
                </button>
                <button
                  onClick={() => handleDraft(c.id, "dm")}
                  disabled={busy === `draft-dm-${c.id}`}
                  className="rounded-md border border-[#0a66c2] px-3 py-1.5 text-sm font-medium text-[#0a66c2] hover:bg-[#0a66c2]/5 disabled:opacity-50"
                  title="A LinkedIn message to send after they accept"
                >
                  {busy === `draft-dm-${c.id}` ? "Drafting…" : "LinkedIn DM"}
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Inline drafts created here */}
      {drafts.length > 0 && (
        <div className="mt-5 space-y-4">
          <p className="text-sm text-green-700">
            Draft created — review it below or in the{" "}
            <a href="/emails" className="font-medium underline">
              email approval queue →
            </a>
          </p>
          {drafts.map((d) => (
            <EmailDraftCard key={d.id} email={d} onUpdated={replaceDraft} />
          ))}
        </div>
      )}
    </section>
  );
}
