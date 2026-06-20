"""Event / conference networking recommendations.

Answers one question for the user: *"Where can I meet people connected to my
strongest job opportunity this week/month?"* — based on the deterministic
strongest job match of the day (reuses the matcher) plus the saved goal.

Hard rules (these are the whole point of the feature):
- NEVER invent events. Every real recommendation comes verbatim from a
  configured provider API and carries a source_url, fetched_at timestamp, and
  whatever date/location the provider returned.
- No scraping. No browser automation. No protected sites (LinkedIn, Indeed,
  Handshake, Google Events, etc.). Provider adapters call documented public
  APIs only, gated behind env keys.
- Permission-first: nothing is registered, no one is emailed, no calendar is
  touched. We surface links; the user decides.
- Degrade gracefully: when no API keys are configured (or a provider returns
  nothing), the feature still produces high-quality MANUAL search links with
  prefilled queries, and says so honestly.

Provider adapters are intentionally small and mirror the job-ingestion style
(plain `requests`, deterministic parsing, no LLM).
"""

from __future__ import annotations

import dataclasses
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import requests
from sqlalchemy.orm import Session

from .. import config
from ..models import DEMO_USER_ID, Goal
from . import matcher

# ----- Controlled vocabularies -----

EVENT_TYPES = (
    "conference",
    "meetup",
    "career_fair",
    "hackathon",
    "tech_talk",
    "webinar",
    "other",
)
FRESHNESS_LABELS = ("fresh", "upcoming", "stale_unknown")
CONFIDENCE_LEVELS = ("high", "medium", "low")

# An event landing further out than this (or with no date) can't be "fresh".
_FRESH_WINDOW_DAYS = 14

# Role-family inference from a job title. First match wins (most specific top).
# `keywords` are short search phrases used to build provider queries + manual
# links; `title_terms` are substrings we look for in the strongest match title.
_ROLE_FAMILIES: list[tuple[str, list[str], list[str]]] = [
    ("AI / ML engineering", ["AI engineer", "machine learning", "MLOps"],
     ["machine learning", "ml engineer", "ai engineer", "ai/ml",
      "artificial intelligence", "data scientist", "applied scientist",
      "deep learning", "nlp"]),
    ("Data engineering", ["data engineering", "data engineer", "analytics engineering"],
     ["data engineer", "data engineering", "analytics engineer"]),
    ("Backend engineering", ["backend engineering", "backend developer", "APIs"],
     ["backend", "back end", "back-end"]),
    ("Frontend engineering", ["frontend engineering", "frontend developer", "web development"],
     ["frontend", "front end", "front-end"]),
    ("Full-stack engineering", ["full stack engineering", "full stack developer"],
     ["full stack", "full-stack"]),
    ("DevOps / Platform / SRE", ["devops", "platform engineering", "site reliability"],
     ["devops", "platform engineer", "infrastructure engineer",
      "site reliability", "sre", "cloud engineer"]),
    ("Mobile engineering", ["mobile engineering", "iOS development", "Android development"],
     ["mobile engineer", "android", "ios"]),
    ("Security engineering", ["security engineering", "cybersecurity"],
     ["security engineer", "cybersecurity", "infosec"]),
    ("Software engineering", ["software engineering", "software developer"],
     ["software engineer", "software developer", "sde", "swe"]),
]
_DEFAULT_FAMILY = ("Software engineering", ["software engineering", "tech"])

# confs.tech open dataset: one JSON file per (year, topic). Map each role family
# to the most relevant topic files so we pull conferences that actually fit the
# user's target — the topic match IS the relevance signal here (no firehose).
_CONFS_TECH_FAMILY_TOPICS: dict[str, list[str]] = {
    "AI / ML engineering": ["data", "python", "general"],
    "Data engineering": ["data", "python", "general"],
    "Backend engineering": ["api", "java", "python", "dotnet", "rust", "general"],
    "Frontend engineering": ["javascript", "typescript", "css", "performance", "general"],
    "Full-stack engineering": ["javascript", "typescript", "api", "general"],
    "DevOps / Platform / SRE": ["devops", "sre", "networking", "general"],
    "Mobile engineering": ["android", "ios", "kotlin", "general"],
    "Security engineering": ["security", "general"],
    "Software engineering": ["general", "javascript", "python", "api"],
}
_CONFS_TECH_DEFAULT_TOPICS = ["general"]

