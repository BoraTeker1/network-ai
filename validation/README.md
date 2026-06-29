# 7-Day Validation Sprint — Network AI (Remote/EU wedge)

**Goal of this week:** find out whether Turkish engineers chasing remote/EU roles
will *pay* for an outreach copilot — **before** building any more product.

You have a working demo. The unproven, business-killing questions are:

1. **Willingness to pay (WTP).** Will this specific person pay $9–19/mo?
2. **Distribution.** Can you reach them repeatably and cheaply?

This sprint answers #1 directly and gives an early read on #2. It is deliberately
**cheap and fast** — no new features, no billing integration, no infra.

> Target customer (decided): **a Turkish software engineer (junior–mid, in Turkey)
> actively trying to land a remote or European role for €/$ pay.** Not domestic
> juniors, not students broadly — the segment with money on the line.

---

## The three instruments

| File | What it is | Decides |
| --- | --- | --- |
| [`interview-script.md`](interview-script.md) | 15 customer-discovery calls (Mom-Test style) | Is the *pain* real and acute? Do they already spend money/time on it? |
| [`landing-page.md`](landing-page.md) | Landing page + **fake-door price button** copy | Will strangers click "pay"? (the WTP signal) |
| [`concierge-runbook.md`](concierge-runbook.md) | Do the workflow by hand for 5 people | Does the value actually land — do they get replies? |

Run all three in parallel. They triangulate: interviews tell you *why*, the landing
page tells you *how many*, the concierge runs tell you *whether it works*.

---

## Day-by-day

**Day 1 — Setup**
- Stand up the landing page (Carrd/Framer/Typedream — no code, ~2 hrs). Copy is in `landing-page.md`.
- Wire the email capture (the page's form → a Google Sheet or ConvertKit) and the
  fake-door price click → an event you can count (Plausible/PostHog, or just a second
  form step). See `landing-page.md` § "Instrumentation".
- Line up interview targets (see `interview-script.md` § "Where to find 15 people").

**Days 2–5 — Run in parallel**
- **Interviews:** book and run 3–4 calls/day → 15 by Day 5. Log each in the sheet.
- **Traffic:** post the landing page where the audience already is (see below). Aim
  for ~100 real visitors.
- **Concierge:** recruit 5 from interviews/landing page; run the `concierge-runbook.md`
  for each (find roles → find contacts → draft → they send).

**Day 6 — Tally**
- Fill in the scoreboard below from real numbers.

**Day 7 — Decide**
- Apply the go/no-go thresholds. Write a 1-paragraph decision and the reason.

---

## Where to get traffic & interviewees (free, where they already are)

- **r/cscareerquestionsEU**, **r/Turkey**, **r/developersTR**, **Devnot** Discord/Slack,
  **Kommunity** TR tech communities, **Turkish dev Twitter/X**, GDG İstanbul/Ankara groups.
- DM engineers on LinkedIn who recently posted "open to remote/relocation."
- Your own university/bootcamp alumni network.
- **Do not** spam. Post one honest "I'm researching how Turkish engineers land remote
  roles — 15-min call?" message. Offer the concierge run as the thank-you.

---

## Scoreboard (fill in on Day 6)

| Metric | Target (go signal) | Actual |
| --- | --- | --- |
| Interviews completed | ≥ 15 | |
| ...who described an *active, painful* remote/EU search | ≥ 60% | |
| ...who already pay for *anything* job-search-related (courses, Premium, coaches) | ≥ 30% | |
| Landing-page unique visitors | ≥ 100 | |
| Email signups | ≥ 25% of visitors | |
| **Fake-door "pay" clicks** | **≥ 8% of visitors** | |
| Concierge runs completed | ≥ 5 | |
| Concierge runs that got ≥1 reply within the week | ≥ 2 | |
| Anyone who *unprompted* asked "when can I pay / can I keep using it" | ≥ 1 | |

---

## Go / No-Go

- **Strong go:** fake-door clicks ≥ 8% **and** ≥ 3 interviewees already pay for
  job-search tools **and** ≥ 2 concierge runs got replies. → Build billing + onboard
  the waitlist. Charge from day one.
- **Weak / iterate:** signals mixed (e.g. lots of email signups but ~0 price clicks).
  → The pain is real but WTP isn't proven. Re-test price point / framing / channel
  before building. *Email signups are not validation — a price click is.*
- **No-go:** < 3% price clicks and interviewees treat it as "nice to have." → The
  individual won't pay. Either pivot the buyer (universities/bootcamps/coaches — a
  different sprint) or drop the idea. Better to learn this in a week than a year.

---

## Rules so you don't fool yourself

1. **A price click counts; a compliment does not.** "Cool idea, I'd totally use it"
   is worthless. Track behavior, not politeness.
2. **Don't pitch in interviews.** Ask about their *past* (what they did last month),
   not their *future* (what they'd hypothetically do). See the Mom-Test notes.
3. **Charge real money as soon as you can.** The fake-door is a proxy; an actual
   pre-order/deposit is the gold standard. If ≥3 people will Stripe you $5 to hold a
   spot, that beats 100 email signups.
4. **Write the decision down on Day 7** with the numbers, even if it's "no-go." That's
   the deliverable of the week — not more code.
