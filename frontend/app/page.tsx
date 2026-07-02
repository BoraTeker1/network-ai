"use client";

// Turkish landing page for first-time (logged-out) visitors. Logged-in users
// skip it and land on /opportunities, the start of the product loop. The page
// is public (RouteGuard allows "/"); auth state comes from the client-side
// AuthProvider, so the redirect happens after /auth/me resolves.

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { Card } from "@/components/ui";

/* ----------------------------- Copy ----------------------------- */

const VALUE_CARDS = [
  {
    icon: "search",
    title: "Gerçekçi rolleri bul",
    body: "Türkiye’den başvurulabilecek junior, staj ve remote/EU rollerini tek yerde gör.",
  },
  {
    icon: "rank",
    title: "Profiline göre sırala",
    body: "CV’ndeki becerilerle hangi rollerin sana daha yakın olduğunu hızlıca anla.",
  },
  {
    icon: "pencil",
    title: "Dürüst outreach yaz",
    body: "LinkedIn veya e-posta için Türkçe/İngilizce, düşük baskılı mesaj taslakları hazırla.",
  },
  {
    icon: "board",
    title: "Pipeline’da takip et",
    body: "Kime yazdığını, ne zaman gönderdiğini ve cevap gelince sonraki adımı tek yerde takip et.",
  },
] as const;

const STEPS = [
  { n: 1, title: "CV’ni ekle", body: "Becerilerin otomatik çıkarılır." },
  { n: 2, title: "Rol seç", body: "Uygunluk etiketleriyle birlikte." },
  { n: 3, title: "Outreach taslağı oluştur", body: "TR/EN, düşük baskılı ton." },
  { n: 4, title: "Pipeline’a kaydet", body: "Gönderimi ve cevabı takip et." },
];

const TRUST_BULLETS = [
  "LinkedIn veya Kariyer.net scraping yapmaz.",
  "Senin adına otomatik mesaj göndermez.",
  "Toplu spam gönderimi yoktur.",
  "Her mesajı sen inceler, düzenler ve gönderirsin.",
  "CV ve mesaj verilerin kullanıcı hesabına özeldir.",
];

/* --------------------------- Small bits --------------------------- */

function PrimaryCta({ children }: { children: React.ReactNode }) {
  return (
    <Link
      href="/signup"
      className="inline-flex items-center justify-center rounded-md bg-blue-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700"
    >
      {children}
    </Link>
  );
}

function SecondaryCta({ children }: { children: React.ReactNode }) {
  return (
    <Link
      href="/login"
      className="inline-flex items-center justify-center rounded-md border border-slate-300 bg-white px-5 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:border-slate-400 hover:bg-slate-50"
    >
      {children}
    </Link>
  );
}

/** Tiny hand-drawn icons — no icon library. */
function ValueIcon({ name }: { name: (typeof VALUE_CARDS)[number]["icon"] }) {
  const paths: Record<string, React.ReactNode> = {
    search: (
      <>
        <circle cx="11" cy="11" r="6" />
        <path d="m20 20-4.8-4.8" />
      </>
    ),
    rank: (
      <>
        <path d="M4 18h6" />
        <path d="M4 12h10" />
        <path d="M4 6h16" />
      </>
    ),
    pencil: (
      <>
        <path d="M17 3a2.8 2.8 0 1 1 4 4L7.5 20.5 3 21.5l1-4.5Z" />
      </>
    ),
    board: (
      <>
        <rect x="4" y="4" width="6" height="16" rx="1.5" />
        <rect x="14" y="4" width="6" height="10" rx="1.5" />
      </>
    ),
  };
  return (
    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
      <svg
        viewBox="0 0 24 24"
        className="h-[18px] w-[18px]"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden
      >
        {paths[name]}
      </svg>
    </span>
  );
}

/* ------------------------- Product mockup ------------------------- */

