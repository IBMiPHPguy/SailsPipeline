import { REPORT_CATEGORIES, getReportsByCategory, type ReportId } from "./reportsCatalog";
import { REPORT_CATEGORY_ICONS } from "./SidebarNavIcons";

type ReportsPageProps = {
  onViewReport: (reportId: ReportId) => void;
};

export default function ReportsPage({ onViewReport }: ReportsPageProps) {
  return (
    <section className="reports-page">
      <header className="request-summary-card request-summary-card-compact reports-summary-card">
        <div className="request-summary-compact-row">
          <div className="request-summary-compact-title">
            <h2>Reports</h2>
          </div>
        </div>
        <div className="request-summary-compact-meta">
          <span>
            A curated library of canned operational ledgers, performance insights, and sales volume
            statistics.
          </span>
        </div>
      </header>

      <div className="reports-catalog-grid">
        {REPORT_CATEGORIES.map((category) => {
          const reports = getReportsByCategory(category.id);
          const CategoryIcon = REPORT_CATEGORY_ICONS[category.id];

          return (
            <section className="card reports-category-card" key={category.id}>
              <h3 className="reports-category-title">
                <CategoryIcon />
                <span>{category.title}</span>
              </h3>
              <ul className="reports-catalog-list">
                {reports.map((report) => (
                  <li className="reports-catalog-row" key={report.id}>
                    <div className="reports-catalog-copy">
                      <strong className="reports-catalog-title">{report.title}</strong>
                      <p className="reports-catalog-description">{report.description}</p>
                    </div>
                    <button type="button" className="reports-view-button" onClick={() => onViewReport(report.id)}>
                      View Report
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
      </div>
    </section>
  );
}
