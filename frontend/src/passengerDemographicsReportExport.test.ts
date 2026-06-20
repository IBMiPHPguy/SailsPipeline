import { describe, expect, it } from "vitest";
import { buildPassengerDemographicsExportValues } from "./passengerDemographicsReportExport";
import type { PassengerDemographicsRow } from "./types";

function demographicsRow(overrides: Partial<PassengerDemographicsRow> = {}): PassengerDemographicsRow {
  return {
    passenger_id: 1,
    passenger_name: "Alex Veteran",
    date_of_birth: "1975-06-10",
    state_of_residence: "Texas",
    contact_phone: "5551234567.0",
    email_address: "alex@example.com",
    qualifiers: ["Military"],
    ...overrides,
  };
}

describe("buildPassengerDemographicsExportValues", () => {
  it("formats rows like the HTML table body", () => {
    expect(buildPassengerDemographicsExportValues([demographicsRow()])).toEqual([
      ["Alex Veteran", "06/10/1975", "Texas", "(555) 123-4567", "alex@example.com", ""],
    ]);
  });

  it("returns the empty-state row when no records match", () => {
    expect(buildPassengerDemographicsExportValues([])).toEqual([
      ["No records match the selected filters.", "", "", "", "", ""],
    ]);
  });
});
