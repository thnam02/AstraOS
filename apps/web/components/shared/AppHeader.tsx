"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { MerchantPolicyDrawer } from "@/components/shared/MerchantPolicyDrawer";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

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
      <header className="sticky top-0 z-30 border-b border-line bg-surface">
        <div className="mx-auto flex h-14 w-full max-w-[1480px] items-center gap-6 px-6">
          <Link
            href="/"
            className="text-sm font-semibold tracking-[0.12em] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
          >
            ASTRAOS
          </Link>
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
                  className={cn(
                    "px-2.5 py-1 text-xs font-semibold tracking-[0.08em] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
                    isActive
                      ? "bg-ink text-surface"
                      : "text-muted hover:text-ink",
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <Separator orientation="vertical" className="hidden h-4 bg-line sm:block" />
            <Link
              href="/catalogue"
              aria-label="Merchant Data"
              className={cn(
                "text-[11px] tracking-[0.04em] text-muted hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
                pathname.startsWith("/catalogue") && "text-ink",
              )}
            >
              Data
            </Link>
            <button
              type="button"
              onClick={() => setRulesOpen(true)}
              aria-label="Merchant Rules"
              className="cursor-pointer text-[11px] tracking-[0.04em] text-muted hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
            >
              Rules
            </button>
          </div>
        </div>
      </header>
      <MerchantPolicyDrawer open={rulesOpen} onClose={() => setRulesOpen(false)} />
    </>
  );
}
