"use client";

// The app frame: a left sidebar (nav + plan usage + account) and a top bar
// (feed search, TR/EN, notifications, avatar). Three frames, picked by route:
//
//   /                 anonymous → marketing header (LandingNav)
//   /login, /signup   → no chrome, the form centers itself
//   everything else   → the sidebar shell
//
// The search box lives in the top bar but filters the opportunities feed, so
// the query is held here and read by the page through useFeedSearch().

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api, type BillingOverview } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import LandingNav, { LangToggle, PRIMARY, Wordmark, isActive } from "@/components/Nav";
import Footer from "@/components/Footer";
import { Bell, ChevronDown, Menu, Search, X } from "@/components/icons";
import { useT } from "@/lib/i18n";

const SearchContext = createContext<{ query: string; setQuery: (q: string) => void }>({
  query: "",
  setQuery: () => {},
});

/** The top-bar search query. Only the opportunities feed consumes it today. */
export function useFeedSearch() {
  return useContext(SearchContext);
}

/** Free-plan meters — the two limits that actually gate the core loop. */
function PlanCard() {
  const t = useT();
  const { user } = useAuth();
  const [overview, setOverview] = useState<BillingOverview | null>(null);

  useEffect(() => {
    if (!user || user.plan !== "free") {
      setOverview(null);
      return;
    }
    api.getBillingPlan().then(setOverview).catch(() => {});
  }, [user]);

  if (!user || user.plan !== "free" || !overview) return null;

  const meters = [
    { key: "outreach_draft", label: t.sidebar.drafts },
    { key: "pipeline_save", label: t.sidebar.saves },
  ].map((m) => ({
    ...m,
    used: overview.usage[m.key] ?? 0,
    limit: overview.limits[m.key] ?? null,
  }));
  const bar = meters[0];
  const pct =
    bar.limit && bar.limit > 0 ? Math.min(100, Math.round((bar.used / bar.limit) * 100)) : 0;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3">
      <div className="text-xs font-semibold text-slate-800">{t.sidebar.freePlan}</div>
      <div className="mt-1 text-[11px] text-slate-500">
        {meters
          .map((m) => `${m.used} / ${m.limit ?? "∞"} ${m.label}`)
          .join(" · ")}
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-brand-500" style={{ width: `${pct}%` }} />
      </div>
      <Link
        href="/pricing"
        className="mt-2 flex items-center justify-between text-[11px] font-medium text-slate-500 hover:text-brand-700"
      >
        {t.sidebar.seeUpgrade}
        <span aria-hidden>›</span>
      </Link>
    </div>
  );
}

