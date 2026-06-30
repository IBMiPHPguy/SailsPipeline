import { useMemo } from "react";
import type { ReportWorkflowTaskGroup } from "./types";
import { QUALIFIERS } from "./formOptions";
import { qualifierBadgeClass } from "./qualifierDisplay";
import {
  REPORT_LOSS_SEGMENT_OPTIONS,
  REPORT_PIPELINE_STATUS_OPTIONS,
  REPORT_REJECTION_REASON_OPTIONS,
  REPORT_SUPPLIER_OPTIONS,
  REPORT_TIMEFRAME_OPTIONS,
  type ReportFilterState,
} from "./reportFilters";

export type ReportControlVariant =
  | "manifest"
  | "ledger"
  | "funnel-leak"
  | "advisor-scorecard"
  | "passenger-demographics";

type ReportControlBarProps = {
  filters: ReportFilterState;
  variant: ReportControlVariant;
  workflowTaskGroups?: ReportWorkflowTaskGroup[];
  advisorNames?: string[];
  residenceStates?: string[];
  exporting?: boolean;
  onChange: (next: Partial<ReportFilterState>) => void;
  onExport: () => void;
};

export default function ReportControlBar({
  filters,
  variant,
  workflowTaskGroups = [],
  advisorNames = [],
  residenceStates = [],
  exporting = false,
  onChange,
  onExport,
}: ReportControlBarProps) {
  const showPipelineFilters = variant === "manifest";
  const showCruiseLine = variant === "manifest" || variant === "ledger" || variant === "funnel-leak";
  const showFunnelFilters = variant === "funnel-leak";
  const showAdvisorFilter = variant === "advisor-scorecard";
  const showQualifierFilter = variant === "passenger-demographics";
  const showTimeframeFilter = variant !== "passenger-demographics";

  const workflowTaskOptions = useMemo(() => {
    const options = new Map<string, string>();
    for (const group of workflowTaskGroups) {
      for (const task of group.tasks) {
        if (!options.has(task.value)) {
          options.set(task.value, task.label);
        }
      }
    }
    return [...options.entries()]
      .sort((left, right) => left[1].localeCompare(right[1], undefined, { sensitivity: "base" }))
      .map(([value, label]) => ({ value, label }));
  }, [workflowTaskGroups]);

  function toggleQualifier(qualifier: string) {
    const selected = filters.qualifiers.includes(qualifier);
    const nextQualifiers = selected
      ? filters.qualifiers.filter((value) => value !== qualifier)
      : [...filters.qualifiers, qualifier];
    onChange({ qualifiers: nextQualifiers, page: 1 });
  }

  return (
    <section className="report-control-bar" aria-label="Report filters">
      <div className="report-control-fields">
      {showCruiseLine ? (
        <label className="report-control-field">
          <span>Supplier / Cruise Line</span>
          <select
            value={filters.cruiseLine}
            onChange={(event) => onChange({ cruiseLine: event.target.value, page: 1 })}
          >
            {REPORT_SUPPLIER_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {showTimeframeFilter ? (
        <label className="report-control-field">
          <span>Timeframe / Created Date</span>
          <select
            value={filters.timeframe}
            onChange={(event) => onChange({ timeframe: event.target.value, page: 1 })}
          >
            {REPORT_TIMEFRAME_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {showFunnelFilters ? (
        <>
          <label className="report-control-field">
            <span>Loss Segment</span>
            <select
              value={filters.lossSegment}
              onChange={(event) => onChange({ lossSegment: event.target.value, page: 1 })}
            >
              {REPORT_LOSS_SEGMENT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="report-control-field">
            <span>Primary Rejection Reason</span>
            <select
              value={filters.rejectionReason}
              onChange={(event) => onChange({ rejectionReason: event.target.value, page: 1 })}
            >
              {REPORT_REJECTION_REASON_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </>
      ) : null}

      {showAdvisorFilter ? (
        <label className="report-control-field">
          <span>Advisor</span>
          <select
            value={filters.advisor}
            onChange={(event) => onChange({ advisor: event.target.value, page: 1 })}
          >
            <option value="all">All Advisors</option>
            {advisorNames.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {showQualifierFilter ? (
        <div className="report-control-demographics-filters">
          <span className="report-control-demographics-label">State</span>
          <span className="report-control-demographics-label">Qualifier</span>
          <div className="report-control-state-control">
            <select
              value={filters.state}
              aria-label="State"
              onChange={(event) => onChange({ state: event.target.value, page: 1 })}
            >
              <option value="all">All States</option>
              {residenceStates.map((state) => (
                <option key={state} value={state}>
                  {state}
                </option>
              ))}
            </select>
          </div>
          <div className="report-control-qualifier-control">
            <div className="passenger-qualifier-picker" role="group" aria-label="Qualifier">
              {QUALIFIERS.map((qualifier) => {
                const selected = filters.qualifiers.includes(qualifier);
                return (
                  <button
                    key={qualifier}
                    type="button"
                    className={`passenger-qualifier-picker-pill ${qualifierBadgeClass(qualifier)}${
                      selected ? " is-selected" : ""
                    }`}
                    aria-pressed={selected}
                    onClick={() => toggleQualifier(qualifier)}
                  >
                    {qualifier}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      ) : null}

      {showPipelineFilters ? (
        <>
          <label className="report-control-field">
            <span>Pipeline Status</span>
            <select
              value={filters.pipelineStatus}
              onChange={(event) => onChange({ pipelineStatus: event.target.value, page: 1 })}
            >
              {REPORT_PIPELINE_STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="report-control-field">
            <span>Open task</span>
            <select
              value={filters.workflowTask}
              onChange={(event) => onChange({ workflowTask: event.target.value, page: 1 })}
            >
              <option value="all">All open tasks</option>
              {workflowTaskOptions.map((task) => (
                <option key={task.value} value={task.value}>
                  {task.label}
                </option>
              ))}
            </select>
          </label>
        </>
      ) : null}
      </div>

      <div className="report-control-export">
        <button type="button" className="report-export-button" disabled={exporting} onClick={onExport}>
          <span aria-hidden="true">📤</span>
          Export to Excel
        </button>
      </div>
    </section>
  );
}
