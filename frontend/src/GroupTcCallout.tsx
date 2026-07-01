import type { AgencyGroupTourConductorMetrics } from "./types";

type GroupTcCalloutProps = {
  tourConductor: AgencyGroupTourConductorMetrics;
  compact?: boolean;
};

export default function GroupTcCallout({ tourConductor, compact = false }: GroupTcCalloutProps) {
  return (
    <section
      className={`group-tc-callout${compact ? " group-tc-callout--compact" : ""}`}
      aria-label="Tour Conductor progress"
    >
      <header className="group-tc-callout-header">
        <h4>Tour Conductor progress</h4>
        <span className="group-tc-callout-ratio">
          Ratio {tourConductor.ratio_label} · {tourConductor.berths_per_credit} berths per credit
        </span>
      </header>
      <p className="group-tc-callout-message">{tourConductor.message}</p>
      {tourConductor.used_default_ratio ? (
        <p className="group-tc-callout-warning">Using default TC ratio (1:16) because the saved ratio is invalid.</p>
      ) : null}
    </section>
  );
}
