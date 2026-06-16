// Vibe Mode — a focused 25-minute networking sprint with mood-based music.
//
// IMPORTANT (product guardrails):
// - We NEVER host audio. Every mood points at a third-party *embed* player.
// - Music NEVER autoplays — the embed requires the user to press play.
// - The embeds below are curated, swappable defaults. To change a mood's
//   soundtrack, just replace `embedUrl` with any embed URL from:
//     Spotify:    https://open.spotify.com/embed/playlist/<id>
//     SoundCloud: https://w.soundcloud.com/player/?url=<encoded-track-or-set-url>
//     YouTube:    https://www.youtube-nocookie.com/embed/videoseries?list=<id>
//   (Do not add an autoplay parameter.)

export type VibeProvider = "Spotify" | "SoundCloud" | "YouTube";

export type VibeMood = {
  id: string; // stable key persisted to localStorage
  name: string;
  tagline: string;
  description: string;
  accent: string; // tailwind gradient for the mood chip/accent
  provider: VibeProvider;
  embedUrl: string;
};

export const VIBE_SPRINT_MINUTES = 25;
export const VIBE_SPRINT_SECONDS = VIBE_SPRINT_MINUTES * 60;

export const VIBE_STORAGE_KEYS = {
  mood: "vibe-mode:mood",
  checklist: "vibe-mode:checklist",
} as const;

export const VIBE_MOODS: VibeMood[] = [
  {
    id: "sunset-house",
    name: "Sunset House",
    tagline: "Warm, golden-hour grooves",
    description: "Easy, melodic house to start the sprint without friction.",
    accent: "from-orange-400 to-pink-500",
    provider: "Spotify",
    embedUrl: "https://open.spotify.com/embed/playlist/37i9dQZF1DX4WYpdgoIcn6",
  },
  {
    id: "deep-house-focus",
    name: "Deep House Focus",
    tagline: "Steady, heads-down momentum",
    description: "Minimal vocals, deep grooves — for reviewing matches in flow.",
    accent: "from-indigo-500 to-blue-600",
    provider: "Spotify",
    embedUrl: "https://open.spotify.com/embed/playlist/37i9dQZF1DWZeKCadgRdKQ",
  },
  {
    id: "rooftop-outreach",
    name: "Rooftop Outreach",
    tagline: "Bright, confident energy",
    description: "Upbeat and social — the vibe for approving and sending drafts.",
    accent: "from-amber-400 to-rose-500",
    provider: "Spotify",
    embedUrl: "https://open.spotify.com/embed/playlist/37i9dQZF1DX3rxVfibe1L0",
  },
  {
    id: "late-night-follow-up",
    name: "Late Night Follow-Up",
    tagline: "Low-key, focused calm",
    description: "Chilled lo-fi for quiet follow-ups and updating your pipeline.",
    accent: "from-slate-600 to-indigo-700",
    provider: "Spotify",
    embedUrl: "https://open.spotify.com/embed/playlist/37i9dQZF1DWWQRwui0ExPn",
  },
  {
    id: "interview-energy",
    name: "Interview Energy",
    tagline: "Get-up, get-ready hype",
    description: "Higher tempo to shake off nerves before a call or interview.",
    accent: "from-emerald-500 to-teal-600",
    provider: "Spotify",
    embedUrl: "https://open.spotify.com/embed/playlist/37i9dQZF1DX76Wlfdnj7AP",
  },
];

// The four-step sprint checklist. Each step deep-links to the page where the
// work actually happens — Vibe Mode organizes the existing workflow, it never
// changes it (no scraping, no auto-send, no bulk; manual approval only).
export const VIBE_CHECKLIST: { id: string; label: string; href: string }[] = [
  { id: "matches", label: "Review strong matches", href: "/matches" },
  { id: "approve", label: "Approve drafts", href: "/messages" },
  { id: "send", label: "Copy / manual-send outreach", href: "/emails" },
  { id: "outcomes", label: "Update pipeline outcomes", href: "/pipeline" },
];

export function defaultMood(): VibeMood {
  return VIBE_MOODS[0];
}

export function findMood(id: string | null | undefined): VibeMood {
  return VIBE_MOODS.find((m) => m.id === id) ?? defaultMood();
}

/** Pad seconds into mm:ss. */
export function formatSprint(totalSeconds: number): string {
  const clamped = Math.max(0, totalSeconds);
  const m = Math.floor(clamped / 60)
    .toString()
    .padStart(2, "0");
  const s = (clamped % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}
