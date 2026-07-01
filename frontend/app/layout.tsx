import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";
import AuthProvider, { RouteGuard } from "@/components/AuthProvider";
import MomentumProvider from "@/components/MomentumProvider";

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
          <MomentumProvider>
            <Nav />
            <main className="mx-auto max-w-5xl px-6 py-8">
              <RouteGuard>{children}</RouteGuard>
            </main>
          </MomentumProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
