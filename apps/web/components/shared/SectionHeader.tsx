import { AstraSectionHeader } from "@/components/astra";

export function SectionHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
}) {
  return (
    <AstraSectionHeader eyebrow={eyebrow} title={title} description={description} />
  );
}
