import { useCallback, useEffect, useState } from "react";
import {
  fetchAdvisorScorecard,
  fetchFunnelLeakReport,
  fetchPassengerDemographics,
  fetchReportMeta,
} from "./api";
import { formatMoney } from "./cabinPricing";
import { formatDisplayPhone } from "./passengerDisplay";
import PassengerQualifierBadges from "./PassengerQualifierBadges";
import ReportControlBar, { type ReportControlVariant } from "./ReportControlBar";
import ReportPagination from "./ReportPagination";
import { getReportById } from "./reportsCatalog";
import {
  DEFAULT_REPORT_FILTERS,
  REPORT_PAGE_SIZE,
  type ReportFilterState,
} from "./reportFilters";
import { buildExcelFilename } from "./reportExport";
import { downloadAdvisorScorecardXlsx } from "./advisorScorecardReportExport";
import { downloadFunnelLeakXlsx } from "./funnelLeakReportExport";
import { downloadPassengerDemographicsXlsx } from "./passengerDemographicsReportExport";
import type {
  AdvisorScorecardRow,
  FunnelLeakRow,
  PassengerDemographicsRow,
} from "./types";
import { formatDate } from "./utils";

type DiagnosticReportId =
  | "funnel-leak-lost-business"
  | "advisor-productivity-quota"
  | "passenger-demographics-qualifier";

type DiagnosticReportViewProps = {
  reportId: DiagnosticReportId;
  onBack: () => void;
};

const CONTROL_VARIANT_BY_REPORT: Record<DiagnosticReportId, ReportControlVariant> = {
  "funnel-leak-lost-business": "funnel-leak",
  "advisor-productivity-quota": "advisor-scorecard",
  "passenger-demographics-qualifier": "passenger-demographics",
};

async function fetchAllFunnelRows(filters: ReportFilterState): Promise<FunnelLeakRow[]> {
  const rows: FunnelLeakRow[] = [];
  let page = 1;
  let totalPages = 1;

  while (page <= totalPages) {
    const response = await fetchFunnelLeakReport(filters, page);
    rows.push(...response.items);
    totalPages = response.total_pages;
    page += 1;
  }

  return rows;
}

async function fetchAllAdvisorRows(filters: ReportFilterState): Promise<AdvisorScorecardRow[]> {
  const rows: AdvisorScorecardRow[] = [];
  let page = 1;
  let totalPages = 1;

  while (page <= totalPages) {
    const response = await fetchAdvisorScorecard(filters, page);
    rows.push(...response.items);
    totalPages = response.total_pages;
    page += 1;
  }

  return rows;
}

async function fetchAllPassengerRows(filters: ReportFilterState): Promise<PassengerDemographicsRow[]> {
  const rows: PassengerDemographicsRow[] = [];
  let page = 1;
  let totalPages = 1;

  while (page <= totalPages) {
    const response = await fetchPassengerDemographics(filters, page);
    rows.push(...response.items);
    totalPages = response.total_pages;
    page += 1;
  }

  return rows;
}

function formatReportPhone(phone: string | null | undefined): string {
  return formatDisplayPhone(phone) ?? "—";
}

function formatRatioPercent(value: number | null): string {
  if (value === null) {
    return "—";
  }

  return `${value.toFixed(1)}%`;
}

function formatVelocityDays(value: number | null): string {
  if (value === null) {
    return "—";
  }

  return value.toFixed(1);
}

