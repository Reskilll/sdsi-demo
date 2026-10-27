import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SLA Tracker — IT Service Desk",
  description: "IT Service-Desk SLA Tracking Application",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}