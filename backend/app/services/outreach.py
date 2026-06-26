"""Paste-a-JD bilingual outreach drafting (Turkey → remote/EU wedge).

The user pastes a job description they found themselves (no scraping, no stored
Job row required), names a contact, picks a language (English/Turkish) and a
channel (email / LinkedIn note), and optionally adds remote/EU framing. We draft
a short, honest, low-pressure message — via Claude when configured, with a
deterministic template fallback — personalize it with the saved profile's real
skills, recompute the quality + risk checklists locally in the chosen language,
and add manual "who to contact" guidance (safe search links only).

Guardrails are unchanged: AI proposes, the user reviews, edits, copies, and sends
manually. No scraping, no network calls here, no auto-send, no bulk. We never
invent skills, projects, employers, achievements, locations, or work
authorization — only facts the user/profile supplied.
"""

import re
import urllib.parse

from . import email_generator, llm_client

LANGUAGES = ("en", "tr")
CHANNELS = ("email", "linkedin")
TARGET_REGIONS = ("remote", "europe", "global", "turkey")

EMAIL_WORD_LIMIT = email_generator.WORD_LIMIT  # 180 words
LINKEDIN_CHAR_LIMIT = 280

_ROLE_FALLBACK = {"en": "the role", "tr": "ilgili pozisyon"}
_COMPANY_FALLBACK = {"en": "your team", "tr": "ekibiniz"}

# How the chosen target region reads inside the message.
_REGION_PHRASE = {
    "en": {
        "remote": "remote roles",
        "europe": "roles based in Europe",
        "global": "global remote roles",
        "turkey": "roles in Turkey",
        None: "remote and European roles",
    },
    "tr": {
        "remote": "uzaktan çalışılan roller",
        "europe": "Avrupa merkezli roller",
        "global": "global uzaktan roller",
        "turkey": "Türkiye'deki roller",
        None: "uzaktan ve Avrupa odaklı roller",
    },
}


def _norm_language(language: str | None) -> str:
    return "tr" if (language or "en").lower().startswith("tr") else "en"


def _norm_channel(channel: str | None) -> str:
    return "linkedin" if (channel or "email").lower() == "linkedin" else "email"


def _norm_region(region: str | None) -> str | None:
    r = (region or "").lower().strip()
    return r if r in TARGET_REGIONS else None


# ----- Light heuristic extraction (for the fallback + checklist mentions) -----

def _extract_role(jd_text: str, language: str) -> str:
    for raw in (jd_text or "").splitlines():
        line = raw.strip(" \t-*•·:")
        if 3 <= len(line) <= 80 and not line.endswith("."):
            return line
    return _ROLE_FALLBACK[language]


def _extract_company(jd_text: str, contact: dict, explicit: str | None, language: str) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    if contact.get("company"):
        return contact["company"].strip()
    text = jd_text or ""
    m = re.search(r"(?im)^\s*company\s*[:\-]\s*(.+)$", text)
    if m:
        return m.group(1).strip()[:60]
    m = re.search(r"\bat\s+([A-Z][\w&.\- ]{1,40})", text)
    if m:
        return m.group(1).strip()
    return _COMPANY_FALLBACK[language]


def _skill_in_text(skill: str, text_lower: str) -> bool:
    """Token-aware, case-insensitive skill match (so 'Java' != 'JavaScript')."""
    return bool(
        re.search(rf"(?<![a-z0-9]){re.escape(skill.lower())}(?![a-z0-9])", text_lower)
    )


def relevant_skills(jd_text: str, profile_skills: list[str], n: int = 3) -> list[str]:
    """The user's OWN skills that the JD emphasizes (never invents skills).

    Falls back to the user's top skills if none overlap, so an honest skill line
    is still possible — these are still the user's real skills, just not matched."""
    skills = [s for s in (profile_skills or []) if s]
    if not skills:
        return []
    text_lower = (jd_text or "").lower()
    matched = [s for s in skills if _skill_in_text(s, text_lower)]
    return (matched or skills)[:n]


def _join(skills: list[str]) -> str:
    skills = skills[:3]
    if len(skills) <= 1:
        return skills[0] if skills else ""
    return ", ".join(skills[:-1]) + " and " + skills[-1]


# ----- Sentence builders (honest, opt-in) -----

def _skill_line(skills: list[str], language: str, override: str | None) -> str:
    if override and override.strip():
        return override.strip()
    if not skills:
        return ""
    joined = _join(skills)
    if language == "tr":
        return (
            f"İlanda {joined} tarafının öne çıktığını gördüm; {joined} ile proje "
            "geliştirdim ve junior adaylarda ekibin neye baktığını öğrenmek isterim."
        )
    return (
        f"I noticed the role emphasizes {joined}; I've built projects using "
        f"{joined} and would value your advice on how the team evaluates junior "
        "candidates."
    )


