import Link from "next/link";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/profile", label: "Profile" },
  { href: "/goals", label: "Goals" },
  { href: "/jobs", label: "Jobs" },
  { href: "/matches", label: "Matches" },
  { href: "/messages", label: "Messages" },
  { href: "/emails", label: "Emails" },
  { href: "/pipeline", label: "Pipeline" },
  { href: "/pitch", label: "Pitch" },
];

export default function Nav() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-6 py-3">
        <Link href="/" className="shrink-0 whitespace-nowrap font-semibold text-slate-900">
          Network<span className="text-blue-600">AI</span>
        </Link>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
          {links.slice(1).map((l) => (
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
