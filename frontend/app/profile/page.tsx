"use client";

// The profile is the input to everything else: it ranks the opportunity feed,
// feeds the Turkey-applicability verdict, and personalizes outreach drafts.
// So it's laid out as one editable workspace (tabs) plus a right rail that
// answers "what's still missing?" and "why does this matter?".

import { useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  PRIORITY_KEYS,
  SENIORITY_LEVELS,
  WORK_MODELS,
  type PriorityKey,
  type Profile,
  type Seniority,
  type WorkModel,
} from "@/lib/api";
import { Button, Card, PageHeader } from "@/components/ui";
import { useAuth } from "@/components/AuthProvider";
import { useLang, useT, type Lang } from "@/lib/i18n";
import {
  AlertTriangle,
  ArrowUpRight,
  Briefcase,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Code,
  FileText,
  GripVertical,
  Info,
  MapPin,
  Pencil,
  Plus,
  Send,
  ShieldCheck,
  Sliders,
  Target,
  Upload,
  X,
} from "@/components/icons";

const input =
  "rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100";

type TabKey = "goals" | "skills" | "experience" | "prefs";

/** Priorities are a ranked list — always all three keys, order = rank. */
function normalizePriorities(stored: PriorityKey[] | null | undefined): PriorityKey[] {
  const known = (stored ?? []).filter((k) => PRIORITY_KEYS.includes(k));
  return [...known, ...PRIORITY_KEYS.filter((k) => !known.includes(k))];
}

/** Small "what is this for?" hint — native tooltip, no popover machinery. */
function InfoHint({ text }: { text: string }) {
  return (
    <span title={text} aria-label={text} className="cursor-help text-slate-300 hover:text-slate-500">
      <Info className="h-3.5 w-3.5" />
    </span>
  );
}

/** One labelled row inside the editor: label + hint on the left, control right. */
function FieldRow({
  label,
  info,
  children,
}: {
  label: string;
  info: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-[180px_minmax(0,1fr)] sm:items-start sm:gap-4">
      <div className="flex items-center gap-1.5 pt-1.5 text-sm text-slate-600">
        {label}
        <InfoHint text={info} />
      </div>
      <div className="min-w-0">{children}</div>
    </div>
  );
}

/** Chip list with an inline "+ add" affordance. */
function ChipEditor({
  values,
  onChange,
  addLabel,
  removeTitle,
}: {
  values: string[];
  onChange: (next: string[]) => void;
  addLabel: string;
  removeTitle: string;
}) {
  const [adding, setAdding] = useState(false);
  const [text, setText] = useState("");
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (adding) ref.current?.focus();
  }, [adding]);

  function commit() {
    const v = text.trim();
    if (v && !values.some((s) => s.toLowerCase() === v.toLowerCase())) {
      onChange([...values, v]);
    }
    setText("");
    setAdding(false);
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {values.map((s) => (
        <span
          key={s}
          className="inline-flex items-center gap-1.5 rounded-lg bg-brand-50 px-2.5 py-1.5 text-sm font-medium text-brand-800"
        >
          {s}
          <button
            onClick={() => onChange(values.filter((v) => v !== s))}
            title={removeTitle}
            aria-label={`${removeTitle}: ${s}`}
            className="text-brand-400 transition-colors hover:text-brand-800"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </span>
      ))}

      {adding ? (
        <input
          ref={ref}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              commit();
            }
            if (e.key === "Escape") {
              setText("");
              setAdding(false);
            }
          }}
          placeholder={addLabel}
          aria-label={addLabel}
          className={`w-44 ${input}`}
        />
      ) : (
        <button
          onClick={() => setAdding(true)}
          className="inline-flex items-center gap-1 rounded-lg border border-dashed border-slate-300 px-2.5 py-1.5 text-sm font-medium text-slate-500 transition-colors hover:border-brand-400 hover:text-brand-700"
        >
          <Plus className="h-3.5 w-3.5" />
          {addLabel}
        </button>
      )}
    </div>
  );
}

