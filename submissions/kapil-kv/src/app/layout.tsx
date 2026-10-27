import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SLA Tracker — IT Service Desk",
  description: "IT Service-Desk SLA Tracking Application",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}