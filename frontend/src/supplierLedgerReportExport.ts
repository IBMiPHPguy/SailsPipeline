import ExcelJS from "exceljs";
import { formatMoney } from "./cabinPricing";
import { downloadWorkbookBuffer } from "./reportExport";
import type { ReportSupplierLedgerRow } from "./types";

export const SUPPLIER_LEDGER_EXPORT_HEADERS = [
  "CRUISE LINE BRAND",
  "ACTIVE BOOKING COUNT",
  "TOTAL VOLUME ($)",
  "TOTAL COMMISSION BOOKED ($)",
  "MEDIAN PRICE PER ROOM BOOKED ($)",
  "AVERAGE COMMISSION RATE (%)",
] as const;

const SUPPLIER_LEDGER_COLUMN_WIDTHS = [28, 18, 18, 22, 24, 22];
const SUPPLIER_LEDGER_NUMERIC_COLUMNS = new Set([2, 3, 4, 5, 6]);
const SUPPLIER_LEDGER_METRIC_COLUMNS = new Set([3, 4, 5, 6]);

const DEFAULT_HEADER_STYLE = {
  fill: "F8FAFC",
  fontColor: "486581",
  bottomBorder: "E2E8F0",
  bottomStyle: "thin" as ExcelJS.BorderStyle,
};

const METRIC_HEADER_STYLE = {
  fill: "F1FDFF",
  fontColor: "0B7285",
  bottomBorder: "99E9F2",
  bottomStyle: "medium" as ExcelJS.BorderStyle,
};

const SUPPLIER_LEDGER_EMPTY_ROW = [
  "No records match the selected filters.",
  "",
  "",
  "",
  "",
  "",
];

function argb(color: string): string {
  return color.startsWith("FF") ? color : `FF${color}`;
}

function buildBorder(color?: string, style: ExcelJS.BorderStyle = "thin"): Partial<ExcelJS.Border> | undefined {
  if (!color) {
    return undefined;
  }

  return { style, color: { argb: argb(color) } };
}

function headerStyleForColumn(column: number) {
  return SUPPLIER_LEDGER_METRIC_COLUMNS.has(column) ? METRIC_HEADER_STYLE : DEFAULT_HEADER_STYLE;
}

export function buildSupplierLedgerExportRows(rows: ReportSupplierLedgerRow[]): string[][] {
  if (rows.length === 0) {
    return [SUPPLIER_LEDGER_EMPTY_ROW];
  }

  return rows.map((row) => [
    row.cruise_line,
    String(row.active_booking_count),
    formatMoney(row.total_volume),
    formatMoney(row.total_commission_booked),
    formatMoney(row.median_price_per_room),
    `${row.average_commission_rate_percent.toFixed(1)}%`,
  ]);
}

function applyHeaderRow(headerRow: ExcelJS.Row, columnCount: number): void {
  headerRow.height = 22;

  for (let column = 1; column <= columnCount; column += 1) {
    const cell = headerRow.getCell(column);
    const style = headerStyleForColumn(column);

    cell.fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: argb(style.fill) },
    };
    cell.font = {
      bold: true,
      color: { argb: argb(style.fontColor) },
      size: 11,
    };
    cell.alignment = {
      vertical: "middle",
      horizontal: SUPPLIER_LEDGER_NUMERIC_COLUMNS.has(column) ? "right" : "left",
      wrapText: true,
    };
    cell.border = {
      bottom: buildBorder(style.bottomBorder, style.bottomStyle),
      ...(column < columnCount ? { right: buildBorder("E2E8F0") } : {}),
    };
  }
}

function applyBodyRow(row: ExcelJS.Row, columnCount: number): void {
  row.height = 18;

  for (let column = 1; column <= columnCount; column += 1) {
    const cell = row.getCell(column);
    const isMetric = SUPPLIER_LEDGER_METRIC_COLUMNS.has(column);
    const isBrand = column === 1;

    cell.fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: argb("FFFFFF") },
    };
    cell.font = {
      bold: isBrand || SUPPLIER_LEDGER_NUMERIC_COLUMNS.has(column),
      color: { argb: argb(isBrand ? "243B53" : "102A43") },
      size: 11,
    };
    cell.alignment = {
      vertical: "middle",
      horizontal: SUPPLIER_LEDGER_NUMERIC_COLUMNS.has(column) ? "right" : "left",
      wrapText: true,
    };
    cell.border = {
      bottom: buildBorder("E2E8F0"),
      ...(column < columnCount ? { right: buildBorder("E2E8F0") } : {}),
    };

    if (isMetric) {
      cell.font = {
        ...cell.font,
        bold: true,
        color: { argb: argb("102A43") },
      };
    }
  }
}

export async function downloadSupplierLedgerXlsx(
  filename: string,
  rows: ReportSupplierLedgerRow[],
): Promise<void> {
  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet("Supplier Ledger");
  const columnCount = SUPPLIER_LEDGER_EXPORT_HEADERS.length;
  const exportRows = buildSupplierLedgerExportRows(rows);

  SUPPLIER_LEDGER_EXPORT_HEADERS.forEach((_, index) => {
    worksheet.getColumn(index + 1).width = SUPPLIER_LEDGER_COLUMN_WIDTHS[index] ?? 18;
  });

  applyHeaderRow(worksheet.addRow([...SUPPLIER_LEDGER_EXPORT_HEADERS]), columnCount);

  exportRows.forEach((values) => {
    const row = worksheet.addRow(values);
    applyBodyRow(row, columnCount);
  });

  worksheet.views = [{ state: "frozen", ySplit: 1, activeCell: "A2" }];

  await downloadWorkbookBuffer(workbook, filename);
}
