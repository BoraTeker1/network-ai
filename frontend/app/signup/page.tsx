"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { Button, Card, ErrorBanner, Pill } from "@/components/ui";

const input =
  "w-full rounded-md border border-slate-300 p-2 text-sm focus:border-blue-500 focus:outline-none";

export default function SignupPage() {
  const router = useRouter();
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
      await api.signup(email, password);
      await refresh();
      router.push("/welcome");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm space-y-4 px-6 py-12">
      <div className="text-center">
        <div className="mb-2 flex justify-center">
          <Pill tone="blue">Early access beta</Pill>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Create your account
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          For Turkish engineers landing Türkiye, remote &amp; EU roles through
          honest outreach.
        </p>
      </div>

      <Card className="p-5">
        <form onSubmit={submit} className="space-y-3">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            autoComplete="email"
            className={input}
          />
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password (min 8 characters)"
            autoComplete="new-password"
            className={input}
          />
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? "Creating account…" : "Sign up free"}
          </Button>
        </form>
        <ErrorBanner message={error} />
      </Card>

      {/* Privacy / trust note — honest, no marketing fluff. */}
      <div className="rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-500">
        <p className="font-medium text-slate-700">Your data, plainly:</p>
        <ul className="mt-1 space-y-0.5">
          <li>· Your résumé, drafts, and pipeline are private to your account.</li>
          <li>· Passwords are hashed; sessions are HttpOnly cookies.</li>
          <li>· No scraping, no auto-send — you review and send everything.</li>
          <li>· We never guarantee jobs or interviews. This is a copilot.</li>
        </ul>
      </div>

      <p className="text-center text-sm text-slate-600">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-blue-600 hover:underline">
          Log in
        </Link>
      </p>
    </div>
  );
}
