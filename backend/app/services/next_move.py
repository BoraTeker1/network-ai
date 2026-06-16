"""Next Move AI — analyze a reply the user RECEIVED and propose their next move.

The user pastes the reply text manually (we never read LinkedIn or email). The
model (OpenAI Responses API only) classifies intent, summarizes, recommends a
next action, and drafts a response — with a deterministic keyword-based fallback
that runs whenever the LLM is unavailable or returns anything malformed.

Nothing is ever sent. AI proposes, the user reviews/edits/approves, the user
sends manually. Checklists are always recomputed locally on the final drafts so
verification never depends on the model's self-report.
"""

import json

from . import llm_client, momentum

WORD_LIMIT = 180

# Primary intent vocabulary (the UI shows one primary + any extra signals).
INTENTS = (
    "positive",
    "neutral",
    "negative",
    "referral_possible",
    "interview_related",
    "asks_for_resume",
    "asks_for_work_authorization",
    "needs_follow_up",
)
URGENCIES = ("low", "medium", "high")

# Specific signals we can detect deterministically (positive/negative/neutral
# are derived separately as the overall tone).
_SIGNAL_KEYWORDS = {
    "interview_related": [
        "interview", "phone screen", "onsite", "on-site", "schedule a call",
        "set up a time", "set up some time", "find a time", "hop on a call",
        "jump on a call", "quick call", "a call", "phone call", "give you a call",
        "availability", "available", "are you free", "free for", "free to",
        "calendar", "chat", "to talk", "speak with", "speak", "meet", "video call",
        "grab some time", "grab time", "connect live",
    ],
    "referral_possible": [
        "refer", "referral", "pass along", "pass your", "forward your",
        "put in a good word", "connect you with", "introduce you", "internal",
    ],
    "asks_for_resume": [
        "resume", "résumé", "cv", "send me your", "share your resume",
        "attach your", "updated resume",
    ],
    "asks_for_work_authorization": [
        "work authorization", "authorized to work", "visa", "sponsorship",
        "sponsor", "require sponsorship", "h-1b", "h1b", "opt", "cpt",
        "citizen", "green card", "work permit",
    ],
    "needs_follow_up": [
        "circle back", "follow up", "follow-up", "next week", "later",
        "busy right now", "touch base", "reach back out", "check back",
        "get back to you", "in a few weeks",
    ],
}
_NEGATIVE_KEYWORDS = [
    "unfortunately", "not a fit", "not a good fit", "no longer", "already filled",
    "position is filled", "moving forward with other", "won't be moving forward",
    "not moving forward", "decided to go", "we have decided", "regret to",
    "declined", "no openings", "not hiring",
]
_POSITIVE_KEYWORDS = [
    "happy to", "glad to", "great to hear", "would love", "sounds good",
    "let's", "lets ", "sure", "yes", "excited", "love to", "more than happy",
    "great fit", "impressed", "look forward",
]
_URGENT_KEYWORDS = [
    "today", "tomorrow", "asap", "as soon as possible", "by end of day",
    "this week", "by friday", "urgent", "time sensitive", "deadline",
]

# Map a detected primary intent -> the outcome to suggest logging in the pipeline.
_INTENT_OUTCOME = {
    "interview_related": "interview_received",
    "referral_possible": "referral_received",
    "negative": "rejected",
    "positive": "replied",
    "neutral": "replied",
    "needs_follow_up": "replied",
    "asks_for_resume": "replied",
    "asks_for_work_authorization": "replied",
}

_AGGRESSIVE_TERMS = (
    "asap", "as soon as possible", "urgent", "you must", "guarantee",
    "right away", "immediately", "need this", "demand",
)
_SOFT_ASK_TERMS = (
    "would you", "could we", "happy to", "no pressure", "whenever works",
    "if it's helpful", "let me know", "would love", "open to", "at your convenience",
)
_FAKE_CLAIM_TERMS = (
    "as we discussed", "as promised", "per our agreement", "you offered",
    "you said you would", "as you committed",
)


# ----- Deterministic detection -----

