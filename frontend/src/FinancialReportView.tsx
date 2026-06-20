import { useCallback, useEffect, useState } from "react";
import { fetchReportMeta, fetchSalesManifest, fetchSupplierLedger } from "./api";
import { formatMoney } from "./cabinPricing";
import { PRIMARY_CLOSE_REASON } from "./formOptions";
import {
  buildManifestExportModel,
  buildManifestRenderRows,
} from "./manifestReportLayout";
import { downloadManifestXlsx } from "./manifestReportExport";
import { downloadSupplierLedgerXlsx } from "./supplierLedgerReportExport";
import ReportControlBar from "./ReportControlBar";
import ReportPagination from "./ReportPagination";
import { getReportById, type ReportId } from "./reportsCatalog";
import {
  DEFAULT_REPORT_FILTERS,
  REPORT_PAGE_SIZE,
  type ReportFilterState,
} from "./reportFilters";
import { buildExcelFilename } from "./reportExport";
import type {
  ReportManifestRow,
  ReportSupplierLedgerRow,
  ReportWorkflowTaskGroup,
} from "./types";

type FinancialReportViewProps = {
  reportId: "sales-volume-target-manifest" | "supplier-share-volume-ledger";
  onBack: () => void;
};

async function fetchAllManifestRows(filters: ReportFilterState): Promise<ReportManifestRow[]> {
  const rows: ReportManifestRow[] = [];
  let page = 1;
  let totalPages = 1;

  while (page <= totalPages) {
    const response = await fetchSalesManifest(filters, page);
    rows.push(...response.items);
    totalPages = response.total_pages;
    page += 1;
  }

  return rows;
}

async function fetchAllSupplierRows(filters: ReportFilterState): Promise<ReportSupplierLedgerRow[]> {
  const rows: ReportSupplierLedgerRow[] = [];
  let page = 1;
  let totalPages = 1;

  while (page <= totalPages) {
    const response = await fetchSupplierLedger(filters, page);
    rows.push(...response.items);
    totalPages = response.total_pages;
    page += 1;
  }

  return rows;
}

function workflowBandClass(workflowType?: string): string {
  if (workflowType === "research") {
    return "report-manifest-group-row-workflow report-manifest-group-row-workflow-research";
  }
  if (workflowType === "communicate_research") {
    return "report-manifest-group-row-workflow report-manifest-group-row-workflow-communicate";
  }
  if (workflowType === "enter_trip_crm") {
    return "report-manifest-group-row-workflow report-manifest-group-row-workflow-crm";
  }
  return "report-manifest-group-row-workflow report-manifest-group-row-workflow-default";
}

function taskBandClass(workflowType?: string): string {
  if (workflowType === "research") {
    return "report-manifest-group-row-task report-manifest-group-row-task-research";
  }
  if (workflowType === "communicate_research") {
    return "report-manifest-group-row-task report-manifest-group-row-task-communicate";
  }
  if (workflowType === "enter_trip_crm") {
    return "report-manifest-group-row-task report-manifest-group-row-task-crm";
  }
  return "report-manifest-group-row-task report-manifest-group-row-task-default";
}

