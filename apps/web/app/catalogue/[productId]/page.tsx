import { ProductInspector } from "@/components/catalogue/ProductInspector";
import { PageContainer } from "@/components/shared/PageContainer";

export default async function CatalogueProductPage({
  params,
}: {
  params: Promise<{ productId: string }>;
}) {
  const { productId } = await params;
  return (
    <PageContainer wide>
      <ProductInspector productId={productId} />
    </PageContainer>
  );
}
