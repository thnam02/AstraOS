import { MetricHint } from "@/components/live/MetricHint";
import { StageSection } from "@/components/live/StageShell";
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
  const baseline = baselineTermsForProduct(topMatch, optimisation, construction);
  const deltas = commercialDeltas(baseline, termsFromScored(offer));

  return (
    <>
      <StageSection title="How did AstraOS get here?">
        <ol className="grid gap-5 lg:grid-cols-4">
          <li>
            <p className="type-small text-muted">1 · Best product match</p>
            <p className="mt-1 font-semibold">{topMatch.product_name}</p>
            <p className="mt-1 font-mono text-sm tabular-nums">
              {productScore.value} {productScore.suffix}
            </p>
            <p className="mt-1 text-xs text-muted">Product match</p>
          </li>
          <li>
            <p className="type-small text-muted">2 · Build complete offers</p>
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
                <p className="mt-1 text-xs text-muted">Offers considered</p>
              </>
            ) : (
              <p className="mt-1 text-sm text-muted">
                Matched products expanded into commercial configurations.
              </p>
            )}
          </li>
          <li>
            <p className="type-small text-muted">3 · Optimise buyer × merchant</p>
            {optimisation ? (
              <dl className="mt-1 space-y-1 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-muted">Policy-safe</dt>
                  <dd className="font-mono tabular-nums">
                    {optimisation.summary.policy_safe.toLocaleString()}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt>
                    <MetricHint label="Pareto-efficient" hint={METRIC_HELP.pareto} />
                  </dt>
                  <dd className="font-mono tabular-nums">
                    {optimisation.summary.pareto_efficient}
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="mt-1 text-sm text-muted">
                Policy and efficiency filters applied.
              </p>
            )}
          </li>
          <li>
            <p className="type-small text-muted">4 · Best complete offer</p>
            <p className="mt-1 font-semibold">{offer.product_name}</p>
            <p className="mt-1 font-mono text-sm tabular-nums">
              {offer.buyer_utility.toFixed(2)}
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
        <p className="mt-6 text-sm">
          <span className="font-semibold">Best product ≠ best offer</span>
          <span className="mx-2 text-muted">·</span>
          <span className="text-muted">
            AstraOS optimises the complete merchant response, not the SKU alone.
          </span>
        </p>
      </StageSection>

      {differ ? (
        <StageSection title="Why did the winner change?">
          <div className="grid gap-8 md:grid-cols-2">
            <div>
              <p className="type-small text-muted">Best product match</p>
              <p className="mt-1 font-semibold">{topMatch.product_name}</p>
              <p className="mt-3 type-small text-muted">
                <MetricHint label="Product match" hint={METRIC_HELP.productMatch} />
              </p>
              <p className="mt-1 font-mono text-lg tabular-nums">
                {productScore.value} {productScore.suffix}
              </p>
            </div>
            <div>
              <p className="type-small text-muted">Best complete offer</p>
              <p className="mt-1 font-semibold">{offer.product_name}</p>
              <p className="mt-3 type-small text-muted">
                <MetricHint label="Product match" hint={METRIC_HELP.productMatch} />
              </p>
              <p className="mt-1 font-mono text-lg tabular-nums">
                {selectedMatch.value} {selectedMatch.suffix}
              </p>
              <dl className="mt-4 space-y-1 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-muted">
                    <MetricHint
                      label="Simulated buyer utility"
                      hint={METRIC_HELP.buyerUtility}
                    />
                  </dt>
                  <dd className="font-mono tabular-nums">
                    {offer.buyer_utility.toFixed(2)}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
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
            </div>
          </div>
          {deltas.length ? (
            <dl className="mt-6 max-w-xl space-y-2 text-sm">
              <p className="type-small text-muted">Product / commercial differences</p>
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
          <p className="mt-5 max-w-2xl text-[15px] leading-6">
            {winnerChangeSummary(topMatch.product_name, offer.product_name, deltas)}
          </p>
        </StageSection>
      ) : (
        <StageSection title="Top product remained the best complete offer">
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
          <p className="mt-4 max-w-2xl text-[15px] leading-6">
            {sameProductOfferSummary(offer.product_name, deltas)}
          </p>
        </StageSection>
      )}
    </>
  );
}
