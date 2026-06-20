import { describe, expect, it } from "vitest";
import { buildAdvisorScorecardExportRows } from "./advisorScorecardReportExport";
import type { AdvisorScorecardRow } from "./types";

function scorecardRow(overrides: Partial<AdvisorScorecardRow> = {}): AdvisorScorecardRow {
  return {
    advisor_name: "scorecard-agent",
    active_lead_count: 3,
    proposals_pending: 2,
    completed_bookings: 4,
    avg_pipeline_velocity_days: 12.5,
    request_to_close_ratio_percent: 40,
    ...overrides,
  };
}

describe("buildAdvisorScorecardExportRows", () => {
  it("formats scorecard rows like the HTML table", () => {
    expect(buildAdvisorScorecardExportRows([scorecardRow()])).toEqual([
      ["scorecard-agent", "3", "2", "4", "12.5", "40.0%"],
    ]);
  });

  it("returns the empty-state row when no records match", () => {
    expect(buildAdvisorScorecardExportRows([])).toEqual([
      ["No records match the selected filters.", "", "", "", "", ""],
    ]);
  });

  it("renders null metrics as em dashes", () => {
    expect(
      buildAdvisorScorecardExportRows([
        scorecardRow({
          avg_pipeline_velocity_days: null,
          request_to_close_ratio_percent: null,
        }),
      ]),
    ).toEqual([["scorecard-agent", "3", "2", "4", "—", "—"]]);
  });
});
