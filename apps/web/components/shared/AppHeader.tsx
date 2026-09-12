"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { MerchantPolicyDrawer } from "@/components/shared/MerchantPolicyDrawer";

const NAV_ITEMS = [
  { href: "/", label: "LIVE" },
  { href: "/arena", label: "ARENA" },
  { href: "/learn", label: "LEARN" },
] as const;

export function AppHeader() {
  const pathname = usePathname();
  const [rulesOpen, setRulesOpen] = useState(false);

  return (
    <>
      <header className="sticky top-0 z-30 border-b border-line bg-surface/95 backdrop-blur-sm">
        <div className="mx-auto flex h-14 w-full max-w-7xl items-center justify-between px-6">
          <Link
            href="/"
            className="text-sm font-semibold tracking-[0.08em] text-ink"
          >
            ASTRAOS
          </Link>
          <div className="flex items-center gap-2">
            <nav className="flex items-center gap-1" aria-label="Primary">
              {NAV_ITEMS.map((item) => {
                const isActive =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href);

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={isActive ? "page" : undefined}
                    className={`rounded-[6px] px-3 py-1.5 text-xs font-medium tracking-[0.06em] transition-colors ${
                      isActive
                        ? "bg-ink text-surface"
                        : "text-muted hover:bg-canvas hover:text-ink"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
            <Link
              href="/catalogue"
              className={`rounded-[6px] px-3 py-1.5 text-xs font-medium tracking-[0.06em] ${
                pathname.startsWith("/catalogue")
                  ? "bg-canvas text-ink"
                  : "text-muted hover:text-ink"
              }`}
            >
              Merchant Data
            </Link>
            <button
              type="button"
              onClick={() => setRulesOpen(true)}
              className="btn-ghost"
            >
              Merchant Rules
            </button>
          </div>
        </div>
      </header>
      <MerchantPolicyDrawer open={rulesOpen} onClose={() => setRulesOpen(false)} />
    </>
  );
}
