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
import { useT } from "@/lib/i18n";

type Language = "en" | "tr";
type Channel = "email" | "linkedin";
type Region = "remote" | "europe" | "global" | "turkey";



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
              ? "bg-brand-600 text-white"
              : "text-slate-600 hover:text-brand-600"
          }`}
        >
          {labels[opt]}
        </button>
      ))}
    </div>
  );
}

function RiskChecklist({ checklist }: { checklist: Checklist }) {
  const t = useT();
  return (
    <div className="rounded-md border border-slate-100 bg-slate-50 p-3">
      <div className="flex items-center justify-between">
        <SectionLabel>{t.outreach.riskChecklist}</SectionLabel>
        <span className="text-xs font-medium text-green-700">
          {t.ui.checklistPassed(checklist.passed, checklist.total)}
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
  "rounded-md border border-slate-300 p-2 text-sm focus:border-brand-500 focus:outline-none";

export default function OutreachPage() {
  const t = useT();
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

  // Entry mode: the primary path is arriving prefilled from /opportunities;
  // pasting an external posting is the secondary "Harici ilan ekle" path.
  const [hasPrefill, setHasPrefill] = useState(false);
  const [showManual, setShowManual] = useState(false);
  const [showJd, setShowJd] = useState(false);

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
      setHasPrefill(true);
      setNotice(t.outreach.prefilledNotice);
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
      setError(t.outreach.addContactFirst);
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
      setNotice(t.outreach.contactSavedNotice);
    } catch (e) {
      setError(e instanceof Error ? e.message : t.outreach.contactSaveFailed);
    }
  }

  async function generate() {
    if (!jdText.trim()) {
      setError(t.outreach.pasteJdFirst);
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
      handleApiError(e, t.outreach.draftFailed);
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
      setNotice(t.outreach.savedPipelineNotice);
    } catch (e) {
      handleApiError(e, t.outreach.savePipelineFailed);
    } finally {
      setSaving(false);
    }
  }

  async function copy() {
    const text = subject ? `Subject: ${subject}\n\n${body}` : body;
    try {
      await navigator.clipboard.writeText(text);
      setNotice(t.outreach.copiedNotice);
    } catch {
      setNotice(t.outreach.clipboardFailed);
    }
  }

  // No job selected yet and manual mode not chosen → point at the feed first.
  if (!hasPrefill && !showManual && !draft) {
    return (
      <div className="mx-auto max-w-3xl space-y-6 px-6 py-8">
        <PageHeader title={t.outreach.title} subtitle={t.outreach.subtitle} />
        <TrustLine />
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center">
          <div className="text-base font-semibold text-slate-800">
            {t.outreach.pickTitle}
          </div>
          <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">
            {t.outreach.pickDesc}
          </p>
          <Link
            href="/opportunities"
            className="mt-4 inline-block rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            {t.outreach.pickCta}
          </Link>
          <div className="mt-3">
            <button
              onClick={() => setShowManual(true)}
              className="text-sm font-medium text-slate-500 hover:text-slate-800 hover:underline"
            >
              {t.outreach.addExternal}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-6 py-8">
      <PageHeader title={t.outreach.title} subtitle={t.outreach.subtitle} />

      <TrustLine />

      <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        {hasPrefill && !showManual ? (
          /* Primary path: the selected opportunity, prefilled. JD is editable
             behind a disclosure instead of dominating the page. */
          <div className="rounded-md border border-brand-100 bg-brand-50/40 p-3">
            <SectionLabel>{t.outreach.selectedJob}</SectionLabel>
            <div className="mt-1 text-base font-semibold leading-snug text-slate-900">
              {role || company}
            </div>
            <div className="text-sm text-slate-600">
              {role ? company : null}
              {jobUrl && (
                <>
                  {role ? " · " : null}
                  <a
                    href={jobUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-brand-600 hover:underline"
                  >
                    {t.opportunities.openApplication}
                  </a>
                </>
              )}
            </div>
            <button
              onClick={() => setShowJd((v) => !v)}
              className="mt-2 text-xs font-medium text-slate-500 hover:text-slate-800"
            >
              {t.outreach.editJd} {showJd ? "▴" : "▾"}
            </button>
            {showJd && (
              <textarea
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                rows={7}
                className={`mt-2 w-full ${input}`}
              />
            )}
          </div>
        ) : (
          /* Secondary path: paste an external posting yourself. */
          <div>
            <label className="text-sm font-medium text-slate-700">
              {t.outreach.jdLabel}
            </label>
            <p className="text-xs text-slate-500">{t.outreach.addExternalHint}</p>
            <textarea
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              rows={7}
              placeholder={t.outreach.jdPlaceholder}
              className={`mt-1 w-full ${input}`}
            />
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          {(!hasPrefill || showManual) && (
            <>
              <input value={company} onChange={(e) => setCompany(e.target.value)} onBlur={() => loadGuidance()} placeholder={t.outreach.companyPh} className={input} />
              <input value={role} onChange={(e) => setRole(e.target.value)} placeholder={t.outreach.rolePh} className={input} />
            </>
          )}
          <input value={name} onChange={(e) => { setName(e.target.value); setContactSaved(false); }} placeholder={t.outreach.namePh} className={input} />
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={t.outreach.titlePh} className={input} />
        </div>

        {/* Who to contact — surfaced BEFORE drafting so the user finds a real
            person first, then pastes the name above and drafts to them. */}
        {(guidance || guidanceLoading) && (
          <div className="space-y-3 rounded-md border border-brand-100 bg-brand-50/50 p-4">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-slate-900">
                {t.outreach.whoToContact(guidance?.company ?? "")}
              </h3>
              {name.trim() && (
                <button
                  type="button"
                  onClick={saveContact}
                  className="shrink-0 rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  {contactSaved ? t.outreach.savedTick : t.outreach.saveContact}
                </button>
              )}
            </div>
            {guidanceLoading && !guidance ? (
              <p className="text-xs text-slate-500">{t.outreach.findingRoles}</p>
            ) : guidance ? (
              <>
                <p className="text-xs text-slate-500">{guidance.note}</p>
                <ol className="space-y-1.5">
                  {guidance.recommended_contact_roles
                    .slice()
                    .sort((a, b) => a.priority - b.priority)
                    .map((r) => (
                      <li key={r.role} className="flex gap-2 text-sm">
                        <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-semibold text-brand-700">
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
                  <SectionLabel>{t.outreach.searchForName}</SectionLabel>
                  <ul className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1">
                    {guidance.manual_search_links.map((l) => (
                      <li key={l.url}>
                        <a href={l.url} target="_blank" rel="noopener noreferrer" className="text-sm text-brand-600 hover:underline">
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
            <SectionLabel>{t.outreach.languageLabel}</SectionLabel>
            <Toggle
              value={language}
              options={["en", "tr"]}
              onChange={(l) => { setLanguage(l); if (guidance) loadGuidance(company, l); }}
              labels={t.outreach.language}
            />
          </div>
          <div className="flex items-center gap-2">
            <SectionLabel>{t.outreach.channelLabel}</SectionLabel>
            <Toggle value={channel} options={["email", "linkedin"]} onChange={setChannel} labels={t.outreach.channel} />
          </div>
          <div className="flex items-center gap-2">
            <SectionLabel>{t.outreach.targetLabel}</SectionLabel>
            <Toggle
              value={region}
              options={["remote", "europe", "global", "turkey"]}
              onChange={setRegion}
              labels={t.opportunities.region as Record<Region, string>}
            />
          </div>
        </div>

        <div className="space-y-2 rounded-md border border-slate-100 bg-slate-50 p-3">
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={includeLocation} onChange={(e) => setIncludeLocation(e.target.checked)} />
            {t.outreach.locationLine}
          </label>
          {includeLocation && (
            <input
              value={timezoneOverlap}
              onChange={(e) => setTimezoneOverlap(e.target.value)}
              placeholder={t.outreach.timezonePh}
              className={`w-full ${input}`}
            />
          )}
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={includeWorkAuth} onChange={(e) => setIncludeWorkAuth(e.target.checked)} />
            {t.outreach.workAuthLine}
          </label>
          {includeWorkAuth && (
            <input
              value={workAuthNote}
              onChange={(e) => setWorkAuthNote(e.target.value)}
              placeholder={t.outreach.workAuthPh}
              className={`w-full ${input}`}
            />
          )}
          <input
            value={skillHighlight}
            onChange={(e) => setSkillHighlight(e.target.value)}
            placeholder={t.outreach.skillPh}
            className={`w-full ${input}`}
          />
        </div>

        <div className="flex items-center">
          <button
            onClick={generate}
            disabled={loading}
            className="ml-auto rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {loading ? t.outreach.drafting : t.outreach.draftBtn}
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
              <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-600">{t.outreach.language[draft.language]}</span>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-600">{t.outreach.channel[draft.channel]}</span>
              {draft.target_region && (
                <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-600">
                  {(t.opportunities.region as Record<string, string>)[draft.target_region] ?? draft.target_region}
                </span>
              )}
              <span
                className={`rounded-full px-2 py-0.5 font-medium ${
                  draft.llm_used ? "bg-violet-100 text-violet-800" : "bg-slate-100 text-slate-500"
                }`}
              >
                {draft.llm_used ? t.outreach.aiWritten : t.outreach.templateNoKey}
              </span>
              {draft.relevant_skills.length > 0 && (
                <span className="text-slate-500">{t.outreach.skillsUsed(draft.relevant_skills.join(", "))}</span>
              )}
            </div>

            {draft.channel === "email" && (
              <div>
                <SectionLabel>{t.outreach.subject}</SectionLabel>
                <input value={subject} onChange={(e) => setSubject(e.target.value)} className={`mt-1 w-full ${input}`} />
              </div>
            )}

            <div>
              <SectionLabel>{t.outreach.messageEdit}</SectionLabel>
              <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={10} className={`mt-1 w-full ${input}`} />
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {savedId ? (
                <Link
                  href="/pipeline"
                  className="rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
                >
                  {t.outreach.savedView}
                </Link>
              ) : (
                <button
                  onClick={saveToPipeline}
                  disabled={saving}
                  className="rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
                >
                  {saving ? t.common.saving : t.outreach.saveToPipeline}
                </button>
              )}
              <button onClick={copy} className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:border-slate-400 hover:bg-slate-50">
                {t.outreach.copyMessage}
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
            <SectionLabel>{t.outreach.suggestedFollowUp}</SectionLabel>
            <p className="mt-1 text-sm text-amber-900">{draft.suggested_follow_up}</p>
          </div>
        </>
      )}
    </div>
  );
}