export default function FinancialReportView({ reportId, onBack }: FinancialReportViewProps) {
  const report = getReportById(reportId);
  const [filters, setFilters] = useState<ReportFilterState>(DEFAULT_REPORT_FILTERS);
  const [workflowTaskGroups, setWorkflowTaskGroups] = useState<ReportWorkflowTaskGroup[]>([]);
  const [manifestRows, setManifestRows] = useState<ReportManifestRow[]>([]);
  const [supplierRows, setSupplierRows] = useState<ReportSupplierLedgerRow[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (reportId !== "sales-volume-target-manifest") {
      return;
    }

    void fetchReportMeta()
      .then((meta) => setWorkflowTaskGroups(meta.workflow_task_groups))
      .catch(() => undefined);
  }, [reportId]);

  const loadReport = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      if (reportId === "sales-volume-target-manifest") {
        const response = await fetchSalesManifest(filters, filters.page);
        setManifestRows(response.items);
        setTotal(response.total);
        setTotalPages(response.total_pages);
      } else {
        const response = await fetchSupplierLedger(filters, filters.page);
        setSupplierRows(response.items);
        setTotal(response.total);
        setTotalPages(response.total_pages);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load report.");
      setManifestRows([]);
      setSupplierRows([]);
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
      if (reportId === "sales-volume-target-manifest") {
        const rows = await fetchAllManifestRows(filters);
        await downloadManifestXlsx(
          buildExcelFilename("sales-volume-target-manifest"),
          "Sales Manifest",
          buildManifestExportModel(rows),
        );
      } else {
        const rows = await fetchAllSupplierRows(filters);
        await downloadSupplierLedgerXlsx(
          buildExcelFilename("supplier-share-volume-ledger"),
          rows,
        );
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

  const manifestRenderRows = buildManifestRenderRows(manifestRows);

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
        workflowTaskGroups={workflowTaskGroups}
        variant={reportId === "sales-volume-target-manifest" ? "manifest" : "ledger"}
        exporting={exporting}
        onChange={(next) => setFilters((current) => ({ ...current, ...next }))}
        onExport={() => void handleExport()}
      />

      {error ? <p className="status error">{error}</p> : null}

      <section className="card report-view-table-card">
        {loading ? (
          <p className="report-view-loading">Loading report...</p>
        ) : reportId === "sales-volume-target-manifest" ? (
          <div className="report-view-table-wrap">
            <table className="report-view-table report-manifest-table">
              <thead>
                <tr>
                  <th scope="col">Request ID / Status</th>
                  <th scope="col">Primary Passenger</th>
                  <th scope="col">Destination</th>
                  <th scope="col">Cruise Line</th>
                  <th scope="col">Sailing Month/Year</th>
                  <th scope="col" className="report-cell-numeric">
                    Est. Gross Booking Total
                  </th>
                  <th scope="col" className="report-cell-numeric">
                    Projected Commission Target
                  </th>
                  <th scope="col">Owner Agent</th>
                </tr>
              </thead>
              <tbody>
                {manifestRows.length === 0 ? (
                  <tr className="report-view-empty-row">
                    <td colSpan={8}>No records match the selected filters.</td>
                  </tr>
                ) : (
                  manifestRenderRows.map((entry) => {
                    if (entry.kind === "status") {
                      return (
                        <tr
                          className={`report-manifest-status-row ${
                            entry.statusType === "open"
                              ? "report-manifest-status-row-open"
                              : "report-manifest-status-row-closed"
                          }`}
                          key={entry.key}
                        >
                          <td colSpan={8}>{entry.label}</td>
                        </tr>
                      );
                    }

                    if (entry.kind === "group") {
                      const groupClass =
                        entry.groupType === "workflow"
                          ? workflowBandClass(entry.workflowType)
                          : entry.groupType === "task"
                            ? taskBandClass(entry.workflowType)
                            : entry.label === PRIMARY_CLOSE_REASON
                              ? "report-manifest-group-row-closed-reason report-manifest-group-row-closed-reason-purchased"
                              : "report-manifest-group-row-closed-reason";
                      return (
                        <tr className={`report-manifest-group-row ${groupClass}`} key={entry.key}>
                          <td colSpan={8}>{entry.label}</td>
                        </tr>
                      );
                    }

                    const row = entry.row;

                    return (
                      <tr className="report-manifest-request-row" key={entry.key}>
                        <td>
                          <div className="report-manifest-id-status">
                            <strong>#{row.request_id}</strong>
                          </div>
                        </td>
                        <td>{row.primary_passenger}</td>
                        <td>{row.destination}</td>
                        <td>{row.cruise_line}</td>
                        <td>{row.sailing_month_year}</td>
                        <td className="report-cell-numeric">{formatMoney(row.estimated_gross_booking_total)}</td>
                        <td className="report-cell-numeric">{formatMoney(row.projected_commission_target)}</td>
                        <td>
                          <div className="report-manifest-owner-agent">
                            <span className="report-manifest-owner-agent-name">{row.owner_agent}</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="report-view-table-wrap">
            <table className="report-view-table report-ledger-table">
              <thead>
                <tr>
                  <th scope="col">Cruise Line Brand</th>
                  <th scope="col" className="report-cell-numeric">
                    Active Booking Count
                  </th>
                  <th scope="col" className="report-ledger-metric-header">
                    Total Volume ($)
                  </th>
                  <th scope="col" className="report-ledger-metric-header">
                    Total Commission Booked ($)
                  </th>
                  <th scope="col" className="report-ledger-metric-header">
                    Median Price Per Room Booked ($)
                  </th>
                  <th scope="col" className="report-ledger-metric-header">
                    Average Commission Rate (%)
                  </th>
                </tr>
              </thead>
              <tbody>
                {supplierRows.length === 0 ? (
                  <tr className="report-view-empty-row">
                    <td colSpan={6}>No records match the selected filters.</td>
                  </tr>
                ) : (
                  supplierRows.map((row) => (
                    <tr key={row.cruise_line}>
                      <td>
                        <strong className="report-ledger-brand">{row.cruise_line}</strong>
                      </td>
                      <td className="report-cell-numeric">{row.active_booking_count}</td>
                      <td className="report-ledger-metric-cell">{formatMoney(row.total_volume)}</td>
                      <td className="report-ledger-metric-cell">{formatMoney(row.total_commission_booked)}</td>
                      <td className="report-ledger-metric-cell">{formatMoney(row.median_price_per_room)}</td>
                      <td className="report-ledger-metric-cell">
                        {row.average_commission_rate_percent.toFixed(1)}%
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