/** Ranked priority list. Reordered with the arrow buttons (keyboard-safe). */
function PriorityEditor({
  values,
  labels,
  onChange,
  upLabel,
  downLabel,
}: {
  values: PriorityKey[];
  labels: Record<PriorityKey, string>;
  onChange: (next: PriorityKey[]) => void;
  upLabel: string;
  downLabel: string;
}) {
  function move(from: number, to: number) {
    if (to < 0 || to >= values.length) return;
    const next = [...values];
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    onChange(next);
  }

  return (
    <div className="space-y-2">
      {values.map((key, i) => (
        <div
          key={key}
          className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2"
        >
          <GripVertical className="h-4 w-4 shrink-0 text-slate-300" />
          <span className="min-w-0 flex-1 truncate text-sm text-slate-700">{labels[key]}</span>
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-slate-200 text-xs font-semibold text-slate-600">
            {i + 1}
          </span>
          <div className="flex shrink-0 flex-col">
            <button
              onClick={() => move(i, i - 1)}
              disabled={i === 0}
              aria-label={`${upLabel}: ${labels[key]}`}
              title={upLabel}
              className="rounded p-0.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 disabled:opacity-25 disabled:hover:bg-transparent"
            >
              <ChevronUp className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => move(i, i + 1)}
              disabled={i === values.length - 1}
              aria-label={`${downLabel}: ${labels[key]}`}
              title={downLabel}
              className="rounded p-0.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 disabled:opacity-25 disabled:hover:bg-transparent"
            >
              <ChevronDown className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function ProfilePage() {
  const t = useT();
  const tp = t.profile;
  const { lang, setLang } = useLang();
  const { user } = useAuth();

  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<TabKey>("goals");

  // Editable profile state (initialized from the loaded profile).
  const [skills, setSkills] = useState<string[]>([]);
  const [targetRoles, setTargetRoles] = useState<string[]>([]);
  const [summary, setSummary] = useState("");
  const [seniority, setSeniority] = useState<Seniority | null>(null);
  const [locations, setLocations] = useState<string[]>([]);
  const [workModels, setWorkModels] = useState<WorkModel[]>([]);
  const [priorities, setPriorities] = useState<PriorityKey[]>(normalizePriorities(null));
  const [dirty, setDirty] = useState(false);
  const [savingEdits, setSavingEdits] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // Resume update panel (upload primary, paste secondary).
  const [showResumeSection, setShowResumeSection] = useState(false);
  const [showPaste, setShowPaste] = useState(false);
  const [resumeText, setResumeText] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadNotice, setUploadNotice] = useState<string | null>(null);

  function adopt(p: Profile | null) {
    setProfile(p);
    setSkills(p?.skills ?? []);
    setTargetRoles(p?.target_roles ?? []);
    setSummary(p?.experience_summary ?? "");
    setSeniority(p?.seniority ?? null);
    setLocations(p?.preferred_locations ?? []);
    setWorkModels(p?.work_models ?? []);
    setPriorities(normalizePriorities(p?.priorities));
    setDirty(false);
  }

  useEffect(() => {
    api
      .getProfile()
      .then(adopt)
      // 404 = no profile yet; that's a normal empty state, not an error.
      .catch(() => adopt(null))
      .finally(() => setLoading(false));
  }, []);

  /** Any edit marks the form dirty — the header reflects the save state. */
  function edit<T>(setter: (v: T) => void) {
    return (v: T) => {
      setter(v);
      setDirty(true);
    };
  }

  async function saveEdits() {
    setSavingEdits(true);
    setEditError(null);
    try {
      const p = await api.updateProfile({
        skills,
        target_roles: targetRoles,
        experience_summary: summary,
        ...(seniority ? { seniority } : {}),
        preferred_locations: locations,
        work_models: workModels,
        priorities,
      });
      adopt(p);
    } catch (e) {
      setEditError(e instanceof Error ? e.message : tp.updateFailed);
    } finally {
      setSavingEdits(false);
    }
  }

  async function handleSave() {
    if (!resumeText.trim()) {
      setError(tp.pasteFirst);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      adopt(await api.saveProfile(resumeText));
      setResumeText("");
    } catch (e) {
      setError(e instanceof Error ? e.message : tp.saveFailed);
    } finally {
      setSaving(false);
    }
  }

  async function handleUpload() {
    if (!selectedFile) {
      setUploadError(tp.chooseFileFirst);
      return;
    }
    setUploading(true);
    setUploadError(null);
    setUploadNotice(null);
    try {
      adopt(await api.uploadResumeFile(selectedFile));
      setUploadNotice(tp.parsedNotice(selectedFile.name));
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : tp.uploadFailed);
    } finally {
      setUploading(false);
    }
  }

  const SENIORITY_LABELS: Record<Seniority, string> = {
    new_grad: tp.seniorityNewGrad,
    intern: tp.seniorityIntern,
    mid: tp.seniorityMid,
  };
  const WORK_LABELS: Record<WorkModel, string> = {
    remote: tp.workRemote,
    hybrid: tp.workHybrid,
    office: tp.workOffice,
  };
  const PRIORITY_LABELS: Record<PriorityKey, string> = {
    visa: tp.priorityVisa,
    tech_fit: tp.priorityTechFit,
    company_quality: tp.priorityCompanyQuality,
  };

  // Readiness drives both the strength meter and the right-rail checklist, so
  // it's derived from the live form state — it updates as you type, not on save.
  const checks = useMemo(
    () => [
      {
        key: "cv" as const,
        ok: !!profile?.has_resume,
        label: profile?.has_resume ? tp.readyCv : tp.missingCv,
      },
      {
        key: "roles" as const,
        ok: targetRoles.length > 0,
        label: targetRoles.length > 0 ? tp.readyRoles : tp.missingRoles,
        tab: "goals" as TabKey,
      },
      {
        key: "skills" as const,
        ok: skills.length > 0,
        label: skills.length > 0 ? tp.readySkills : tp.missingSkills,
        tab: "skills" as TabKey,
      },
      {
        key: "summary" as const,
        ok: summary.trim().length > 0,
        label: summary.trim().length > 0 ? tp.readySummary : tp.missingSummary,
        tab: "experience" as TabKey,
      },
      {
        key: "prefs" as const,
        ok: !!seniority && locations.length > 0 && workModels.length > 0,
        label:
          !!seniority && locations.length > 0 && workModels.length > 0
            ? tp.readyPrefs
            : tp.missingPrefs,
        tab: "goals" as TabKey,
      },
    ],
    [profile, targetRoles, skills, summary, seniority, locations, workModels, tp],
  );

  const doneCount = checks.filter((c) => c.ok).length;
  const missingCount = checks.length - doneCount;
  const strength = Math.round((doneCount / checks.length) * 100);

  /** Jump to wherever a missing item is fixed (the CV lives in its own panel). */
  function goTo(check: (typeof checks)[number]) {
    if (check.key === "cv") {
      setShowResumeSection(true);
      return;
    }
    if (check.tab) setTab(check.tab);
  }

  function completeMissing() {
    const first = checks.find((c) => !c.ok);
    if (first) goTo(first);
  }

  const name = user?.email.split("@")[0] ?? "";
  const initials = name.slice(0, 2).toUpperCase();
  const headline = [seniority ? SENIORITY_LABELS[seniority] : null, targetRoles[0]]
    .filter(Boolean)
    .join(" · ");

  const resumeDate = profile?.resume_updated_at
    ? new Date(profile.resume_updated_at).toLocaleDateString(lang === "tr" ? "tr-TR" : "en-GB", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : null;

  const uploadCard = (
    <Card className="p-5">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {tp.option1}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx"
          onChange={(e) => {
            setSelectedFile(e.target.files?.[0] ?? null);
            setUploadError(null);
            setUploadNotice(null);
          }}
          className="block text-sm text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-200"
        />
        <Button onClick={handleUpload} disabled={uploading || !selectedFile}>
          {uploading ? tp.uploading : tp.uploadBtn}
        </Button>
      </div>
      <p className="mt-2 text-xs text-slate-500">
        {tp.acceptsPre}
        <span className="font-medium">.pdf</span>
        {tp.acceptsOr}
        <span className="font-medium">.docx</span>
        {tp.acceptsPost}
      </p>
      {uploadNotice && (
        <p className="mt-2 rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
          {uploadNotice}
        </p>
      )}
      {uploadError && (
        <p className="mt-2 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{uploadError}</p>
      )}

      {/* Paste text — secondary, behind a disclosure */}
      <button
        onClick={() => setShowPaste((v) => !v)}
        className="mt-4 text-xs font-medium text-slate-500 hover:text-slate-800"
      >
        {tp.option2} {showPaste ? "▴" : "▾"}
      </button>
      {showPaste && (
        <div className="mt-2">
          <textarea
            className="h-40 w-full rounded-lg border border-slate-300 p-3 text-sm focus:border-brand-500 focus:outline-none"
            placeholder={tp.pastePh}
            value={resumeText}
            onChange={(e) => setResumeText(e.target.value)}
          />
          <div className="mt-2 flex items-center gap-3">
            <Button onClick={handleSave} disabled={saving}>
              {saving ? t.common.saving : tp.saveProfile}
            </Button>
            {error && <span className="text-sm text-red-600">{error}</span>}
          </div>
        </div>
      )}
    </Card>
  );

  const TABS: { key: TabKey; label: string; Icon: (p: { className?: string }) => JSX.Element }[] = [
    { key: "goals", label: tp.tabGoals, Icon: Target },
    { key: "skills", label: tp.tabSkills, Icon: Code },
    { key: "experience", label: tp.tabExperience, Icon: Briefcase },
    { key: "prefs", label: tp.tabPreferences, Icon: Sliders },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title={tp.title}
        subtitle={tp.subtitle}
        action={
          <div className="flex items-center gap-4">
            <span
              className={`hidden items-center gap-1.5 text-sm sm:flex ${
                dirty ? "text-amber-600" : "text-slate-500"
              }`}
            >
              {dirty ? (
                <AlertTriangle className="h-4 w-4" />
              ) : (
                <CheckCircle className="h-4 w-4 text-brand-600" />
              )}
              {dirty ? tp.unsaved : tp.allSaved}
            </span>
            <Button variant="secondary" onClick={() => setShowResumeSection((v) => !v)}>
              <Upload className="h-4 w-4" />
              {tp.updateResume}
            </Button>
          </div>
        }
      />

      {loading ? (
        <p className="text-sm text-slate-500">{t.common.loading}</p>
      ) : !profile ? (
        /* Empty state: one clear action — get a CV in. */
        <>
          <div className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-center">
            <div className="text-base font-semibold text-slate-800">{tp.emptyTitle}</div>
            <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">{tp.emptyDesc}</p>
          </div>
          {uploadCard}
        </>
      ) : (
        <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          {/* ---------- Main column ---------- */}
          <div className="min-w-0 space-y-6">
            {showResumeSection && uploadCard}

            {/* Identity + profile strength */}
            <Card className="flex flex-col gap-5 p-5 sm:flex-row sm:items-center sm:gap-6">
              <div className="flex min-w-0 flex-1 items-center gap-4">
                <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-brand-600 text-lg font-semibold text-white">
                  {initials}
                </span>
                <div className="min-w-0">
                  <div className="truncate text-lg font-semibold capitalize text-slate-900">
                    {name}
                  </div>
                  <div className="truncate text-sm text-slate-600">
                    {headline || tp.noHeadline}
                  </div>
                  <div className="mt-1 flex items-center gap-1.5 text-xs text-slate-500">
                    <MapPin className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">
                      {locations.length > 0 ? locations.join(" · ") : tp.noLocations}
                    </span>
                  </div>
                </div>
              </div>

              <div className="shrink-0 sm:w-64 sm:border-l sm:border-slate-100 sm:pl-6">
                <div className="flex items-center gap-1.5 text-sm text-slate-600">
                  {tp.strength}
                  <InfoHint text={tp.strengthInfo} />
                </div>
                <div className="mt-2 flex items-center gap-3">
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-brand-500 transition-all"
                      style={{ width: `${strength}%` }}
                    />
                  </div>
                  <span className="text-xl font-bold text-slate-900">{strength}%</span>
                </div>
                <div className="mt-2 flex items-center justify-between gap-2">
                  <span className="text-xs text-brand-700">
                    {missingCount > 0 ? tp.stepsLeft(missingCount) : tp.allComplete}
                  </span>
                  {missingCount > 0 && (
                    <Button size="sm" onClick={completeMissing}>
                      {tp.completeProfile}
                    </Button>
                  )}
                </div>
              </div>
            </Card>

            {/* Editor */}
            <Card>
              <div
                role="tablist"
                aria-label={tp.title}
                className="flex gap-1 overflow-x-auto border-b border-slate-200 px-3"
              >
                {TABS.map(({ key, label, Icon }) => {
                  const active = tab === key;
                  return (
                    <button
                      key={key}
                      role="tab"
                      aria-selected={active}
                      onClick={() => setTab(key)}
                      className={`-mb-px flex shrink-0 items-center gap-2 border-b-2 px-3 py-3 text-sm transition-colors ${
                        active
                          ? "border-brand-600 font-semibold text-brand-700"
                          : "border-transparent text-slate-500 hover:text-slate-800"
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      {label}
                    </button>
                  );
                })}
              </div>

              <div className="p-5">
                {tab === "goals" && (
                  <div className="space-y-5">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <h2 className="text-base font-semibold text-slate-900">{tp.goalsTitle}</h2>
                      <span className="text-xs text-slate-500">{tp.goalsHint}</span>
                    </div>

                    <FieldRow label={tp.targetRolesLabel} info={tp.rolesInfo}>
                      <ChipEditor
                        values={targetRoles}
                        onChange={edit(setTargetRoles)}
                        addLabel={tp.addRoleBtn}
                        removeTitle={tp.removeSkillTitle}
                      />
                    </FieldRow>

                    <FieldRow label={tp.seniorityLabel} info={tp.seniorityInfo}>
                      <div className="inline-flex flex-wrap rounded-lg border border-slate-200 p-0.5">
                        {SENIORITY_LEVELS.map((level) => {
                          const active = seniority === level;
                          return (
                            <button
                              key={level}
                              aria-pressed={active}
                              onClick={() => edit(setSeniority)(level)}
                              className={`rounded-md px-4 py-1.5 text-sm transition-colors ${
                                active
                                  ? "bg-brand-50 font-semibold text-brand-800 ring-1 ring-brand-200"
                                  : "text-slate-600 hover:bg-slate-50"
                              }`}
                            >
                              {SENIORITY_LABELS[level]}
                            </button>
                          );
                        })}
                      </div>
                    </FieldRow>

                    <FieldRow label={tp.locationsLabel} info={tp.locationsInfo}>
                      <ChipEditor
                        values={locations}
                        onChange={edit(setLocations)}
                        addLabel={tp.addLocationBtn}
                        removeTitle={tp.removeSkillTitle}
                      />
                    </FieldRow>

                    <FieldRow label={tp.workModelLabel} info={tp.workModelInfo}>
                      <div className="flex flex-wrap gap-5 pt-1.5">
                        {WORK_MODELS.map((model) => (
                          <label
                            key={model}
                            className="flex cursor-pointer items-center gap-2 text-sm text-slate-700"
                          >
                            <input
                              type="checkbox"
                              checked={workModels.includes(model)}
                              onChange={(e) =>
                                edit(setWorkModels)(
                                  e.target.checked
                                    ? [...workModels, model]
                                    : workModels.filter((m) => m !== model),
                                )
                              }
                              className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                            />
                            {WORK_LABELS[model]}
                          </label>
                        ))}
                      </div>
                    </FieldRow>

                    <FieldRow label={tp.prioritiesLabel} info={tp.prioritiesInfo}>
                      <PriorityEditor
                        values={priorities}
                        labels={PRIORITY_LABELS}
                        onChange={edit(setPriorities)}
                        upLabel={tp.moveUp}
                        downLabel={tp.moveDown}
                      />
                    </FieldRow>
                  </div>
                )}

                {tab === "skills" && (
                  <div className="space-y-4">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <h2 className="text-base font-semibold text-slate-900">{tp.skills}</h2>
                      <span className="text-xs text-slate-500">{tp.skillsInfo}</span>
                    </div>
                    <ChipEditor
                      values={skills}
                      onChange={edit(setSkills)}
                      addLabel={tp.addSkillBtn}
                      removeTitle={tp.removeSkillTitle}
                    />
                  </div>
                )}

                {tab === "experience" && (
                  <div className="space-y-4">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <h2 className="text-base font-semibold text-slate-900">
                        {tp.experienceTitle}
                      </h2>
                      <span className="text-xs text-slate-500">{tp.experienceHint}</span>
                    </div>
                    <textarea
                      value={summary}
                      onChange={(e) => edit(setSummary)(e.target.value)}
                      rows={5}
                      aria-label={tp.summaryLabel}
                      className="w-full rounded-lg border border-slate-300 p-3 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
                    />
                    {profile.education && (
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          {tp.educationLabel}
                        </div>
                        <p className="mt-1 text-sm text-slate-700">{profile.education}</p>
                      </div>
                    )}
                  </div>
                )}

                {tab === "prefs" && (
                  <div className="space-y-4">
                    <h2 className="text-base font-semibold text-slate-900">{tp.prefsTitle}</h2>
                    <FieldRow label={tp.langLabel} info={tp.langHint}>
                      <div className="inline-flex rounded-lg border border-slate-200 p-0.5">
                        {(["tr", "en"] as Lang[]).map((code) => {
                          const active = lang === code;
                          return (
                            <button
                              key={code}
                              aria-pressed={active}
                              onClick={() => setLang(code)}
                              className={`rounded-md px-4 py-1.5 text-sm uppercase transition-colors ${
                                active
                                  ? "bg-brand-50 font-semibold text-brand-800 ring-1 ring-brand-200"
                                  : "text-slate-600 hover:bg-slate-50"
                              }`}
                            >
                              {code}
                            </button>
                          );
                        })}
                      </div>
                    </FieldRow>
                  </div>
                )}
              </div>

              {/* The language toggle persists itself, so no save bar on that tab. */}
              {tab !== "prefs" && (
                <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 p-4">
                  <div className="flex items-center gap-3">
                    <Button
                      variant="secondary"
                      onClick={() => adopt(profile)}
                      disabled={!dirty || savingEdits}
                    >
                      {tp.discard}
                    </Button>
                    {editError && <span className="text-sm text-red-600">{editError}</span>}
                  </div>
                  <Button onClick={saveEdits} disabled={!dirty || savingEdits}>
                    {savingEdits ? t.common.saving : tp.saveChanges}
                  </Button>
                </div>
              )}
            </Card>

            {/* Skills at a glance — the pencil jumps to the editor above. */}
            <Card className="p-5">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <h2 className="text-base font-semibold text-slate-900">{tp.skills}</h2>
                  <InfoHint text={tp.skillsInfo} />
                </div>
                <button
                  onClick={() => setTab("skills")}
                  aria-label={tp.editSkills}
                  title={tp.editSkills}
                  className="rounded-lg border border-slate-200 p-2 text-slate-500 transition-colors hover:border-slate-300 hover:text-slate-800"
                >
                  <Pencil className="h-4 w-4" />
                </button>
              </div>
              {skills.length > 0 ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  {skills.map((s) => (
                    <span
                      key={s}
                      className="rounded-lg bg-brand-50 px-2.5 py-1.5 text-sm font-medium text-brand-800"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="mt-3 text-sm text-slate-500">{tp.noSkillsYet}</p>
              )}
            </Card>
          </div>

          {/* ---------- Right rail ---------- */}
          <div className="space-y-4 lg:sticky lg:top-20">
            <Card className="p-4">
              <h2 className="text-sm font-semibold text-slate-900">{tp.readinessTitle}</h2>
              <div className="mt-3 space-y-2">
                {checks.map((check) => (
                  <button
                    key={check.key}
                    onClick={() => goTo(check)}
                    className="flex w-full items-center gap-2 rounded-lg border border-slate-200 px-3 py-2.5 text-left transition-colors hover:border-slate-300 hover:bg-slate-50"
                  >
                    {check.ok ? (
                      <CheckCircle className="h-4 w-4 shrink-0 text-brand-600" />
                    ) : (
                      <AlertTriangle className="h-4 w-4 shrink-0 text-amber-500" />
                    )}
                    <span className="min-w-0 flex-1 text-sm text-slate-700">{check.label}</span>
                    <ChevronRight className="h-4 w-4 shrink-0 text-slate-300" />
                  </button>
                ))}
              </div>
              {missingCount > 0 && (
                <button
                  onClick={completeMissing}
                  className="mt-3 w-full rounded-full border border-brand-200 px-4 py-2 text-sm font-medium text-brand-700 transition-colors hover:bg-brand-50"
                >
                  {tp.completeMissing}
                </button>
              )}
            </Card>

            <Card className="p-4">
              <h2 className="text-sm font-semibold text-slate-900">{tp.impactTitle}</h2>
              <div className="mt-3 space-y-4">
                {[
                  {
                    Icon: ArrowUpRight,
                    title: tp.impactRanking,
                    desc: tp.impactRankingDesc,
                  },
                  {
                    Icon: ShieldCheck,
                    title: tp.impactEligibility,
                    desc: tp.impactEligibilityDesc,
                  },
                  {
                    Icon: Send,
                    title: tp.impactOutreach,
                    desc: tp.impactOutreachDesc,
                  },
                ].map(({ Icon, title, desc }) => (
                  <div key={title} className="flex gap-3">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                      <Icon className="h-4 w-4" />
                    </span>
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-slate-800">{title}</div>
                      <p className="mt-0.5 text-xs leading-relaxed text-slate-500">{desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="p-4">
              <h2 className="text-sm font-semibold text-slate-900">{tp.lastCvTitle}</h2>
              {profile.has_resume ? (
                <>
                  <div className="mt-3 flex items-start gap-3">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 text-slate-400">
                      <FileText className="h-4 w-4" />
                    </span>
                    <div className="min-w-0">
                      <div className="text-sm text-slate-800">{resumeDate ?? "—"}</div>
                      <div className="truncate text-xs text-slate-500">
                        {profile.resume_filename ?? tp.lastCvPasted}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => setShowResumeSection(true)}
                    className="mt-4 flex w-full items-center justify-between border-t border-slate-100 pt-3 text-sm text-slate-600 transition-colors hover:text-brand-700"
                  >
                    {tp.lastCvUpdate}
                    <Upload className="h-4 w-4" />
                  </button>
                </>
              ) : (
                <>
                  <p className="mt-2 text-sm text-slate-500">{tp.lastCvNone}</p>
                  <button
                    onClick={() => setShowResumeSection(true)}
                    className="mt-3 flex w-full items-center justify-between text-sm font-medium text-brand-700 hover:text-brand-800"
                  >
                    {tp.lastCvNoneCta}
                    <Upload className="h-4 w-4" />
                  </button>
                </>
              )}
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