def detect_signals(text: str) -> list[str]:
    """Return the specific signals present in the reply (order = INTENTS order)."""
    low = (text or "").lower()
    found = [sig for sig, kws in _SIGNAL_KEYWORDS.items() if any(k in low for k in kws)]
    return found


def detect_tone(text: str) -> str:
    """Overall tone: negative > positive > neutral (negatives are decisive)."""
    low = (text or "").lower()
    if any(k in low for k in _NEGATIVE_KEYWORDS):
        return "negative"
    if any(k in low for k in _POSITIVE_KEYWORDS):
        return "positive"
    return "neutral"


def primary_intent(text: str) -> tuple[str, list[str]]:
    """Pick the single most actionable intent + the full signal list."""
    signals = detect_signals(text)
    tone = detect_tone(text)
    # Negative tone wins — never push a rejected lead toward an interview ask.
    if tone == "negative":
        return "negative", signals
    # Otherwise the most actionable specific signal leads.
    for intent in (
        "interview_related",
        "referral_possible",
        "asks_for_resume",
        "asks_for_work_authorization",
        "needs_follow_up",
    ):
        if intent in signals:
            return intent, signals
    return tone, signals  # "positive" or "neutral"


def detect_urgency(text: str, intent: str, signals: list[str]) -> str:
    low = (text or "").lower()
    if (
        intent in ("interview_related", "asks_for_resume", "asks_for_work_authorization")
        or any(k in low for k in _URGENT_KEYWORDS)
    ):
        return "high"
    if intent in ("positive", "referral_possible", "needs_follow_up"):
        return "medium"
    return "low"


def _recommended_action(intent: str) -> str:
    return {
        "interview_related": (
            "They want to talk. Reply within 24h with 2–3 specific time windows in "
            "your timezone and confirm the format (phone/video)."
        ),
        "referral_possible": (
            "A referral is on the table. Thank them, send a 2-line summary plus the "
            "exact role link, and make it effortless for them to forward you."
        ),
        "asks_for_resume": (
            "Send your tailored resume as a PDF, name the role you're interested in, "
            "and add one honest line on why you're a fit."
        ),
        "asks_for_work_authorization": (
            "Answer the work-authorization question plainly and truthfully. State your "
            "status in one sentence — don't over-explain or misrepresent it."
        ),
        "needs_follow_up": (
            "They're open but busy. Acknowledge it, propose one specific follow-up "
            "date, and keep the note short."
        ),
        "positive": (
            "Warm reply — keep the momentum. Thank them and propose one concrete next "
            "step (a short call or a single specific question)."
        ),
        "negative": (
            "It's a no for now. Reply graciously, ask to stay connected for the future, "
            "and redirect your energy to other targets — no pushback, no burned bridges."
        ),
        "neutral": (
            "Acknowledge their note and restate your ask in one clear sentence so it's "
            "easy for them to respond."
        ),
    }.get(intent, "Reply briefly and keep a single, low-pressure ask.")


def _risk_notes(intent: str, signals: list[str]) -> str:
    notes = [
        "Keep it honest and low-pressure — don't over-promise or invent availability "
        "you don't have."
    ]
    if "asks_for_work_authorization" in signals or intent == "asks_for_work_authorization":
        notes.append(
            "Be truthful about your work-authorization status; never misrepresent it."
        )
    if intent == "negative":
        notes.append(
            "Don't argue or push back — a gracious close keeps the door open."
        )
    return " ".join(notes)


# ----- Deterministic drafts -----

def _role_phrase(company, role) -> str:
    if role and company:
        return f"the {role} role at {company}"
    if role:
        return f"the {role} role"
    if company:
        return f"the opportunity at {company}"
    return "the role"


