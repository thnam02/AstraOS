import { Drawer } from "@/components/shared/Drawer";
import { nearTie } from "@/lib/arenaDisplay";
import type { ArenaRunResponse } from "@/types";

export function ExperimentInspector({
  open,
  duel,
  onClose,
}: {
  open: boolean;
  duel: ArenaRunResponse | null;
  onClose: () => void;
}) {
  return (
    <Drawer open={open} title="Inspect experiment" onClose={onClose}>
      {duel ? (
        <div className="space-y-4 text-xs">
          <dl className="space-y-1">
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Arena run</dt>
              <dd className="font-mono">{duel.arena_run_id}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Mission</dt>
              <dd className="font-mono">{duel.mission_id}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Buyer profile</dt>
              <dd>{duel.buyer_profile}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Selection reason</dt>
              <dd>{duel.buyer_selection.reason}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Tie-break</dt>
              <dd>{duel.buyer_selection.tie_break ?? "none"}</dd>
            </div>
            {nearTie(duel) ? (
              <p className="text-muted">
                Near-equivalent responses differ by less than 0.01 buyer utility.
                Deterministic tie-break: price, then delivery, then strategy name.
              </p>
            ) : null}
          </dl>
          <div>
            <p className="eyebrow">Strategy responses</p>
            <pre className="mt-2 overflow-x-auto border border-line bg-canvas p-3 text-[11px] text-muted">
              {JSON.stringify(duel.strategies, null, 2)}
            </pre>
          </div>
          <div>
            <p className="eyebrow">Buyer utility decomposition</p>
            <pre className="mt-2 overflow-x-auto border border-line bg-canvas p-3 text-[11px] text-muted">
              {JSON.stringify(duel.explanation, null, 2)}
            </pre>
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted">Run a duel to inspect the experiment.</p>
      )}
    </Drawer>
  );
}
