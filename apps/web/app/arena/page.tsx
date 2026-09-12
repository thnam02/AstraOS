import { ArenaWorkbench } from "@/components/arena/ArenaWorkbench";
import { PageContainer } from "@/components/shared/PageContainer";
import { SectionHeader } from "@/components/shared/SectionHeader";

export default function ArenaPage() {
  return (
    <PageContainer wide>
      <SectionHeader
        eyebrow="Arena"
        title="Agent Arena"
        description="Synthetic comparison of merchant strategies against the same catalogue, policy, and transparent simulated buyer. Not a conversion study."
      />
      <div className="mt-6">
        <ArenaWorkbench />
      </div>
    </PageContainer>
  );
}