# Words that classify an event by type (checked against title/description text).
_TYPE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("hackathon", ["hackathon", "hack day", "hack night", "codefest"]),
    ("career_fair", ["career fair", "job fair", "recruiting event",
                     "recruiting fair", "hiring event", "career expo"]),
    ("conference", ["conference", "summit", "convention", "expo", "symposium",
                    "con 20", "devcon", "kubecon"]),
    ("tech_talk", ["tech talk", "lightning talk", "lecture", "fireside",
                   "workshop", "seminar"]),
    ("webinar", ["webinar", "virtual event", "online event", "livestream"]),
    ("meetup", ["meetup", "meet-up", "networking", "user group", "mixer"]),
]

_DISCLAIMER = (
    "We do not guarantee availability; verify on the source before attending. "
    "Events are surfaced from configured providers or as manual search links — "
    "nothing is registered or sent on your behalf."
)


# ----- Data structures -----

@dataclass
class EventSearchQuery:
    """A deterministic, prefilled MANUAL search link (the safe fallback)."""

    label: str
    provider: str            # google / eventbrite / meetup / luma / company
    query: str               # human-readable query string
    url: str                 # prefilled search URL the user opens themselves
    why: str                 # why this search is relevant to the strongest match


@dataclass
class EventRecommendation:
    """A single real event returned verbatim by a provider. Never invented."""

    title: str
    organizer: str | None
    event_type: str          # one of EVENT_TYPES
    relevance_reason: str
    matched_terms: list[str]
    start_datetime: str | None
    end_datetime: str | None
    location: str | None
    is_online: bool | None
    source_name: str         # provider that returned it (e.g. "ticketmaster")
    source_url: str
    fetched_at: str          # ISO-8601 UTC timestamp of the fetch
    freshness_label: str     # one of FRESHNESS_LABELS
    confidence: str          # one of CONFIDENCE_LEVELS
    rank_score: float = 0.0  # surfaced for transparency/debuggability


@dataclass
class EventProviderResult:
    """Per-provider status so the UI can be honest about what ran."""

    provider: str
    configured: bool
    ok: bool
    count: int
    note: str


@dataclass
class EventRecommendationResponse:
    ready: bool
    message: str
    strongest_match: dict | None
    search_context: dict
    filters: dict
    providers: list[EventProviderResult] = field(default_factory=list)
    recommendations: list[EventRecommendation] = field(default_factory=list)
    search_links: list[EventSearchQuery] = field(default_factory=list)
    disclaimer: str = _DISCLAIMER


# ----- Helpers -----

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _slug(text: str) -> str:
    """URL-path slug: lowercase, spaces/punctuation -> single hyphens."""
    out = "".join(c.lower() if c.isalnum() else "-" for c in (text or ""))
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


def _google_url(query: str) -> str:
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)


def _role_family(title: str | None) -> tuple[str, list[str]]:
    """Map a job title to (family_label, search_keywords)."""
    low = (title or "").lower()
    for label, keywords, terms in _ROLE_FAMILIES:
        if any(t in low for t in terms):
            return label, keywords
    return _DEFAULT_FAMILY


def _is_remote_pref(location: str | None) -> bool:
    low = (location or "").lower()
    return "remote" in low or "anywhere" in low


# Location strings that are NOT a physical city and must never be sent as a
# geo filter to a provider (Ticketmaster would return 0 results for "Remote").
_NON_CITY_VALUES = {
    "remote", "anywhere", "united states", "usa", "us", "u.s.", "u.s.a.",
    "america", "multiple locations", "various", "various locations",
    "hybrid", "n/a", "na", "none", "tbd", "flexible", "nationwide",
    "worldwide", "global", "unknown",
}


