import { describe, expect, it } from "vitest";
import {
  buildManifestExportModel,
  buildManifestRenderRows,
} from "./manifestReportLayout";
import type { ReportManifestRow } from "./types";

function manifestRow(overrides: Partial<ReportManifestRow> & Pick<ReportManifestRow, "request_id">): ReportManifestRow {
  return {
    request_status: "Open",
    pipeline_status: "Open",
    close_reason: null,
    primary_passenger: "Jane Doe",
    destination: "Caribbean",
    cruise_line: "Royal Caribbean International",
    sailing_month_year: "Jan 2026",
    estimated_gross_booking_total: 5000,
    projected_commission_target: 500,
    owner_agent: "Agent Smith",
    current_task: null,
    ...overrides,
  };
}

describe("buildManifestRenderRows", () => {
  it("groups open requests by open task, then closed requests by reason", () => {
    const rows = buildManifestRenderRows([
      manifestRow({
        request_id: 1,
        current_task: {
          id: "1",
          task_key: "research_cruise_options",
          title: "Research Cruise",
          workflow_name: "Research",
          workflow_type: "research",
        },
      }),
      manifestRow({
        request_id: 2,
        pipeline_status: "Closed",
        close_reason: "Purchased - Trip Created",
      }),
    ]);

    expect(rows.map((entry) => (entry.kind === "request" ? entry.row.request_id : entry.label))).toEqual([
      "Open Requests",
      "Research Cruise",
      1,
      "Closed Requests",
      "Purchased - Trip Created",
      2,
    ]);
  });
});

describe("buildManifestExportModel", () => {
  it("mirrors HTML table columns and inserts section break rows", () => {
    const exportRows = buildManifestExportModel([
      manifestRow({
        request_id: 10,
        current_task: {
          id: "2",
          task_key: "send_research_communication",
          title: "Send Proposal",
          workflow_name: "Communicate",
          workflow_type: "communicate_research",
        },
      }),
    ]);

    expect(exportRows[0]).toEqual({
      cells: ["Open Requests", "", "", "", "", "", "", ""],
      style: "status-open",
      merge: true,
    });
    expect(exportRows[1]).toEqual({
      cells: ["Send Proposal", "", "", "", "", "", "", ""],
      style: "task-communicate",
      merge: true,
    });
    expect(exportRows[2]?.cells[0]).toBe("#10");
    expect(exportRows[2]?.cells[5]).toBe("$5,000.00");
    expect(exportRows[2]?.style).toBe("request");
    expect(exportRows[2]?.merge).toBe(false);
  });

  it("returns the empty-state row when no records match", () => {
    expect(buildManifestExportModel([])).toEqual([
      {
        cells: ["No records match the selected filters.", "", "", "", "", "", "", ""],
        style: "empty",
        merge: true,
      },
    ]);
  });
});
