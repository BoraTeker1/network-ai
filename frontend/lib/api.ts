// Tiny typed API client for the Network AI backend.
// All calls are local-first against the FastAPI server.

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Profile = {
  id: number;
  user_id: string;
  skills: string[];
  education: string | null;
  experience_summary: string | null;
  target_roles: string[];
  created_at: string | null;
};

export type ChecklistItem = {
  key: string;
  label: string;
  passed: boolean;
};

export type Checklist = {
  items: ChecklistItem[];
  passed: number;
  total: number;
};


// ----- Next Move AI -----

export type NextMoveTarget = {
  type: "message" | "email" | null;
  id: number | null;
};

export type NextMoveAnalysis = {
  summary: string;
  intent: string;
  signals: string[];
  urgency: "low" | "medium" | "high";
  recommended_next_action: string;
  risk_notes: string;
  suggested_pipeline_update: string | null;
  drafted_email: { subject: string; body: string };
  drafted_short_message: string;
  quality_checklist: Checklist;
  safety_checklist: Checklist;
  pipeline_target: NextMoveTarget;
  llm_used: boolean;
};

export type NextMoveInput = {
  reply_text: string;
  job_id?: number | null;
  contact_id?: number | null;
  message_id?: number | null;
  email_id?: number | null;
};

// ----- Paste-a-JD bilingual outreach (Turkey → remote/EU wedge) -----

export type ContactRole = {
  role: string;
  label: string;
  why: string;
  priority: number;
};

export type ManualSearchLink = { label: string; url: string };

export type ContactGuidance = {
  company: string;
  recommended_contact_roles: ContactRole[];
  contact_priority_order: string[];
  manual_search_links: ManualSearchLink[];
  note: string;
};

export type OutreachDraft = {
  subject: string;
  body: string;
  language: "en" | "tr";
  channel: "email" | "linkedin";
  message_type: string;
  tone: string;
  detected_company: string | null;
  detected_role: string | null;
  target_region: string | null;
  based_in: string;
  relevant_skills: string[];
  personalization_notes: string | null;
  quality_checklist: Checklist;
  risk_checklist: Checklist;
  why_safe: string | null;
  suggested_next_step: string | null;
  suggested_follow_up: string;
  contact_guidance: ContactGuidance;
  llm_used: boolean;
};

export type OutreachPasteInput = {
  jd_text: string;
  contact?: { name?: string; title?: string; company?: string };
  language?: "en" | "tr";
  channel?: "email" | "linkedin";
  tone?: string;
  company?: string;
  role?: string;
  target_region?: "remote" | "europe" | "global" | "turkey" | null;
  based_in?: string;
  timezone_overlap?: string;
  work_authorization_note?: string;
  include_location_line?: boolean;
  include_work_auth_line?: boolean;
  skill_highlight?: string;
};

// ----- Curated Turkey + Remote/EU opportunity feed -----

export type OutreachPrefill = {
  id?: number;
  company: string;
  role: string;
  jd_text: string;
  url?: string;
  target_region: "turkey" | "europe" | "remote" | "global";
  language: "en" | "tr";
  include_location_line: boolean;
};

export type OutreachSaveInput = {
  body: string;
  subject?: string | null;
  company?: string | null;
  role?: string | null;
  channel: "email" | "linkedin";
  language: "en" | "tr";
  opportunity_id?: number | null;
  job_url?: string | null;
  contact_name?: string | null;
  contact_title?: string | null;
  status?: string;
};

export type OpportunityMatch = {
  matched_skills: string[];
  missing_skills: string[];
  matched_count: number;
  total_skills: number;
  reason: string | null;
};

export type Opportunity = {
  id: number;
  source: string;
  company: string | null;
  title: string | null;
  location: string | null;
  url: string | null;
  source_url: string | null;
  target_region: string;
  seniority_level: string;
  job_function: string;
  remote_policy: string;
  country_scope: string | null;
  turkey_applicability_label: string | null;
  turkey_applicability_reason: string | null;
  language_expectation: string | null;
  work_auth_note: string | null;
  tags: string[];
  date_posted: string | null;
  is_sample: boolean;
  source_provider: string | null;
  source_confidence: string | null;
  outreach_prefill: OutreachPrefill;
  match: OpportunityMatch;
};

export type OpportunitiesResponse = {
  count: number;
  function: string;
  applicability_labels: Record<string, string>;
  items: Opportunity[];
};

export type OpportunityFilters = {
  region?: string;
  seniority?: string;
  remote?: boolean;
  applicability?: string;
  tag?: string;
  source?: string;
  confidence?: string;
  function?: string; // all|software_engineering|business|other|any
  include_ineligible?: boolean;
};

