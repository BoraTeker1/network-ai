"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError, OutreachDraft, Checklist, ContactGuidance } from "@/lib/api";
import {
  PageHeader,
  ErrorBanner,
  QualityChecklist,
  SectionLabel,
  TrustLine,
} from "@/components/ui";
import UpgradeCallout from "@/components/UpgradeCallout";

type Language = "en" | "tr";
type Channel = "email" | "linkedin";
type Region = "remote" | "europe" | "global" | "turkey";

const LANG_LABEL: Record<Language, string> = { en: "English", tr: "Türkçe" };
const CHANNEL_LABEL: Record<Channel, string> = {
  email: "Email",
  linkedin: "LinkedIn note",
};
const REGION_LABEL: Record<Region, string> = {
  remote: "Remote",
  europe: "Europe",
  global: "Global",
  turkey: "Turkey",
};

function Toggle<T extends string>({
  value,
  options,
  onChange,
  labels,
}: {
  value: T;
  options: T[];
  onChange: (v: T) => void;
  labels: Record<T, string>;
}) {
  return (
    <div className="inline-flex rounded-md border border-slate-300 bg-white p-0.5">
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          onClick={() => onChange(opt)}
          className={`rounded px-3 py-1 text-sm font-medium ${
            value === opt
              ? "bg-blue-600 text-white"
              : "text-slate-600 hover:text-blue-600"
          }`}
        >
          {labels[opt]}
        </button>
      ))}
    </div>
  );
}

