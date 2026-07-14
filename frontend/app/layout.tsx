import type { Metadata } from "next";
import "./globals.css";
import AppShell from "@/components/AppShell";
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
            <AppShell>
              <RouteGuard>{children}</RouteGuard>
            </AppShell>
          </AuthProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
