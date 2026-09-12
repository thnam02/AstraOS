import { Suspense } from "react";

import { LearnWorkbench } from "@/components/learn/LearnWorkbench";
import { PageContainer } from "@/components/shared/PageContainer";

export default function LearnPage() {
  return (
    <PageContainer wide>
      <Suspense fallback={<p className="text-sm text-muted">Loading LEARN…</p>}>
        <LearnWorkbench />
      </Suspense>
    </PageContainer>
  );
}
