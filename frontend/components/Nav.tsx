"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/components/AuthProvider";

// The core workflow, in loop order: Opportunities → Outreach → Pipeline → Next Move.
// Profile sits alongside as the input that powers ranking + personalization.
const PRIMARY = [
  { href: "/opportunities", label: "Opportunities" },
  { href: "/outreach", label: "Outreach" },
  { href: "/pipeline", label: "Pipeline" },
  { href: "/next-move", label: "Next Move" },
  { href: "/profile", label: "Profile" },
];

// Supporting surfaces — de-emphasized behind a "More" menu.
const SECONDARY = [
  { href: "/goals", label: "Goals" },
  { href: "/events", label: "Events" },
  { href: "/vibe", label: "Vibe Mode" },
  { href: "/pitch", label: "Pitch" },
];

function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

const PLAN_TONE: Record<string, string> = {
  free: "bg-slate-100 text-slate-600",
  pro: "bg-blue-50 text-blue-700",
  admin: "bg-violet-100 text-violet-800",
};

export default function Nav() {
  const pathname = usePathname() || "";
  const router = useRouter();
  const { user, loading, signOut } = useAuth();
  const [moreOpen, setMoreOpen] = useState(false);
  const moreActive = SECONDARY.some((l) => isActive(pathname, l.href));

  async function handleLogout() {
    await signOut();
    router.push("/login");
  }

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
      <nav className="mx-auto flex max-w-5xl items-center gap-x-1 gap-y-2 px-6 py-2.5">
        <Link
          href="/opportunities"
          className="mr-1 shrink-0 whitespace-nowrap text-[15px] font-semibold tracking-tight text-slate-900"
        >
          Network<span className="text-blue-600">AI</span>
        </Link>
        <span className="mr-2 rounded-full bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-blue-600">
          Beta
        </span>

        <div className="flex flex-wrap items-center gap-1">
          {PRIMARY.map((l) => {
            const active = isActive(pathname, l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={active ? "page" : undefined}
                className={`whitespace-nowrap rounded-md px-3 py-1.5 text-sm transition-colors ${
                  active
                    ? "bg-blue-50 font-medium text-blue-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </div>

        {/* Account area */}
        <div className="ml-auto flex items-center gap-2">
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
                  className="whitespace-nowrap text-xs font-medium text-blue-600 hover:underline"
                >
                  Upgrade
                </Link>
              )}
              <button
                onClick={handleLogout}
                className="rounded-md px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 hover:text-slate-900"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="rounded-md px-2.5 py-1.5 text-sm text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              >
                Log in
              </Link>
              <Link
                href="/signup"
                className="whitespace-nowrap rounded-md bg-blue-600 px-2.5 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
              >
                Sign up
              </Link>
            </>
          )}
        </div>

        {/* More menu — supporting pages, visually de-emphasized. */}
        <div className="relative">
          <button
            onClick={() => setMoreOpen((v) => !v)}
            className={`flex items-center gap-1 rounded-md px-3 py-1.5 text-sm transition-colors ${
              moreActive || moreOpen
                ? "bg-slate-100 text-slate-900"
                : "text-slate-500 hover:bg-slate-100 hover:text-slate-900"
            }`}
          >
            More
            <span aria-hidden className="text-xs text-slate-400">
              ▾
            </span>
          </button>
          {moreOpen && (
            <>
              {/* click-away backdrop */}
              <button
                aria-hidden
                tabIndex={-1}
                onClick={() => setMoreOpen(false)}
                className="fixed inset-0 z-10 cursor-default"
              />
              <div className="absolute right-0 z-20 mt-1 w-40 overflow-hidden rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
                {SECONDARY.map((l) => (
                  <Link
                    key={l.href}
                    href={l.href}
                    onClick={() => setMoreOpen(false)}
                    className={`block px-3 py-1.5 text-sm ${
                      isActive(pathname, l.href)
                        ? "bg-blue-50 font-medium text-blue-700"
                        : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                    }`}
                  >
                    {l.label}
                  </Link>
                ))}
              </div>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
