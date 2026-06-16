import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";
import MomentumProvider from "@/components/MomentumProvider";

export const metadata: Metadata = {
  title: "Network AI",
  description: "AI networking copilot for new-grad job search",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <MomentumProvider>
          <Nav />
          <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
        </MomentumProvider>
      </body>
    </html>
  );
}
