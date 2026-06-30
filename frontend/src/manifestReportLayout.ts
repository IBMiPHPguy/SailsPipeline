import { formatMoney } from "./cabinPricing";
import { PRIMARY_CLOSE_REASON } from "./formOptions";
import {
  type ManifestExportRowStyle,
  taskKeyStyleSuffix,
} from "./manifestReportStyles";
import type { ReportManifestRow } from "./types";
export type ManifestRenderRow =
  | { kind: "status"; key: string; label: string; statusType: "open" | "closed" }
  | {
      kind: "group";
      key: string;
      label: string;
      groupType: "workflow" | "task" | "closed-reason";
      taskKey?: string;
    }
  | { kind: "request"; key: string; row: ReportManifestRow };

export const MANIFEST_EXPORT_HEADERS = [
  "Request ID / Status",
  "Primary Passenger",
  "Destination",
  "Cruise Line",
  "Sailing Month/Year",
  "Est. Gross Booking Total",
  "Projected Commission Target",
  "Owner Agent",
] as const;

const MANIFEST_EXPORT_EMPTY_ROW: string[] = [
  "No records match the selected filters.",
  "",
  "",
  "",
  "",
  "",
  "",
  "",
];

function emptyManifestExportCells(): string[] {
  return ["", "", "", "", "", "", ""];
}

export function buildManifestRenderRows(rows: ReportManifestRow[]): ManifestRenderRow[] {
  const openRows = rows.filter((row) => row.pipeline_status === "Open");
  const closedRows = rows.filter((row) => row.pipeline_status === "Closed");
  const renderRows: ManifestRenderRow[] = [];

  if (openRows.length > 0) {
    renderRows.push({ kind: "status", key: "status-open", label: "Open Requests", statusType: "open" });

    const taskOrder = new Map<string, number>();
    openRows.forEach((row, index) => {
      const taskKey = row.current_task?.task_key || `title:${row.current_task?.title ?? "none"}`;
      if (!taskOrder.has(taskKey)) {
        taskOrder.set(taskKey, index);
      }
    });

    const groupedByTask = new Map<string, ReportManifestRow[]>();
    openRows.forEach((row) => {
      const taskKey = row.current_task?.task_key || `title:${row.current_task?.title ?? "none"}`;
      if (!groupedByTask.has(taskKey)) {
        groupedByTask.set(taskKey, []);
      }
      groupedByTask.get(taskKey)?.push(row);
    });

    [...groupedByTask.entries()]
      .sort((left, right) => (taskOrder.get(left[0]) ?? 0) - (taskOrder.get(right[0]) ?? 0))
      .forEach(([taskKey, taskRows]) => {
        const taskLabel = taskRows[0]?.current_task?.title ?? "No Open Workflow Task";
        renderRows.push({
          kind: "group",
          key: `task-${taskKey}`,
          label: taskLabel,
          groupType: "task",
          taskKey: taskRows[0]?.current_task?.task_key ?? undefined,
        });
        taskRows.forEach((row) =>
          renderRows.push({
            kind: "request",
            key: `request-${row.request_id}`,
            row,
          }),
        );
      });
  }

  if (closedRows.length > 0) {
    renderRows.push({ kind: "status", key: "status-closed", label: "Closed Requests", statusType: "closed" });

    const reasonOrder = new Map<string, number>();
    closedRows.forEach((row, index) => {
      const reason = row.close_reason?.trim() || "No close reason recorded";
      if (!reasonOrder.has(reason)) {
        reasonOrder.set(reason, index);
      }
    });

    const groupedByReason = new Map<string, ReportManifestRow[]>();
    closedRows.forEach((row) => {
      const reason = row.close_reason?.trim() || "No close reason recorded";
      if (!groupedByReason.has(reason)) {
        groupedByReason.set(reason, []);
      }
      groupedByReason.get(reason)?.push(row);
    });

    [...groupedByReason.entries()]
      .sort((left, right) => (reasonOrder.get(left[0]) ?? 0) - (reasonOrder.get(right[0]) ?? 0))
      .forEach(([reason, reasonRows]) => {
        renderRows.push({
          kind: "group",
          key: `closed-${reason}`,
          label: reason,
          groupType: "closed-reason",
        });
        reasonRows.forEach((row) =>
          renderRows.push({
            kind: "request",
            key: `request-${row.request_id}`,
            row,
          }),
        );
      });
  }

  return renderRows;
}

function exportStyleForRenderRow(entry: ManifestRenderRow): ManifestExportRowStyle {
  if (entry.kind === "status") {
    return entry.statusType === "open" ? "status-open" : "status-closed";
  }

  if (entry.kind === "group") {
    if (entry.groupType === "closed-reason") {
      return entry.label === PRIMARY_CLOSE_REASON ? "closed-reason-purchased" : "closed-reason";
    }

    const suffix = taskKeyStyleSuffix(entry.taskKey);
    return entry.groupType === "workflow" ? `workflow-${suffix}` : `task-${suffix}`;
  }

  return "request";
}

export type ManifestExportRow = {
  cells: string[];
  style: ManifestExportRowStyle;
  merge: boolean;
};

function manifestRenderRowToExportRow(entry: ManifestRenderRow): string[] {  if (entry.kind === "status") {
    return [entry.label, ...emptyManifestExportCells()];
  }

  if (entry.kind === "group") {
    const label = entry.groupType === "task" ? entry.label : entry.label;
    return [label, ...emptyManifestExportCells()];
  }

  const row = entry.row;
  return [
    `#${row.request_id}`,
    row.primary_passenger,
    row.destination,
    row.cruise_line,
    row.sailing_month_year,
    formatMoney(row.estimated_gross_booking_total),
    formatMoney(row.projected_commission_target),
    row.owner_agent,
  ];
}

export function buildManifestExportModel(rows: ReportManifestRow[]): ManifestExportRow[] {
  if (rows.length === 0) {
    return [{ cells: [...MANIFEST_EXPORT_EMPTY_ROW], style: "empty", merge: true }];
  }

  return buildManifestRenderRows(rows).map((entry) => ({
    cells: manifestRenderRowToExportRow(entry),
    style: exportStyleForRenderRow(entry),
    merge: entry.kind !== "request",
  }));
}

export function buildManifestExportRows(rows: ReportManifestRow[]): string[][] {
  return buildManifestExportModel(rows).map((entry) => entry.cells);
}