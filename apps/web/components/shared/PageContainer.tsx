import type { ReactNode } from "react";

export function PageContainer({
  children,
  wide = false,
}: {
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <main
      className={`mx-auto w-full px-6 py-8 ${wide ? "max-w-7xl" : "max-w-5xl"}`}
    >
      {children}
    </main>
  );
}