def _clean_city(value: str | None) -> str | None:
    """Return a usable city string, or None for remote/non-city values."""
    if not value:
        return None
    v = value.strip().strip(",.").strip()
    if not v:
        return None
    low = v.lower()
    if low in _NON_CITY_VALUES:
        return None
    # A "Remote …" / "Hybrid …" / "Anywhere …" prefix means no real locality,
    # even when extra text follows (e.g. "Remote - US", "Remote (USA)").
    for marker in ("remote", "anywhere", "hybrid"):
        if low == marker or low.startswith(f"{marker} ") or low.startswith(
            f"{marker}-"
        ) or low.startswith(f"{marker},") or low.startswith(f"{marker}("):
            return None
    return v


def normalize_event_location(
    raw_location: str | None,
    goal_location: str | None,
    user_location: str | None = None,
) -> str | None:
    """Resolve the best *real city* to search near, or None for remote/unknown.

    Preference order: an explicit user-provided location, then the goal's target
    location, then the job's location — using the first that looks like a real
    city. Returns None when none of them name a physical place (Remote, Anywhere,
    United States, Multiple Locations, etc.), so callers never geo-filter on a
    non-city value.
    """
    for candidate in (user_location, goal_location, raw_location):
        city = _clean_city(candidate)
        if city:
            return city
    return None


def _classify_event_type(text: str, is_online: bool | None) -> str:
    """Best-effort event-type from the event's own text. Defaults to 'other'."""
    low = (text or "").lower()
    for etype, words in _TYPE_KEYWORDS:
        if any(w in low for w in words):
            # Don't mislabel an in-person talk as a webinar just because the
            # word 'online' appears; webinar requires the online signal too.
            if etype == "webinar" and not is_online:
                continue
            return etype
    return "webinar" if is_online else "other"


