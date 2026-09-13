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
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <Sheet open={open} onOpenChange={(next) => !next && onClose()}>
      <SheetContent
        side="right"
        className="w-full max-w-lg border-l border-line bg-surface p-0 sm:max-w-lg"
      >
        <SheetHeader className="border-b border-line px-5 py-4 text-left">
          <SheetTitle className="text-sm font-semibold">{title}</SheetTitle>
        </SheetHeader>
        <div className="overflow-y-auto px-5 py-4">{children}</div>
      </SheetContent>
    </Sheet>
  );
}
