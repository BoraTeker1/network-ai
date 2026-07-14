"use client";

// Bookmarked roles, browser-local only. There is no saved-jobs table yet, so
// these ids live in localStorage — which also means a bookmark can go stale if
// a source re-import renumbers the opportunity. Acceptable until the backend
// grows a real endpoint; nothing else depends on this state.

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "network_ai_saved_opps";

function read(): number[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((n) => typeof n === "number") : [];
  } catch {
    return [];
  }
}

export function useSavedOpportunities() {
  // Start empty so the server render and the first client paint agree; the
  // stored ids arrive right after mount.
  const [saved, setSaved] = useState<number[]>([]);

  useEffect(() => {
    setSaved(read());
  }, []);

  const toggle = useCallback((id: number) => {
    setSaved((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        /* private mode — the toggle still works for this session */
      }
      return next;
    });
  }, []);

  const has = useCallback((id: number) => saved.includes(id), [saved]);

  return { saved, toggle, has };
}
