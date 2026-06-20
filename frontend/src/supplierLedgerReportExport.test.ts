import { describe, expect, it } from "vitest";
import { buildSupplierLedgerExportRows } from "./supplierLedgerReportExport";
import type { ReportSupplierLedgerRow } from "./types";

function ledgerRow(overrides: Partial<ReportSupplierLedgerRow> = {}): ReportSupplierLedgerRow {
  return {
    cruise_line: "Royal Caribbean International",
    active_booking_count: 2,
    total_volume: 8000,
    total_commission_booked: 800,
    median_price_per_room: 4000,
    average_commission_rate_percent: 10,
    share_percent: 100,
    ...overrides,
  };
}

describe("buildSupplierLedgerExportRows", () => {
  it("formats ledger rows like the HTML table", () => {
    expect(buildSupplierLedgerExportRows([ledgerRow()])).toEqual([
      [
        "Royal Caribbean International",
        "2",
        "$8,000.00",
        "$800.00",
        "$4,000.00",
        "10.0%",
      ],
    ]);
  });

  it("returns the empty-state row when no records match", () => {
    expect(buildSupplierLedgerExportRows([])).toEqual([
      ["No records match the selected filters.", "", "", "", "", ""],
    ]);
  });
});
