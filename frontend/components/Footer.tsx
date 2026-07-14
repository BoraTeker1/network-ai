"use client";

import { useT } from "@/lib/i18n";

/** Lightweight founder-contact line on every page — beta users need a
 * zero-friction way to report issues. mailto only; no support system. */
export default function Footer() {
  const t = useT();
  return (
    <footer className="px-6 pb-8 text-center text-xs text-slate-400">
      {t.footer.beta}{" "}
      <a
        href="mailto:tekerbora@gmail.com?subject=Network%20AI%20feedback"
        className="font-medium text-brand-700 hover:underline"
      >
        {t.footer.emailFounder}
      </a>
    </footer>
  );
}
