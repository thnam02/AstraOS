export const HERO_INTENT = `I'm flying from Sydney to Singapore tomorrow and need wireless noise-cancelling headphones under A$350. I need them delivered today. I'll wear them for hours, so comfort and reliability matter more than getting the absolute cheapest option.`;

export function fieldLabel(field: string): string {
  const labels: Record<string, string> = {
    anc: "ANC",
    price: "Price",
    delivery_days: "Delivery",
    same_day_delivery: "Same-day delivery",
    battery_hours: "Battery",
    weight_g: "Weight",
    foldable: "Foldable",
    wireless: "Wireless",
    microphone: "Microphone",
    in_stock: "In stock",
    category: "Category",
    brand: "Brand",
    unsupported: "Unsupported",
    comfort: "Comfort",
    reliability: "Reliability",
    travel: "Travel suitability",
    battery: "Battery",
    weight: "Weight",
    delivery: "Delivery",
    warranty: "Warranty",
  };
  return labels[field] ?? field.replace(/_/g, " ");
}

export function contextLabel(tag: string): string {
  return tag.replace(/_/g, " ");
}
