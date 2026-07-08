import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import AuthProvider, { RouteGuard } from "@/components/AuthProvider";
import { LanguageProvider } from "@/lib/i18n";

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
    <html lang="tr">
      <body>
        <LanguageProvider>
          <AuthProvider>
            <Nav />
            <main className="mx-auto max-w-5xl px-6 py-8">
              <RouteGuard>{children}</RouteGuard>
            </main>
            <Footer />
          </AuthProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