def _location_line(based_in: str, timezone_overlap: str | None, language: str) -> str:
    if language == "tr":
        place = "Türkiye" if (based_in or "").strip().lower() in ("turkey", "türkiye") else based_in
        tz = timezone_overlap or "CET ile uyumlu saatlerde"
        return f"{place}'de yaşıyorum ve {tz} çalışabilirim."
    tz = timezone_overlap or "CET-friendly hours"
    return f"I'm based in {based_in} and can work {tz}."


def _work_auth_line(note: str | None, language: str) -> str:
    """Echo the user's OWN work-authorization note verbatim. Never invented."""
    if not note or not note.strip():
        return ""
    note = note.strip()
    if language == "tr":
        return f"Çalışma izni konusunda kısa bir not: {note}"
    return f"A quick note on work authorization: {note}"


def follow_up_text(language: str) -> str:
    if language == "tr":
        return (
            "Yanıt alamazsan 5–7 iş günü sonra kısa ve kibar bir hatırlatma "
            "gönder — sonra bırak. Nicelik değil, nitelik."
        )
    return (
        "If you don't hear back, send one short, polite follow-up after 5–7 "
        "business days — then stop. Quality over volume."
    )


# ----- Contact guidance (manual search links only — no scraping, no network) -----

def _g(query: str) -> str:
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)


def contact_guidance(company: str, language: str) -> dict:
    """Who to contact + safe manual search links. Builds URL strings only — it
    makes NO network calls and never scrapes any site."""
    company = (company or "").strip() or ("the company" if language == "en" else "şirket")

    if language == "tr":
        roles = [
            {"role": "recruiter", "label": "İşe alım / yetenek kazanımı uzmanı", "priority": 1,
             "why": "Rolün profiline ve saat dilimine açık olup olmadığını en hızlı o teyit eder."},
            {"role": "software_engineer", "label": "İlgili ekipten bir yazılım mühendisi", "priority": 2,
             "why": "Ekibin neye değer verdiğine dair dürüst tavsiye için en iyi kişi — referans değil, tavsiye iste."},
            {"role": "engineering_manager", "label": "Mühendislik müdürü", "priority": 3,
             "why": "İşe alım çıtasını o belirler; düşünülmüş kısa bir mesaj fark yaratabilir."},
            {"role": "turkish_alumni", "label": "Şirkette çalışan Türk / mezun", "priority": 4,
             "why": "Ortak dil/geçmiş sıcak bir tanışmayı kolaylaştırır — kendin manuel bul."},
        ]
        note = ("Bu linkleri kendin aç — Network AI LinkedIn'i taramaz ve senin "
                "adına kimseyle iletişime geçmez.")
        links = [
            {"label": f"LinkedIn — {company} işe alım uzmanları",
             "url": "https://www.linkedin.com/search/results/people/?keywords="
                    + urllib.parse.quote_plus(f"{company} recruiter")},
            {"label": f"Google — {company} yazılım mühendisleri (Türkiye)",
             "url": _g(f'site:linkedin.com/in "{company}" software engineer Turkey')},
            {"label": f"Google — {company} yetenek kazanımı",
             "url": _g(f'"{company}" talent acquisition LinkedIn')},
            {"label": f"Google — {company} mühendislik müdürü",
             "url": _g(f'"{company}" engineering manager LinkedIn')},
            {"label": f"GitHub — {company} ile ilişkili kişiler",
             "url": "https://github.com/search?q=" + urllib.parse.quote_plus(company) + "&type=users"},
        ]
    else:
        roles = [
            {"role": "recruiter", "label": "Recruiter / talent acquisition", "priority": 1,
             "why": "Fastest to confirm the role is open to your profile and timezone."},
            {"role": "software_engineer", "label": "Software engineer on the relevant team", "priority": 2,
             "why": "Best for honest advice on what the team values — ask for advice, not a referral."},
            {"role": "engineering_manager", "label": "Engineering manager", "priority": 3,
             "why": "Owns the hiring bar; one thoughtful, short note can stand out."},
            {"role": "turkish_alumni", "label": "Turkish employee / alumni at the company", "priority": 4,
             "why": "Shared language/background makes a warm intro more likely — find them manually."},
        ]
        note = ("Open these links yourself — Network AI never scrapes LinkedIn and "
                "never contacts anyone on your behalf.")
        links = [
            {"label": f"LinkedIn — recruiters at {company}",
             "url": "https://www.linkedin.com/search/results/people/?keywords="
                    + urllib.parse.quote_plus(f"{company} recruiter")},
            {"label": f"Google — engineers at {company} in Turkey",
             "url": _g(f'site:linkedin.com/in "{company}" software engineer Turkey')},
            {"label": f"Google — talent acquisition at {company}",
             "url": _g(f'"{company}" talent acquisition LinkedIn')},
            {"label": f"Google — engineering managers at {company}",
             "url": _g(f'"{company}" engineering manager LinkedIn')},
            {"label": f"GitHub — people associated with {company}",
             "url": "https://github.com/search?q=" + urllib.parse.quote_plus(company) + "&type=users"},
        ]

    return {
        "company": company,
        "recommended_contact_roles": roles,
        "contact_priority_order": [r["role"] for r in sorted(roles, key=lambda x: x["priority"])],
        "manual_search_links": links,
        "note": note,
    }


