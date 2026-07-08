"use client";

import { useEffect, useRef, useState } from "react";
import { api, Profile } from "@/lib/api";
import { Button, PageHeader, SectionLabel } from "@/components/ui";
import { useT } from "@/lib/i18n";

const input =
  "rounded-md border border-slate-300 p-2 text-sm focus:border-brand-500 focus:outline-none";

/** Chip list with inline add/remove — the editable core of the profile. */
function ChipEditor({
  values,
  onChange,
  placeholder,
  addLabel,
  removeTitle,
}: {
  values: string[];
  onChange: (next: string[]) => void;
  placeholder: string;
  addLabel: string;
  removeTitle: string;
}) {
  const [text, setText] = useState("");

  function add() {
    const v = text.trim();
    if (!v) return;
    if (!values.some((s) => s.toLowerCase() === v.toLowerCase())) {
      onChange([...values, v]);
    }
    setText("");
  }

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {values.map((s) => (
          <span
            key={s}
            className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700"
          >
            {s}
            <button
              onClick={() => onChange(values.filter((v) => v !== s))}
              title={removeTitle}
              className="text-brand-400 hover:text-brand-800"
            >
              ×
            </button>
          </span>
        ))}
      </div>
      <div className="mt-2 flex items-center gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
          placeholder={placeholder}
          className={`w-56 ${input}`}
        />
        <Button variant="secondary" size="sm" onClick={add}>
          {addLabel}
        </Button>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const t = useT();
  const tp = t.profile;
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  // Editable structured fields (initialized from the loaded profile).
  const [skills, setSkills] = useState<string[]>([]);
  const [targetRoles, setTargetRoles] = useState<string[]>([]);
  const [summary, setSummary] = useState("");
  const [dirty, setDirty] = useState(false);
  const [savingEdits, setSavingEdits] = useState(false);
  const [editNotice, setEditNotice] = useState<string | null>(null);
  const [editError, setEditError] = useState<string | null>(null);

  // Resume update section (upload primary, paste secondary).
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

  async function saveEdits() {
    setSavingEdits(true);
    setEditError(null);
    setEditNotice(null);
    try {
      const p = await api.updateProfile({
        skills,
        target_roles: targetRoles,
        experience_summary: summary,
      });
      adopt(p);
      setEditNotice(tp.savedNotice);
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

  const resumeSectionOpen = showResumeSection || !profile;

  const uploadCard = (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
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
        <button
          onClick={handleUpload}
          disabled={uploading || !selectedFile}
          className="rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {uploading ? tp.uploading : tp.uploadBtn}
        </button>
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
        <p className="mt-2 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {uploadError}
        </p>
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
    </div>
  );

  return (
    <div className="space-y-4">
      <PageHeader title={tp.title} subtitle={tp.subtitle} />

      {loading ? (
        <p className="text-sm text-slate-500">{t.common.loading}</p>
      ) : !profile ? (
        /* Empty state: one clear action — get a resume in. */
        <>
          <div className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-center">
            <div className="text-base font-semibold text-slate-800">{tp.emptyTitle}</div>
            <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">{tp.emptyDesc}</p>
          </div>
          {uploadCard}
        </>
      ) : (
        <>
          {/* The structured, editable profile — the primary surface. */}
          <div className="space-y-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-base font-semibold text-slate-900">{tp.yourProfile}</h2>
              <button
                onClick={() => setShowResumeSection((v) => !v)}
                className="text-xs font-medium text-slate-500 hover:text-slate-800"
              >
                {tp.updateResume} {resumeSectionOpen ? "▴" : "▾"}
              </button>
            </div>

            <div>
              <SectionLabel>{tp.skills}</SectionLabel>
              <div className="mt-2">
                <ChipEditor
                  values={skills}
                  onChange={(v) => {
                    setSkills(v);
                    setDirty(true);
                  }}
                  placeholder={tp.addSkillPh}
                  addLabel={tp.addBtn}
                  removeTitle={tp.removeSkillTitle}
                />
              </div>
            </div>

            <div>
              <SectionLabel>{tp.targetRolesLabel}</SectionLabel>
              <div className="mt-2">
                <ChipEditor
                  values={targetRoles}
                  onChange={(v) => {
                    setTargetRoles(v);
                    setDirty(true);
                  }}
                  placeholder={tp.addRolePh}
                  addLabel={tp.addBtn}
                  removeTitle={tp.removeSkillTitle}
                />
              </div>
            </div>

            <div>
              <SectionLabel>{tp.summaryLabel}</SectionLabel>
              <textarea
                value={summary}
                onChange={(e) => {
                  setSummary(e.target.value);
                  setDirty(true);
                }}
                rows={3}
                className={`mt-2 w-full ${input}`}
              />
            </div>

            <div className="flex items-center gap-3 border-t border-slate-100 pt-4">
              <Button onClick={saveEdits} disabled={!dirty || savingEdits}>
                {savingEdits ? t.common.saving : tp.saveChanges}
              </Button>
              {editNotice && !dirty && (
                <span className="text-sm text-green-700">{editNotice}</span>
              )}
              {editError && <span className="text-sm text-red-600">{editError}</span>}
            </div>
          </div>

          {resumeSectionOpen && uploadCard}
        </>
      )}
    </div>
  );
}
