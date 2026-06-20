import { describe, expect, it } from "vitest";
import { buildFunnelLeakExportRows } from "./funnelLeakReportExport";
import type { FunnelLeakRow } from "./types";

function funnelRow(overrides: Partial<FunnelLeakRow> = {}): FunnelLeakRow {
  return {
    request_id: 42,
    client_name: "Jamie Cruise",
    quoted_cruise_line: "Royal Caribbean International",
    quoted_destination: "Caribbean",
    estimated_value_lost: 3900,
    primary_rejection_reason: "Price",
    loss_segment: "rejected_quote",
    ...overrides,
  };
}

describe("buildFunnelLeakExportRows", () => {
  it("formats funnel leak rows like the HTML table", () => {
    expect(buildFunnelLeakExportRows([funnelRow()])).toEqual([
      ["#42", "Jamie Cruise", "Royal Caribbean International", "Caribbean", "$3,900.00", "Price"],
    ]);
  });

  it("returns the empty-state row when no records match", () => {
    expect(buildFunnelLeakExportRows([])).toEqual([
      ["No records match the selected filters.", "", "", "", "", ""],
    ]);
  });
});
