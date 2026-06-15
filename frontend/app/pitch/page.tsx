import Link from "next/link";
import { WhyNotSpam } from "@/components/ui";

export const metadata = {
  title: "Network AI — Pitch",
  description: "Why Network AI, and how it's different from spam tools.",
};

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-t border-slate-200 pt-6">
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      <div className="mt-2 space-y-2 text-sm leading-relaxed text-slate-600">
        {children}
      </div>
    </section>
  );
}

export default function PitchPage() {
  return (
    <div className="space-y-8">
      {/* Hero */}
      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-blue-600">
          The pitch
        </div>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
          A permission-based networking copilot for job seekers
        </h1>
        <p className="mt-3 max-w-2xl text-slate-600">
          Network AI turns new job postings into working actions: it finds
          relevant new-grad roles, suggests who to contact, drafts honest
          outreach, and tracks outcomes — while you stay in full control of every
          message.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link
            href="/"
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Open the app →
          </Link>
          <Link
            href="/profile"
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:border-blue-400"
          >
            Save a profile
          </Link>
        </div>
      </div>

      <Section title="The problem">
        <p>
          New grads and international students don&apos;t lose offers because they
          can&apos;t code — they lose them because applications vanish into ATS
          black holes. Referrals and warm intros are what actually convert, but
          most students don&apos;t know who to contact, what to say, or when to
          follow up.
        </p>
      </Section>

      <Section title="Why networking matters more now">
        <p>
          Auto-apply tools flooded every job board, so a single posting can draw
          thousands of one-click applications within hours. Recruiters respond by
          leaning even harder on referrals and inbound relationships. The edge has
          shifted from <em>applying faster</em> to <em>networking better</em>.
        </p>
      </Section>

      <Section title="Why auto-apply is broken">
        <p>
          Mass auto-apply optimizes for volume, the one metric that no longer
          works. It produces generic applications, burns the candidate&apos;s
          reputation, and trains employers to ignore the channel. It also pushes
          students toward grey-area scraping and spam bots that risk their
          accounts.
        </p>
      </Section>

      <Section title="What Network AI does">
        <ul className="ml-5 list-disc space-y-1">
          <li>Ingests fresh new-grad postings and ranks them against your resume.</li>
          <li>
            Labels every role (Strong Target → Poor Fit) and gives a concrete{" "}
            <strong>next best action</strong>.
          </li>
          <li>
            Builds a deterministic <strong>outreach strategy</strong>: who to
            contact first, how many people, what tone, advice vs. referral, and a
            step sequence.
          </li>
          <li>
            Drafts four message types (connection, recruiter, engineer-advice,
            alumni) with a transparent quality checklist.
          </li>
          <li>
            Tracks the whole pipeline — drafts, approvals, manual sends,
            follow-ups, and real outcomes.
          </li>
        </ul>
      </Section>

      <Section title="How it's different from spam bots">
        <p>
          Network AI is a copilot, not an autopilot. It never scrapes, never
          auto-sends, and never fakes personalization. Every message needs your
          approval and is sent by hand. Outcome tracking rewards quality over
          volume by design.
        </p>
        <div className="mt-3">
          <WhyNotSpam />
        </div>
      </Section>

      <Section title="Target user">
        <ul className="ml-5 list-disc space-y-1">
          <li>New-grad and early-career software engineers.</li>
          <li>International students who rely on referrals for visa-friendly roles.</li>
          <li>Bootcamp grads and career-changers breaking into tech.</li>
          <li>
            Later: career coaches and university career centers running cohorts.
          </li>
        </ul>
      </Section>

      <Section title="Future roadmap">
        <ul className="ml-5 list-disc space-y-1">
          <li>Optional LLM-assisted drafting — still reviewed, never auto-sent.</li>
          <li>Richer matching using full job descriptions, not just titles.</li>
          <li>Saved contacts per company and smart follow-up reminders.</li>
          <li>Pipeline export (CSV) and weekly networking digests.</li>
          <li>Multi-user accounts, coach dashboards, and cohort analytics.</li>
        </ul>
      </Section>

      <Section title="Business model (planned)">
        <ul className="ml-5 list-disc space-y-1">
          <li>
            <strong>B2C job seekers:</strong> $9–19/month for tracking, drafting,
            and reminders.
          </li>
          <li>
            <strong>Career coaches:</strong> $49–199/month to manage multiple
            clients.
          </li>
          <li>
            <strong>Universities, bootcamps &amp; clubs:</strong> team/cohort
            pricing for career centers.
          </li>
        </ul>
        <p className="text-xs text-slate-400">
          No revenue yet — this is a local MVP. Payments and accounts are
          intentionally not built.
        </p>
      </Section>
    </div>
  );
}
