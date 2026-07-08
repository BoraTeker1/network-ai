import Link from "next/link";
import { WhyNotSpam } from "@/components/ui";

export const metadata = {
  title: "Network AI — Pitch",
  description:
    "A bilingual referral & outreach copilot for Turkish junior engineers targeting Turkey, remote, and EU roles.",
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
        <div className="text-xs font-semibold uppercase tracking-wide text-brand-600">
          The pitch
        </div>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
          A bilingual referral &amp; outreach copilot for Turkish junior engineers
        </h1>
        <p className="mt-3 max-w-2xl text-slate-600">
          Network AI helps Turkish junior software engineers find Turkey-relevant
          opportunities — Turkey-based, remote, European, and global roles they can
          realistically apply to — and turn them into warm, honest bilingual
          (Turkish/English) outreach they send themselves.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link
            href="/opportunities"
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            See opportunities →
          </Link>
          <Link
            href="/outreach"
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:border-brand-400"
          >
            Draft outreach
          </Link>
        </div>
      </div>

      <Section title="The problem">
        <p>
          Turkish juniors and new grads don&apos;t lose interviews because they
          can&apos;t code — they lose them because cold applications vanish into ATS
          black holes. In Turkey, referrals matter even more than in most markets,
          but most early-career engineers don&apos;t know <em>who</em> to contact,
          <em> what</em> to say in English without sounding cringe, or how to handle
          the &quot;can a Turkey-based candidate even apply?&quot; question.
        </p>
      </Section>

      <Section title="Why now">
        <p>
          ICT graduates have Turkey&apos;s highest emigration rate, and a
          &quot;virtual brain drain&quot; is growing — engineers in Istanbul working
          remotely for Berlin, Stockholm, and global teams for EUR/USD pay.
          Auto-apply tools flooded the boards, so the edge has shifted from{" "}
          <em>applying faster</em> to <em>networking better</em> — exactly where no
          Turkish platform helps the individual.
        </p>
      </Section>

      <Section title="What Network AI does">
        <ul className="ml-5 list-disc space-y-1">
          <li>
            Curates <strong>Turkey-relevant opportunities</strong> — Turkey-based,
            remote, EMEA/Europe, and global remote roles — from companies&apos;
            official public ATS APIs, public job feeds, and manual curation.
          </li>
          <li>
            Labels every role with a conservative{" "}
            <strong>&quot;can a Turkey-based candidate apply?&quot;</strong> verdict
            (Strong fit → Probably not eligible) with a reason — hiding US-only /
            EU-citizenship-only roles by default.
          </li>
          <li>
            Tells you <strong>who to contact</strong> (recruiter, engineer, manager,
            Turkish alumni) with manual search links.
          </li>
          <li>
            Drafts honest, low-pressure <strong>bilingual outreach</strong> (Turkish
            for domestic roles, English for remote/EU/global) with optional
            Turkey/CET and work-authorization framing — personalized with your real
            skills, with a quality checklist.
          </li>
          <li>Tracks manual follow-up. You approve and send everything yourself.</li>
        </ul>
      </Section>

      <Section title="How it's different">
        <p>
          Not a generic job board, not &quot;Kariyer.net with AI,&quot; not an
          auto-apply bot. It&apos;s a narrow workflow tool: a copilot, not an
          autopilot. It never scrapes protected sites, never auto-sends, and never
          fakes personalization. Every message needs your approval and is sent by
          hand.
        </p>
        <div className="mt-3">
          <WhyNotSpam />
        </div>
      </Section>

      <Section title="Target user">
        <ul className="ml-5 list-disc space-y-1">
          <li>Turkish junior software engineers and CS new grads based in Turkey.</li>
          <li>Early-career developers targeting remote, European, or global roles.</li>
          <li>Bootcamp grads (Patika, Techcareer, etc.) breaking into tech.</li>
          <li>Later: Turkish universities, bootcamps, and communities running cohorts.</li>
        </ul>
      </Section>

      <Section title="Source policy">
        <p>
          Compliant by design: companies&apos; <strong>official public ATS APIs</strong>{" "}
          (Lever/Greenhouse/Ashby), public job-board APIs, manual JSON import, and a
          clearly-labelled sample seed. <strong>No scraping</strong> of LinkedIn,
          Kariyer.net, Youthall, Techcareer, or any protected site. Eligibility
          labels are conservative guesses you must verify on the company page.
        </p>
      </Section>

      <Section title="Status">
        <p className="text-xs text-slate-400">
          Local MVP, pre-validation. Live Turkish sources currently include Dream
          Games, Codeway, and Commencis via their public Lever boards; more companies
          are registered for manual curation. Payments and accounts are intentionally
          not built yet.
        </p>
      </Section>
    </div>
  );
}
