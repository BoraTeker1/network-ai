"use client";

import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { Button, Card, ErrorBanner, TrustLine } from "@/components/ui";
import { useT } from "@/lib/i18n";

const input =
  "w-full rounded-md border border-slate-300 p-2 text-sm focus:border-blue-500 focus:outline-none";

function LoginForm() {
  const t = useT();
  const router = useRouter();
  const params = useSearchParams();
  const { refresh } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.login(email, password);
      await refresh();
      router.push(params.get("next") || "/opportunities");
    } catch (err) {
      setError(err instanceof Error ? err.message : t.auth.loginFailed);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm space-y-4 px-6 py-12">
      <div className="text-center">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          {t.auth.welcomeBack}
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          {t.auth.loginSubtitle}
        </p>
      </div>

      <Card className="p-5">
        <form onSubmit={submit} className="space-y-3">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={t.auth.emailPh}
            autoComplete="email"
            className={input}
          />
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t.auth.passwordPh}
            autoComplete="current-password"
            className={input}
          />
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? t.auth.loggingIn : t.auth.loginBtn}
          </Button>
        </form>
        <ErrorBanner message={error} />
      </Card>

      <p className="text-center text-sm text-slate-600">
        {t.auth.newHere}
        <Link href="/signup" className="font-medium text-blue-600 hover:underline">
          {t.auth.createAccount}
        </Link>
      </p>
      <TrustLine />
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