export type OpportunitySource = {
  id: string;
  company_name: string;
  ats_provider: string;
  board_token: string | null;
  careers_url: string;
  country_scope: string;
  company_category: string;
  enabled: boolean;
  live: boolean;
  source_confidence: string;
  notes: string;
};

export type RefreshSourceResult = {
  id: string;
  company: string;
  provider: string;
  status: "success" | "failed" | "skipped";
  jobs_imported: number;
  created?: number;
  error?: string;
};

export type RefreshSourcesResult = {
  sources: RefreshSourceResult[];
  created: number;
  succeeded: number;
  failed: number;
  skipped: number;
  total: number;
};

export type RefreshAllResult = {
  created: number;
  succeeded: number;
  failed: number;
  skipped: number;
  errors: string[];
  ats: RefreshSourcesResult;
  public: { created: number; updated: number; errors: string[]; total: number };
  total: number;
};

export type Message = {
  id: number;
  job_id: number | null;
  opportunity_id: number | null;
  company: string | null;
  title: string | null;
  subject: string | null;
  channel: string | null;
  language: string | null;
  job_url: string | null;
  contact_name: string | null;
  contact_title: string | null;
  message_type: string;
  tone: string;
  draft_text: string | null;
  status: string;
  outcome: string | null;
  follow_up_status: string | null;
  follow_up_due_date: string | null;
  char_count: number;
  checklist: Checklist;
  // Present only on action responses (approve/copy/sent/outcome/follow-up).
  created_at: string | null;
  updated_at: string | null;
};

// ----- AI outreach layer -----

export const OUTREACH_GOALS = [
  "advice",
  "referral",
  "recruiter_intro",
  "hiring_manager_intro",
  "founder_intro",
] as const;

export const CONTACT_TYPES = [
  "recruiter",
  "technical_recruiter",
  "hiring_manager",
  "engineer",
  "alumni",
  "founder",
] as const;

