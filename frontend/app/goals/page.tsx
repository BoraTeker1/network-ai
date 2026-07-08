"use client";

import { useEffect, useState } from "react";
import {
  api,
  Goal,
  GoalInput,
  OUTREACH_GOALS,
  CONTACT_TYPES,
} from "@/lib/api";
import { PageHeader, ErrorBanner, EmptyState } from "@/components/ui";
import { useT } from "@/lib/i18n";

const TONE_OPTIONS = ["warm_low_pressure", "concise", "direct", "warm"];

const EMPTY: GoalInput = {
  target_role: "",
  target_location: "",
  target_company_type: "",
  outreach_goal: "advice",
  tone_preference: "warm_low_pressure",
  max_contacts_per_company: 3,
  preferred_contact_types: [],
  notes: "",
};

export default function GoalsPage() {
  const t = useT();
  const [goal, setGoal] = useState<Goal | null>(null);
  const [form, setForm] = useState<GoalInput>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const goals = await api.getGoals();
      const current = goals[0] ?? null;
      setGoal(current);
      if (current) {
        setForm({
          target_role: current.target_role ?? "",
          target_location: current.target_location ?? "",
          target_company_type: current.target_company_type ?? "",
          outreach_goal: current.outreach_goal ?? "advice",
          tone_preference: current.tone_preference ?? "warm_low_pressure",
          max_contacts_per_company: current.max_contacts_per_company ?? 3,
          preferred_contact_types: current.preferred_contact_types ?? [],
          notes: current.notes ?? "",
        });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : t.goals.loadFailed);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function toggleType(t: string) {
    setForm((f) => {
      const current = f.preferred_contact_types ?? [];
      const next = current.includes(t)
        ? current.filter((x) => x !== t)
        : [...current, t];
      return { ...f, preferred_contact_types: next };
    });
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const saved = goal
        ? await api.updateGoal(goal.id, form)
        : await api.createGoal(form);
      setGoal(saved);
      setNotice(t.goals.savedNotice);
    } catch (e) {
      setError(e instanceof Error ? e.message : t.goals.saveFailed);
    } finally {
      setSaving(false);
    }
  }

  const field =
    "mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none";

  return (
    <div>
      <PageHeader title={t.goals.title} subtitle={t.goals.subtitle} />

      {notice && (
        <p className="mt-3 rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
          {notice}
        </p>
      )}
      <ErrorBanner message={error} />

      {loading ? (
        <p className="mt-6 text-sm text-slate-500">{t.common.loading}</p>
      ) : (
        <div className="mt-6 space-y-4 rounded-lg border border-slate-200 bg-white p-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t.goals.targetRole}
              </label>
              <input
                className={field}
                placeholder={t.goals.rolePh}
                value={form.target_role}
                onChange={(e) => setForm({ ...form, target_role: e.target.value })}
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t.goals.targetLocation}
              </label>
              <input
                className={field}
                placeholder={t.goals.locPh}
                value={form.target_location}
                onChange={(e) =>
                  setForm({ ...form, target_location: e.target.value })
                }
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t.goals.targetCompanyType}
              </label>
              <input
                className={field}
                placeholder={t.goals.companyTypePh}
                value={form.target_company_type}
                onChange={(e) =>
                  setForm({ ...form, target_company_type: e.target.value })
                }
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t.goals.outreachGoal}
              </label>
              <select
                className={field}
                value={form.outreach_goal}
                onChange={(e) =>
                  setForm({ ...form, outreach_goal: e.target.value })
                }
              >
                {OUTREACH_GOALS.map((g) => (
                  <option key={g} value={g}>
                    {(t.goals.outreachGoals as Record<string, string>)[g] ?? g.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t.goals.tonePreference}
              </label>
              <select
                className={field}
                value={form.tone_preference}
                onChange={(e) =>
                  setForm({ ...form, tone_preference: e.target.value })
                }
              >
                {TONE_OPTIONS.map((tone) => (
                  <option key={tone} value={tone}>
                    {(t.goals.tones as Record<string, string>)[tone] ?? tone.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t.goals.maxContacts}
              </label>
              <input
                type="number"
                min={1}
                max={10}
                className={field}
                value={form.max_contacts_per_company}
                onChange={(e) =>
                  setForm({
                    ...form,
                    max_contacts_per_company: Number(e.target.value),
                  })
                }
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t.goals.preferredContactTypes}
            </label>
            <div className="mt-2 flex flex-wrap gap-2">
              {CONTACT_TYPES.map((ct) => {
                const active = (form.preferred_contact_types ?? []).includes(ct);
                return (
                  <button
                    key={ct}
                    type="button"
                    onClick={() => toggleType(ct)}
                    className={`rounded-full border px-3 py-1 text-xs ${
                      active
                        ? "border-brand-500 bg-brand-50 font-medium text-brand-700"
                        : "border-slate-300 text-slate-600 hover:border-brand-400"
                    }`}
                  >
                    {(t.goals.contactTypes as Record<string, string>)[ct] ?? ct.replace(/_/g, " ")}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t.goals.notes}
            </label>
            <textarea
              className={field}
              placeholder={t.goals.notesPh}
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
          </div>

          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {saving ? t.common.saving : goal ? t.goals.updateGoal : t.goals.createGoal}
          </button>
        </div>
      )}

      {!loading && !goal && (
        <div className="mt-4">
          <EmptyState title={t.goals.emptyTitle} description={t.goals.emptyDesc} />
        </div>
      )}
    </div>
  );
}
