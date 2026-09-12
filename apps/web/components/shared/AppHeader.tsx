"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { MerchantPolicyDrawer } from "@/components/shared/MerchantPolicyDrawer";

const NAV_ITEMS = [
  { href: "/", label: "LIVE" },
  { href: "/arena", label: "ARENA" },
  { href: "/learn", label: "LEARN" },
] as const;

function HeaderInner() {
  const pathname = usePathname();
  const router = useRouter();
  const params = useSearchParams();
  const [rulesOpen, setRulesOpen] = useState(false);
  const presentation = params.get("presentation") === "1";

  function togglePresentation() {
    const next = new URLSearchParams(params.toString());
    if (presentation) next.delete("presentation");
    else next.set("presentation", "1");
    const query = next.toString();
    router.replace(query ? `${pathname}?${query}` : pathname);
  }

  return (
    <>
      <header className="sticky top-0 z-30 border-b border-line bg-surface/95 backdrop-blur-sm">
        <div className="mx-auto flex h-14 w-full max-w-[1480px] items-center justify-between px-6">
          <Link href="/" className="text-sm font-semibold tracking-[0.1em]">
            ASTRAOS
          </Link>
          <nav className="flex items-center gap-5" aria-label="Primary">
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
                  className={`text-xs font-medium tracking-[0.08em] ${
                    isActive ? "text-ink" : "text-muted hover:text-ink"
                  }`}
                >
                  {item.label}
                  {isActive ? (
                    <span className="mt-1 block h-px bg-ink" />
                  ) : (
                    <span className="mt-1 block h-px bg-transparent" />
                  )}
                </Link>
              );
            })}
          </nav>
          <div className="flex items-center gap-4">
            <button type="button" className="btn-quiet" onClick={togglePresentation}>
              {presentation ? "Exit presentation" : "Presentation"}
            </button>
            <Link
              href="/catalogue"
              className={`text-xs tracking-[0.04em] ${
                pathname.startsWith("/catalogue")
                  ? "text-ink"
                  : "text-muted hover:text-ink"
              }`}
            >
              Merchant Data
            </Link>
            <button
              type="button"
              onClick={() => setRulesOpen(true)}
              className="btn-quiet"
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

export function AppHeader() {
  return (
    <Suspense fallback={<header className="h-14 border-b border-line bg-surface" />}>
      <HeaderInner />
    </Suspense>
  );
}
