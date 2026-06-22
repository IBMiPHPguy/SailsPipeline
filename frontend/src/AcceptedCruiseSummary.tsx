import type { ProposedCruise } from "./types";
import { formatDate } from "./utils";

type AcceptedCruiseSummaryProps = {
  cruise: Pick<ProposedCruise, "cruise_line" | "ship" | "departure_date">;
};

export default function AcceptedCruiseSummary({ cruise }: AcceptedCruiseSummaryProps) {
  return (
    <dl className="crm-entry-grid accepted-cruise-summary-grid">
      <div>
        <dt>Cruise line</dt>
        <dd>{cruise.cruise_line}</dd>
      </div>
      <div>
        <dt>Ship</dt>
        <dd>{cruise.ship}</dd>
      </div>
      <div>
        <dt>Departure</dt>
        <dd>{formatDate(cruise.departure_date)}</dd>
      </div>
    </dl>
  );
}
