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

export type Job = {
  id: number;
  source: string;
  company: string | null;
  title: string | null;
  location: string | null;
  url: string | null;
  created_at: string | null;
};

export type MatchBreakdownItem = {
  label: string;
  points: number;
  max: number;
  detail: string;
};

export type RankedMatch = {
  job_id: number;
  company: string | null;
  title: string | null;
  location: string | null;
  url: string | null;
  match_score: number;
  recommendation: string | null;
  next_best_action: string | null;
  explanation: string | null;
  matched_skills: string[];
  missing_skills: string[];
  breakdown: MatchBreakdownItem[];
};

export type MatchResult = {
  job_id: number;
  company: string | null;
  title: string | null;
  location?: string | null;
  url?: string | null;
  match_score: number;
  recommendation: string | null;
  next_best_action: string | null;
  explanation: string | null;
  matched_skills: string[];
  missing_skills: string[];
  breakdown: MatchBreakdownItem[];
};

export type StrategyStep = {
  step: number;
  title: string;
  detail: string;
};

export type OutreachStrategy = {
  label: string;
  score: number;
  who_first: string;
  contact_count: string;
  tone: string;
  ask_type: string;
  sequence: StrategyStep[];
  next_best_action: string;
};

export type ContactSearch = {
  label: string;
  query: string;
  google_search_url: string;
  linkedin_search_url: string;
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

// ----- Momentum (Vibe Mode gamification) -----

export type MomentumAward = {
  event_type: string;
  points: number;
  label: string;
  celebration: "big" | "medium" | "small" | "none";
  message: string;
};

export type MomentumWin = {
  event_type: string;
  label: string;
  points: number;
  created_at: string | null;
};

export type MomentumSummary = {
  points_today: number;
  total_points: number;
  streak: number;
  recent_wins: MomentumWin[];
};

export type Message = {
  id: number;
  job_id: number | null;
  company: string | null;
  title: string | null;
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
  momentum?: MomentumAward | null;
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
  job_id: number | null;
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
  momentum?: MomentumAward | null;
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

export type FunnelStage = { label: string; value: number };

export type DashboardStats = {
  total_jobs: number;
  total_matches: number;
  strong_targets: number;
  total_messages: number;
  status_counts: Record<string, number>;
  outcome_counts: Record<string, number>;
  follow_ups_due: number;
  funnel: FunnelStage[];
  top_matches: RankedMatch[];
  recent_messages: Message[];
};

export type OutcomesResponse = {
  supported: string[];
  counts: Record<string, number>;
  messages: Message[];
};

export type SeedResult = {
  ok: boolean;
  actions: string[];
  total_jobs: number;
  total_messages: number;
};

export type IngestResult = {
  ingested: number;
  skipped_duplicates: number;
  parsed_rows: number;
  total_in_db: number;
  source: string;
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...options,
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(detail);
  }
  // Some endpoints may return empty bodies; guard against that.
  const text = await res.text();
  return (text ? JSON.parse(text) : null) as T;
}

export const api = {
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

  // Jobs
  ingestJobs: () =>
    request<IngestResult>("/jobs/ingest/simplify", { method: "POST" }),
  getJobs: (limit = 100) => request<Job[]>(`/jobs?limit=${limit}`),
  getJob: (id: number) => request<Job>(`/jobs/${id}`),
  matchJob: (id: number) =>
    request<MatchResult>(`/jobs/${id}/match`, { method: "POST" }),
  matchAll: () =>
    request<{ profile_id: number; matched_jobs: number }>("/jobs/match-all", {
      method: "POST",
    }),
  getRankedMatches: (limit = 25) =>
    request<RankedMatch[]>(`/jobs/matches/ranked?limit=${limit}`),
  getContactSearches: (id: number) =>
    request<ContactSearch[]>(`/jobs/${id}/contact-searches`),
  getStrategy: (id: number) =>
    request<OutreachStrategy>(`/jobs/${id}/strategy`),

  // Messages
  generateMessages: (
    job_id: number,
    contact_name?: string,
    contact_title?: string
  ) =>
    request<Message[]>("/messages/generate", {
      method: "POST",
      body: JSON.stringify({
        job_id,
        contact_name: contact_name || null,
        contact_title: contact_title || null,
      }),
    }),
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

  // Insights / dashboard
  getStats: () => request<DashboardStats>("/stats"),
  getOutcomes: () => request<OutcomesResponse>("/outcomes"),

  // Momentum (Vibe Mode gamification)
  getMomentum: () => request<MomentumSummary>("/momentum/summary"),

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
    job_id: number;
    contact_id: number;
    goal_id?: number | null;
    tone?: string;
  }) =>
    request<EmailDraft>("/emails/draft", {
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
  seedDemo: () => request<SeedResult>("/demo/seed", { method: "POST" }),
};
