import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgenticP1 — AI Calling Agent Platform",
  description: "Enterprise-grade AI Voice Calling Agent SaaS for businesses",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
