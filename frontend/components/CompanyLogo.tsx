"use client";

// Opportunities carry no logo, so we derive one from the company's own domain
// and fall back to a monogram tile when we don't have one.
//
// The apply URL is almost never the company's site — it's the ATS board the job
// was imported from — so a favicon keyed off it would render the same Greenhouse
// icon on 84 of 100 cards. Hosts on ATS_HOSTS are therefore rejected outright;
// the real domain, when we have it, comes from the source registry's careers_url.

import { useState } from "react";

// Applicant-tracking systems and job aggregators: their favicon says nothing
// about the company, so treat these as "no logo" and use the monogram instead.
const ATS_HOSTS = [
  "greenhouse.io",
  "lever.co",
  "ashbyhq.com",
  "workable.com",
  "recruitee.com",
  "smartrecruiters.com",
  "myworkdayjobs.com",
  "personio.de",
  "careers-page.com",
  "arbeitnow.com",
  "remotive.com",
  "jobicy.com",
  "weworkremotely.com",
  "linkedin.com",
  "kariyer.net",
];

function hostOf(url: string | null): string | null {
  if (!url) return null;
  try {
    const host = new URL(url).hostname;
    if (ATS_HOSTS.some((ats) => host === ats || host.endsWith(`.${ats}`))) return null;
    return host;
  } catch {
    return null;
  }
}

// Stable hue per company so a given logo tile never changes color between renders.
function hueOf(name: string): number {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) % 360;
  return hash;
}

export default function CompanyLogo({
  company,
  url,
  careersUrl,
  className = "h-12 w-12",
}: {
  company: string | null;
  /** The apply link — usable only when it isn't an ATS board. */
  url: string | null;
  /** The company's own careers page, from the source registry. Preferred. */
  careersUrl?: string | null;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  const name = company?.trim() || "?";
  const host = hostOf(careersUrl ?? null) ?? hostOf(url);

  if (host && !failed) {
    return (
      <div
        className={`flex shrink-0 items-center justify-center overflow-hidden rounded-xl border border-slate-200 bg-white ${className}`}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`https://www.google.com/s2/favicons?domain=${host}&sz=64`}
          alt=""
          width={28}
          height={28}
          className="h-7 w-7 object-contain"
          onError={() => setFailed(true)}
        />
      </div>
    );
  }

  const hue = hueOf(name);
  return (
    <div
      aria-hidden
      className={`flex shrink-0 items-center justify-center rounded-xl border border-slate-200 text-base font-semibold ${className}`}
      style={{
        backgroundColor: `hsl(${hue} 70% 96%)`,
        color: `hsl(${hue} 45% 38%)`,
      }}
    >
      {name.charAt(0).toLocaleUpperCase("tr")}
    </div>
  );
}
