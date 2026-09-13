import {
  processRailState,
  type LiveStage,
} from "@/components/live/ProcessRail";

export function stageReachable(
  id: LiveStage,
  flags: Parameters<typeof processRailState>[1],
  active: LiveStage,
): boolean {
  const state = processRailState(id, flags, active);
  if (state !== "future") return true;
  if (id === "transact" && flags.hasNego) return true;
  if (id === "learn" && (flags.hasNego || flags.hasTxn)) return true;
  return false;
}

export const STAGE_META: Record<
  LiveStage,
  {
    number: string;
    title: string;
    subtitle: string;
    heading: string;
    description: string;
    continueLabel?: string;
  }
> = {
  understand: {
    number: "01",
    title: "Understand",
    subtitle: "Intent",
    heading: "Buyer interpretation",
    description:
      "Interpret the buyer request into structured requirements, preferences and trade-offs.",
    continueLabel: "Continue to qualification",
  },
  qualify: {
    number: "02",
    title: "Qualify",
    subtitle: "Eligibility",
    heading: "Qualification",
    description:
      "Remove variants that do not satisfy the buyer’s hard constraints.",
    continueLabel: "Continue to product matching",
  },
  match: {
    number: "03",
    title: "Match",
    subtitle: "Products",
    heading: "Product matching",
    description:
      "Rank eligible products against the buyer’s requirements and preferences.",
    continueLabel: "Continue to offer construction",
  },
  construct: {
    number: "04",
    title: "Construct",
    subtitle: "Offer space",
    heading: "Offer construction",
    description:
      "Expand matched products into commercial configurations. No winner is chosen here.",
    continueLabel: "Continue to optimisation",
  },
  optimise: {
    number: "05",
    title: "Optimise",
    subtitle: "Decision",
    heading: "Commercial decision",
    description:
      "Select the strongest complete commercial response from policy-safe, efficient offers.",
    continueLabel: "Continue to negotiation",
  },
  negotiate: {
    number: "06",
    title: "Negotiate",
    subtitle: "Terms",
    heading: "Negotiation",
    description:
      "Exchange terms with the buyer agent. Language is interpreted; commercial control stays deterministic.",
  },
  transact: {
    number: "07",
    title: "Transact",
    subtitle: "Order",
    heading: "Transaction",
    description:
      "Accept a proposal to revalidate, reserve inventory and write the order. AstraOS does not take payment.",
  },
  learn: {
    number: "08",
    title: "Learn",
    subtitle: "Outcome",
    heading: "Outcome",
    description:
      "Close the decision lifecycle with the outcome this run actually produced.",
  },
};
