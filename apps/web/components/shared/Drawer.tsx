import type { ReactNode } from "react";

import { AstraInspector } from "@/components/astra";

export function Drawer({
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
    <AstraInspector open={open} title={title} onClose={onClose} wide={wide}>
      {children}
    </AstraInspector>
  );
}
