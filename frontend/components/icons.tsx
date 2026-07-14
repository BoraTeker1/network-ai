// Inline stroke icons — no icon library, no runtime cost. Every icon inherits
// the current text color and sizes off `className` (default 1rem square).

type IconProps = { className?: string };

function Svg({
  className = "h-4 w-4",
  children,
}: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      {children}
    </svg>
  );
}

export function Briefcase(p: IconProps) {
  return (
    <Svg {...p}>
      <rect x="2.5" y="7" width="19" height="13" rx="2" />
      <path d="M8.5 7V5.5a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2V7" />
      <path d="M2.5 12h19" />
    </Svg>
  );
}

export function FileText(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
      <path d="M14 3v5h5" />
      <path d="M9 13h6M9 17h4" />
    </Svg>
  );
}

export function Send(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M21 3 10.5 13.5" />
      <path d="M21 3l-6.5 18-4-8-8-4z" />
    </Svg>
  );
}

export function User(p: IconProps) {
  return (
    <Svg {...p}>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
    </Svg>
  );
}

export function Search(p: IconProps) {
  return (
    <Svg {...p}>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4.5 4.5" />
    </Svg>
  );
}

export function Bell(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M18 9a6 6 0 1 0-12 0c0 5-2 6-2 6h16s-2-1-2-6" />
      <path d="M13.7 20a2 2 0 0 1-3.4 0" />
    </Svg>
  );
}

export function Refresh(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M20 11a8 8 0 0 0-13.7-5.2L3 9" />
      <path d="M3 4v5h5" />
      <path d="M4 13a8 8 0 0 0 13.7 5.2L21 15" />
      <path d="M21 20v-5h-5" />
    </Svg>
  );
}

export function ShieldCheck(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M12 3 5 6v5.5c0 4.3 2.9 8.2 7 9.5 4.1-1.3 7-5.2 7-9.5V6z" />
      <path d="m9 12 2 2 4-4" />
    </Svg>
  );
}

export function Target(p: IconProps) {
  return (
    <Svg {...p}>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="4.5" />
      <circle cx="12" cy="12" r="1" />
    </Svg>
  );
}

export function Bookmark({ className = "h-4 w-4", filled = false }: IconProps & { filled?: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      <path d="M18 21 12 17l-6 4V5.5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2z" />
    </svg>
  );
}

export function Sliders(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M4 7h10M18 7h2M4 17h4M12 17h8" />
      <circle cx="16" cy="7" r="2" />
      <circle cx="10" cy="17" r="2" />
    </Svg>
  );
}

export function ArrowUpRight(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M8 16 16 8" />
      <path d="M9 8h7v7" />
    </Svg>
  );
}

export function ChevronDown(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="m6 9 6 6 6-6" />
    </Svg>
  );
}

export function GraduationCap(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M12 4 2 9l10 5 10-5z" />
      <path d="M6 11.5V16c0 1.7 2.7 3 6 3s6-1.3 6-3v-4.5" />
    </Svg>
  );
}

export function Menu(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M4 6h16M4 12h16M4 18h16" />
    </Svg>
  );
}

export function X(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M6 6l12 12M18 6 6 18" />
    </Svg>
  );
}

export function SortDesc(p: IconProps) {
  return (
    <Svg {...p}>
      <path d="M4 6h13M4 12h9M4 18h5" />
    </Svg>
  );
}