# ----- Prompt -----

def build_prompt(*, jd_text, contact, language, channel, tone, role, company,
                 skills, region_phrase, resume_summary,
                 include_location_line, based_in, timezone_overlap,
                 include_work_auth_line, work_authorization_note,
                 skill_override) -> str:
    lang_name = "Turkish" if language == "tr" else "English"
    if channel == "linkedin":
        channel_rule = (
            f"This is a LinkedIn connection note: keep the body under "
            f"{LINKEDIN_CHAR_LIMIT} characters; leave subject empty."
        )
    else:
        channel_rule = f"This is an email: keep the body under {EMAIL_WORD_LIMIT} words."

    skills_str = ", ".join(skills) if skills else "(none on file)"
    lines = [
        f"Write a short, honest networking message in {lang_name} for a software "
        f"engineer based in {based_in} reaching out about {region_phrase}.",
        "",
        "PASTED JOB DESCRIPTION (the only facts about the role you may use):",
        (jd_text or "").strip()[:4000],
        "",
        "ABOUT THE SENDER (facts you MAY use — do NOT add anything beyond these):",
        f"- Role of interest: {role}",
        f"- Company: {company}",
        f"- Sender's real skills (use 1–3 that fit the JD): {skills_str}",
        f"- Resume summary: {resume_summary or '(none)'}",
        "",
        "CONTACT THE USER WILL MESSAGE:",
        f"- Name: {contact.get('name') or '(unknown)'}",
        f"- Title: {contact.get('title') or '(unknown)'}",
        f"- Company: {contact.get('company') or company}",
        "",
        "RULES:",
        f"- Write ENTIRELY in {lang_name}.",
        "- Never invent skills, projects, employers, achievements, locations, or",
        "  work authorization. Use only the facts above.",
        "- Do NOT claim the user already applied, was referred, or already knows",
        "  the contact. No 'perfect fit' or 'production experience' unless the",
        "  resume summary explicitly supports it.",
        "- Reference the role and company naturally, and 1–3 of the sender's real",
        "  skills that the JD emphasizes.",
        "- Keep a single, low-pressure ask (advice or a brief chat), never a",
        "  demanding referral ask.",
    ]
    if skill_override:
        lines.append(f"- Include this sender-provided highlight verbatim in spirit: {skill_override}")
    if include_location_line:
        tz = timezone_overlap or ("CET ile uyumlu saatlerde" if language == "tr" else "CET-friendly hours")
        lines.append(
            f"- Include ONE honest line that the sender is based in {based_in} and can work {tz}."
        )
    if include_work_auth_line and (work_authorization_note or "").strip():
        lines.append(
            "- Include this work-authorization note VERBATIM (do not embellish): "
            f"{work_authorization_note.strip()}"
        )
    else:
        lines.append("- Do NOT mention visas, sponsorship, or work authorization at all.")
    lines += [
        f"- {channel_rule}",
        "- No spammy phrasing, no exclamation spam, no false urgency.",
        "",
        "Return STRICT JSON only with exactly these keys:",
        '{"subject": str, "body": str, "personalization_notes": str, '
        '"detected_company": str, "detected_role": str}',
    ]
    return "\n".join(lines)


# ----- Deterministic fallback -----

