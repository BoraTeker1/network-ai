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
  created_at: string | null;
  updated_at: string | null;
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

  // Demo
  seedDemo: () => request<SeedResult>("/demo/seed", { method: "POST" }),
};
