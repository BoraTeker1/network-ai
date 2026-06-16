"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/ui";
import {
  VIBE_CHECKLIST,
  VIBE_MOODS,
  VIBE_SPRINT_SECONDS,
  VIBE_STORAGE_KEYS,
  findMood,
  formatSprint,
} from "@/lib/vibe";

export default function VibeModePage() {
  // --- Mood (persisted) ---
  const [moodId, setMoodId] = useState(VIBE_MOODS[0].id);
  const mood = findMood(moodId);

  // --- Sprint timer ---
  const [secondsLeft, setSecondsLeft] = useState(VIBE_SPRINT_SECONDS);
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // --- Checklist (persisted) ---
  const [checked, setChecked] = useState<Record<string, boolean>>({});

  // Hydrate persisted state on mount (client-only — avoids SSR mismatch).
  useEffect(() => {
    try {
      const savedMood = localStorage.getItem(VIBE_STORAGE_KEYS.mood);
      if (savedMood) setMoodId(findMood(savedMood).id);
      const savedChecklist = localStorage.getItem(VIBE_STORAGE_KEYS.checklist);
      if (savedChecklist) setChecked(JSON.parse(savedChecklist));
    } catch {
      /* localStorage may be unavailable; defaults are fine */
    }
  }, []);

  // Tick the countdown while running.
  useEffect(() => {
    if (!running) return;
    intervalRef.current = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          setRunning(false);
          setDone(true);
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [running]);

  const selectMood = useCallback((id: string) => {
    setMoodId(id);
    try {
      localStorage.setItem(VIBE_STORAGE_KEYS.mood, id);
    } catch {
      /* ignore */
    }
  }, []);

  const toggleCheck = useCallback((id: string) => {
    setChecked((prev) => {
      const next = { ...prev, [id]: !prev[id] };
      try {
        localStorage.setItem(VIBE_STORAGE_KEYS.checklist, JSON.stringify(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  function resetSprint() {
    setRunning(false);
    setDone(false);
    setSecondsLeft(VIBE_SPRINT_SECONDS);
  }

  function resetChecklist() {
    setChecked({});
    try {
      localStorage.removeItem(VIBE_STORAGE_KEYS.checklist);
    } catch {
      /* ignore */
    }
  }

  const doneCount = VIBE_CHECKLIST.filter((c) => checked[c.id]).length;
  const progressPct = Math.round(
    ((VIBE_SPRINT_SECONDS - secondsLeft) / VIBE_SPRINT_SECONDS) * 100
  );

  return (
    <div>
      <PageHeader
        title="Vibe Mode"
        subtitle="A focused 25-minute networking sprint. Pick a mood, press play on the embedded player, start the timer, and work the checklist — same permission-based workflow, just less boring."
      />

      {/* Accent banner */}
      <div className={`mt-6 h-2 w-full rounded-full bg-gradient-to-r ${mood.accent}`} />

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        {/* Timer */}
        <section className="rounded-lg border border-slate-200 bg-white p-5">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Sprint timer
          </div>
          <div className="mt-2 text-center">
            <div className="font-mono text-5xl font-bold tracking-tight text-slate-900">
              {formatSprint(secondsLeft)}
            </div>
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-200">
              <div
                className={`h-full rounded-full bg-gradient-to-r ${mood.accent}`}
                style={{ width: `${progressPct}%` }}
              />
            </div>
            {done && (
              <p className="mt-3 rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
                Sprint complete — nice work. Update your outcomes and take a break. 🎉
              </p>
            )}
          </div>
          <div className="mt-4 flex justify-center gap-2">
            <button
              onClick={() => {
                setDone(false);
                setRunning((r) => !r);
              }}
              disabled={secondsLeft === 0}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {running ? "Pause" : secondsLeft === VIBE_SPRINT_SECONDS ? "Start" : "Resume"}
            </button>
            <button
              onClick={resetSprint}
              className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:border-blue-400"
            >
              Reset
            </button>
          </div>
          <p className="mt-3 text-center text-xs text-slate-400">
            The timer is independent of the music — nothing autoplays.
          </p>
        </section>

        {/* Player */}
        <section className="rounded-lg border border-slate-200 bg-white p-5 lg:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Now playing · {mood.name}
            </div>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-500">
              {mood.provider} embed
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-600">{mood.description}</p>
          <div className="mt-3 overflow-hidden rounded-lg border border-slate-200">
            <iframe
              key={mood.id}
              title={`${mood.name} player`}
              src={mood.embedUrl}
              width="100%"
              height="352"
              style={{ border: 0 }}
              loading="lazy"
              allow="encrypted-media; clipboard-write; fullscreen; picture-in-picture"
            />
          </div>
          <p className="mt-2 text-xs text-slate-400">
            Music is streamed by {mood.provider} in an embedded player. Network AI
            does not host any audio and never plays it automatically — press play
            when you&apos;re ready.
          </p>
        </section>
      </div>

      {/* Mood selector */}
      <section className="mt-8">
        <h2 className="text-lg font-semibold text-slate-900">Choose your mood</h2>
        <p className="mt-1 text-sm text-slate-500">
          Your choice is saved for next time.
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {VIBE_MOODS.map((m) => {
            const active = m.id === moodId;
            return (
              <button
                key={m.id}
                onClick={() => selectMood(m.id)}
                className={`overflow-hidden rounded-lg border bg-white text-left transition ${
                  active
                    ? "border-blue-500 ring-2 ring-blue-200"
                    : "border-slate-200 hover:border-blue-400"
                }`}
              >
                <div className={`h-1.5 w-full bg-gradient-to-r ${m.accent}`} />
                <div className="p-3">
                  <div className="text-sm font-semibold text-slate-900">
                    {m.name}
                  </div>
                  <div className="mt-0.5 text-xs text-slate-500">{m.tagline}</div>
                  {active && (
                    <div className="mt-2 text-[11px] font-medium text-blue-600">
                      ✓ Selected
                    </div>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </section>

      {/* Sprint checklist */}
      <section className="mt-8 rounded-lg border border-slate-200 bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Sprint checklist</h2>
          <span className="text-sm font-medium text-slate-500">
            {doneCount}/{VIBE_CHECKLIST.length} done
          </span>
        </div>
        <p className="mt-1 text-sm text-slate-500">
          Four steps, one focused block. Each opens the page where the work
          actually happens.
        </p>
        <ul className="mt-3 space-y-2">
          {VIBE_CHECKLIST.map((c) => {
            const isChecked = !!checked[c.id];
            return (
              <li
                key={c.id}
                className="flex items-center justify-between gap-3 rounded-md border border-slate-100 bg-slate-50 p-3"
              >
                <label className="flex cursor-pointer items-center gap-3">
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => toggleCheck(c.id)}
                    className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span
                    className={`text-sm ${
                      isChecked
                        ? "text-slate-400 line-through"
                        : "font-medium text-slate-800"
                    }`}
                  >
                    {c.label}
                  </span>
                </label>
                <Link
                  href={c.href}
                  className="shrink-0 text-sm font-medium text-blue-600 hover:underline"
                >
                  Open →
                </Link>
              </li>
            );
          })}
        </ul>
        {doneCount > 0 && (
          <button
            onClick={resetChecklist}
            className="mt-3 text-xs font-medium text-slate-400 hover:text-slate-600"
          >
            Reset checklist
          </button>
        )}
      </section>

      <p className="mt-8 text-xs text-slate-400">
        Vibe Mode only changes the pacing and atmosphere of your outreach — the
        rules are unchanged: no scraping, no auto-send, no bulk sending. You still
        review, approve, and send everything yourself.
      </p>
    </div>
  );
}
