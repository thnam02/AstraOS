import type { ReactNode } from "react";

import { AstraInspector } from "@/components/astra";

export function Drawer({
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
    <AstraInspector open={open} title={title} onClose={onClose}>
      {children}
    </AstraInspector>
  );
}
