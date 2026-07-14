"use client";

// Marketing header for anonymous visitors on the landing page. Logged-in users
// live inside the sidebar shell instead (components/AppShell.tsx), which reuses
// the wordmark, the language toggle, and the PRIMARY nav list exported here.

import Link from "next/link";
import { useLang, useT, type Lang } from "@/lib/i18n";
import type { Dict } from "@/lib/i18n/en";
import { Briefcase, FileText, Send, User } from "@/components/icons";

// The core workflow, in loop order: Opportunities → Applications → Outreach.
// Profile sits alongside as the input that powers ranking + personalization.
// Reply analysis (/next-move) is reached from within a tracked application.
export const PRIMARY: {
  href: string;
  label: (t: Dict) => string;
  Icon: (p: { className?: string }) => JSX.Element;
}[] = [
  { href: "/opportunities", label: (t) => t.nav.opportunities, Icon: Briefcase },
  { href: "/pipeline", label: (t) => t.nav.pipeline, Icon: FileText },
  { href: "/outreach", label: (t) => t.nav.outreach, Icon: Send },
  { href: "/profile", label: (t) => t.nav.profile, Icon: User },
];

export function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

// Marketing links shown to logged-out visitors on the landing page only.
const LANDING_LINKS: { href: string; label: (t: Dict) => string }[] = [
  { href: "/opportunities", label: (t) => t.nav.opportunities },
  { href: "/#nasil-calisir", label: (t) => t.nav.landingHow },
  { href: "/#guven", label: (t) => t.nav.landingTrust },
];

/** TR/EN segmented toggle — the user's language choice, persisted per browser. */
export function LangToggle() {
  const { lang, setLang } = useLang();
  return (
    <div className="flex shrink-0 items-center rounded-full border border-slate-200 bg-slate-50 p-0.5">
      {(["tr", "en"] as Lang[]).map((l) => (
        <button
          key={l}
          onClick={() => setLang(l)}
          aria-pressed={lang === l}
          className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase transition-colors ${
            lang === l
              ? "bg-white text-slate-900 shadow-sm"
              : "text-slate-400 hover:text-slate-700"
          }`}
        >
          {l}
        </button>
      ))}
    </div>
  );
}

export function Wordmark({ href }: { href: string }) {
  return (
    <div className="flex items-center gap-2">
      <Link
        href={href}
        className="shrink-0 whitespace-nowrap text-[15px] font-semibold tracking-tight text-slate-900"
      >
        Network<span className="text-brand-600">AI</span>
      </Link>
      <span className="rounded-full bg-brand-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-brand-700">
        Beta
      </span>
    </div>
  );
}

/** Simplified marketing nav — landing page, anonymous visitors only. */
export default function LandingNav() {
  const t = useT();
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/80 backdrop-blur">
      <nav className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-2 gap-y-2 px-6 py-3">
        <Wordmark href="/" />

        <div className="hidden items-center gap-1 sm:flex">
          {LANDING_LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="whitespace-nowrap rounded-full px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 hover:text-slate-900"
            >
              {l.label(t)}
            </Link>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-2">
          <LangToggle />
          <Link
            href="/login"
            className="rounded-full px-2.5 py-1.5 text-sm text-slate-600 hover:bg-slate-100 hover:text-slate-900"
          >
            {t.nav.login}
          </Link>
          <Link
            href="/signup"
            className="whitespace-nowrap rounded-full bg-brand-600 px-3.5 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
          >
            {t.nav.landingCta}
          </Link>
        </div>
      </nav>
    </header>
  );
}
