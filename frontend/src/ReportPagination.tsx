import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, type PageSizeOption } from "./pagination";

type ReportPaginationProps = {
  page: number;
  total: number;
  totalPages: number;
  pageSize: number;
  loading?: boolean;
  summaryLabel?: string;
  className?: string;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (pageSize: PageSizeOption) => void;
};

export default function ReportPagination({
  page,
  total,
  totalPages,
  pageSize,
  loading = false,
  summaryLabel = "records",
  className = "",
  onPageChange,
  onPageSizeChange,
}: ReportPaginationProps) {
  const pageStart = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const pageEnd = total === 0 ? 0 : Math.min(page * pageSize, total);

  return (
    <div className={`table-pagination${className ? ` ${className}` : ""}`}>
      <p className="table-pagination-summary">
        Showing {pageStart}-{pageEnd} of {total} {summaryLabel}
      </p>
      <div className="table-pagination-controls">
        {onPageSizeChange ? (
          <label className="table-pagination-page-size">
            Rows per page
            <select
              value={pageSize}
              disabled={loading}
              onChange={(event) => onPageSizeChange(Number(event.target.value) as PageSizeOption)}
            >
              {PAGE_SIZE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <button
          type="button"
          className="secondary-button"
          disabled={page <= 1 || loading}
          onClick={() => onPageChange(Math.max(1, page - 1))}
        >
          Previous
        </button>
        <span className="table-pagination-status">
          Page {totalPages === 0 ? 0 : page} of {totalPages}
        </span>
        <button
          type="button"
          className="secondary-button"
          disabled={page >= totalPages || totalPages === 0 || loading}
          onClick={() => onPageChange(page + 1)}
        >
          Next
        </button>
      </div>
    </div>
  );
}

export { DEFAULT_PAGE_SIZE };