function RiskChecklist({ checklist }: { checklist: Checklist }) {
  return (
    <div className="rounded-md border border-slate-100 bg-slate-50 p-3">
      <div className="flex items-center justify-between">
        <SectionLabel>Risk checklist</SectionLabel>
        <span className="text-xs font-medium text-green-700">
          {checklist.passed}/{checklist.total} passed
        </span>
      </div>
      <ul className="mt-2 grid gap-1 sm:grid-cols-2">
        {checklist.items.map((item) => (
          <li
            key={item.key}
            className={`flex items-center gap-1.5 text-xs ${
              item.passed ? "text-slate-600" : "text-slate-400"
            }`}
          >
            <span>{item.passed ? "✓" : "○"}</span>
            <span>{item.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const input =
  "rounded-md border border-slate-300 p-2 text-sm focus:border-blue-500 focus:outline-none";

export default function OutreachPage() {
  const [jdText, setJdText] = useState("");
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [name, setName] = useState("");
  const [title, setTitle] = useState("");
  const [language, setLanguage] = useState<Language>("en");
  const [channel, setChannel] = useState<Channel>("email");
  const [region, setRegion] = useState<Region>("remote");

  const [includeLocation, setIncludeLocation] = useState(true);
  const [timezoneOverlap, setTimezoneOverlap] = useState("");
  const [includeWorkAuth, setIncludeWorkAuth] = useState(false);
  const [workAuthNote, setWorkAuthNote] = useState("");
  const [skillHighlight, setSkillHighlight] = useState("");

  const [draft, setDraft] = useState<OutreachDraft | null>(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");

  // Preserved opportunity context (set when arriving from the feed) so a saved
  // pipeline item links back to its source opportunity + apply URL.
  const [opportunityId, setOpportunityId] = useState<number | null>(null);
  const [jobUrl, setJobUrl] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [savedId, setSavedId] = useState<number | null>(null);

  // "Who to contact" guidance, loaded up-front so the user finds a real person
  // BEFORE drafting (then pastes the name above and drafts to them).
  const [guidance, setGuidance] = useState<ContactGuidance | null>(null);
  const [guidanceLoading, setGuidanceLoading] = useState(false);
  const [contactSaved, setContactSaved] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [planLimit, setPlanLimit] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  function handleApiError(e: unknown, fallback: string) {
    if (e instanceof ApiError && e.code === "plan_limit") {
      setPlanLimit(e.message);
      return;
    }
    setError(e instanceof Error ? e.message : fallback);
  }

  // Prefill from an opportunity the user clicked "Draft outreach" on.
  useEffect(() => {
    const raw = sessionStorage.getItem("outreach_prefill");
    if (!raw) return;
    try {
      const p = JSON.parse(raw);
      if (p.jd_text) setJdText(p.jd_text);
      if (typeof p.id === "number") setOpportunityId(p.id);
      if (p.url) setJobUrl(p.url);
      const lang: Language = p.language === "tr" ? "tr" : "en";
      if (p.company) {
        setCompany(p.company);
        loadGuidance(p.company, lang); // show who-to-contact straight away
      }
      if (p.role) setRole(p.role);
      if (p.language === "tr" || p.language === "en") setLanguage(p.language);
      if (["remote", "europe", "global", "turkey"].includes(p.target_region))
        setRegion(p.target_region);
      if (typeof p.include_location_line === "boolean")
        setIncludeLocation(p.include_location_line);
      setNotice("Prefilled from the opportunity feed — review and draft.");
    } catch {
      /* ignore malformed prefill */
    }
    sessionStorage.removeItem("outreach_prefill");
  }, []);

  async function loadGuidance(co = company, lang = language) {
    co = co.trim();
    if (!co) return;
    setGuidanceLoading(true);
    try {
      setGuidance(await api.getContactGuidance(co, lang));
    } catch {
      /* guidance is a non-essential helper — never block the flow on it */
    } finally {
      setGuidanceLoading(false);
    }
  }

  async function saveContact() {
    if (!name.trim()) {
      setError("Add the contact's name first (find one via the search links).");
      return;
    }
    setError(null);
    try {
      await api.addManualContact({
        name: name.trim(),
        title: title.trim() || undefined,
        company: company.trim() || undefined,
        source_note: "Found via the outreach copilot's search links.",
      });
      setContactSaved(true);
      setNotice("Saved to your contacts.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't save the contact.");
    }
  }

  async function generate() {
    if (!jdText.trim()) {
      setError("Paste a job description first.");
      return;
    }
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      const result = await api.draftOutreachFromPaste({
        jd_text: jdText,
        contact: { name, title, company },
        company,
        role,
        language,
        channel,
        target_region: region,
        timezone_overlap: timezoneOverlap || undefined,
        include_location_line: includeLocation,
        include_work_auth_line: includeWorkAuth,
        work_authorization_note: workAuthNote || undefined,
        skill_highlight: skillHighlight || undefined,
      });
      setDraft(result);
      setSubject(result.subject);
      setBody(result.body);
      setSavedId(null); // a fresh draft hasn't been saved yet
    } catch (e) {
      handleApiError(e, "Failed to draft outreach.");
    } finally {
      setLoading(false);
    }
  }

  async function saveToPipeline() {
    if (!draft || !body.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const saved = await api.saveOutreachToPipeline({
        body,
        subject: draft.channel === "email" ? subject : null,
        company: company || draft.detected_company || null,
        role: role || draft.detected_role || null,
        channel: draft.channel,
        language: draft.language,
        opportunity_id: opportunityId,
        job_url: jobUrl || null,
        contact_name: name || null,
        contact_title: title || null,
        status: "copied",
      });
      setSavedId(saved.id);
      setNotice("Saved to your pipeline — track it there.");
    } catch (e) {
      handleApiError(e, "Couldn't save to pipeline.");
    } finally {
      setSaving(false);
    }
  }

  async function copy() {
    const text = subject ? `Subject: ${subject}\n\n${body}` : body;
    try {
      await navigator.clipboard.writeText(text);
      setNotice("Copied. Send it yourself from your own inbox/LinkedIn.");
    } catch {
      setNotice("Couldn't access the clipboard — select and copy manually.");
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-6 py-8">
      <PageHeader
        title="Outreach copilot"
        subtitle="For Turkish engineers targeting Turkey, remote, European, or global roles. Paste a job you found (or start one from Opportunities), find the right people to contact in two clicks, then get an honest, low-pressure draft in English or Turkish — personalized with your saved profile skills."
      />

      <TrustLine />

      <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div>
          <label className="text-sm font-medium text-slate-700">
            Job description (paste it yourself — no scraping)
          </label>
          <textarea
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
            rows={7}
            placeholder="Paste the full job posting here…"
            className={`mt-1 w-full ${input}`}
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <input value={company} onChange={(e) => setCompany(e.target.value)} onBlur={() => loadGuidance()} placeholder="Company" className={input} />
          <input value={role} onChange={(e) => setRole(e.target.value)} placeholder="Role title (optional)" className={input} />
          <input value={name} onChange={(e) => { setName(e.target.value); setContactSaved(false); }} placeholder="Contact name" className={input} />
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Their title (optional)" className={input} />
        </div>

        {/* Who to contact — surfaced BEFORE drafting so the user finds a real
            person first, then pastes the name above and drafts to them. */}
        {(guidance || guidanceLoading) && (
          <div className="space-y-3 rounded-md border border-blue-100 bg-blue-50/50 p-4">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-slate-900">
                Who to contact{guidance?.company ? ` at ${guidance.company}` : ""}
              </h3>
              {name.trim() && (
                <button
                  type="button"
                  onClick={saveContact}
                  className="shrink-0 rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  {contactSaved ? "Saved ✓" : "Save to my contacts"}
                </button>
              )}
            </div>
            {guidanceLoading && !guidance ? (
              <p className="text-xs text-slate-500">Finding the right roles…</p>
            ) : guidance ? (
              <>
                <p className="text-xs text-slate-500">{guidance.note}</p>
                <ol className="space-y-1.5">
                  {guidance.recommended_contact_roles
                    .slice()
                    .sort((a, b) => a.priority - b.priority)
                    .map((r) => (
                      <li key={r.role} className="flex gap-2 text-sm">
                        <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-semibold text-blue-700">
                          {r.priority}
                        </span>
                        <div>
                          <span className="font-medium text-slate-800">{r.label}</span>
                          <span className="text-slate-500"> — {r.why}</span>
                        </div>
                      </li>
                    ))}
                </ol>
                <div>
                  <SectionLabel>Search for a name, then paste it above</SectionLabel>
                  <ul className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1">
                    {guidance.manual_search_links.map((l) => (
                      <li key={l.url}>
                        <a href={l.url} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline">
                          {l.label} ↗
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            ) : null}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <SectionLabel>Language</SectionLabel>
            <Toggle
              value={language}
              options={["en", "tr"]}
              onChange={(l) => { setLanguage(l); if (guidance) loadGuidance(company, l); }}
              labels={LANG_LABEL}
            />
          </div>
          <div className="flex items-center gap-2">
            <SectionLabel>Channel</SectionLabel>
            <Toggle value={channel} options={["email", "linkedin"]} onChange={setChannel} labels={CHANNEL_LABEL} />
          </div>
          <div className="flex items-center gap-2">
            <SectionLabel>Target</SectionLabel>
            <Toggle
              value={region}
              options={["remote", "europe", "global", "turkey"]}
              onChange={setRegion}
              labels={REGION_LABEL}
            />
          </div>
        </div>

        <div className="space-y-2 rounded-md border border-slate-100 bg-slate-50 p-3">
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={includeLocation} onChange={(e) => setIncludeLocation(e.target.checked)} />
            Add a “based in Turkey / CET-compatible hours” line
          </label>
          {includeLocation && (
            <input
              value={timezoneOverlap}
              onChange={(e) => setTimezoneOverlap(e.target.value)}
              placeholder="Timezone note (optional, e.g. Istanbul time with CET overlap)"
              className={`w-full ${input}`}
            />
          )}
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={includeWorkAuth} onChange={(e) => setIncludeWorkAuth(e.target.checked)} />
            Include a work-authorization note (your own words only)
          </label>
          {includeWorkAuth && (
            <input
              value={workAuthNote}
              onChange={(e) => setWorkAuthNote(e.target.value)}
              placeholder="e.g. EU citizen, no sponsorship needed — only what's true for you"
              className={`w-full ${input}`}
            />
          )}
          <input
            value={skillHighlight}
            onChange={(e) => setSkillHighlight(e.target.value)}
            placeholder="Optional: your own skill/project highlight line (overrides the auto one)"
            className={`w-full ${input}`}
          />
        </div>

        <div className="flex items-center">
          <button
            onClick={generate}
            disabled={loading}
            className="ml-auto rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Drafting…" : "Draft outreach"}
          </button>
        </div>

        <ErrorBanner message={error} />
        {planLimit && <UpgradeCallout message={planLimit} />}
      </div>

      {draft && (
        <>
          {/* 1. Draft message */}
          <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-600">{LANG_LABEL[draft.language]}</span>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-600">{CHANNEL_LABEL[draft.channel]}</span>
              {draft.target_region && (
                <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-600">
                  {REGION_LABEL[draft.target_region as Region] ?? draft.target_region}
                </span>
              )}
              <span
                className={`rounded-full px-2 py-0.5 font-medium ${
                  draft.llm_used ? "bg-violet-100 text-violet-800" : "bg-slate-100 text-slate-500"
                }`}
              >
                {draft.llm_used ? "AI-written (Claude)" : "Template (no AI key set)"}
              </span>
              {draft.relevant_skills.length > 0 && (
                <span className="text-slate-500">skills: {draft.relevant_skills.join(", ")}</span>
              )}
            </div>

            {draft.channel === "email" && (
              <div>
                <SectionLabel>Subject</SectionLabel>
                <input value={subject} onChange={(e) => setSubject(e.target.value)} className={`mt-1 w-full ${input}`} />
              </div>
            )}

            <div>
              <SectionLabel>Message — edit before you send</SectionLabel>
              <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={10} className={`mt-1 w-full ${input}`} />
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {savedId ? (
                <Link
                  href="/pipeline"
                  className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                >
                  Saved ✓ · View in pipeline →
                </Link>
              ) : (
                <button
                  onClick={saveToPipeline}
                  disabled={saving}
                  className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? "Saving…" : "Save to pipeline"}
                </button>
              )}
              <button onClick={copy} className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:border-slate-400 hover:bg-slate-50">
                Copy message
              </button>
              {notice && <span className="text-sm text-green-700">{notice}</span>}
            </div>

            {draft.why_safe && (
              <p className="rounded-md border border-slate-100 bg-slate-50 p-3 text-sm text-slate-600">{draft.why_safe}</p>
            )}
          </div>

          {/* 2 + 3. Checklists */}
          <div className="grid gap-4 sm:grid-cols-2">
            <QualityChecklist checklist={draft.quality_checklist} />
            <RiskChecklist checklist={draft.risk_checklist} />
          </div>

          {/* Follow-up timing (who-to-contact is shown up-front, above the draft) */}
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
            <SectionLabel>Suggested follow-up</SectionLabel>
            <p className="mt-1 text-sm text-amber-900">{draft.suggested_follow_up}</p>
          </div>
        </>
      )}
    </div>
  );
}
