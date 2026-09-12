import { LearnWorkbench } from "@/components/learn/LearnWorkbench";
import { PageContainer } from "@/components/shared/PageContainer";
import { SectionHeader } from "@/components/shared/SectionHeader";

export default function LearnPage() {
  return (
    <PageContainer wide>
      <SectionHeader
        eyebrow="Learn"
        title="Intent → Offer → Outcome"
        description="A learning architecture for future observed B2A outcomes. Current models are trained only on synthetic Arena selections."
      />
      <div className="mt-6">
        <LearnWorkbench />
      </div>
    </PageContainer>
  );
}
