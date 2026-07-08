"use client";

// Lightweight TR/EN i18n: React context + typed dictionaries, no dependencies.
// Turkish is the default; the choice persists in localStorage and can be
// switched to English from the nav toggle.

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { en, type Dict } from "./en";
import { tr } from "./tr";

export type Lang = "en" | "tr";
const DICTS: Record<Lang, Dict> = { en, tr };
const STORAGE_KEY = "network_ai_lang";

const LangContext = createContext<{
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: Dict;
}>({ lang: "tr", setLang: () => {}, t: tr });

export function LanguageProvider({ children }: { children: ReactNode }) {
  // Render Turkish on the server / first paint, then swap after mount —
  // avoids an SSR hydration mismatch at the cost of a brief flash for EN users.
  const [lang, setLangState] = useState<Lang>("tr");

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored === "en" || stored === "tr") setLangState(stored);
    } catch {
      /* private mode etc. — stay on the Turkish default */
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  function setLang(next: Lang) {
    setLangState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* best-effort persistence */
    }
  }

  return (
    <LangContext.Provider value={{ lang, setLang, t: DICTS[lang] }}>
      {children}
    </LangContext.Provider>
  );
}

/** Current language + setter, e.g. for the nav toggle. */
export function useLang() {
  return useContext(LangContext);
}

/** The active dictionary — `const t = useT(); t.nav.opportunities`. */
export function useT(): Dict {
  return useContext(LangContext).t;
}
