import Link from "next/link";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/profile", label: "Profile" },
  { href: "/jobs", label: "Jobs" },
  { href: "/matches", label: "Matches" },
  { href: "/messages", label: "Messages" },
  { href: "/pipeline", label: "Pipeline" },
  { href: "/pitch", label: "Pitch" },
];

export default function Nav() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex max-w-5xl items-center gap-6 px-6 py-4">
        <Link href="/" className="font-semibold text-slate-900">
          Network<span className="text-blue-600">AI</span>
        </Link>
        <div className="flex gap-4 text-sm">
          {links.slice(1).map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="text-slate-600 hover:text-blue-600"
            >
              {l.label}
            </Link>
          ))}
        </div>
      </nav>
    </header>
  );
}
