"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { useLang, useT, type Lang } from "@/lib/i18n";
import type { Dict } from "@/lib/i18n/en";

// The core workflow, in loop order: Opportunities → Applications → Outreach.
// Profile sits alongside as the input that powers ranking + personalization.
// Reply analysis (/next-move) is reached from within a tracked application.
const PRIMARY: { href: string; label: (t: Dict) => string }[] = [
  { href: "/opportunities", label: (t) => t.nav.opportunities },
  { href: "/pipeline", label: (t) => t.nav.pipeline },
  { href: "/outreach", label: (t) => t.nav.outreach },
  { href: "/profile", label: (t) => t.nav.profile },
];

function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

const PLAN_TONE: Record<string, string> = {
  free: "bg-slate-100 text-slate-600",
  pro: "bg-brand-50 text-brand-700",
  admin: "bg-violet-100 text-violet-800",
};

// Marketing links shown to logged-out visitors on the landing page only.
const LANDING_LINKS: { href: string; label: (t: Dict) => string }[] = [
  { href: "/opportunities", label: (t) => t.nav.opportunities },
  { href: "/#nasil-calisir", label: (t) => t.nav.landingHow },
  { href: "/#guven", label: (t) => t.nav.landingTrust },
];

/** TR/EN segmented toggle — the user's language choice, persisted per browser. */
function LangToggle() {
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

function Wordmark({ href }: { href: string }) {
  return (
    <>
      <Link
        href={href}
        className="mr-1 shrink-0 whitespace-nowrap text-[15px] font-semibold tracking-tight text-slate-900"
      >
        Network<span className="text-brand-600">AI</span>
      </Link>
      <span className="mr-2 rounded-full bg-brand-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-brand-700">
        Beta
      </span>
    </>
  );
}

/** Simplified marketing nav — landing page, anonymous visitors only.
 * Logged-in users never see this (they're redirected off "/" anyway). */
function LandingNav() {
  const t = useT();
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/80 backdrop-blur">
      <nav className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-1 gap-y-2 px-6 py-3">
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

export default function Nav() {
  const pathname = usePathname() || "";
  const router = useRouter();
  const { user, loading, signOut } = useAuth();
  const t = useT();

  // Landing page for anonymous visitors gets the simplified marketing nav.
  // While the session check is loading on "/" we also show it — logged-in
  // users get redirected to /opportunities immediately after, so the app nav
  // never flashes.
  if (pathname === "/" && (loading || !user)) {
    return <LandingNav />;
  }

  async function handleLogout() {
    await signOut();
    router.push("/login");
  }

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/80 backdrop-blur">
      <nav className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-1 gap-y-2 px-6 py-3">
        <Wordmark href="/opportunities" />

        <div className="flex flex-wrap items-center gap-1">
          {PRIMARY.map((l) => {
            const active = isActive(pathname, l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={active ? "page" : undefined}
                className={`whitespace-nowrap rounded-full px-3 py-1.5 text-sm transition-colors ${
                  active
                    ? "bg-brand-50 font-medium text-brand-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                {l.label(t)}
              </Link>
            );
          })}
        </div>

        {/* Account area */}
        <div className="ml-auto flex items-center gap-2">
          <LangToggle />
          {loading ? null : user ? (
            <>
              <span className="hidden max-w-[160px] truncate text-xs text-slate-500 sm:inline">
                {user.email}
              </span>
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                  PLAN_TONE[user.plan] ?? PLAN_TONE.free
                }`}
              >
                {user.plan}
              </span>
              {user.plan === "free" && (
                <Link
                  href="/pricing"
                  className="whitespace-nowrap rounded-full bg-brand-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-brand-700"
                >
                  {t.nav.upgrade}
                </Link>
              )}
              <button
                onClick={handleLogout}
                className="rounded-full px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 hover:text-slate-900"
              >
                {t.nav.logout}
              </button>
            </>
          ) : (
            <>
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
                {t.nav.signup}
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
