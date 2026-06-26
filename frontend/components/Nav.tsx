import Link from "next/link";

// Turkey → remote/EU focus: the primary journey is Opportunities → Outreach.
// The legacy U.S. new-grad pages (Jobs, Matches, Messages, Emails) still exist
// as routes but are intentionally off the primary nav.
const links = [
  { href: "/opportunities", label: "Opportunities" },
  { href: "/outreach", label: "Outreach" },
  { href: "/next-move", label: "Next Move" },
  { href: "/pipeline", label: "Pipeline" },
  { href: "/profile", label: "Profile" },
  { href: "/goals", label: "Goals" },
  { href: "/events", label: "Events" },
  { href: "/vibe", label: "Vibe Mode" },
  { href: "/pitch", label: "Pitch" },
];

export default function Nav() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-6 py-3">
        <Link href="/opportunities" className="shrink-0 whitespace-nowrap font-semibold text-slate-900">
          Network<span className="text-blue-600">AI</span>
        </Link>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="whitespace-nowrap text-slate-600 hover:text-blue-600"
            >
              {l.label}
            </Link>
          ))}
        </div>
      </nav>
    </header>
  );
}
