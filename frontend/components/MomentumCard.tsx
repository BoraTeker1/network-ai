"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, MomentumSummary } from "@/lib/api";
import { useMomentum } from "@/components/MomentumProvider";

/** "Today's Momentum" — points today, total, streak, and recent wins.
 *  Refetches whenever points are awarded (via the provider's version counter). */
export default function MomentumCard() {
  const { version, muted, toggleMuted } = useMomentum();
  const [summary, setSummary] = useState<MomentumSummary | null>(null);

  useEffect(() => {
    let active = true;
    api
      .getMomentum()
      .then((s) => active && setSummary(s))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [version]);

  const today = summary?.points_today ?? 0;
  const total = summary?.total_points ?? 0;
  const streak = summary?.streak ?? 0;
  const wins = summary?.recent_wins ?? [];

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div className="h-1.5 w-full bg-gradient-to-r from-emerald-400 via-blue-500 to-indigo-600" />
      <div className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-base">⚡</span>
            <h3 className="text-sm font-semibold text-slate-900">
              Today&apos;s Momentum
            </h3>
          </div>
          <button
            onClick={toggleMuted}
            title={muted ? "Sounds muted — click to unmute" : "Mute celebration sounds"}
            className="rounded-md border border-slate-200 px-2 py-1 text-xs text-slate-500 hover:border-slate-400"
          >
            {muted ? "🔇 Muted" : "🔊 Sound on"}
          </button>
        </div>

        <div className="mt-3 grid grid-cols-3 gap-3">
          <div className="rounded-md bg-slate-50 p-3 text-center">
            <div className="text-2xl font-bold text-slate-900">{today}</div>
            <div className="mt-0.5 text-[11px] font-medium uppercase tracking-wide text-slate-500">
              Points today
            </div>
          </div>
          <div className="rounded-md bg-slate-50 p-3 text-center">
            <div className="text-2xl font-bold text-slate-900">{total}</div>
            <div className="mt-0.5 text-[11px] font-medium uppercase tracking-wide text-slate-500">
              Total points
            </div>
          </div>
          <div className="rounded-md bg-slate-50 p-3 text-center">
            <div className="text-2xl font-bold text-slate-900">
              {streak > 0 ? `🔥 ${streak}` : "—"}
            </div>
            <div className="mt-0.5 text-[11px] font-medium uppercase tracking-wide text-slate-500">
              Day streak
            </div>
          </div>
        </div>

        <div className="mt-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Recent wins
          </div>
          {wins.length === 0 ? (
            <p className="mt-1 text-sm text-slate-500">
              No momentum yet today. Approve a draft or log an outcome in{" "}
              <Link href="/messages" className="font-medium text-blue-600 hover:underline">
                Messages
              </Link>{" "}
              to start building momentum.
            </p>
          ) : (
            <ul className="mt-2 space-y-1">
              {wins.map((w, i) => (
                <li
                  key={`${w.event_type}-${i}`}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-slate-700">{w.label}</span>
                  <span className="font-semibold text-emerald-600">
                    +{w.points}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <p className="mt-3 text-[11px] text-slate-400">
          Momentum rewards quality progress you confirm by hand — never volume,
          bulk, or anything automated.
        </p>
      </div>
    </div>
  );
}
