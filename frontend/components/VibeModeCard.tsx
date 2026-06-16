import Link from "next/link";
import { VIBE_SPRINT_MINUTES } from "@/lib/vibe";

/** Dashboard promo for Vibe Mode — a branded entry point into the sprint.
 *  Professional, not gimmicky: a single tasteful accent bar, no autoplay. */
export default function VibeModeCard() {
  return (
    <Link
      href="/vibe"
      className="group block overflow-hidden rounded-lg border border-slate-200 bg-white transition hover:border-blue-400"
    >
      <div className="h-1.5 w-full bg-gradient-to-r from-orange-400 via-rose-500 to-indigo-600" />
      <div className="flex flex-wrap items-center justify-between gap-3 p-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-base">🎧</span>
            <h3 className="text-sm font-semibold text-slate-900">Vibe Mode</h3>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-500">
              New
            </span>
          </div>
          <p className="mt-1 max-w-xl text-sm text-slate-600">
            Turn outreach into a focused {VIBE_SPRINT_MINUTES}-minute networking
            sprint — pick a mood, start the timer, and work the checklist with
            sunset/deep-house music playing alongside.
          </p>
        </div>
        <span className="shrink-0 rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white transition group-hover:bg-blue-600">
          Start a sprint →
        </span>
      </div>
    </Link>
  );
}
