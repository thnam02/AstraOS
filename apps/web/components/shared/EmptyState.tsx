export function EmptyState({
  title,
  body,
}: {
  title: string;
  body: string;
}) {
  return (
    <div className="border border-dashed border-line px-4 py-6">
      <p className="text-sm font-medium">{title}</p>
      <p className="mt-1 text-sm text-muted">{body}</p>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <p className="border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger">
      {message}
    </p>
  );
}
