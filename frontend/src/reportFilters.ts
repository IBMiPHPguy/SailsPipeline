import { CRUISE_LINES, PROPOSED_CRUISE_REJECTION_REASONS } from "./formOptions";
import { DEFAULT_PAGE_SIZE } from "./pagination";

export const REPORT_PAGE_SIZE = DEFAULT_PAGE_SIZE;

const SORTED_CRUISE_LINES = [...CRUISE_LINES].sort((left, right) => left.localeCompare(right));

export const REPORT_SUPPLIER_OPTIONS = [
  { value: "all", label: "All" },
  ...SORTED_CRUISE_LINES.map((line) => ({
    value: line,
    label: line,
  })),
];

export const REPORT_TIMEFRAME_OPTIONS = [
  { value: "all_time", label: "All Time" },
  { value: "current_month", label: "Current Month" },
  { value: "last_30_days", label: "Last 30 Days" },
  { value: "current_year", label: "Current Year" },
] as const;

export const REPORT_PIPELINE_STATUS_OPTIONS = [
  { value: "all", label: "All Statuses" },
  { value: "open", label: "Open" },
  { value: "closed", label: "Closed" },
] as const;

export const REPORT_LOSS_SEGMENT_OPTIONS = [
  { value: "all", label: "All Loss Types" },
  { value: "rejected_quote", label: "Rejected Quote" },
  { value: "closed_lost", label: "Closed Without Booking" },
] as const;

export const REPORT_REJECTION_REASON_OPTIONS = [
  { value: "all", label: "All Reasons" },
  ...PROPOSED_CRUISE_REJECTION_REASONS.map((reason) => ({ value: reason, label: reason })),
  { value: "Reason not recorded", label: "Reason not recorded" },
];

export type ReportFilterState = {
  cruiseLine: string;
  timeframe: string;
  pipelineStatus: string;
  workflowTask: string;
  rejectionReason: string;
  lossSegment: string;
  advisor: string;
  qualifiers: string[];
  state: string;
  page: number;
  pageSize: number;
};

export const DEFAULT_REPORT_FILTERS: ReportFilterState = {
  cruiseLine: "all",
  timeframe: "all_time",
  pipelineStatus: "all",
  workflowTask: "all",
  rejectionReason: "all",
  lossSegment: "all",
  advisor: "all",
  qualifiers: [],
  state: "all",
  page: 1,
  pageSize: DEFAULT_PAGE_SIZE,
};

function baseReportParams(filters: ReportFilterState, page: number): URLSearchParams {
  const params = new URLSearchParams();
  params.set("timeframe", filters.timeframe);
  params.set("page", String(page));
  params.set("page_size", String(filters.pageSize || DEFAULT_PAGE_SIZE));
  return params;
}

export function reportFiltersToQuery(filters: ReportFilterState): URLSearchParams {
  const params = baseReportParams(filters, filters.page);
  params.set("cruise_line", filters.cruiseLine);
  params.set("pipeline_status", filters.pipelineStatus);
  params.set("workflow_task", filters.workflowTask);
  return params;
}

export function ledgerFiltersToQuery(filters: ReportFilterState): URLSearchParams {
  const params = baseReportParams(filters, filters.page);
  params.set("cruise_line", filters.cruiseLine);
  return params;
}

export function funnelLeakFiltersToQuery(filters: ReportFilterState): URLSearchParams {
  const params = baseReportParams(filters, filters.page);
  params.set("cruise_line", filters.cruiseLine);
  params.set("rejection_reason", filters.rejectionReason);
  params.set("loss_segment", filters.lossSegment);
  return params;
}

export function advisorScorecardFiltersToQuery(filters: ReportFilterState): URLSearchParams {
  const params = baseReportParams(filters, filters.page);
  params.set("advisor", filters.advisor);
  return params;
}

export function passengerDemographicsFiltersToQuery(filters: ReportFilterState): URLSearchParams {
  const params = new URLSearchParams();
  filters.qualifiers.forEach((qualifier) => params.append("qualifier", qualifier));
  params.set("state", filters.state);
  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize || DEFAULT_PAGE_SIZE));
  return params;
}