def _parse_dt(value: str | None) -> datetime | None:
    """Parse an ISO datetime or plain date string into an aware UTC datetime."""
    if not value:
        return None
    raw = value.strip().replace("Z", "+00:00")
    for parse in (datetime.fromisoformat,):
        try:
            dt = parse(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    # Plain date (YYYY-MM-DD) — treat as midnight UTC.
    try:
        dt = datetime.strptime(raw[:10], "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _freshness(start: datetime | None, now: datetime) -> str:
    if start is None:
        return "stale_unknown"
    if start <= now + timedelta(days=_FRESH_WINDOW_DAYS):
        return "fresh"
    return "upcoming"


def _confidence(*, has_date: bool, has_location: bool, matched: int) -> str:
    if has_date and (has_location or matched) and matched:
        return "high"
    if has_date or has_location:
        return "medium"
    return "low"


def _matched_terms(text: str, context: dict) -> list[str]:
    """Which of the context's search terms literally appear in the event text."""
    low = (text or "").lower()
    candidates = [context["company"]] if context.get("company") else []
    candidates += context.get("role_family_keywords", [])
    candidates += context.get("matched_skills", [])
    seen: list[str] = []
    for term in candidates:
        if term and term.lower() in low and term not in seen:
            seen.append(term)
    return seen


# ----- Search context (from the strongest match + goal) -----

def _best_match(db: Session) -> dict | None:
    ranked = matcher.ranked_matches(db, limit=1)
    return ranked[0] if ranked else None


def _goal(db: Session) -> Goal | None:
    return (
        db.query(Goal)
        .filter(Goal.user_id == DEMO_USER_ID)
        .order_by(Goal.id.desc())
        .first()
    )


def build_search_context(
    db: Session, *, location_override: str | None = None
) -> tuple[dict, dict | None]:
    """Build the keyword/location context that drives provider + manual search.

    Returns (context, strongest_match). Works even with no profile/match by
    falling back to the goal and then to generic tech-networking terms, so the
    feature is never blank.
    """
    best = _best_match(db)
    goal = _goal(db)

    job_title = (best or {}).get("title")
    company = (best or {}).get("company")
    matched_skills = list((best or {}).get("matched_skills") or [])[:5]

    family_label, family_keywords = _role_family(
        job_title or (goal.target_role if goal else None)
    )

    goal_location = goal.target_location if goal and goal.target_location else None
    job_location = (best or {}).get("location")
    user_location = (location_override or "").strip() or None

    # Human-readable resolved location (may be "Remote") — used in the UI.
    display_location = user_location or goal_location or job_location
    # The real city to geo-filter on (None when everything is remote/unknown).
    city = normalize_event_location(job_location, goal_location, user_location)
    # "Remote" means: we have a location string, but it's not a usable city.
    is_remote = display_location is not None and city is None

    context = {
        "job_title": job_title,
        "company": company,
        "role_family": family_label,
        "role_family_keywords": family_keywords,
        "matched_skills": matched_skills,
        "location": display_location,
        "city": city,
        "is_remote": is_remote,
        "is_remote_pref": _is_remote_pref(display_location),
        # The flat keyword list other layers can reuse.
        "keywords": [k for k in ([company] + family_keywords + matched_skills) if k],
    }
    return context, best


# ----- Manual search links (always available) -----

def build_search_links(context: dict) -> list[EventSearchQuery]:
    """5–8 deterministic, prefilled manual search links from the context.

    These are the honest fallback when no provider events are found; they invent
    nothing and always point at a real search the user runs themselves.
    """
    family = context["role_family"]
    primary = context["role_family_keywords"][0]
    company = context.get("company")
    city = context.get("city")
    has_city = bool(city)
    # Phrase geo-specific links with the real city, or "near me" when remote.
    loc = city if has_city else "near me"
    month_year = _now().strftime("%B %Y")

    links: list[EventSearchQuery] = []

    def add(label, provider, query, url, why):
        links.append(EventSearchQuery(label=label, provider=provider,
                                      query=query, url=url, why=why))

    # 1–2: Google meetup / networking near the (real) location or "near me".
    q1 = f"{primary} meetup {loc} {month_year}".strip()
    add("Local meetups this month", "google", q1, _google_url(q1),
        f"Finds {family} meetups {loc} happening now.")
    q2 = f"{primary} networking events {loc}".strip()
    add("Local networking events", "google", q2, _google_url(q2),
        f"Surfaces {family} networking events {loc}.")

    # 3: conference near location.
    q3 = f"{primary} conference {loc}".strip()
    add("Conferences nearby", "google", q3, _google_url(q3),
        f"Larger {family} conferences {loc}.")

    # 4: new-grad career fair.
    q4 = f"new grad software engineer career fair {loc}".strip()
    add("New-grad career fairs", "google", q4, _google_url(q4),
        f"Career fairs aimed at new-grad software engineers {loc}.")

    # Remote-only nudge: example cities so the user picks a real place to meet
    # people, instead of staring at zero local events.
    if not has_city:
        for example in ("Atlanta", "New York"):
            eq = f"{primary} meetup {example}"
            add(f"Try a hub city: {example}", "google", eq, _google_url(eq),
                f"Your match is remote — try {family} meetups in {example} or "
                "another city you can travel to.")

    # 5–6: company-specific events (only when we know the company).
    if company:
        q5 = f"{company} engineering event {month_year}"
        add(f"{company} events", "company", q5, _google_url(q5),
            f"Talks / meetups hosted by {company}'s engineering org.")
        q6 = f"{company} university recruiting event"
        add(f"{company} campus recruiting", "company", q6, _google_url(q6),
            f"Where {company} recruiters meet early-career candidates.")

    # 7: Eventbrite search (geo or online).
    eb_geo = _slug(city) if has_city else "online"
    eb_q = _slug(primary)
    eb_url = f"https://www.eventbrite.com/d/{eb_geo}/{eb_q}/"
    add("Eventbrite", "eventbrite", f"{primary} {loc}".strip(), eb_url,
        f"Eventbrite listings for {family} {loc}."
        if has_city else f"Online Eventbrite listings for {family}.")

    # 8: Meetup search.
    mu_params = {"keywords": primary}
    if has_city:
        mu_params["location"] = city
    mu_url = "https://www.meetup.com/find/?" + urllib.parse.urlencode(mu_params)
    add("Meetup", "meetup", f"{primary} {loc}".strip(), mu_url,
        f"Recurring {family} Meetup groups {loc}.")

    # 9: Luma — no open search API, so route a site-restricted Google search.
    lu_q = f"site:lu.ma {primary} {city or ''}".strip()
    add("Luma (lu.ma)", "luma", lu_q, _google_url(lu_q),
        f"Luma-hosted {family} events (via a site-restricted search).")

    return links


# ----- Provider adapters -----

def _fetch_ticketmaster_raw(params: dict) -> dict:
    """Thin HTTP boundary for the Ticketmaster Discovery API (mockable in tests)."""
    resp = requests.get(
        "https://app.ticketmaster.com/discovery/v2/events.json",
        params=params,
        timeout=20,
        headers={"User-Agent": "network-ai/0.1"},
    )
    resp.raise_for_status()
    return resp.json()


def _ticketmaster_provider(
    context: dict, filters: dict, fetched_at: str
) -> tuple[EventProviderResult, list[EventRecommendation]]:
    """Ticketmaster Discovery API adapter. Returns real events only, or empty.

    Ticketmaster skews toward concerts/sports, so we KEEP an event only when it
    matches a context term or classifies as a tech/career/networking event —
    keeping results honest and relevant rather than padded.
    """
    api_key = config.get_ticketmaster_api_key()
    if not api_key:
        return (EventProviderResult("ticketmaster", False, False, 0,
                                    "Set TICKETMASTER_API_KEY to enable."), [])

    now = _now()
    params: dict = {
        "apikey": api_key,
        "size": 30,
        "sort": "date,asc",
        "startDateTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDateTime": (now + timedelta(days=filters["days_ahead"])).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "keyword": context["role_family_keywords"][0],
    }
    # Only geo-filter on a REAL city. A remote/unknown match leaves the city out
    # so Ticketmaster falls back to a keyword (+ online) search instead of
    # matching the non-city "Remote" and returning nothing.
    if filters.get("city"):
        params["city"] = filters["city"]
        params["radius"] = filters.get("radius_miles") or 50
        params["unit"] = "miles"

    try:
        data = _fetch_ticketmaster_raw(params)
    except Exception as exc:  # never crash the endpoint on a provider failure
        return (EventProviderResult("ticketmaster", True, False, 0,
                                    f"Request failed: {type(exc).__name__}"), [])

    events = (data.get("_embedded") or {}).get("events") or []
    recs: list[EventRecommendation] = []
    for ev in events:
        rec = _ticketmaster_to_rec(ev, context, filters, fetched_at, now)
        if rec is not None:
            recs.append(rec)

    note = "OK" if recs else "No matching tech/networking events in range."
    return (EventProviderResult("ticketmaster", True, True, len(recs), note), recs)


def _ticketmaster_to_rec(
    ev: dict, context: dict, filters: dict, fetched_at: str, now: datetime
) -> EventRecommendation | None:
    """Map one Ticketmaster event dict -> EventRecommendation, or None to drop."""
    title = (ev.get("name") or "").strip()
    source_url = ev.get("url")
    if not title or not source_url:
        return None  # never surface an event we can't link to

    dates = ev.get("dates") or {}
    start_raw = (dates.get("start") or {}).get("dateTime") or (
        dates.get("start") or {}
    ).get("localDate")
    end_raw = (dates.get("end") or {}).get("dateTime")
    start_dt = _parse_dt(start_raw)
    end_dt = _parse_dt(end_raw)

    # Filter out past events; respect the days_ahead window.
    if start_dt is not None:
        if start_dt < now:
            return None
        if start_dt > now + timedelta(days=filters["days_ahead"]):
            return None

    venues = (ev.get("_embedded") or {}).get("venues") or []
    venue = venues[0] if venues else {}
    is_online = bool(
        (venue.get("type") == "online")
        or "virtual" in title.lower()
        or "online" in title.lower()
    )
    if is_online and not filters.get("include_online", True):
        return None

    location = None
    if venue:
        city = ((venue.get("city") or {}).get("name") or "").strip()
        state = ((venue.get("state") or {}).get("stateCode") or "").strip()
        name = (venue.get("name") or "").strip()
        location = ", ".join(p for p in [name, city, state] if p) or None
    if is_online and not location:
        location = "Online"

    classifications = ev.get("classifications") or []
    class_text = " ".join(
        str(((classifications[0] if classifications else {}).get(k) or {}).get("name", ""))
        for k in ("segment", "genre", "subGenre")
    )
    full_text = f"{title} {class_text}"
    event_type = _classify_event_type(full_text, is_online)
    matched = _matched_terms(full_text, context)

    # Honesty/relevance gate: keep only events that match a term or are a
    # genuine tech/career/networking type. Drop generic concerts/sports.
    relevant_types = {"conference", "meetup", "career_fair", "hackathon",
                      "tech_talk", "webinar"}
    if not matched and event_type not in relevant_types:
        return None

    if matched:
        reason = (
            f"Mentions {', '.join(matched[:3])} — relevant to your "
            f"{context['role_family']} target."
        )
    else:
        reason = (
            f"A {event_type.replace('_', ' ')} that fits your "
            f"{context['role_family']} networking goal."
        )

    start_iso = start_dt.isoformat() if start_dt else None
    rec = EventRecommendation(
        title=title,
        organizer=(venue.get("name") if venue else None),
        event_type=event_type,
        relevance_reason=reason,
        matched_terms=matched,
        start_datetime=start_iso,
        end_datetime=end_dt.isoformat() if end_dt else None,
        location=location,
        is_online=is_online,
        source_name="ticketmaster",
        source_url=source_url,
        fetched_at=fetched_at,
        freshness_label=_freshness(start_dt, now),
        confidence=_confidence(
            has_date=start_dt is not None,
            has_location=bool(location),
            matched=len(matched),
        ),
    )
    return rec


# ----- confs.tech provider (open tech-conference dataset, no key) -----

_CONFS_TECH_BASE = (
    "https://raw.githubusercontent.com/tech-conferences/"
    "conference-data/main/conferences"
)
# Small in-process cache so one endpoint call doesn't refetch the same file and
# repeated calls within the hour stay cheap. Keyed by (year, topic).
_CONFS_TECH_CACHE: dict[tuple[int, str], tuple[float, list]] = {}
_CONFS_TECH_TTL = 3600.0


def _topics_for_family(role_family: str) -> list[str]:
    return _CONFS_TECH_FAMILY_TOPICS.get(role_family, _CONFS_TECH_DEFAULT_TOPICS)


def _fetch_confs_tech_raw(year: int, topic: str) -> list:
    """Fetch one confs.tech (year, topic) file. [] for a 404 (topic absent that
    year); raises on a real network/HTTP failure so the provider can report it."""
    key = (year, topic)
    cached = _CONFS_TECH_CACHE.get(key)
    now = time.time()
    if cached and now - cached[0] < _CONFS_TECH_TTL:
        return cached[1]

    resp = requests.get(
        f"{_CONFS_TECH_BASE}/{year}/{topic}.json",
        timeout=20,
        headers={"User-Agent": "network-ai/0.1"},
    )
    if resp.status_code == 404:
        data: list = []  # this topic simply has no file for this year
    else:
        resp.raise_for_status()
        body = resp.json()
        data = body if isinstance(body, list) else []
    _CONFS_TECH_CACHE[key] = (now, data)
    return data


def _confs_tech_to_rec(
    ev: dict, topic: str, context: dict, filters: dict, fetched_at: str, now: datetime
) -> EventRecommendation | None:
    """Map one confs.tech record -> EventRecommendation, or None to drop.

    These are real, dated tech conferences; the topic file already establishes
    role relevance, so we don't apply the Ticketmaster firehose gate here.
    """
    title = (ev.get("name") or "").strip()
    url = (ev.get("url") or "").strip()
    if not title or not url:
        return None

    start_dt = _parse_dt(ev.get("startDate"))
    end_dt = _parse_dt(ev.get("endDate"))
    if start_dt is None:
        return None  # every real confs.tech record has a start date

    # Compare by DATE so an all-day conf happening today isn't treated as past,
    # and a multi-day conf still counts while it's ongoing.
    today = now.date()
    effective_end = (end_dt or start_dt).date()
    if effective_end < today:
        return None  # already over
    if start_dt.date() > (now + timedelta(days=filters["days_ahead"])).date():
        return None  # beyond the requested window

    is_online = bool(ev.get("online"))
    city = (ev.get("city") or "").strip()
    country = (ev.get("country") or "").strip()
    # Drop purely-online events when the user excluded online.
    if is_online and not city and not filters.get("include_online", True):
        return None

    if city:
        location = ", ".join(p for p in [city, country] if p)
    elif is_online:
        location = "Online"
    else:
        location = country or None

    matched = _matched_terms(title, context)
    where = location or "TBD"
    reason = (
        f"Upcoming {context['role_family']} conference"
        f" ({'online' if is_online and not city else where})"
        f" — from the {topic} track on confs.tech."
    )

    rec = EventRecommendation(
        title=title,
        organizer=None,
        event_type="conference",
        relevance_reason=reason,
        matched_terms=matched,
        start_datetime=start_dt.isoformat(),
        end_datetime=end_dt.isoformat() if end_dt else None,
        location=location,
        is_online=is_online,
        source_name="confs_tech",
        source_url=url,
        fetched_at=fetched_at,
        freshness_label=_freshness(start_dt, now),
        confidence=_confidence(
            has_date=True, has_location=bool(location), matched=len(matched)
        ),
    )
    return rec


def _confs_tech_provider(
    context: dict, filters: dict, fetched_at: str
) -> tuple[EventProviderResult, list[EventRecommendation]]:
    """confs.tech adapter — real upcoming tech conferences, no API key needed.

    Pulls the topic files that map to the user's role family across the year(s)
    the search window spans, then filters to upcoming + in-window events.
    """
    topics = _topics_for_family(context["role_family"])[:6]
    now = _now()
    years = sorted({now.year, (now + timedelta(days=filters["days_ahead"])).year})

    recs: list[EventRecommendation] = []
    seen: set[str] = set()
    attempts = 0
    errors = 0
    for year in years:
        for topic in topics:
            attempts += 1
            try:
                raw = _fetch_confs_tech_raw(year, topic)
            except Exception:
                errors += 1
                continue
            for ev in raw:
                rec = _confs_tech_to_rec(ev, topic, context, filters, fetched_at, now)
                if rec is not None and rec.source_url not in seen:
                    seen.add(rec.source_url)
                    recs.append(rec)

    # confs.tech needs no key, so it's always "configured".
    if attempts and errors == attempts:
        return (EventProviderResult("confs_tech", True, False, 0,
                                    "Request failed; using manual search links."), [])
    note = "OK" if recs else "No upcoming conferences for your role in range."
    return (EventProviderResult("confs_tech", True, True, len(recs), note), recs)


# ----- Ranking -----

def _rank_score(rec: EventRecommendation, context: dict) -> float:
    """Higher = surface earlier. Rewards dated, local, relevant, focused events."""
    score = 0.0
    if rec.source_url:
        score += 5.0
    if rec.start_datetime:
        score += 10.0
        if rec.freshness_label == "fresh":
            score += 15.0
        elif rec.freshness_label == "upcoming":
            score += 8.0
    else:
        score -= 5.0  # undated events rank lower

    # Reward overlap with the user's real target city (not a remote/unknown
    # value — those don't carry a place to overlap with).
    city = (context.get("city") or "").lower()
    if rec.location:
        token = city.split(",")[0].strip()
        score += 8.0 if token and token in rec.location.lower() else 3.0

    score += 4.0 * len(rec.matched_terms)

    if rec.event_type in (
        "conference", "meetup", "career_fair", "hackathon", "tech_talk", "webinar"
    ):
        score += 6.0

    company = (context.get("company") or "").lower()
    if company and (
        (rec.organizer and company in rec.organizer.lower())
        or company in rec.title.lower()
    ):
        score += 10.0

    score += {"high": 6.0, "medium": 3.0, "low": 0.0}[rec.confidence]
    return round(score, 2)


# ----- Public entry point -----

def recommend_events(
    db: Session,
    *,
    location: str | None = None,
    radius_miles: int = 50,
    days_ahead: int = 30,
    include_online: bool = True,
    max_results: int = 12,
) -> EventRecommendationResponse:
    """Recommend upcoming networking events for the strongest job match today.

    API-backed events (when providers are configured) are ranked by relevance +
    freshness. Manual search links are ALWAYS returned, so the user gets a
    useful answer even with no keys configured and no live results.
    """
    days_ahead = max(1, min(int(days_ahead), 180))
    max_results = max(1, min(int(max_results), 50))
    radius_miles = max(1, min(int(radius_miles), 500))

    context, best = build_search_context(db, location_override=location)
    filters = {
        "location": context["location"],   # human-readable (may be "Remote")
        "city": context["city"],           # normalized real city, or None
        "is_remote": context["is_remote"],
        "radius_miles": radius_miles,
        "days_ahead": days_ahead,
        "include_online": include_online,
        "max_results": max_results,
    }
    fetched_at = _now().isoformat()

    # Run configured providers. Today: Ticketmaster (real) + manual fallbacks.
    providers: list[EventProviderResult] = []
    recommendations: list[EventRecommendation] = []

    tm_result, tm_recs = _ticketmaster_provider(context, filters, fetched_at)
    providers.append(tm_result)
    recommendations.extend(tm_recs)

    # confs.tech — real, key-less open dataset of tech conferences. This is the
    # main source of actual tech events (Ticketmaster carries almost none).
    ct_result, ct_recs = _confs_tech_provider(context, filters, fetched_at)
    providers.append(ct_result)
    recommendations.extend(ct_recs)

    # Eventbrite / Meetup / Luma have no compliant public event-DISCOVERY API
    # (Eventbrite's was retired; Meetup needs paid OAuth; Luma has none), so we
    # surface them as prefilled manual search links instead of faking results.
    providers.append(EventProviderResult(
        "eventbrite", config.get_eventbrite_api_token() != "", False, 0,
        "Public event-discovery API was retired; using manual search links.",
    ))
    providers.append(EventProviderResult(
        "meetup", config.get_meetup_api_key() != "", False, 0,
        "API needs paid OAuth; using manual search links.",
    ))
    providers.append(EventProviderResult(
        "luma", False, False, 0, "No open search API; using manual search links.",
    ))

    # Rank + dedupe by source_url, then cap.
    seen: set[str] = set()
    deduped: list[EventRecommendation] = []
    for rec in recommendations:
        if rec.source_url in seen:
            continue
        seen.add(rec.source_url)
        rec.rank_score = _rank_score(rec, context)
        deduped.append(rec)
    deduped.sort(key=lambda r: r.rank_score, reverse=True)
    recommendations = deduped[:max_results]

    search_links = build_search_links(context)

    if recommendations:
        message = (
            f"Found {len(recommendations)} upcoming event(s) relevant to your "
            f"{context['role_family']} target."
        )
    elif context["is_remote"]:
        message = (
            "Your strongest job is remote, so we're not using it as a city. "
            "Add a city to find local networking events — meanwhile, here are "
            "safe manual searches (including online events)."
        )
    else:
        message = (
            "No verified upcoming events found from configured providers. "
            "Here are safe manual searches built from your strongest match."
        )

    return EventRecommendationResponse(
        ready=best is not None,
        message=message,
        strongest_match=best,
        search_context=context,
        filters=filters,
        providers=providers,
        recommendations=recommendations,
        search_links=search_links,
    )


def response_to_dict(resp: EventRecommendationResponse) -> dict:
    """Convert the response dataclass tree into a JSON-friendly dict."""
    return dataclasses.asdict(resp)
