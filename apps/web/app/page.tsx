import { Suspense } from "react";

import { LiveWorkbench } from "@/components/live/LiveWorkbench";
import { PageContainer } from "@/components/shared/PageContainer";

export default function LivePage() {
  return (
    <PageContainer wide>
      <Suspense fallback={<p className="text-sm text-muted">Loading LIVE…</p>}>
        <LiveWorkbench />
      </Suspense>
    </PageContainer>
  );
}
