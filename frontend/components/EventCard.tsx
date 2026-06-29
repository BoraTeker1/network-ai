// Shared rendering for event recommendations + manual search links.
// Used by both the dashboard "Networking events" card and the /events page.

import type { EventRecommendation, EventSearchQuery } from "@/lib/api";

const FRESHNESS_STYLES: Record<string, string> = {
  fresh: "bg-green-100 text-green-800",
  upcoming: "bg-amber-100 text-amber-800",
  stale_unknown: "bg-slate-100 text-slate-500",
};

const FRESHNESS_LABELS: Record<string, string> = {
  fresh: "Fresh",
  upcoming: "Upcoming",
  stale_unknown: "Date unknown",
};

const CONFIDENCE_STYLES: Record<string, string> = {
  high: "bg-emerald-50 text-emerald-700",
  medium: "bg-sky-50 text-sky-700",
  low: "bg-slate-100 text-slate-500",
};

const EVENT_TYPE_LABELS: Record<string, string> = {
  conference: "Conference",
  meetup: "Meetup",
  career_fair: "Career fair",
  hackathon: "Hackathon",
  tech_talk: "Tech talk",
  webinar: "Webinar",
  other: "Event",
};

const PROVIDER_LABELS: Record<string, string> = {
  confs_tech: "confs.tech",
  kommunity: "Kommunity",
  eventbrite: "Eventbrite",
  meetup: "Meetup",
  luma: "Luma",
};

/** Friendly display name for a provider / source key. */
export function providerLabel(key: string): string {
  return PROVIDER_LABELS[key] ?? key.replace(/_/g, " ");
}

export function FreshnessBadge({ label }: { label: string }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
        FRESHNESS_STYLES[label] ?? FRESHNESS_STYLES.stale_unknown
      }`}
    >
      {FRESHNESS_LABELS[label] ?? label}
    </span>
  );
}

export function ConfidenceBadge({ level }: { level: string }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
        CONFIDENCE_STYLES[level] ?? CONFIDENCE_STYLES.low
      }`}
    >
      {level} confidence
    </span>
  );
}

function formatWhen(rec: EventRecommendation): string {
  if (!rec.start_datetime) return "Date TBD — verify on source";
  const start = new Date(rec.start_datetime);
  if (Number.isNaN(start.getTime())) return "Date TBD — verify on source";
  return start.toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatFetched(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** A single real, provider-backed event. Always shows source + freshness. */
export function EventCard({
  rec,
  compact = false,
}: {
  rec: EventRecommendation;
  compact?: boolean;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium uppercase tracking-wide text-slate-600">
              {EVENT_TYPE_LABELS[rec.event_type] ?? "Event"}
            </span>
            <FreshnessBadge label={rec.freshness_label} />
            {!compact && <ConfidenceBadge level={rec.confidence} />}
          </div>
          <div className="mt-1.5 font-semibold text-slate-900">{rec.title}</div>
          <div className="mt-0.5 text-sm text-slate-600">
            {formatWhen(rec)}
            {rec.location ? ` · ${rec.location}` : ""}
            {rec.is_online ? " · Online" : ""}
          </div>
        </div>
      </div>

      <p className="mt-2 text-sm text-slate-700">{rec.relevance_reason}</p>
      {rec.matched_terms.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {rec.matched_terms.slice(0, 6).map((t) => (
            <span
              key={t}
              className="rounded-full bg-green-50 px-2 py-0.5 text-xs text-green-700"
            >
              ✓ {t}
            </span>
          ))}
        </div>
      )}

      {!compact && (
        <div className="mt-3 text-xs text-slate-400">
          Source: {providerLabel(rec.source_name)} · Fetched{" "}
          {formatFetched(rec.fetched_at)}
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        <a
          href={rec.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          View event ↗
        </a>
      </div>
    </div>
  );
}

/** A manual, prefilled search link (the safe fallback — invents nothing). */
export function SearchLinkRow({
  link,
  onCopyQuery,
  copied,
}: {
  link: EventSearchQuery;
  onCopyQuery?: (query: string) => void;
  copied?: boolean;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 rounded-lg border border-slate-200 bg-white p-4">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="rounded bg-indigo-50 px-1.5 py-0.5 text-[11px] font-medium uppercase tracking-wide text-indigo-600">
            {link.provider}
          </span>
          <span className="text-sm font-medium text-slate-800">{link.label}</span>
        </div>
        <p className="mt-1 text-xs text-slate-500">{link.why}</p>
        <p className="mt-1 break-words font-mono text-xs text-slate-400">
          {link.query}
        </p>
      </div>
      <div className="flex shrink-0 gap-2">
        {onCopyQuery && (
          <button
            onClick={() => onCopyQuery(link.query)}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:border-blue-400"
          >
            {copied ? "Copied!" : "Copy query"}
          </button>
        )}
        <a
          href={link.url}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-blue-600 hover:border-blue-400"
        >
          Search ↗
        </a>
      </div>
    </div>
  );
}
