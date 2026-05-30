import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BAOS AI â€” Maritime Decision Intelligence",
  description:
    "AI-powered berth allocation optimization system for maritime ports. Optimize vessel assignments, reduce turnaround times, and maximize port revenue.",
  keywords: "berth optimization, maritime, port management, AI, vessel allocation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col antialiased">
        {children}
      </body>
    </html>
  );
}
