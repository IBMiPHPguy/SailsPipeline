import ExcelJS from "exceljs";
import {
  ADVISOR_SCORECARD_BODY_STYLE,
  ADVISOR_SCORECARD_CLOSE_RATIO_HEADER_STYLE,
  ADVISOR_SCORECARD_HEADER_STYLE,
} from "./advisorScorecardReportStyles";
import { downloadWorkbookBuffer } from "./reportExport";
import type { AdvisorScorecardRow } from "./types";

export const ADVISOR_SCORECARD_EXPORT_HEADERS = [
  "ADVISOR NAME",
  "ACTIVE LEAD COUNT",
  "PROPOSALS PENDING",
  "COMPLETED BOOKINGS",
  "AVG PIPELINE VELOCITY (DAYS)",
  "REQUEST-TO-CLOSE (DEPOSITED) RATIO (%)",
] as const;

const COLUMN_WIDTHS = [22, 16, 18, 18, 24, 28];
const COLUMN_COUNT = ADVISOR_SCORECARD_EXPORT_HEADERS.length;
const NUMERIC_COLUMNS = new Set([2, 3, 4, 5, 6]);
const CLOSE_RATIO_COLUMN = 6;

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

function formatVelocityDays(value: number | null): string {
  if (value === null) {
    return "—";
  }

  return value.toFixed(1);
}

function formatRatioPercent(value: number | null): string {
  if (value === null) {
    return "—";
  }

  return `${value.toFixed(1)}%`;
}

export function buildAdvisorScorecardExportRows(rows: AdvisorScorecardRow[]): string[][] {
  if (rows.length === 0) {
    return [EMPTY_ROW];
  }

  return rows.map((row) => [
    row.advisor_name,
    String(row.active_lead_count),
    String(row.proposals_pending),
    String(row.completed_bookings),
    formatVelocityDays(row.avg_pipeline_velocity_days),
    formatRatioPercent(row.request_to_close_ratio_percent),
  ]);
}

function headerStyleForColumn(column: number) {
  return column === CLOSE_RATIO_COLUMN
    ? ADVISOR_SCORECARD_CLOSE_RATIO_HEADER_STYLE
    : ADVISOR_SCORECARD_HEADER_STYLE;
}

function applyHeaderRow(headerRow: ExcelJS.Row): void {
  headerRow.height = 22;

  for (let column = 1; column <= COLUMN_COUNT; column += 1) {
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
      horizontal: NUMERIC_COLUMNS.has(column) ? "right" : "left",
      wrapText: true,
    };
    cell.border = {
      bottom: buildBorder(
        style.bottomBorder,
        column === CLOSE_RATIO_COLUMN ? "medium" : "thin",
      ),
      ...(column < COLUMN_COUNT ? { right: buildBorder(ADVISOR_SCORECARD_BODY_STYLE.border) } : {}),
    };
  }
}

function applyBodyRow(row: ExcelJS.Row, isEmptyState: boolean): void {
  row.height = 18;

  for (let column = 1; column <= COLUMN_COUNT; column += 1) {
    const cell = row.getCell(column);
    const isNameColumn = column === 1;
    const isCloseRatioColumn = column === CLOSE_RATIO_COLUMN;
    const isNumericColumn = NUMERIC_COLUMNS.has(column);

    cell.fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: argb(ADVISOR_SCORECARD_BODY_STYLE.fill) },
    };
    cell.font = {
      bold: isEmptyState ? false : isNameColumn || isNumericColumn,
      color: {
        argb: argb(
          isEmptyState
            ? ADVISOR_SCORECARD_BODY_STYLE.emptyFontColor
            : isCloseRatioColumn
              ? ADVISOR_SCORECARD_BODY_STYLE.closeRatioFontColor
              : isNameColumn
                ? ADVISOR_SCORECARD_BODY_STYLE.nameFontColor
                : ADVISOR_SCORECARD_BODY_STYLE.numericFontColor,
        ),
      },
      size: 11,
    };
    cell.alignment = {
      vertical: "middle",
      horizontal: isEmptyState && column === 1 ? "center" : isNumericColumn ? "right" : "left",
      wrapText: true,
    };
    cell.border = {
      bottom: buildBorder(ADVISOR_SCORECARD_BODY_STYLE.border),
      ...(column < COLUMN_COUNT ? { right: buildBorder(ADVISOR_SCORECARD_BODY_STYLE.border) } : {}),
    };

    if (isCloseRatioColumn && !isEmptyState) {
      cell.font = {
        bold: true,
        color: { argb: argb(ADVISOR_SCORECARD_BODY_STYLE.closeRatioFontColor) },
        size: 11,
      };
    }
  }

  if (isEmptyState) {
    row.worksheet.mergeCells(row.number, 1, row.number, COLUMN_COUNT);
  }
}

export async function downloadAdvisorScorecardXlsx(
  filename: string,
  rows: AdvisorScorecardRow[],
): Promise<void> {
  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet("Advisor Scorecard");
  const exportRows = buildAdvisorScorecardExportRows(rows);

  COLUMN_WIDTHS.forEach((width, index) => {
    worksheet.getColumn(index + 1).width = width;
  });

  applyHeaderRow(worksheet.addRow([...ADVISOR_SCORECARD_EXPORT_HEADERS]));

  exportRows.forEach((values) => {
    const row = worksheet.addRow(values);
    applyBodyRow(row, rows.length === 0);
  });

  worksheet.views = [{ state: "frozen", ySplit: 1, activeCell: "A2" }];
  await downloadWorkbookBuffer(workbook, filename);
}
