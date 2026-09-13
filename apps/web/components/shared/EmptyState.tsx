import { AstraEmptyState, AstraErrorState } from "@/components/astra";

export function EmptyState({
  title,
  body,
}: {
  title: string;
  body: string;
}) {
  return <AstraEmptyState title={title} body={body} />;
}

export function ErrorState({ message }: { message: string }) {
  return <AstraErrorState message={message} />;
}
