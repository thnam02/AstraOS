export function formatAudCents(cents: number): string {
  return new Intl.NumberFormat("en-AU", {
    style: "currency",
    currency: "AUD",
  }).format(cents / 100);
}

export function formatRate(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}
