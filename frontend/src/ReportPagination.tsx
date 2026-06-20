type ReportPaginationProps = {
  page: number;
  total: number;
  totalPages: number;
  pageSize: number;
  loading?: boolean;
  onPageChange: (page: number) => void;
};

export default function ReportPagination({
  page,
  total,
  totalPages,
  pageSize,
  loading = false,
  onPageChange,
}: ReportPaginationProps) {
  const pageStart = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const pageEnd = total === 0 ? 0 : Math.min(page * pageSize, total);

  return (
    <div className="table-pagination report-table-pagination">
      <p className="table-pagination-summary">
        Showing {pageStart}-{pageEnd} of {total} records
      </p>
      <div className="table-pagination-controls">
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