def _build_drafts(intent: str, company, role, first: str) -> dict:
    greet = f"Hi {first}," if first else "Hi,"
    rp = _role_phrase(company, role)

    if intent == "interview_related":
        body = (
            f"{greet}\n\nThank you — I'd be glad to talk about {rp}. I'm generally "
            "free Tuesday and Thursday afternoons (ET) this week and can be flexible "
            "around what works for you. A phone or video call both work on my end.\n\n"
            "Just let me know a time and I'll make it work. Looking forward to it."
        )
        subject = "Re: happy to find a time to talk"
        short = (
            f"Thanks so much! I'd love to talk about {rp}. I'm free Tue/Thu afternoons "
            "(ET) this week and happy to work around your schedule — just send a time "
            "that suits you."
        )
    elif intent == "referral_possible":
        body = (
            f"{greet}\n\nThank you, I really appreciate it. To make it easy: I'm "
            f"interested in {rp}, and in short I'm a new-grad engineer with hands-on "
            "project and internship experience. I'm happy to send my resume or anything "
            "else that would help — no pressure at all, and thank you either way."
        )
        subject = "Re: thank you — quick summary to pass along"
        short = (
            f"Thank you, that means a lot! Quick summary to forward: new-grad engineer "
            f"interested in {rp}, with project + internship experience. Happy to send my "
            "resume whenever helpful — and thanks again either way."
        )
    elif intent == "asks_for_resume":
        body = (
            f"{greet}\n\nAbsolutely — I'll send my resume over (PDF). I'm interested in "
            f"{rp}, and I think my project and internship work lines up well with what "
            "the team is doing. Please let me know if there's anything else that would "
            "be useful. Thank you!"
        )
        subject = "Re: resume attached"
        short = (
            f"Of course — sending my resume now. I'm interested in {rp}; happy to share "
            "anything else that helps. Thanks!"
        )
    elif intent == "asks_for_work_authorization":
        body = (
            f"{greet}\n\nThanks for asking. To answer directly: [state your work-"
            "authorization status here in one honest sentence — e.g. authorized to work "
            "in the US / will require sponsorship]. Happy to clarify anything else, and "
            f"I remain very interested in {rp}."
        )
        subject = "Re: work authorization"
        short = (
            "Thanks for checking — to be upfront: [your honest work-authorization status "
            f"in one line]. Still very interested in {rp}; glad to clarify anything."
        )
    elif intent == "needs_follow_up":
        body = (
            f"{greet}\n\nTotally understand — no rush at all. Would it be alright if I "
            "followed up in a couple of weeks? I'm still very interested in "
            f"{rp}, and I appreciate you keeping me in mind. Thanks!"
        )
        subject = "Re: happy to follow up later"
        short = (
            f"No rush at all — totally understand. Mind if I check back in a couple of "
            f"weeks? Still very interested in {rp}. Thanks for keeping me in mind!"
        )
    elif intent == "negative":
        body = (
            f"{greet}\n\nThank you for letting me know — I really appreciate you taking "
            "the time. Even though it didn't work out for {rp}, I'd love to stay "
            "connected for the future. Wishing the team all the best, and thanks again."
        ).replace("{rp}", rp)
        subject = "Re: thank you for the update"
        short = (
            "Thank you for letting me know — I appreciate the update! Would love to stay "
            "connected for the future. Wishing you and the team all the best."
        )
    else:  # positive / neutral
        body = (
            f"{greet}\n\nThank you for getting back to me! I'm really interested in "
            f"{rp}. Would you be open to a quick call so I can learn more about the team "
            "and what you'd be looking for? No pressure on timing — whatever works for "
            "you. Thanks again."
        )
        subject = "Re: thank you — would love to learn more"
        short = (
            f"Thanks so much for the reply! I'm really interested in {rp}. Would you be "
            "open to a quick call to chat about the team? No pressure on timing — happy "
            "to work around you."
        )
    return {"subject": subject, "body": body, "short": short}


# ----- Checklists (computed locally on the final drafts) -----

