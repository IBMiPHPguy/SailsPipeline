import { formatMoney } from "./cabinPricing";
import type { AgencyGroupMetricsTotals } from "./types";

type GroupYieldPanelProps = {
  totals: AgencyGroupMetricsTotals;
  linkedRequestCount: number;
};

export default function GroupYieldPanel({ totals, linkedRequestCount }: GroupYieldPanelProps) {
  return (
    <section className="group-yield-panel" aria-label="Group financial yield">
      <header className="group-yield-panel-header">
        <h4>Financial yield</h4>
        <p className="meta">{linkedRequestCount} linked requests</p>
      </header>
      <dl className="group-yield-panel-grid">
        <div>
          <dt>Max potential gross</dt>
          <dd>{formatMoney(totals.max_gross_yield)}</dd>
        </div>
        <div>
          <dt>Accrued gross</dt>
          <dd>{formatMoney(totals.accrued_gross_yield)}</dd>
        </div>
        <div>
          <dt>Remaining potential</dt>
          <dd>{formatMoney(totals.remaining_gross_yield)}</dd>
        </div>
      </dl>
    </section>
  );
}
