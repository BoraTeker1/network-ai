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
        </AuthProvider>
      </body>
    </html>
  );
}
