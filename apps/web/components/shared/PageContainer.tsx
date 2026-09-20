import type { ReactNode } from "react";

export function PageContainer({
  children,
  wide = false,
}: {
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <main className={wide ? "page-shell py-5 md:py-6" : "mx-auto w-full max-w-5xl px-4 py-4 md:px-6"}>
      {children}
    </main>
  );
}
