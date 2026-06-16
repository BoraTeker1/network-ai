"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { MomentumAward } from "@/lib/api";
import { isMuted, playChime, setMutedPref } from "@/lib/sound";

type MomentumContextValue = {
  /** Show a celebration toast (+ optional chime) for an awarded event. */
  celebrate: (award?: MomentumAward | null) => void;
  muted: boolean;
  toggleMuted: () => void;
  /** Increments whenever points are awarded — lets the dashboard card refetch. */
  version: number;
};

// Safe no-op default so components never crash if rendered outside the provider.
const MomentumContext = createContext<MomentumContextValue>({
  celebrate: () => {},
  muted: false,
  toggleMuted: () => {},
  version: 0,
});

export function useMomentum(): MomentumContextValue {
  return useContext(MomentumContext);
}

type Toast = { id: number; award: MomentumAward };

const TOAST_STYLES: Record<
  MomentumAward["celebration"],
  { wrap: string; bar: string; emoji: string }
> = {
  big: {
    wrap: "border-transparent ring-2 ring-rose-300",
    bar: "bg-gradient-to-r from-amber-400 via-rose-500 to-indigo-600",
    emoji: "🎉",
  },
  medium: {
    wrap: "border-blue-200",
    bar: "bg-blue-500",
    emoji: "✨",
  },
  small: {
    wrap: "border-emerald-200",
    bar: "bg-emerald-500",
    emoji: "✓",
  },
  none: {
    wrap: "border-slate-200",
    bar: "bg-slate-300",
    emoji: "•",
  },
};

function MomentumToast({
  award,
  onClose,
}: {
  award: MomentumAward;
  onClose: () => void;
}) {
  const s = TOAST_STYLES[award.celebration] ?? TOAST_STYLES.small;
  const big = award.celebration === "big";
  return (
    <div
      role="status"
      className={`pointer-events-auto overflow-hidden rounded-lg border bg-white shadow-lg ${s.wrap}`}
    >
      <div className={`h-1 w-full ${s.bar}`} />
      <div className="flex items-start gap-3 p-3">
        <span className={big ? "text-2xl" : "text-lg"}>{s.emoji}</span>
        <div className="min-w-0 flex-1">
          <div
            className={`font-semibold text-slate-900 ${big ? "text-base" : "text-sm"}`}
          >
            {award.points > 0 ? `Momentum +${award.points}` : "Outcome logged"}
          </div>
          <div className="mt-0.5 text-xs text-slate-600">
            {award.points > 0
              ? award.label
              : "No points, no pressure — tracked for your pipeline."}
          </div>
        </div>
        <button
          onClick={onClose}
          aria-label="Dismiss"
          className="shrink-0 text-slate-300 hover:text-slate-500"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

export default function MomentumProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [muted, setMuted] = useState(false);
  const [version, setVersion] = useState(0);
  const idRef = useRef(0);

  // Sync mute preference from localStorage on mount.
  useEffect(() => {
    setMuted(isMuted());
  }, []);

  const dismiss = useCallback((id: number) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  const celebrate = useCallback(
    (award?: MomentumAward | null) => {
      if (!award) return;
      const id = (idRef.current += 1);
      setToasts((t) => [...t, { id, award }]);
      // Chime respects the persisted mute preference (read inside playChime).
      playChime(award.celebration);
      if (award.points > 0) setVersion((v) => v + 1);
      const ttl = award.celebration === "big" ? 5200 : 3600;
      window.setTimeout(() => dismiss(id), ttl);
    },
    [dismiss]
  );

  const toggleMuted = useCallback(() => {
    setMuted((m) => {
      const next = !m;
      setMutedPref(next);
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({ celebrate, muted, toggleMuted, version }),
    [celebrate, muted, toggleMuted, version]
  );

  return (
    <MomentumContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed right-4 top-4 z-50 flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2">
        {toasts.map((t) => (
          <MomentumToast
            key={t.id}
            award={t.award}
            onClose={() => dismiss(t.id)}
          />
        ))}
      </div>
    </MomentumContext.Provider>
  );
}
