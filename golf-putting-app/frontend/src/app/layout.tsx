import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GreenReader — Putting Gradient Analyser",
  description: "AI-powered putting green slope detection for golfers",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