def quality_checklist(*, subject, body, short, company, role) -> dict:
    text = f"{subject}\n{body}\n{short}".lower()
    body_words = len((body or "").split())
    items = [
        {"key": "polite", "label": "Polite / appreciative",
         "passed": any(t in text for t in ("thank", "appreciate", "grateful"))},
        {"key": "clear_next_step", "label": "Proposes a clear next step",
         "passed": ("?" in (body or "") + (short or "")) or any(t in text for t in _SOFT_ASK_TERMS)},
        {"key": "mentions_role", "label": "References the role/company",
         "passed": (bool(role) and role.lower() in text) or (bool(company) and company.lower() in text)},
        {"key": "under_limit", "label": f"Email under {WORD_LIMIT} words",
         "passed": 0 < body_words <= WORD_LIMIT},
        {"key": "no_fake_claim", "label": "No invented commitments",
         "passed": not any(t in text for t in _FAKE_CLAIM_TERMS)},
    ]
    passed = sum(1 for i in items if i["passed"])
    return {"items": items, "passed": passed, "total": len(items)}


def safety_checklist(*, intent, signals, subject, body, short) -> dict:
    text = f"{subject}\n{body}\n{short}".lower()
    low_pressure = not any(t in text for t in _AGGRESSIVE_TERMS)
    items = [
        {"key": "manual_send", "label": "Manual send only — nothing is sent for you",
         "passed": True},
        {"key": "low_pressure", "label": "Low-pressure, no false urgency",
         "passed": low_pressure},
        {"key": "no_overpromise", "label": "No invented availability or commitments",
         "passed": not any(t in text for t in _FAKE_CLAIM_TERMS)},
        {"key": "review_before_send", "label": "You review & edit before sending",
         "passed": True},
    ]
    if intent == "asks_for_work_authorization" or "asks_for_work_authorization" in signals:
        items.append({
            "key": "truthful_authorization",
            "label": "Answer work authorization truthfully (placeholder to fill in)",
            "passed": True,
        })
    passed = sum(1 for i in items if i["passed"])
    return {"items": items, "passed": passed, "total": len(items)}


# ----- Suggested momentum preview -----

def _momentum_preview(outcome: str | None) -> dict | None:
    if not outcome:
        return None
    event_type = momentum.OUTCOME_EVENT.get(outcome)
    if not event_type:
        return None
    return {
        "event_type": event_type,
        "points": momentum.POINTS.get(event_type, 0),
        "label": momentum.LABELS.get(event_type, event_type),
    }


# ----- LLM prompt -----

def _build_prompt(*, reply_text, company, role, contact_name, contact_title) -> str:
    lines = [
        "Analyze a networking/job-search reply the user RECEIVED and propose their",
        "next move. Be honest, concise, and low-pressure. Never invent facts.",
        "",
        "CONTEXT (may be partial):",
        f"- Company: {company or '(unknown)'}",
        f"- Role: {role or '(unknown)'}",
        f"- Contact: {contact_name or '(unknown)'} ({contact_title or 'unknown title'})",
        "",
        "THE REPLY THEY RECEIVED:",
        f'"""{reply_text}"""',
        "",
        "Return STRICT JSON with exactly these keys:",
        "{",
        '  "summary": str,  // one or two sentences',
        f'  "intent": one of {list(INTENTS)},',
        f'  "signals": array of any of {list(_SIGNAL_KEYWORDS.keys())},',
        '  "urgency": one of ["low","medium","high"],',
        '  "recommended_next_action": str,',
        '  "risk_notes": str,',
        '  "suggested_pipeline_update": one of '
        '["replied","referral_received","interview_received","rejected"] or null,',
        '  "drafted_email": {"subject": str, "body": str},',
        '  "drafted_short_message": str',
        "}",
        "",
        "RULES: single low-pressure ask; keep the email under 180 words; never",
        "claim the user already applied or promised anything; if work authorization",
        "is asked, instruct the user to answer truthfully (use a placeholder, never",
        "fabricate a status).",
    ]
    return "\n".join(lines)


# ----- Public entry point -----

