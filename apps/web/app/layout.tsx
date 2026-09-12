import type { Metadata } from "next";
import { Geist } from "next/font/google";

import { AppHeader } from "@/components/shared/AppHeader";

import "./globals.css";

const geist = Geist({
  subsets: ["latin"],
  variable: "--font-geist",
});

export const metadata: Metadata = {
  title: "AstraOS",
  description: "Merchant-side offer intelligence for AI commerce.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geist.variable} min-h-screen bg-canvas font-sans text-ink antialiased`}
      >
        <AppHeader />
        {children}
      </body>
    </html>
  );
}
