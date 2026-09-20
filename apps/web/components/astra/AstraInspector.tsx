"use client";

import type { ReactNode } from "react";

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

export function AstraInspector({
  open,
  title,
  onClose,
  children,
  wide = false,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <Sheet open={open} onOpenChange={(next) => !next && onClose()}>
      <SheetContent
        side="right"
        className={`flex h-dvh w-full flex-col gap-0 overflow-hidden border-l border-line bg-surface p-0 ${wide ? "max-w-6xl sm:max-w-6xl" : "max-w-lg sm:max-w-lg"}`}
      >
        <SheetHeader className="shrink-0 border-b border-line px-5 py-4 text-left">
          <SheetTitle className="text-sm font-semibold">{title}</SheetTitle>
        </SheetHeader>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          {children}
        </div>
      </SheetContent>
    </Sheet>
  );
}
