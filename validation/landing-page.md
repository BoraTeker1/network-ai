# Landing Page + Fake-Door Price Test

**Purpose:** measure the one number that matters — what % of real visitors will click
a **"Start" button that shows a price.** Email signups are interest; a price click is
intent. We measure intent.

**Build it codeless** (Carrd, Framer, Typedream, or a Notion page + Tally form). ~2 hrs.
Primary language **English** (the audience reads English and is targeting EU/remote),
with a one-line Turkish subhead so it feels native. Don't connect it to the real app.

---

## Page copy (English primary)

### Hero
**Headline:** Land a remote or European role — by networking, not just applying.

**Subhead:** Network AI finds remote/EU jobs you actually fit, tells you who to
contact, and drafts an honest outreach message in English or Turkish. You review and
send it yourself. Built for engineers in Türkiye.

**Turkish subhead (small, under it):** Türkiye'den uzaktan ve Avrupa rollerine ulaşmanın
en hızlı yolu — doğru kişiyi bul, dürüst bir mesaj taslağı al, sen gönder.

**Primary CTA button:** `Start landing interviews →`
**Secondary line under button:** Join the first batch. No spam, no auto-sending — ever.

### Problem (3 short bullets)
- Cold applications vanish into ATS black holes. In this market, **referrals decide.**
- You know you should reach out — but *who?* And what do you say in English without
  sounding cringe?
- So you don't. The best roles go to people who networked. **That stops now.**

### How it works (3 steps, with a screenshot of your real app for each)
1. **See roles you fit.** Real remote/EU + Turkey listings, ranked by your résumé —
   each labeled for whether a Turkey-based candidate can actually apply.
2. **Find the right person.** We show who to contact and give you the exact search
   links — find them in two clicks. No scraping, no shady data.
3. **Send an honest message.** A personalized, low-pressure draft in English *or*
   Turkish, using your real skills. You edit, copy, and send it yourself.

### Why it's not spam (trust block — this audience is wary)
Copilot, not autopilot. **No scraping. No auto-sending. No bulk blasts.** Every message
is yours to review and send. We help you network *better*, not spam more.

### Pricing (the fake door)
> Show real prices. This is the test.

**Free** — Browse ranked roles + 3 outreach drafts / month.
`Start free →`

**Pro — $12 / month** — Unlimited drafts, who-to-contact for every role, follow-up
reminders, bilingual TR/EN. `Start Pro →`  ← *primary, visually emphasized*

**Coach — $39 / month** — For mentors/coaches managing several job seekers. `Start →`

*(Price points to test: Pro at $12 is the anchor. If you want a second variant later,
test $19. Don't show two prices on the same page.)*

### FAQ
- **Is my data scraped from LinkedIn?** No. You paste jobs and find contacts via
  normal search links. We never scrape or auto-message.
- **English or Turkish?** Both — drafts in either, your choice per message.
- **Do you apply for me?** No. You stay in control; you send everything.
- **I'm based in Türkiye — can I really get these roles?** Every listing is labeled for
  Turkey-applicability (remote-worldwide, EMEA, etc.), so you don't waste time on
  US-only roles.

### Final CTA
**Get in the first batch.** `Start →` + email field.

---

## Instrumentation (how to actually measure)

The funnel you're measuring:

```
Visitor  →  clicks "Start Pro" (PRICE CLICK = the WTP signal)  →  enters email  →  (optional) pre-pay
```

**Minimum viable setup:**
1. Add **Plausible** or **PostHog** (free tiers, 5 min) for visitor count + button clicks.
   Make the price buttons fire a tracked event (`start_pro_click`, `start_free_click`).
2. The "Start Pro" button opens a **2nd step**, not the app:
   > "We're onboarding the first batch this week. Drop your email and you're in —
   > and tell us one thing: what would make this a no-brainer to pay for?"
   - Email field + one open text question. (The open answer is gold for messaging.)
3. Count: `start_pro_click / unique_visitors` = your headline WTP number.

**Stronger setup (do this if you can — it's the real test):**
- Make "Start Pro" go to a **Stripe Payment Link** for a **$5 refundable deposit /
  founding-member pre-order** ("$5 holds your spot and 50% off the first 3 months").
- *Anyone who actually pays $5 is worth ~50 email signups.* If even 3 strangers do this,
  you have real validation. Refund them all later (or honor it).

**What to log per visitor source:** which channel (Reddit / Discord / LinkedIn / Twitter)
drove the click, so you also learn **distribution**, not just WTP.

---

## Targets (repeated from the scoreboard)
- ≥ 100 unique visitors this week.
- ≥ 25% leave an email.
- **≥ 8% click "Start Pro"** (the number that decides go/no-go).
- Bonus gold: ≥ 3 people pay the $5 deposit.

## Don't fool yourself
- A pretty page with 200 email signups and **zero** price clicks = **not validated.**
- One channel converting at 15% while others get 1% tells you *where* your customer is —
  that's the distribution answer hiding in the data. Note it.
