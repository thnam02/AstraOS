import { CatalogueExplorer } from "@/components/catalogue/CatalogueExplorer";
import { PageContainer } from "@/components/shared/PageContainer";
import { SectionHeader } from "@/components/shared/SectionHeader";

export default function CataloguePage() {
  return (
    <PageContainer wide>
      <div className="space-y-6">
        <SectionHeader
          eyebrow="Data"
          title="What AstraOS knows"
          description="Merchant truth AstraOS can ground decisions on: products, prices, inventory, fulfilment, evidence, and commercial options."
        />
        <CatalogueExplorer />
      </div>
    </PageContainer>
  );
}
