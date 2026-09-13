export function formatAudCents(cents: number): string {
  const amount = (cents / 100).toLocaleString("en-AU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `A$${amount}`;
}

export function formatRate(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}

export function centsToPlainDollars(cents: number): string {
  return (cents / 100).toLocaleString("en-AU", {
    maximumFractionDigits: cents % 100 === 0 ? 0 : 2,
    useGrouping: false,
  });
}
