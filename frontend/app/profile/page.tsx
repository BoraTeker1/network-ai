"use client";

import { useEffect, useRef, useState } from "react";
import { api, Profile } from "@/lib/api";
import { EmptyState, PageHeader, WorkflowHint } from "@/components/ui";
import { useT } from "@/lib/i18n";

export default function ProfilePage() {
  const t = useT();
  const [resumeText, setResumeText] = useState("");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // File-upload state (separate from the paste-text flow).
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadNotice, setUploadNotice] = useState<string | null>(null);

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
      setError(t.profile.pasteFirst);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const p = await api.saveProfile(resumeText);
      setProfile(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : t.profile.saveFailed);
    } finally {
      setSaving(false);
    }
  }

  async function handleUpload() {
    if (!selectedFile) {
      setUploadError(t.profile.chooseFileFirst);
      return;
    }
    setUploading(true);
    setUploadError(null);
    setUploadNotice(null);
    try {
      const p = await api.uploadResumeFile(selectedFile);
      setProfile(p);
      setUploadNotice(t.profile.parsedNotice(selectedFile.name));
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : t.profile.uploadFailed);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader title={t.profile.title} subtitle={t.profile.subtitle} />

      <WorkflowHint>
        {t.profile.hintPre}
        <strong>{t.profile.hintStrong}</strong>
        {t.profile.hintPost}
      </WorkflowHint>

      {/* Option 1: upload a resume file */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t.profile.option1}
        </div>
        <p className="mt-1 text-sm text-slate-600">
          {t.profile.acceptsPre}
          <span className="font-medium">.pdf</span>
          {t.profile.acceptsOr}
          <span className="font-medium">.docx</span>
          {t.profile.acceptsPost}
        </p>

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
            {uploading ? t.profile.uploading : t.profile.uploadBtn}
          </button>
        </div>

        {selectedFile && !uploading && (
          <p className="mt-2 text-xs text-slate-500">
            {t.profile.selectedLabel} <span className="font-medium">{selectedFile.name}</span>
          </p>
        )}
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
      </div>

      {/* Option 2: paste resume text (existing flow) */}
      <div className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
        {t.profile.option2}
      </div>
      <textarea
        className="mt-2 h-56 w-full rounded-lg border border-slate-300 p-3 text-sm focus:border-brand-500 focus:outline-none"
        placeholder={t.profile.pastePh}
        value={resumeText}
        onChange={(e) => setResumeText(e.target.value)}
      />

      <div className="mt-3 flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {saving ? t.common.saving : t.profile.saveProfile}
        </button>
        {error && <span className="text-sm text-red-600">{error}</span>}
      </div>

      <hr className="my-8 border-slate-200" />

      <h2 className="text-lg font-semibold">{t.profile.extracted}</h2>
      {loading ? (
        <p className="mt-2 text-sm text-slate-500">{t.common.loading}</p>
      ) : !profile ? (
        <div className="mt-4">
          <EmptyState title={t.profile.emptyTitle} description={t.profile.emptyDesc} />
        </div>
      ) : (
        <div className="mt-4 space-y-4 rounded-lg border border-slate-200 bg-white p-5">
          <div>
            <div className="text-xs font-semibold uppercase text-slate-500">
              {t.profile.skills}
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              {profile.skills.length === 0 ? (
                <span className="text-sm text-slate-400">{t.profile.noneDetected}</span>
              ) : (
                profile.skills.map((s) => (
                  <span
                    key={s}
                    className="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700"
                  >
                    {s}
                  </span>
                ))
              )}
            </div>
          </div>

          <div>
            <div className="text-xs font-semibold uppercase text-slate-500">
              {t.profile.expSummary}
            </div>
            <p className="mt-1 text-sm text-slate-700">
              {profile.experience_summary || "—"}
            </p>
          </div>

          <div>
            <div className="text-xs font-semibold uppercase text-slate-500">
              {t.profile.targetRoles}
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
