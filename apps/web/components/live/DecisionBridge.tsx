import { MetricHint } from "@/components/live/MetricHint";
import { StageSection, StageTabs } from "@/components/live/StageShell";
import {
  METRIC_HELP,
  baselineTermsForProduct,
  commercialDeltas,
  constructStory,
  matchScoreDisplay,
  productsDiffer,
  sameProductOfferSummary,
  termsFromScored,
  winnerChangeSummary,
} from "@/lib/decisionNarrative";
import { formatUtilityShort } from "@/lib/format";
import { formatAudCents } from "@/lib/money";
import type {
  GenerateOffersResponse,
  OptimisationResponse,
  PublicScoredOffer,
  RankedProductMatch,
} from "@/types";

export function DecisionBridge({
  topMatch,
  optimisation,
  offer,
  construction,
}: {
  topMatch: RankedProductMatch | null;
  optimisation: OptimisationResponse | null;
  offer: PublicScoredOffer | null;
  construction?: GenerateOffersResponse | null;
}) {
  if (!topMatch || !offer) return null;
  const differ = productsDiffer(topMatch, offer);
  const productScore = matchScoreDisplay(topMatch.overall_semantic_fit);
  const selectedMatch = matchScoreDisplay(offer.product_fit);
  const story = construction ? constructStory(construction) : null;
  const generated =
    story?.generated ?? optimisation?.summary.offers_considered ?? null;
  const baseline = baselineTermsForProduct(
    topMatch,
    optimisation,
    construction,
  );
  const deltas = commercialDeltas(baseline, termsFromScored(offer));

  return (
    <StageTabs
      label="Decision reasoning"
      equalHeight
      items={[
        {
          label: "Decision path",
          content: (
            <StageSection title="How AstraOS got here">
              <ol className="grid gap-3 grid-cols-2 [&>li]:border-b [&>li]:border-line-muted [&>li]:pb-3 [&>li:last-child]:col-span-2">
                <li>
                  <p className="type-small text-muted">1 · Product</p>
                  <p className="mt-1 font-semibold">{topMatch.product_name}</p>
                  <p className="mt-1 font-mono text-sm tabular-nums">
                    {productScore.value} {productScore.suffix}
                  </p>
                  <p className="mt-1 text-xs text-muted">Product match</p>
                </li>
                <li>
                  <p className="type-small text-muted">2 · Offer</p>
                  {story ? (
                    <>
                      <p className="mt-1 font-mono text-xl font-semibold tabular-nums">
                        {generated?.toLocaleString()}
                      </p>
                      <p className="mt-1 text-xs text-muted">
                        {story.products} products × {story.price} price ×{" "}
                        {story.delivery} delivery × {story.warranty} warranty ×{" "}
                        {story.bundle} bundle × {story.returns} returns
                      </p>
                    </>
                  ) : generated != null ? (
                    <>
                      <p className="mt-1 font-mono text-xl font-semibold tabular-nums">
                        {generated.toLocaleString()}
                      </p>
                      <p className="mt-1 text-xs text-muted">
                        Offers considered
                      </p>
                    </>
                  ) : (
                    <p className="mt-1 text-sm text-muted">
                      Matched products expanded into commercial configurations.
                    </p>
                  )}
                </li>
                <li>
                  <p className="type-small text-muted">3 · Safe</p>
                  {optimisation ? (
                    <p className="mt-1 font-mono text-xl font-semibold tabular-nums">
                      {optimisation.summary.policy_safe.toLocaleString()}
                    </p>
                  ) : (
                    <p className="mt-1 text-sm text-muted">—</p>
                  )}
                  <p className="mt-1 text-xs text-muted">Policy-safe offers</p>
                </li>
                <li>
                  <p className="type-small text-muted">4 · Pareto</p>
                  {optimisation ? (
                    <p className="mt-1 font-mono text-xl font-semibold tabular-nums">
                      {optimisation.summary.pareto_efficient}
                    </p>
                  ) : (
                    <p className="mt-1 text-sm text-muted">—</p>
                  )}
                  <p className="mt-1 text-xs text-muted">
                    <MetricHint
                      label="Pareto-efficient"
                      hint={METRIC_HELP.pareto}
                    />
                  </p>
                </li>
                <li>
                  <p className="type-small text-muted">5 · Selected</p>
                  <p className="mt-1 font-semibold">{offer.product_name}</p>
                  <p className="mt-1 font-mono text-sm tabular-nums">
                    {formatUtilityShort(offer.buyer_utility)}
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    <MetricHint
                      label="Simulated buyer utility"
                      hint={METRIC_HELP.buyerUtility}
                    />
                  </p>
                  <p className="mt-2 font-mono text-sm tabular-nums">
                    {formatAudCents(offer.contribution_margin_cents)}
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    <MetricHint
                      label="Merchant contribution"
                      hint={METRIC_HELP.contribution}
                    />
                  </p>
                </li>
              </ol>
              <p className="mt-3 text-sm">
                <span className="font-semibold">Best product ≠ best offer</span>
                <span className="mx-2 text-muted">·</span>
                <span className="text-muted">
                  AstraOS optimises the complete merchant response, not the SKU
                  alone.
                </span>
              </p>
            </StageSection>
          ),
        },
        {
          label: differ ? "Winner changed" : "Counterfactual",
          content: differ ? (
            <StageSection title="Why the winner changed">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="type-small text-muted">Best product match</p>
                  <p className="mt-1 font-semibold">{topMatch.product_name}</p>
                  <p className="mt-3 type-small text-muted">
                    <MetricHint
                      label="Product match"
                      hint={METRIC_HELP.productMatch}
                    />
                  </p>
                  <p className="mt-1 font-mono text-lg tabular-nums">
                    {productScore.value} {productScore.suffix}
                  </p>
                </div>
                <div>
                  <p className="type-small text-muted">Best complete offer</p>
                  <p className="mt-1 font-semibold">{offer.product_name}</p>
                  <p className="mt-3 type-small text-muted">
                    <MetricHint
                      label="Product match"
                      hint={METRIC_HELP.productMatch}
                    />
                  </p>
                  <p className="mt-1 font-mono text-lg tabular-nums">
                    {selectedMatch.value} {selectedMatch.suffix}
                  </p>
                </div>
              </div>
              <dl className="mt-3 grid gap-3 sm:grid-cols-2 border-t border-line-muted pt-3 text-sm">
                <div className="space-y-1">
                  <dt className="text-muted">
                    <MetricHint
                      label="Simulated buyer utility"
                      hint={METRIC_HELP.buyerUtility}
                    />
                  </dt>
                  <dd className="font-mono tabular-nums">
                    {formatUtilityShort(offer.buyer_utility)}
                  </dd>
                </div>
                <div className="space-y-1">
                  <dt className="text-muted">
                    <MetricHint
                      label="Merchant contribution"
                      hint={METRIC_HELP.contribution}
                    />
                  </dt>
                  <dd className="font-mono tabular-nums">
                    {formatAudCents(offer.contribution_margin_cents)}
                  </dd>
                </div>
              </dl>
              {deltas.length ? (
                <dl className="mt-3 space-y-2 border-t border-line-muted pt-3 text-sm">
                  <p className="type-small text-muted">
                    Product / commercial differences
                  </p>
                  {deltas.map((row) => (
                    <div key={row.field} className="flex justify-between gap-4">
                      <dt className="text-muted">{row.field}</dt>
                      <dd>
                        {row.from}
                        <span className="mx-2 text-muted">→</span>
                        {row.to}
                      </dd>
                    </div>
                  ))}
                </dl>
              ) : null}
              <p className="mt-3 text-sm leading-5">
                {winnerChangeSummary(
                  topMatch.product_name,
                  offer.product_name,
                  deltas,
                )}
              </p>
            </StageSection>
          ) : (
            <StageSection title="Counterfactual">
              {deltas.length ? (
                <dl className="max-w-xl space-y-2 text-sm">
                  {deltas.map((row) => (
                    <div key={row.field} className="flex justify-between gap-4">
                      <dt className="text-muted">{row.field}</dt>
                      <dd>
                        {row.from}
                        <span className="mx-2 text-muted">→</span>
                        {row.to}
                      </dd>
                    </div>
                  ))}
                </dl>
              ) : null}
              <p className="mt-3 text-sm leading-5">
                {sameProductOfferSummary(offer.product_name, deltas)}
              </p>
            </StageSection>
          ),
        },
      ]}
    />
  );
}
