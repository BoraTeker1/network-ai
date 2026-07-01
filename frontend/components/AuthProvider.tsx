"use client";

// Client-side auth context. The session cookie lives on the API origin, so the
// Next.js server/middleware can never see it — a client-side guard fetching
// GET /auth/me is the correct mechanism here (documented decision).

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, CurrentUser } from "@/lib/api";

type AuthContextValue = {
  user: CurrentUser | null;
  loading: boolean;
  /** Re-fetch /auth/me (after login/signup/logout). */
  refresh: () => Promise<CurrentUser | null>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  refresh: async () => null,
  signOut: async () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const me = await api.me();
      setUser(me);
      return me;
    } catch {
      // Backend unreachable — treat as anonymous rather than crashing the UI.
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const signOut = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      /* session may already be gone; clearing local state is what matters */
    }
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, refresh, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

// Pages an anonymous visitor may see. Everything else requires a session.
// /opportunities is the public "try before signup" surface; /pitch is the
// investor narrative. There are NO hidden admin pages — admin actions are
// API-only (audited, admin plan required).
const PUBLIC_PATHS = ["/login", "/signup", "/pricing", "/opportunities", "/pitch"];

function isPublic(pathname: string): boolean {
  if (pathname === "/") return true; // redirects to /opportunities
  return PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`),
  );
}

/** Layout-level guard: one place decides public vs private, so no private
 * page can be forgotten. Public pages render immediately. */
export function RouteGuard({ children }: { children: ReactNode }) {
  const pathname = usePathname() || "/";
  if (isPublic(pathname)) return <>{children}</>;
  return <RequireAuth>{children}</RequireAuth>;
}

/** Wrap private page content: shows a skeleton while checking the session and
 * redirects anonymous visitors to /login?next=<here>. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && user === null) {
      router.replace(`/login?next=${encodeURIComponent(pathname || "/")}`);
    }
  }, [loading, user, router, pathname]);

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl space-y-3 px-6 py-10">
        <div className="h-7 w-56 animate-pulse rounded bg-slate-200" />
        <div className="h-4 w-96 animate-pulse rounded bg-slate-100" />
        <div className="mt-6 h-40 animate-pulse rounded-xl bg-slate-100" />
      </div>
    );
  }
  if (user === null) return null; // redirecting
  return <>{children}</>;
}
