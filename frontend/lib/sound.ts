// Momentum sound effects — generated live with the Web Audio API.
//
// Guardrails:
// - NO copyrighted/hosted audio files; every chime is synthesized in-browser.
// - NO autoplay: chimes only play from a user-initiated action (clicking an
//   outcome), so the AudioContext is created/resumed inside a user gesture.
// - Muteable; the preference is persisted in localStorage.

export type Celebration = "big" | "medium" | "small" | "none";

const MUTE_KEY = "vibe-mode:momentum-muted";

let audioCtx: AudioContext | null = null;

function getCtx(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!audioCtx) {
    const AC =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext })
        .webkitAudioContext;
    if (!AC) return null;
    audioCtx = new AC();
  }
  return audioCtx;
}

export function isMuted(): boolean {
  try {
    return localStorage.getItem(MUTE_KEY) === "1";
  } catch {
    return false;
  }
}

export function setMutedPref(muted: boolean): void {
  try {
    localStorage.setItem(MUTE_KEY, muted ? "1" : "0");
  } catch {
    /* localStorage unavailable — ignore */
  }
}

/** A single soft sine "bell" note with a click-free envelope. */
function note(
  ctx: AudioContext,
  freq: number,
  startAt: number,
  duration: number,
  peak = 0.14
): void {
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = "sine";
  osc.frequency.value = freq;
  gain.gain.setValueAtTime(0.0001, startAt);
  gain.gain.exponentialRampToValueAtTime(peak, startAt + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, startAt + duration);
  osc.connect(gain).connect(ctx.destination);
  osc.start(startAt);
  osc.stop(startAt + duration + 0.03);
}

/** Play a short, tasteful chime sized to the celebration level. */
export function playChime(level: Celebration): void {
  if (level === "none") return;
  if (isMuted()) return;
  const ctx = getCtx();
  if (!ctx) return;
  if (ctx.state === "suspended") void ctx.resume();

  const t = ctx.currentTime + 0.01;
  if (level === "big") {
    // Rising major arpeggio — celebratory but not arcade-y.
    [523.25, 659.25, 783.99, 1046.5].forEach((f, i) =>
      note(ctx, f, t + i * 0.1, 0.3, 0.16)
    );
  } else if (level === "medium") {
    [587.33, 880].forEach((f, i) => note(ctx, f, t + i * 0.1, 0.26, 0.14));
  } else {
    note(ctx, 783.99, t, 0.18, 0.12);
  }
}
