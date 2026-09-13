import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";

import { AppHeader } from "@/components/shared/AppHeader";
import { TooltipProvider } from "@/components/ui/tooltip";

import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans-loaded",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono-loaded",
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
        className={`${inter.className} ${jetbrains.variable} min-h-screen bg-canvas text-ink antialiased`}
      >
        <TooltipProvider>
          <AppHeader />
          {children}
        </TooltipProvider>
      </body>
    </html>
  );
}
