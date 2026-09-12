"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { MerchantPolicyDrawer } from "@/components/shared/MerchantPolicyDrawer";

const NAV_ITEMS = [
  { href: "/", label: "LIVE" },
  { href: "/catalogue", label: "CATALOGUE" },
  { href: "/arena", label: "ARENA" },
  { href: "/learn", label: "LEARN" },
] as const;

export function AppHeader() {
  const pathname = usePathname();
  const [rulesOpen, setRulesOpen] = useState(false);

  return (
    <>
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex h-14 w-full max-w-7xl items-center justify-between px-6">
          <Link
            href="/"
            className="text-sm font-semibold tracking-[0.18em] text-ink"
          >
            ASTRAOS
          </Link>
          <div className="flex items-center gap-6">
            <nav className="flex items-center gap-5">
              {NAV_ITEMS.map((item) => {
                const isActive =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href);

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`text-xs font-medium tracking-[0.14em] ${
                      isActive ? "text-ink" : "text-muted hover:text-ink"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
            <button
              type="button"
              onClick={() => setRulesOpen(true)}
              className="text-xs font-medium tracking-[0.14em] text-muted hover:text-ink"
            >
              RULES
            </button>
          </div>
        </div>
      </header>
      <MerchantPolicyDrawer open={rulesOpen} onClose={() => setRulesOpen(false)} />
    </>
  );
}