def analyze_reply(*, reply_text: str, context: dict) -> dict:
    """Return a full Next Move analysis dict (LLM when available, else fallback)."""
    company = context.get("company")
    role = context.get("role")
    contact_name = context.get("contact_name")
    contact_title = context.get("contact_title")
    first = (contact_name or "").strip().split()[0] if contact_name else ""

    summary = intent = urgency = recommended = risk = None
    suggested_outcome = None
    drafted_email = None
    drafted_short = None
    signals: list[str] = []
    llm_used = False

    if llm_client.llm_available():
        try:
            data = llm_client.generate_json_with_openai(
                _build_prompt(
                    reply_text=reply_text, company=company, role=role,
                    contact_name=contact_name, contact_title=contact_title,
                )
            )
            intent = str(data.get("intent") or "").strip()
            urgency = str(data.get("urgency") or "").strip()
            summary = str(data.get("summary") or "").strip()
            recommended = str(data.get("recommended_next_action") or "").strip()
            risk = str(data.get("risk_notes") or "").strip()
            signals = [s for s in (data.get("signals") or []) if s in _SIGNAL_KEYWORDS]
            suggested_outcome = data.get("suggested_pipeline_update")
            email = data.get("drafted_email") or {}
            drafted_email = {
                "subject": str(email.get("subject") or "").strip(),
                "body": str(email.get("body") or "").strip(),
            }
            drafted_short = str(data.get("drafted_short_message") or "").strip()

            # Validate the essentials; bail to fallback on anything missing/invalid.
            if (
                intent not in INTENTS
                or urgency not in URGENCIES
                or not summary
                or not recommended
                or not drafted_email["subject"]
                or not drafted_email["body"]
                or not drafted_short
            ):
                raise ValueError("incomplete LLM analysis")
            if suggested_outcome not in (
                "replied", "referral_received", "interview_received", "rejected", None
            ):
                suggested_outcome = None
            llm_used = True
        except Exception:
            llm_used = False
            summary = intent = urgency = recommended = risk = None
            drafted_email = drafted_short = None
            signals = []

    if not llm_used:
        # Deterministic fallback — fully self-contained, no network.
        intent, signals = primary_intent(reply_text)
        urgency = detect_urgency(reply_text, intent, signals)
        recommended = _recommended_action(intent)
        risk = _risk_notes(intent, signals)
        suggested_outcome = _INTENT_OUTCOME.get(intent, "replied")
        drafts = _build_drafts(intent, company, role, first)
        drafted_email = {"subject": drafts["subject"], "body": drafts["body"]}
        drafted_short = drafts["short"]
        summary = _fallback_summary(intent, signals, company, role)

    quality = quality_checklist(
        subject=drafted_email["subject"], body=drafted_email["body"],
        short=drafted_short, company=company, role=role,
    )
    safety = safety_checklist(
        intent=intent, signals=signals, subject=drafted_email["subject"],
        body=drafted_email["body"], short=drafted_short,
    )

    return {
        "summary": summary,
        "intent": intent,
        "signals": signals,
        "urgency": urgency,
        "recommended_next_action": recommended,
        "risk_notes": risk,
        "suggested_pipeline_update": suggested_outcome,
        "suggested_momentum": _momentum_preview(suggested_outcome),
        "drafted_email": drafted_email,
        "drafted_short_message": drafted_short,
        "quality_checklist": quality,
        "safety_checklist": safety,
        "llm_used": llm_used,
    }


def _fallback_summary(intent, signals, company, role) -> str:
    rp = _role_phrase(company, role)
    base = {
        "interview_related": f"They're interested in talking about {rp} and want to find a time.",
        "referral_possible": f"They've offered to help refer or pass you along for {rp}.",
        "asks_for_resume": f"They're asking for your resume regarding {rp}.",
        "asks_for_work_authorization": "They're asking about your work-authorization status.",
        "needs_follow_up": "They're open but busy and suggest following up later.",
        "positive": f"A warm, encouraging reply about {rp}.",
        "negative": f"It's a polite no for {rp} right now.",
        "neutral": "A brief, neutral reply that needs a clear next step from you.",
    }.get(intent, "A reply that needs a short, thoughtful response.")
    extra = ""
    if "asks_for_work_authorization" in signals and intent != "asks_for_work_authorization":
        extra = " They also raise work authorization."
    return base + extra
