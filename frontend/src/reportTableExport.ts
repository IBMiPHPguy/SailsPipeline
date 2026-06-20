import ExcelJS from "exceljs";
import { downloadWorkbookBuffer } from "./reportExport";

export type ReportTableHeaderStyle = {
  label: string;
  fill?: string;
  fontColor?: string;
  bottomBorder?: string;
  bottomStyle?: ExcelJS.BorderStyle;
  align?: "left" | "right" | "center";
};

export type ReportTableExportOptions = {
  sheetName: string;
  headers: ReportTableHeaderStyle[];
  rows: string[][];
  columnWidths?: number[];
  numericColumns?: number[];
  emphasisColumns?: number[];
};

function argb(color: string): string {
  return color.startsWith("FF") ? color : `FF${color}`;
}

function buildBorder(color?: string, style: ExcelJS.BorderStyle = "thin"): Partial<ExcelJS.Border> | undefined {
  if (!color) {
    return undefined;
  }

  return { style, color: { argb: argb(color) } };
}

export async function downloadReportTableXlsx(filename: string, options: ReportTableExportOptions): Promise<void> {
  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet(options.sheetName.slice(0, 31));
  const columnCount = options.headers.length;
  const numericColumns = new Set(options.numericColumns ?? []);
  const emphasisColumns = new Set(options.emphasisColumns ?? []);

  options.headers.forEach((_, index) => {
    worksheet.getColumn(index + 1).width = options.columnWidths?.[index] ?? (index === 0 ? 24 : 18);
  });

  const headerRow = worksheet.addRow(options.headers.map((header) => header.label));
  headerRow.height = 22;

  options.headers.forEach((header, index) => {
    const cell = headerRow.getCell(index + 1);
    cell.fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: argb(header.fill ?? "F8FAFC") },
    };
    cell.font = {
      bold: true,
      color: { argb: argb(header.fontColor ?? "486581") },
      size: 11,
    };
    cell.alignment = {
      vertical: "middle",
      horizontal: header.align ?? (numericColumns.has(index + 1) ? "right" : "left"),
      wrapText: true,
    };
    cell.border = {
      bottom: buildBorder(header.bottomBorder ?? "E2E8F0", header.bottomStyle ?? "thin"),
      ...(index + 1 < columnCount ? { right: buildBorder("E2E8F0") } : {}),
    };
  });

  options.rows.forEach((values) => {
    const row = worksheet.addRow(values);
    row.height = 18;

    for (let column = 1; column <= columnCount; column += 1) {
      const cell = row.getCell(column);
      const emphasized = emphasisColumns.has(column);

      cell.fill = {
        type: "pattern",
        pattern: "solid",
        fgColor: { argb: argb("FFFFFF") },
      };
      cell.font = {
        bold: column === 1 || emphasized,
        color: { argb: argb(emphasized ? "0B7285" : column === 1 ? "243B53" : "102A43") },
        size: 11,
      };
      cell.alignment = {
        vertical: "middle",
        horizontal: numericColumns.has(column) || emphasized ? "right" : "left",
        wrapText: true,
      };
      cell.border = {
        bottom: buildBorder("E2E8F0"),
        ...(column < columnCount ? { right: buildBorder("E2E8F0") } : {}),
      };
    }
  });

  worksheet.views = [{ state: "frozen", ySplit: 1, activeCell: "A2" }];
  await downloadWorkbookBuffer(workbook, filename);
}
