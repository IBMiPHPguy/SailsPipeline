import ExcelJS from "exceljs";
import { formatMoney } from "./cabinPricing";
import {
  FUNNEL_LEAK_BODY_STYLE,
  FUNNEL_LEAK_HEADER_STYLE,
  FUNNEL_LEAK_VALUE_LOST_COLUMN,
} from "./funnelLeakReportStyles";
import { downloadWorkbookBuffer } from "./reportExport";
import type { FunnelLeakRow } from "./types";

export const FUNNEL_LEAK_EXPORT_HEADERS = [
  "REQUEST ID",
  "CLIENT NAME",
  "QUOTED CRUISE LINE",
  "QUOTED DESTINATION",
  "EST. VALUE LOST",
  "PRIMARY REJECTION REASON",
] as const;

const COLUMN_WIDTHS = [12, 22, 24, 22, 16, 28];
const COLUMN_COUNT = FUNNEL_LEAK_EXPORT_HEADERS.length;
const RIGHT_ALIGNED_COLUMNS = new Set([FUNNEL_LEAK_VALUE_LOST_COLUMN]);

const EMPTY_ROW = [
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

export function buildFunnelLeakExportRows(rows: FunnelLeakRow[]): string[][] {
  if (rows.length === 0) {
    return [EMPTY_ROW];
  }

  return rows.map((row) => [
    `#${row.request_id}`,
    row.client_name,
    row.quoted_cruise_line,
    row.quoted_destination,
    formatMoney(row.estimated_value_lost),
    row.primary_rejection_reason,
  ]);
}

function applyHeaderRow(headerRow: ExcelJS.Row): void {
  headerRow.height = 22;

  for (let column = 1; column <= COLUMN_COUNT; column += 1) {
    const cell = headerRow.getCell(column);

    cell.fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: argb(FUNNEL_LEAK_HEADER_STYLE.fill) },
    };
    cell.font = {
      bold: true,
      color: { argb: argb(FUNNEL_LEAK_HEADER_STYLE.fontColor) },
      size: 11,
    };
    cell.alignment = {
      vertical: "middle",
      horizontal: RIGHT_ALIGNED_COLUMNS.has(column) ? "right" : "left",
      wrapText: true,
    };
    cell.border = {
      bottom: buildBorder(FUNNEL_LEAK_HEADER_STYLE.bottomBorder),
      ...(column < COLUMN_COUNT ? { right: buildBorder(FUNNEL_LEAK_BODY_STYLE.border) } : {}),
    };
  }
}

function applyBodyRow(row: ExcelJS.Row, isEmptyState: boolean): void {
  row.height = 18;

  for (let column = 1; column <= COLUMN_COUNT; column += 1) {
    const cell = row.getCell(column);
    const isRequestIdColumn = column === 1;
    const isValueLostColumn = column === FUNNEL_LEAK_VALUE_LOST_COLUMN;
    const isRightAligned = RIGHT_ALIGNED_COLUMNS.has(column);

    cell.fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: argb(FUNNEL_LEAK_BODY_STYLE.fill) },
    };
    cell.font = {
      bold: !isEmptyState && (isRequestIdColumn || isValueLostColumn),
      color: {
        argb: argb(
          isEmptyState
            ? FUNNEL_LEAK_BODY_STYLE.emptyFontColor
            : isValueLostColumn
              ? FUNNEL_LEAK_BODY_STYLE.valueLostFontColor
              : isRequestIdColumn
                ? FUNNEL_LEAK_BODY_STYLE.requestIdFontColor
                : FUNNEL_LEAK_BODY_STYLE.textFontColor,
        ),
      },
      size: 11,
    };
    cell.alignment = {
      vertical: "middle",
      horizontal: isEmptyState && column === 1 ? "center" : isRightAligned ? "right" : "left",
      wrapText: true,
    };
    cell.border = {
      bottom: buildBorder(FUNNEL_LEAK_BODY_STYLE.border),
      ...(column < COLUMN_COUNT ? { right: buildBorder(FUNNEL_LEAK_BODY_STYLE.border) } : {}),
    };
  }

  if (isEmptyState) {
    row.worksheet.mergeCells(row.number, 1, row.number, COLUMN_COUNT);
  }
}

export async function downloadFunnelLeakXlsx(filename: string, rows: FunnelLeakRow[]): Promise<void> {
  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet("Funnel Leak");
  const exportRows = buildFunnelLeakExportRows(rows);

  COLUMN_WIDTHS.forEach((width, index) => {
    worksheet.getColumn(index + 1).width = width;
  });

  applyHeaderRow(worksheet.addRow([...FUNNEL_LEAK_EXPORT_HEADERS]));

  exportRows.forEach((values) => {
    const row = worksheet.addRow(values);
    applyBodyRow(row, rows.length === 0);
  });

  worksheet.views = [{ state: "frozen", ySplit: 1, activeCell: "A2" }];
  await downloadWorkbookBuffer(workbook, filename);
}
