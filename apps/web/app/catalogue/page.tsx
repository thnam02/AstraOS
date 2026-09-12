import { CatalogueExplorer } from "@/components/catalogue/CatalogueExplorer";
import { PageContainer } from "@/components/shared/PageContainer";
import { SectionHeader } from "@/components/shared/SectionHeader";

export default function CataloguePage() {
  return (
    <PageContainer wide>
      <div className="space-y-6">
        <SectionHeader
          eyebrow="Merchant data"
          title="Catalogue"
          description="Inspect the seeded Astra Electronics headphone catalogue. No offers are generated here."
        />
        <CatalogueExplorer />
      </div>
    </PageContainer>
  );
}
