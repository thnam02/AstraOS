import { ArenaWorkbench } from "@/components/arena/ArenaWorkbench";
import { PageContainer } from "@/components/shared/PageContainer";
import { SectionHeader } from "@/components/shared/SectionHeader";

export default function ArenaPage() {
  return (
    <PageContainer wide>
      <SectionHeader
        eyebrow="Arena"
        title="Merchant strategy comparison"
        description="Same buyer, catalogue, inventory, and merchant policy. Only the merchant strategy changes."
      />
      <div className="mt-6">
        <ArenaWorkbench />
      </div>
    </PageContainer>
  );
}