/** Account chip pinned to the bottom of the sidebar. */
function AccountChip() {
  const t = useT();
  const router = useRouter();
  const { user, loading, signOut } = useAuth();
  const [open, setOpen] = useState(false);

  if (loading) return null;

  if (!user) {
    return (
      <div className="flex items-center gap-2">
        <Link
          href="/login"
          className="flex-1 rounded-full border border-slate-300 px-3 py-1.5 text-center text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          {t.nav.login}
        </Link>
        <Link
          href="/signup"
          className="flex-1 rounded-full bg-brand-600 px-3 py-1.5 text-center text-xs font-medium text-white hover:bg-brand-700"
        >
          {t.nav.signup}
        </Link>
      </div>
    );
  }

  const name = user.email.split("@")[0];

  async function handleLogout() {
    await signOut();
    router.push("/login");
  }

  return (
    <div className="relative">
      {open && (
        <div className="absolute bottom-full left-0 z-30 mb-1 w-full overflow-hidden rounded-xl border border-slate-200 bg-white py-1 shadow-lg">
          <div className="truncate px-3 py-1.5 text-[11px] text-slate-400">{user.email}</div>
          {user.plan === "free" && (
            <Link
              href="/pricing"
              onClick={() => setOpen(false)}
              className="block px-3 py-1.5 text-xs font-medium text-brand-700 hover:bg-brand-50"
            >
              {t.nav.upgrade}
            </Link>
          )}
          <button
            onClick={handleLogout}
            className="block w-full px-3 py-1.5 text-left text-xs text-slate-600 hover:bg-slate-100"
          >
            {t.nav.logout}
          </button>
        </div>
      )}
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 rounded-xl border border-slate-200 bg-white p-2 text-left hover:border-slate-300"
      >
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-semibold uppercase text-white">
          {name.charAt(0)}
        </span>
        <span className="min-w-0 flex-1 truncate text-xs font-medium capitalize text-slate-800">
          {name}
        </span>
        <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" />
      </button>
    </div>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname() || "";
  const t = useT();
  return (
    <div className="flex h-full flex-col gap-6 p-4">
      <div className="px-2 pt-1">
        <Wordmark href="/opportunities" />
      </div>

      <nav className="flex flex-col gap-1">
        {PRIMARY.map(({ href, label, Icon }) => {
          const active = isActive(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${
                active
                  ? "bg-brand-50 font-semibold text-brand-700"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <Icon className="h-[18px] w-[18px]" />
              {label(t)}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto space-y-3">
        <PlanCard />
        <AccountChip />
      </div>
    </div>
  );
}

function TopBar({ onOpenMenu }: { onOpenMenu: () => void }) {
  const t = useT();
  const pathname = usePathname() || "";
  const { query, setQuery } = useFeedSearch();
  const { user } = useAuth();
  // The search box only means something on the feed it filters.
  const showSearch = isActive(pathname, "/opportunities");

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur sm:px-8">
      <button
        onClick={onOpenMenu}
        aria-label={t.sidebar.openMenu}
        className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
      >
        <Menu className="h-5 w-5" />
      </button>

      <div className="flex flex-1 justify-center">
        {showSearch && (
          <div className="relative w-full max-w-md">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t.opportunities.searchPlaceholder}
              aria-label={t.opportunities.searchPlaceholder}
              className="w-full rounded-full border border-slate-200 bg-white py-2 pl-9 pr-8 text-sm text-slate-700 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
            />
            {query && (
              <button
                onClick={() => setQuery("")}
                aria-label={t.common.close}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <LangToggle />
        <button
          aria-label={t.sidebar.notifications}
          className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
        >
          <Bell className="h-5 w-5" />
        </button>
        {user && (
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-600 text-xs font-semibold uppercase text-white">
            {user.email.charAt(0)}
          </span>
        )}
      </div>
    </header>
  );
}

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname() || "/";
  const { user, loading } = useAuth();
  const [query, setQuery] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const t = useT();

  // Auth screens are self-contained forms — no nav chrome around them.
  if (pathname === "/login" || pathname === "/signup") {
    return <main className="mx-auto w-full max-w-5xl px-6 py-8">{children}</main>;
  }

  // The landing page keeps its marketing header while the session check runs and
  // for anonymous visitors; logged-in users get redirected to /opportunities.
  if (pathname === "/" && (loading || !user)) {
    return (
      <>
        <LandingNav />
        <main className="mx-auto w-full max-w-5xl px-6 py-8">{children}</main>
        <Footer />
      </>
    );
  }

  return (
    <SearchContext.Provider value={{ query, setQuery }}>
      <div className="flex min-h-screen bg-slate-50">
        {/* Desktop sidebar */}
        <aside className="fixed inset-y-0 left-0 hidden w-60 border-r border-slate-200 bg-white lg:block">
          <SidebarContent />
        </aside>

        {/* Mobile drawer */}
        {menuOpen && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <div
              className="absolute inset-0 bg-slate-900/30"
              onClick={() => setMenuOpen(false)}
            />
            <aside className="absolute inset-y-0 left-0 w-64 border-r border-slate-200 bg-white shadow-xl">
              <button
                onClick={() => setMenuOpen(false)}
                aria-label={t.sidebar.closeMenu}
                className="absolute right-2 top-3 rounded-lg p-2 text-slate-400 hover:bg-slate-100"
              >
                <X className="h-4 w-4" />
              </button>
              <SidebarContent onNavigate={() => setMenuOpen(false)} />
            </aside>
          </div>
        )}

        <div className="flex min-w-0 flex-1 flex-col lg:pl-60">
          <TopBar onOpenMenu={() => setMenuOpen(true)} />
          <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-8">{children}</main>
          <Footer />
        </div>
      </div>
    </SearchContext.Provider>
  );
}