export type Goal = {
  id: number;
  target_role: string | null;
  target_location: string | null;
  target_company_type: string | null;
  outreach_goal: string | null;
  tone_preference: string | null;
  max_contacts_per_company: number | null;
  preferred_contact_types: string[];
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type GoalInput = {
  target_role?: string;
  target_location?: string;
  target_company_type?: string;
  outreach_goal?: string;
  tone_preference?: string;
  max_contacts_per_company?: number;
  preferred_contact_types?: string[];
  notes?: string;
};

export type Contact = {
  id: number;
  job_id: number | null;
  name: string | null;
  title: string | null;
  company: string | null;
  email: string | null;
  linkedin_url: string | null;
  contact_type: string | null;
  email_confidence: number | null;
  source: string;
  source_note: string | null;
  why_relevant: string | null;
  risk_note: string | null;
  created_at: string | null;
};

export type ManualContactInput = {
  name: string;
  title?: string;
  company?: string;
  email?: string;
  linkedin_url?: string;
  contact_type?: string;
  email_confidence?: number;
  source_note?: string;
  job_id?: number;
};

export type DiscoverResult = {
  id?: number;
  name: string | null;
  title: string | null;
  company: string | null;
  email: string | null;
  email_confidence: number | null;
  source: string;
  contact_type: string | null;
  why_relevant: string | null;
  risk_note: string | null;
};

export type DiscoverResponse = {
  api_discovery_configured: boolean;
  providers_available: string[];
  message: string;
  results: DiscoverResult[];
};

export type EmailDraft = {
  id: number;
  opportunity_id: number | null;
  job_id: number | null; // legacy rows only
  contact_id: number | null;
  goal_id: number | null;
  company: string | null;
  role: string | null;
  contact_name: string | null;
  contact_title: string | null;
  contact_email: string | null;
  contact_why_relevant: string | null;
  subject: string | null;
  body: string | null;
  message_type: string;
  tone: string | null;
  personalization_notes: string | null;
  quality_checklist: Checklist;
  risk_checklist: Checklist;
  why_safe: string | null;
  suggested_next_step: string | null;
  llm_used: boolean;
  // Present only on action responses (approve/copy/sent/outcome/follow-up).
  status: string;
  outcome: string | null;
  follow_up_status: string | null;
  follow_up_due_date: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type GmailSendResponse = {
  ok: boolean;
  sent: boolean;
  status: string;
  message: string;
};

export const OUTCOMES = [
  "connected",
  "replied",
  "referral_received",
  "interview_received",
  "ignored",
  "rejected",
] as const;
export type Outcome = (typeof OUTCOMES)[number];

// Follow-up states (separate from outcome). "none" clears tracking.
export const FOLLOW_UP_STATUSES = [
  "follow_up_needed",
  "followed_up",
  "no_response",
] as const;
export type FollowUpStatus = (typeof FOLLOW_UP_STATUSES)[number];

// ----- Meetings (people you actually met — presence tracking) -----

/** Typed API error: `status` for auth handling (401 → login), `code` for
 * structured errors like plan limits ("plan_limit" → upgrade callout). */
export class ApiError extends Error {
  status: number;
  code?: string;
  detail: unknown;

  constructor(status: number, message: string, detail?: unknown, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.code = code;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    credentials: "include", // send/receive the na_session cookie
    ...options,
  });
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    let detail: unknown;
    let code: string | undefined;
    try {
      const body = await res.json();
      detail = body?.detail;
      if (typeof detail === "string") {
        message = detail;
      } else if (detail && typeof detail === "object") {
        const d = detail as { message?: string; code?: string };
        if (d.message) message = d.message;
        if (d.code) code = d.code;
      }
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new ApiError(res.status, message, detail, code);
  }
  // Some endpoints may return empty bodies; guard against that.
  const text = await res.text();
  return (text ? JSON.parse(text) : null) as T;
}

// ----- Auth / billing types -----

export type CurrentUser = {
  id: string;
  email: string;
  plan: "free" | "pro" | "admin";
  created_at: string | null;
};

export type BillingOverview = {
  plan: string;
  limits: Record<string, number | null>;
  usage: Record<string, number>;
};

export type PricingPlan = {
  id: string;
  name: string;
  price_monthly_usd: number;
  features: string[];
};

export const api = {
  // Auth (session cookie is HttpOnly; JS never sees the token)
  signup: (email: string, password: string) =>
    request<CurrentUser>("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    request<CurrentUser>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () => request<{ status: string }>("/auth/logout", { method: "POST" }),
  // null = not logged in (a 401 here is a normal state, not an error).
  me: async (): Promise<CurrentUser | null> => {
    try {
      return await request<CurrentUser>("/auth/me");
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return null;
      throw e;
    }
  },

  // Product events (first-party, validation sprint). Fire-and-forget: analytics
  // must never break or slow the UI, so failures are swallowed.
  trackEvent: (event: string, note?: string): void => {
    request("/events", {
      method: "POST",
      body: JSON.stringify({ event, note }),
    }).catch(() => {});
  },

  // Eligibility-label feedback (validates the Turkey-applicability classifier).
  sendLabelFeedback: (
    opportunityId: number,
    verdict: "right" | "wrong",
    reason?: string,
  ) =>
    request<{ status: string }>(`/opportunities/${opportunityId}/label-feedback`, {
      method: "POST",
      body: JSON.stringify({ verdict, reason: reason || undefined }),
    }),

  // Billing / plans
  getBillingPlan: () => request<BillingOverview>("/billing/plan"),
  getBillingPlans: () =>
    request<{ plans: PricingPlan[]; beta: boolean }>("/billing/plans"),
  checkout: () =>
    request<{ status: string; message: string; plan: string }>(
      "/billing/checkout",
      { method: "POST" },
    ),

  // Profile
  getProfile: () => request<Profile>("/profile"),
  saveProfile: (resume_text: string) =>
    request<Profile>("/profile/resume-text", {
      method: "POST",
      body: JSON.stringify({ resume_text }),
    }),
  uploadResumeFile: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    // Empty headers => browser sets the multipart boundary itself (don't force
    // application/json here, or FastAPI can't parse the upload).
    return request<Profile>("/profile/resume-file", {
      method: "POST",
      body: form,
      headers: {},
    });
  },

  // Messages (pipeline workflow — drafts are created by the /outreach copilot)
  getMessages: () => request<Message[]>("/messages"),
  patchMessage: (id: number, draft_text: string) =>
    request<Message>(`/messages/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ draft_text }),
    }),
  approveMessage: (id: number) =>
    request<Message>(`/messages/${id}/approve`, { method: "POST" }),
  rejectMessage: (id: number) =>
    request<Message>(`/messages/${id}/reject`, { method: "POST" }),
  markCopied: (id: number) =>
    request<Message>(`/messages/${id}/mark-copied`, { method: "POST" }),
  markSentManually: (id: number) =>
    request<Message>(`/messages/${id}/mark-sent-manually`, { method: "POST" }),
  setOutcome: (id: number, outcome: string, note?: string) =>
    request<Message>(`/messages/${id}/outcome`, {
      method: "POST",
      body: JSON.stringify({ outcome, note: note ?? null }),
    }),
  setFollowUp: (id: number, status: string, due_date?: string | null) =>
    request<Message>(`/messages/${id}/follow-up`, {
      method: "POST",
      body: JSON.stringify({ status, due_date: due_date ?? null }),
    }),

  // Next Move AI (analyze a pasted reply; never auto-reads anything)
  analyzeNextMove: (input: NextMoveInput) =>
    request<NextMoveAnalysis>("/next-move/analyze", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  // Paste-a-JD bilingual outreach (paste a JD you found yourself; draft TR/EN)
  draftOutreachFromPaste: (input: OutreachPasteInput) =>
    request<OutreachDraft>("/outreach/draft-from-paste", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  // Save a reviewed outreach draft as a tracked pipeline item (never sends).
  saveOutreachToPipeline: (input: OutreachSaveInput) =>
    request<Message>("/outreach/save-draft", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  // Who to contact at a company + safe search links, BEFORE drafting.
  getContactGuidance: (company: string, language: "en" | "tr" = "en") =>
    request<ContactGuidance>(
      `/outreach/contact-guidance?company=${encodeURIComponent(company)}&language=${language}`,
    ),

  // Curated Turkey + Remote/EU opportunity feed (no scraping; seeded sample +
  // public feeds + manual import). GET never hits the network.
  getOpportunities: (filters: OpportunityFilters = {}) => {
    const params = new URLSearchParams();
    if (filters.region) params.set("region", filters.region);
    if (filters.seniority) params.set("seniority", filters.seniority);
    if (filters.remote) params.set("remote", "true");
    if (filters.applicability) params.set("applicability", filters.applicability);
    if (filters.tag) params.set("tag", filters.tag);
    if (filters.source) params.set("source", filters.source);
    if (filters.confidence) params.set("confidence", filters.confidence);
    if (filters.function) params.set("function", filters.function);
    if (filters.include_ineligible) params.set("include_ineligible", "true");
    const qs = params.toString();
    return request<OpportunitiesResponse>(`/opportunities${qs ? `?${qs}` : ""}`);
  },
  getOpportunitySources: () =>
    request<{ sources: OpportunitySource[] }>("/opportunities/sources"),
  refreshOpportunitySources: () =>
    request<RefreshSourcesResult>("/opportunities/refresh-sources", { method: "POST" }),
  // Pull everything in one click: official ATS boards + public job APIs.
  refreshAllSources: () =>
    request<RefreshAllResult>("/opportunities/refresh-all", { method: "POST" }),

  // Goals
  getGoals: () => request<Goal[]>("/goals"),
  createGoal: (goal: GoalInput) =>
    request<Goal>("/goals", { method: "POST", body: JSON.stringify(goal) }),
  updateGoal: (id: number, goal: GoalInput) =>
    request<Goal>(`/goals/${id}`, { method: "PATCH", body: JSON.stringify(goal) }),
  deleteGoal: (id: number) =>
    request<{ status: string; id: number }>(`/goals/${id}`, { method: "DELETE" }),

  // Contacts
  getContacts: (jobId?: number) =>
    request<Contact[]>(`/contacts${jobId != null ? `?job_id=${jobId}` : ""}`),
  addManualContact: (input: ManualContactInput) =>
    request<Contact>("/contacts/manual", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  discoverContacts: (input: {
    job_id?: number;
    goal_id?: number;
    contact_type: string;
    max_results?: number;
  }) =>
    request<DiscoverResponse>("/contacts/discover", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  // Emails (AI draft + approval queue; never auto-sends)
  draftEmail: (input: {
    opportunity_id: number;
    contact_id: number;
    goal_id?: number | null;
    tone?: string;
  }) =>
    request<EmailDraft>("/emails/draft", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  // LinkedIn drafts (connection note / post-accept DM). Stored as EmailDraft
  // rows, so they reuse every /emails approval + tracking action below.
  draftLinkedIn: (input: {
    opportunity_id: number;
    contact_id: number;
    goal_id?: number | null;
    kind?: "connection" | "dm";
    tone?: string;
  }) =>
    request<EmailDraft>("/linkedin/draft", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  getEmails: () => request<EmailDraft[]>("/emails"),
  getEmail: (id: number) => request<EmailDraft>(`/emails/${id}`),
  patchEmail: (
    id: number,
    patch: {
      subject?: string;
      body?: string;
      outcome?: string;
      follow_up_status?: string;
      follow_up_due_date?: string | null;
    }
  ) =>
    request<EmailDraft>(`/emails/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  approveEmail: (id: number) =>
    request<EmailDraft>(`/emails/${id}/approve`, { method: "POST" }),
  rejectEmail: (id: number) =>
    request<EmailDraft>(`/emails/${id}/reject`, { method: "POST" }),
  markEmailCopied: (id: number) =>
    request<EmailDraft>(`/emails/${id}/mark-copied`, { method: "POST" }),
  markEmailSentManual: (id: number) =>
    request<EmailDraft>(`/emails/${id}/mark-sent-manual`, { method: "POST" }),
  sendEmailGmail: (id: number, confirm_send = false) =>
    request<GmailSendResponse>(`/emails/${id}/send-gmail`, {
      method: "POST",
      body: JSON.stringify({ confirm_send }),
    }),

  // Demo
};
