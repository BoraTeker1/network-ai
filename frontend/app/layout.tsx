import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";
import AuthProvider, { RouteGuard } from "@/components/AuthProvider";

export const metadata: Metadata = {
  title: "Network AI",
  description:
    "Referral & outreach copilot for Turkish engineers targeting Türkiye, remote, and EU roles",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <Nav />
          <main className="mx-auto max-w-5xl px-6 py-8">
            <RouteGuard>{children}</RouteGuard>
          </main>
          {/* Lightweight founder-contact line on every page — beta users need a
              zero-friction way to report issues. mailto only; no support system. */}
          <footer className="mx-auto max-w-5xl px-6 pb-8 text-center text-xs text-slate-400">
            Beta — found a bug or have feedback?{" "}
            <a
              href="mailto:tekerbora@gmail.com?subject=Network%20AI%20feedback"
              className="font-medium text-blue-600 hover:underline"
            >
              Email the founder
            </a>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
