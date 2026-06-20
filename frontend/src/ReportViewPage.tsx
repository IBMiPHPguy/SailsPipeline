import DiagnosticReportView from "./DiagnosticReportView";
import FinancialReportView from "./FinancialReportView";
import { getReportById, type ReportId } from "./reportsCatalog";

type ReportViewPageProps = {
  reportId: ReportId;
  onBack: () => void;
};

const INTERACTIVE_FINANCIAL_REPORTS = new Set<ReportId>([
  "sales-volume-target-manifest",
  "supplier-share-volume-ledger",
]);

const INTERACTIVE_DIAGNOSTIC_REPORTS = new Set<ReportId>([
  "funnel-leak-lost-business",
  "advisor-productivity-quota",
  "passenger-demographics-qualifier",
]);

export default function ReportViewPage({ reportId, onBack }: ReportViewPageProps) {
  const report = getReportById(reportId);

  if (!report) {
    return (
      <section className="card report-view-page">
        <p>Report not found.</p>
        <button type="button" className="secondary-button" onClick={onBack}>
          Back to Reports
        </button>
      </section>
    );
  }

  if (INTERACTIVE_FINANCIAL_REPORTS.has(reportId)) {
    return (
      <FinancialReportView
        reportId={reportId as "sales-volume-target-manifest" | "supplier-share-volume-ledger"}
        onBack={onBack}
      />
    );
  }

  if (INTERACTIVE_DIAGNOSTIC_REPORTS.has(reportId)) {
    return (
      <DiagnosticReportView
        reportId={
          reportId as
            | "funnel-leak-lost-business"
            | "advisor-productivity-quota"
            | "passenger-demographics-qualifier"
        }
        onBack={onBack}
      />
    );
  }

  return (
    <section className="report-view-page">
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

      <section className="card report-view-table-card">
        <div className="report-view-table-wrap">
          <table className="report-view-table">
            <thead>
              <tr>
                {report.columns.map((column) => (
                  <th key={column} scope="col">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr className="report-view-empty-row">
                <td colSpan={report.columns.length}>
                  Report data will populate here once this ledger is connected to the reporting service.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
