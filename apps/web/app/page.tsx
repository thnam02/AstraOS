import { ApiStatus } from "@/components/live/ApiStatus";
import { PageContainer } from "@/components/shared/PageContainer";

export default function LivePage() {
  return (
    <PageContainer>
      <section className="max-w-xl space-y-8">
        <div className="space-y-3">
          <h1 className="text-3xl font-semibold tracking-tight text-ink">
            AstraOS
          </h1>
          <p className="text-sm leading-6 text-muted">
            Merchant-side offer intelligence for AI commerce.
          </p>
        </div>
        <p className="text-sm font-medium tracking-tight text-ink">
          Product ≠ Offer
        </p>
        <ApiStatus />
      </section>
    </PageContainer>
  );
}
