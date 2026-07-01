"use client";

import { useEffect, useRef, useState } from "react";
import { api, Profile } from "@/lib/api";
import { EmptyState, PageHeader, WorkflowHint } from "@/components/ui";

export default function ProfilePage() {
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

  async function handleUpload() {
    if (!selectedFile) {
      setUploadError("Please choose a .pdf or .docx file first.");
      return;
    }
    setUploading(true);
    setUploadError(null);
    setUploadNotice(null);
    try {
      const p = await api.uploadResumeFile(selectedFile);
      setProfile(p);
      setUploadNotice(`Parsed “${selectedFile.name}” and updated your profile.`);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Failed to upload resume");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Profile"
        subtitle="Upload a PDF/DOCX or paste resume text. We extract your skills and a short summary locally — no LLM, nothing leaves your machine."
      />

      <WorkflowHint>
        Your skills power <strong>role ranking</strong> in Opportunities and personalize every
        outreach draft.
      </WorkflowHint>

      {/* Option 1: upload a resume file */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Option 1 · Upload a resume file
        </div>
        <p className="mt-1 text-sm text-slate-600">
          Accepts <span className="font-medium">.pdf</span> or{" "}
          <span className="font-medium">.docx</span>. Files are parsed locally by
          the backend for this MVP — nothing is sent to a third party.
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
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {uploading ? "Uploading…" : "Upload Resume File"}
          </button>
        </div>

        {selectedFile && !uploading && (
          <p className="mt-2 text-xs text-slate-500">
            Selected: <span className="font-medium">{selectedFile.name}</span>
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
        Option 2 · Paste resume text
      </div>
      <textarea
        className="mt-2 h-56 w-full rounded-lg border border-slate-300 p-3 text-sm focus:border-blue-500 focus:outline-none"
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
