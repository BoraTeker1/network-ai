"use client";

import { useEffect, useState } from "react";
import { api, Profile } from "@/lib/api";
import { EmptyState } from "@/components/ui";

export default function ProfilePage() {
  const [resumeText, setResumeText] = useState("");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadProfile() {
    setLoading(true);
    setError(null);
    try {
      const p = await api.getProfile();
      setProfile(p);
    } catch {
      // 404 = no profile yet; that's a normal empty state, not an error.
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProfile();
  }, []);

  async function handleSave() {
    if (!resumeText.trim()) {
      setError("Please paste your resume text first.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const p = await api.saveProfile(resumeText);
      setProfile(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save profile");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold">Profile</h1>
      <p className="mt-1 text-sm text-slate-600">
        Paste your resume text. We extract skills and a short summary — no LLM,
        fully local.
      </p>

      <textarea
        className="mt-4 h-56 w-full rounded-lg border border-slate-300 p-3 text-sm focus:border-blue-500 focus:outline-none"
        placeholder="Paste your resume text here..."
        value={resumeText}
        onChange={(e) => setResumeText(e.target.value)}
      />

      <div className="mt-3 flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save Profile"}
        </button>
        {error && <span className="text-sm text-red-600">{error}</span>}
      </div>

      <hr className="my-8 border-slate-200" />

      <h2 className="text-lg font-semibold">Extracted Profile</h2>
      {loading ? (
        <p className="mt-2 text-sm text-slate-500">Loading…</p>
      ) : !profile ? (
        <div className="mt-4">
          <EmptyState
            title="No profile saved yet"
            description="Paste your resume text above and click Save Profile. We extract your skills and a short summary locally — no LLM, nothing leaves your machine."
          />
        </div>
      ) : (
        <div className="mt-4 space-y-4 rounded-lg border border-slate-200 bg-white p-5">
          <div>
            <div className="text-xs font-semibold uppercase text-slate-500">
              Skills
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              {profile.skills.length === 0 ? (
                <span className="text-sm text-slate-400">None detected</span>
              ) : (
                profile.skills.map((s) => (
                  <span
                    key={s}
                    className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700"
                  >
                    {s}
                  </span>
                ))
              )}
            </div>
          </div>

          <div>
            <div className="text-xs font-semibold uppercase text-slate-500">
              Experience Summary
            </div>
            <p className="mt-1 text-sm text-slate-700">
              {profile.experience_summary || "—"}
            </p>
          </div>

          <div>
            <div className="text-xs font-semibold uppercase text-slate-500">
              Target Roles
            </div>
            <p className="mt-1 text-sm text-slate-700">
              {profile.target_roles.length
                ? profile.target_roles.join(", ")
                : "—"}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