export default function DiagnosticReportView({ reportId, onBack }: DiagnosticReportViewProps) {
  const report = getReportById(reportId);
  const [filters, setFilters] = useState<ReportFilterState>(DEFAULT_REPORT_FILTERS);
  const [advisorNames, setAdvisorNames] = useState<string[]>([]);
  const [residenceStates, setResidenceStates] = useState<string[]>([]);
  const [funnelRows, setFunnelRows] = useState<FunnelLeakRow[]>([]);
  const [advisorRows, setAdvisorRows] = useState<AdvisorScorecardRow[]>([]);
  const [passengerRows, setPassengerRows] = useState<PassengerDemographicsRow[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (reportId !== "advisor-productivity-quota" && reportId !== "passenger-demographics-qualifier") {
      return;
    }

    void fetchReportMeta()
      .then((meta) => {
        if (reportId === "advisor-productivity-quota") {
          setAdvisorNames(meta.advisor_names);
        }
        if (reportId === "passenger-demographics-qualifier") {
          setResidenceStates(meta.residence_states);
        }
      })
      .catch(() => undefined);
  }, [reportId]);

  const loadReport = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      if (reportId === "funnel-leak-lost-business") {
        const response = await fetchFunnelLeakReport(filters, filters.page);
        setFunnelRows(response.items);
        setTotal(response.total);
        setTotalPages(response.total_pages);
      } else if (reportId === "advisor-productivity-quota") {
        const response = await fetchAdvisorScorecard(filters, filters.page);
        setAdvisorRows(response.items);
        setTotal(response.total);
        setTotalPages(response.total_pages);
      } else {
        const response = await fetchPassengerDemographics(filters, filters.page);
        setPassengerRows(response.items);
        setTotal(response.total);
        setTotalPages(response.total_pages);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load report.");
      setFunnelRows([]);
      setAdvisorRows([]);
      setPassengerRows([]);
      setTotal(0);
      setTotalPages(0);
    } finally {
      setLoading(false);
    }
  }, [filters, reportId]);

  useEffect(() => {
    void loadReport();
  }, [loadReport]);

  async function handleExport() {
    setExporting(true);
    setError("");
    try {
      if (reportId === "funnel-leak-lost-business") {
        const rows = await fetchAllFunnelRows(filters);
        await downloadFunnelLeakXlsx(buildExcelFilename(reportId), rows);
      } else if (reportId === "advisor-productivity-quota") {
        const rows = await fetchAllAdvisorRows(filters);
        await downloadAdvisorScorecardXlsx(buildExcelFilename(reportId), rows);
      } else {
        const rows = await fetchAllPassengerRows(filters);
        await downloadPassengerDemographicsXlsx(buildExcelFilename(reportId), rows);
      }
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : "Unable to export report.");
    } finally {
      setExporting(false);
    }
  }

  if (!report) {
    return null;
  }

  return (
    <section className="report-view-page report-view-page-interactive">
      <button type="button" className="report-back-link" onClick={onBack}>
        ← Back to Reports List
      </button>

      <header className="request-summary-card request-summary-card-compact report-view-summary-card">
        <div className="request-summary-compact-row">
          <div className="request-summary-compact-title">
            <h2>{report.title}</h2>
          </div>
        </div>
        <div className="request-summary-compact-meta">
          <span>{report.description}</span>
        </div>
      </header>

      <ReportControlBar
        filters={filters}
        variant={CONTROL_VARIANT_BY_REPORT[reportId]}
        advisorNames={advisorNames}
        residenceStates={residenceStates}
        exporting={exporting}
        onChange={(next) => setFilters((current) => ({ ...current, ...next }))}
        onExport={() => void handleExport()}
      />

      {error ? <p className="status error">{error}</p> : null}

      <section className="card report-view-table-card">
        {loading ? (
          <p className="report-view-loading">Loading report...</p>
        ) : reportId === "funnel-leak-lost-business" ? (
          <div className="report-view-table-wrap">
            <table className="report-view-table report-diagnostic-table report-funnel-table">
              <thead>
                <tr>
                  <th scope="col">Request ID</th>
                  <th scope="col">Client Name</th>
                  <th scope="col">Quoted Cruise Line</th>
                  <th scope="col">Quoted Destination</th>
                  <th scope="col" className="report-cell-numeric">
                    Est. Value Lost
                  </th>
                  <th scope="col">Primary Rejection Reason</th>
                </tr>
              </thead>
              <tbody>
                {funnelRows.length === 0 ? (
                  <tr className="report-view-empty-row">
                    <td colSpan={6}>No records match the selected filters.</td>
                  </tr>
                ) : (
                  funnelRows.map((row) => (
                    <tr key={row.request_id}>
                      <td>
                        <strong>#{row.request_id}</strong>
                      </td>
                      <td>{row.client_name}</td>
                      <td>{row.quoted_cruise_line}</td>
                      <td>{row.quoted_destination}</td>
                      <td className="report-funnel-value-lost">{formatMoney(row.estimated_value_lost)}</td>
                      <td>{row.primary_rejection_reason}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        ) : reportId === "advisor-productivity-quota" ? (
          <div className="report-view-table-wrap">
            <table className="report-view-table report-diagnostic-table report-advisor-table">
              <thead>
                <tr>
                  <th scope="col">Advisor Name</th>
                  <th scope="col" className="report-cell-numeric">
                    Active Lead Count
                  </th>
                  <th scope="col" className="report-cell-numeric">
                    Proposals Pending
                  </th>
                  <th scope="col" className="report-cell-numeric">
                    Completed Bookings
                  </th>
                  <th scope="col" className="report-cell-numeric">
                    Avg Pipeline Velocity (Days)
                  </th>
                  <th scope="col" className="report-advisor-close-ratio-header">
                    Request-to-Close (Deposited) Ratio (%)
                  </th>
                </tr>
              </thead>
              <tbody>
                {advisorRows.length === 0 ? (
                  <tr className="report-view-empty-row">
                    <td colSpan={6}>No records match the selected filters.</td>
                  </tr>
                ) : (
                  advisorRows.map((row) => (
                    <tr key={row.advisor_name}>
                      <td>
                        <strong>{row.advisor_name}</strong>
                      </td>
                      <td className="report-cell-numeric">{row.active_lead_count}</td>
                      <td className="report-cell-numeric">{row.proposals_pending}</td>
                      <td className="report-cell-numeric">{row.completed_bookings}</td>
                      <td className="report-cell-numeric">
                        {formatVelocityDays(row.avg_pipeline_velocity_days)}
                      </td>
                      <td className="report-advisor-close-ratio">
                        {formatRatioPercent(row.request_to_close_ratio_percent)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="report-view-table-wrap">
            <table className="report-view-table report-diagnostic-table report-passenger-table">
              <thead>
                <tr>
                  <th scope="col">Passenger Name</th>
                  <th scope="col">Date of Birth</th>
                  <th scope="col">State</th>
                  <th scope="col">Contact Phone</th>
                  <th scope="col">Email Address</th>
                  <th scope="col">Active Qualifier Badges</th>
                </tr>
              </thead>
              <tbody>
                {passengerRows.length === 0 ? (
                  <tr className="report-view-empty-row">
                    <td colSpan={6}>No records match the selected filters.</td>
                  </tr>
                ) : (
                  passengerRows.map((row) => (
                    <tr key={row.passenger_id}>
                      <td>
                        <strong>{row.passenger_name}</strong>
                      </td>
                      <td>{row.date_of_birth ? formatDate(row.date_of_birth) : "—"}</td>
                      <td>{row.state_of_residence ?? "—"}</td>
                      <td>{formatReportPhone(row.contact_phone)}</td>
                      <td>{row.email_address ?? "—"}</td>
                      <td>
                        <PassengerQualifierBadges qualifiers={row.qualifiers} />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        <ReportPagination
          page={filters.page}
          total={total}
          totalPages={totalPages}
          pageSize={REPORT_PAGE_SIZE}
          loading={loading}
          onPageChange={(page) => setFilters((current) => ({ ...current, page }))}
        />
      </section>
    </section>
  );
}
