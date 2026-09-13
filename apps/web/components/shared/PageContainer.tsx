import type { ReactNode } from "react";

export function PageContainer({
  children,
  wide = false,
}: {
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <main className={wide ? "page-shell py-6" : "mx-auto w-full max-w-5xl px-6 py-6"}>
      {children}
    </main>
  );
}