function MockRoleRow({
  title,
  place,
  badge,
  badgeTone,
}: {
  title: string;
  place: string;
  badge: string;
  badgeTone: "green" | "blue";
}) {
  const tone =
    badgeTone === "green"
      ? "bg-green-100 text-green-800"
      : "bg-blue-50 text-blue-700";
  return (
    <div className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2">
      <div className="min-w-0">
        <div className="truncate text-[13px] font-medium text-slate-800">
          {title}
        </div>
        <div className="text-[11px] text-slate-500">{place}</div>
      </div>
      <span
        className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${tone}`}
      >
        {badge}
      </span>
    </div>
  );
}

/** Pipeline stage chip for the mockup's tracker strip. */
function MockStage({
  label,
  count,
  active = false,
}: {
  label: string;
  count: number;
  active?: boolean;
}) {
  return (
    <div
      className={`flex flex-1 flex-col items-center rounded-lg border px-2 py-1.5 ${
        active
          ? "border-blue-600 bg-blue-50/70"
          : "border-slate-200 bg-white"
      }`}
    >
      <span
        className={`text-sm font-bold ${active ? "text-blue-700" : "text-slate-700"}`}
      >
        {count}
      </span>
      <span className="whitespace-nowrap text-[9px] font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </span>
    </div>
  );
}

/** Static mini-dashboard: stages → roles → draft in one glance. */
function ProductMockup() {
  return (
    <div aria-hidden className="relative select-none" role="presentation">
      {/* soft glow behind the card */}
      <div className="absolute -inset-4 -z-10 rounded-[28px] bg-white/70 blur-2xl" />
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl">
        {/* window chrome */}
        <div className="flex items-center gap-1.5 border-b border-slate-100 bg-slate-50 px-4 py-2.5">
          <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
          <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
          <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
          <span className="ml-2 text-[11px] font-medium text-slate-400">
            NetworkAI
          </span>
        </div>

        <div className="space-y-3 p-4 pb-8">
          {/* pipeline stage tracker */}
          <div className="flex items-center gap-1.5">
            <MockStage label="Taslak" count={4} />
            <span className="text-slate-300">→</span>
            <MockStage label="Gönderildi" count={3} active />
            <span className="text-slate-300">→</span>
            <MockStage label="Cevap" count={1} />
          </div>

          {/* today's opportunities */}
          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Bugünün fırsatları
              </span>
              <span className="text-[11px] font-medium text-blue-600">
                12 yeni rol
              </span>
            </div>
            <div className="space-y-1.5">
              <MockRoleRow
                title="Backend Engineer Intern"
                place="İstanbul"
                badge="Türkiye’den uygun"
                badgeTone="green"
              />
              <MockRoleRow
                title="Junior Software Engineer"
                place="Remote / EU"
                badge="Remote/EU"
                badgeTone="blue"
              />
            </div>
          </div>

          {/* outreach draft */}
          <div className="rounded-lg bg-slate-50 px-3 py-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Outreach taslağı
              </span>
              <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-blue-700">
                TR / EN
              </span>
            </div>
            <p className="mt-1.5 text-[12px] leading-relaxed text-slate-600">
              “Merhaba Deniz Bey, ilanınızın backend/Spring deneyimimle ilgili
              olduğunu düşündüm…”
            </p>
            <p className="mt-1 text-[10px] text-slate-400">
              Sen düzenler, sen gönderirsin.
            </p>
          </div>

        </div>
      </div>

      {/* popped-out row with cursor — the reply just came in */}
      <div className="absolute -bottom-4 -left-3 right-8 sm:-left-8">
        <div className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-lg">
          <div className="min-w-0">
            <div className="truncate text-[12px] font-medium text-slate-800">
              Junior Software Engineer
            </div>
            <div className="text-[10px] text-slate-500">
              Cevap geldi · Next Move önerisi hazır
            </div>
          </div>
          <span className="shrink-0 rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-semibold text-green-800">
            Cevap ✓
          </span>
        </div>
        {/* cursor arrow */}
        <svg
          viewBox="0 0 24 24"
          className="absolute -bottom-2.5 right-10 h-5 w-5 text-slate-700 drop-shadow"
          fill="currentColor"
        >
          <path d="M5 3l14 8-6.5 1.5L9 19z" />
        </svg>
      </div>
    </div>
  );
}

/* ----------------------------- Page ----------------------------- */

export default function LandingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user !== null) {
      router.replace("/opportunities");
    }
  }, [loading, user, router]);

  // While the session check runs (or while redirecting a logged-in user),
  // show a quiet skeleton instead of flashing the landing page.
  if (loading || user !== null) {
    return (
      <div className="mx-auto max-w-3xl space-y-3 py-10">
        <div className="h-8 w-72 animate-pulse rounded bg-slate-200" />
        <div className="h-4 w-96 max-w-full animate-pulse rounded bg-slate-100" />
        <div className="mt-6 h-40 animate-pulse rounded-xl bg-slate-100" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-16 overflow-x-clip pb-10">
      {/* Hero — full-bleed soft blue band; copy left, product mockup right */}
      <section className="relative left-1/2 -mx-[50vw] -mt-8 w-screen border-b border-blue-100 bg-blue-50/70">
        <div className="mx-auto grid max-w-5xl items-center gap-10 px-6 py-12 sm:py-16 lg:grid-cols-[1fr_minmax(0,26rem)]">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-block rounded-full border border-blue-200 bg-white px-3 py-1 text-xs font-semibold text-blue-700">
                Ücretsiz erken beta
              </span>
              <span className="text-xs font-semibold uppercase tracking-wide text-blue-600">
                Türkiye → Remote/EU outreach copilotu
              </span>
            </div>
            <h1 className="mt-4 text-3xl font-bold leading-tight tracking-tight text-slate-900 sm:text-5xl">
              Türkiye’den global iş aramayı daha düzenli hale getir
            </h1>
            <p className="mt-4 max-w-xl text-slate-600">
              NetworkAI; Türkiye, remote ve Avrupa’daki gerçekçi rolleri
              bulmana, dürüst outreach mesajları hazırlamana ve başvurularını
              tek yerde takip etmene yardımcı olur.
            </p>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <PrimaryCta>Ücretsiz başla</PrimaryCta>
              <SecondaryCta>Giriş yap</SecondaryCta>
              <Link
                href="/opportunities"
                className="text-sm font-medium text-blue-600 hover:underline"
              >
                Fırsatları gör →
              </Link>
            </div>
            <p className="mt-4 text-xs text-slate-500">
              Otomatik başvuru yok. Spam yok. Mesajları sen inceler, sen
              gönderirsin.
            </p>
          </div>
          <ProductMockup />
        </div>
      </section>

      {/* Social proof (honest — no fake numbers) */}
      <p className="border-y border-slate-200 py-4 text-center text-sm text-slate-500">
        Junior mühendisler için erken beta — gerçek kullanıcı geri bildirimiyle
        geliştiriliyor.
      </p>

      {/* Value cards */}
      <section id="ozellikler" className="scroll-mt-20">
        <h2 className="text-center text-2xl font-bold tracking-tight text-slate-900">
          Dağınık iş aramayı tek bir akışa çevir
        </h2>
        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {VALUE_CARDS.map((c) => (
            <Card key={c.title} hover className="p-4">
              <ValueIcon name={c.icon} />
              <h3 className="mt-3 font-semibold text-slate-900">{c.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-600">
                {c.body}
              </p>
            </Card>
          ))}
        </div>
      </section>

      {/* How it works — horizontal stepper on desktop, stacked on mobile */}
      <section id="nasil-calisir" className="scroll-mt-20">
        <h2 className="text-center text-2xl font-bold tracking-tight text-slate-900">
          5 dakikada ilk mesajını hazırla
        </h2>
        <div className="mt-6 flex flex-col gap-3 md:flex-row md:items-stretch md:gap-0">
          {STEPS.map((s, i) => (
            <div key={s.n} className="flex flex-1 items-center md:min-w-0">
              <Card className="flex-1 p-4 md:min-w-0">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white">
                  {s.n}
                </span>
                <h3 className="mt-2.5 text-sm font-semibold text-slate-900">
                  {s.title}
                </h3>
                <p className="mt-1 text-xs text-slate-500">{s.body}</p>
              </Card>
              {i < STEPS.length - 1 && (
                <span
                  aria-hidden
                  className="hidden shrink-0 px-2 text-lg text-slate-300 md:block"
                >
                  →
                </span>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Trust */}
      <section id="guven" className="scroll-mt-20">
        <div className="rounded-2xl border border-blue-100 bg-blue-50/50 p-6 sm:p-8">
          <h2 className="text-xl font-bold tracking-tight text-slate-900">
            Copilot, autopilot değil
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            NetworkAI sana öneri verir; son karar ve gönderim her zaman sende.
          </p>
          <ul className="mt-4 grid gap-x-6 gap-y-2 sm:grid-cols-2">
            {TRUST_BULLETS.map((b) => (
              <li
                key={b}
                className="flex items-start gap-2 text-sm text-slate-700"
              >
                <span
                  aria-hidden
                  className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-blue-600 text-[10px] font-bold text-white"
                >
                  ✓
                </span>
                {b}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Final CTA */}
      <section className="rounded-2xl border border-slate-200 bg-slate-50 px-6 py-10 text-center">
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">
          İlk outreach taslağını bugün hazırla
        </h2>
        <p className="mx-auto mt-2 max-w-xl text-sm text-slate-600">
          CV’ni ekle, gerçekçi rolleri gör ve ilk mesajını birkaç dakika içinde
          oluştur.
        </p>
        <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
          <PrimaryCta>Ücretsiz başla</PrimaryCta>
          <Link
            href="/login"
            className="text-sm font-medium text-slate-600 hover:text-slate-900 hover:underline"
          >
            Giriş yap
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200 pt-6 text-center text-xs text-slate-500">
        NetworkAI — Türkiye’den global iş aramaya daha düzenli bir yol.
      </footer>
    </div>
  );
}
