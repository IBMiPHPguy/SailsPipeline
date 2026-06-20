import ExcelJS from "exceljs";
import {
  MANIFEST_EXPORT_HEADERS,
  type ManifestExportRow,
} from "./manifestReportLayout";
import {
  MANIFEST_HEADER_STYLE,
  MANIFEST_ROW_STYLES,
} from "./manifestReportStyles";
import { downloadWorkbookBuffer } from "./reportExport";

const MANIFEST_COLUMN_WIDTHS = [24, 22, 18, 22, 16, 20, 22, 18];
const MANIFEST_NUMERIC_COLUMNS = new Set([6, 7]);

function argb(color: string): string {
  return color.startsWith("FF") ? color : `FF${color}`;
}

function buildBorder(color?: string, style: ExcelJS.BorderStyle = "thin"): Partial<ExcelJS.Border> | undefined {
  if (!color) {
    return undefined;
  }

  return { style, color: { argb: argb(color) } };
}

function applyBorders(
  cell: ExcelJS.Cell,
  config: {
    leftBorder?: string;
    topBorder?: string;
    bottomBorder?: string;
  },
  column: number,
  columnCount: number,
  includeRightBorder = true,
): void {
  cell.border = {
    left: buildBorder(config.leftBorder, "medium"),
    top: buildBorder(config.topBorder),
    bottom: buildBorder(config.bottomBorder),
    ...(includeRightBorder && column < columnCount
      ? { right: buildBorder(MANIFEST_HEADER_STYLE.bottomBorder, "thin") }
      : {}),
  };
}

function applyHeaderRow(row: ExcelJS.Row, columnCount: number): void {
  row.height = 22;

  for (let column = 1; column <= columnCount; column += 1) {
    const cell = row.getCell(column);
    cell.fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: argb(MANIFEST_HEADER_STYLE.fill) },
    };
    cell.font = {
      bold: true,
      color: { argb: argb(MANIFEST_HEADER_STYLE.fontColor) },
      size: 11,
    };
    cell.alignment = {
      vertical: "middle",
      horizontal: column >= 6 ? "right" : "left",
      wrapText: true,
    };
    cell.border = {
      bottom: buildBorder(MANIFEST_HEADER_STYLE.bottomBorder, "medium"),
    };
  }
}

function applyManifestBodyRow(
  worksheet: ExcelJS.Worksheet,
  row: ExcelJS.Row,
  entry: ManifestExportRow,
  columnCount: number,
): void {
  const style = MANIFEST_ROW_STYLES[entry.style];
  row.height = entry.merge ? 20 : 18;

  if (entry.merge) {
    worksheet.mergeCells(row.number, 1, row.number, columnCount);
  }

  for (let column = 1; column <= columnCount; column += 1) {
    const cell = row.getCell(column);
    const isPrimaryCell = column === 1 || !entry.merge;

    cell.fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: argb(style.fill) },
    };
    cell.font = {
      bold: style.bold ?? false,
      color: { argb: argb(style.fontColor) },
      size: entry.style.startsWith("status-") ? 10 : 11,
    };
    cell.alignment = {
      vertical: "middle",
      horizontal:
        !entry.merge && MANIFEST_NUMERIC_COLUMNS.has(column)
          ? "right"
          : column === 1 && entry.style === "request"
            ? "left"
            : "left",
      wrapText: true,
      indent: entry.style.startsWith("task-") && column === 1 ? 1 : 0,
    };

    if (isPrimaryCell) {
      applyBorders(cell, style, column, columnCount, !entry.merge);
    } else if (entry.merge) {
      cell.border = {
        top: buildBorder(style.topBorder),
        bottom: buildBorder(style.bottomBorder),
      };
    } else {
      applyBorders(cell, style, column, columnCount);
    }

    if (entry.style === "request" && column === 1) {
      cell.font = {
        ...cell.font,
        bold: true,
        color: { argb: argb("102A43") },
      };
    }

    if (entry.style === "request" && MANIFEST_NUMERIC_COLUMNS.has(column)) {
      cell.font = {
        ...cell.font,
        bold: true,
        color: { argb: argb("102A43") },
      };
    }
  }
}

export async function downloadManifestXlsx(
  filename: string,
  sheetName: string,
  rows: ManifestExportRow[],
): Promise<void> {
  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet(sheetName.slice(0, 31));
  const columnCount = MANIFEST_EXPORT_HEADERS.length;

  MANIFEST_EXPORT_HEADERS.forEach((header, index) => {
    worksheet.getColumn(index + 1).width = MANIFEST_COLUMN_WIDTHS[index] ?? 16;
  });

  applyHeaderRow(worksheet.addRow([...MANIFEST_EXPORT_HEADERS]), columnCount);

  rows.forEach((entry) => {
    const displayCells =
      entry.style === "status-open" || entry.style === "status-closed"
        ? [entry.cells[0]?.toUpperCase() ?? "", ...entry.cells.slice(1)]
        : entry.cells;
    const row = worksheet.addRow(displayCells);
    applyManifestBodyRow(worksheet, row, entry, columnCount);
  });

  worksheet.views = [{ state: "frozen", ySplit: 1, activeCell: "A2" }];

  await downloadWorkbookBuffer(workbook, filename);
}