def _deterministic(*, contact, language, channel, role, company, skills,
                   region_phrase, include_location_line, based_in, timezone_overlap,
                   include_work_auth_line, work_authorization_note, skill_override) -> dict:
    first = (contact.get("name") or "").strip().split()[0] if contact.get("name") else ""
    skill_line = _skill_line(skills, language, skill_override)
    loc_line = _location_line(based_in, timezone_overlap, language) if include_location_line else ""
    auth_line = _work_auth_line(work_authorization_note, language) if include_work_auth_line else ""

    if language == "tr":
        greeting = f"Merhaba {first}," if first else "Merhaba,"
        intro = (
            f"{company} bünyesindeki {role} pozisyonuyla ilgilenen bir yazılım "
            f"mühendisiyim; {region_phrase} arıyorum."
        )
        ask = (
            "Birkaç dakikanızı ayırıp ekibin junior adaylarda neye baktığını "
            "paylaşmanız mümkün mü? Hiçbir baskı yok."
        )
        closing = "Her durumda zaman ayırdığınız için teşekkür ederim."
        subject = "" if channel == "linkedin" else f"{role} pozisyonu hakkında kısa bir soru"
        notes = (
            "Deterministik şablon (LLM yok). Rol, şirket ve gerçek becerileri anar; "
            "tek ve düşük baskılı bir rica; uydurma bilgi yok."
        )
    else:
        greeting = f"Hi {first}," if first else "Hi,"
        intro = (
            f"I'm a software engineer interested in the {role} role at {company}, "
            f"focused on {region_phrase}."
        )
        ask = (
            "Would you be open to a few minutes to share what the team looks for in "
            "junior candidates? No pressure either way."
        )
        closing = "Thanks for your time regardless."
        subject = "" if channel == "linkedin" else f"Quick question about the {role} role"
        notes = (
            "Deterministic template (no LLM). Mentions the role, company, and real "
            "skills; a single low-pressure ask; no invented facts."
        )

    middle = " ".join(s for s in (intro, skill_line, loc_line, auth_line, ask) if s)
    body = f"{greeting}\n\n{middle}\n\n{closing}"
    return {
        "subject": subject,
        "body": body,
        "personalization_notes": notes,
        "detected_company": company,
        "detected_role": role,
    }


# ----- Public entry point -----

def generate(*, jd_text, contact, language="en", channel="email", tone=None,
             profile_skills=None, resume_summary=None, company=None, role=None,
             target_region=None, based_in=None, timezone_overlap=None,
             work_authorization_note=None, include_location_line=False,
             include_work_auth_line=False, skill_highlight=None) -> dict:
    """Return a full bilingual outreach draft + contact guidance. Uses the LLM
    when available, else a deterministic template. Checklists are always
    recomputed locally in `language`; never invents facts."""
    language = _norm_language(language)
    channel = _norm_channel(channel)
    region = _norm_region(target_region)
    contact = contact or {}
    based_in = (based_in or "").strip() or "Turkey"
    profile_skills = [s for s in (profile_skills or []) if s]

    company = _extract_company(jd_text, contact, company, language)
    role = (role or "").strip() or _extract_role(jd_text, language)
    skills = relevant_skills(jd_text, profile_skills)
    region_phrase = _REGION_PHRASE[language].get(region, _REGION_PHRASE[language][None])

    subject = body = personalization_notes = None
    llm_used = False

    if llm_client.llm_available():
        prompt = build_prompt(
            jd_text=jd_text, contact=contact, language=language, channel=channel,
            tone=tone, role=role, company=company, skills=skills,
            region_phrase=region_phrase, resume_summary=resume_summary,
            include_location_line=include_location_line, based_in=based_in,
            timezone_overlap=timezone_overlap,
            include_work_auth_line=include_work_auth_line,
            work_authorization_note=work_authorization_note,
            skill_override=skill_highlight,
        )
        try:
            data = llm_client.generate_json(prompt)
            body = str(data.get("body") or "").strip()
            subject = str(data.get("subject") or "").strip()
            personalization_notes = str(data.get("personalization_notes") or "").strip()
            company = str(data.get("detected_company") or "").strip() or company
            role = str(data.get("detected_role") or "").strip() or role
            if not body:
                raise ValueError("missing body")
            llm_used = True
        except Exception:
            subject = body = personalization_notes = None
            llm_used = False

    if not body:
        fb = _deterministic(
            contact=contact, language=language, channel=channel, role=role,
            company=company, skills=skills, region_phrase=region_phrase,
            include_location_line=include_location_line, based_in=based_in,
            timezone_overlap=timezone_overlap,
            include_work_auth_line=include_work_auth_line,
            work_authorization_note=work_authorization_note,
            skill_override=skill_highlight,
        )
        subject = fb["subject"]
        body = fb["body"]
        personalization_notes = fb["personalization_notes"]

    quality = email_generator.quality_checklist(
        subject=subject, body=body, company=company, role=role,
        profile_skills=profile_skills, language=language,
    )
    risk = email_generator.risk_checklist(contact_source="manual")

    return {
        "subject": subject,
        "body": body,
        "language": language,
        "channel": channel,
        "message_type": f"{channel}_outreach",
        "tone": tone or "warm_low_pressure",
        "detected_company": company,
        "detected_role": role,
        "target_region": region,
        "based_in": based_in,
        "relevant_skills": skills,
        "personalization_notes": personalization_notes,
        "quality_checklist": quality,
        "risk_checklist": risk,
        "why_safe": email_generator.safety_summary(risk=risk, quality=quality),
        "suggested_next_step": email_generator.suggested_next_step(status="draft", outcome=None),
        "suggested_follow_up": follow_up_text(language),
        "contact_guidance": contact_guidance(company, language),
        "llm_used": llm_used,
    }
