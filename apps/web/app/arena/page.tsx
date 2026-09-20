import { ArenaWorkbench } from "@/components/arena/ArenaWorkbench";
import { PageContainer } from "@/components/shared/PageContainer";
import { SectionHeader } from "@/components/shared/SectionHeader";

export default function ArenaPage() {
  return (
    <PageContainer wide>
      <SectionHeader
        eyebrow="Evaluate"
        title="Strategy evaluation"
        description="Compare AstraOS with simpler merchant decision strategies under identical commercial conditions."
      />
      <div className="mt-3">
        <ArenaWorkbench />
      </div>
    </PageContainer>
  );
}
