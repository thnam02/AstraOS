import { ArenaWorkbench } from "@/components/arena/ArenaWorkbench";
import { PageContainer } from "@/components/shared/PageContainer";
import { SectionHeader } from "@/components/shared/SectionHeader";

export default function ArenaPage() {
  return (
    <PageContainer wide>
      <SectionHeader
        eyebrow="Evaluate"
        title="Strategy evaluation"
        description="Compare AstraOS with simpler merchant decision strategies under controlled conditions. Same buyer, catalogue, inventory, and merchant policy — only the strategy changes."
      />
      <div className="mt-6">
        <ArenaWorkbench />
      </div>
    </PageContainer>
  );
}
