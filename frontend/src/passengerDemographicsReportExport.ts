import ExcelJS from "exceljs";
import { formatDisplayPhone } from "./passengerDisplay";
import {
  PASSENGER_DEMOGRAPHICS_BODY_STYLE,
  PASSENGER_DEMOGRAPHICS_HEADER_STYLE,
  PASSENGER_QUALIFIER_EXPORT_DEFAULT_STYLE,
  PASSENGER_QUALIFIER_EXPORT_STYLES,
} from "./passengerDemographicsReportStyles";
import { downloadWorkbookBuffer } from "./reportExport";
import type { PassengerDemographicsRow } from "./types";
import { formatDate } from "./utils";

export const PASSENGER_DEMOGRAPHICS_EXPORT_HEADERS = [
  "PASSENGER NAME",
  "DATE OF BIRTH",
  "STATE",
  "CONTACT PHONE",
  "EMAIL ADDRESS",
  "ACTIVE QUALIFIER BADGES",
] as const;

const COLUMN_WIDTHS = [22, 14, 8, 16, 32, 28];
const COLUMN_COUNT = PASSENGER_DEMOGRAPHICS_EXPORT_HEADERS.length;

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

function formatExportPhone(phone: string | null | undefined): string {
  return formatDisplayPhone(phone) ?? "—";
}

function buildQualifierRichText(qualifiers: string[]): ExcelJS.CellRichTextValue {
  if (qualifiers.length === 0) {
    return {
      richText: [
        {
          text: "—",
          font: {
            color: { argb: argb(PASSENGER_DEMOGRAPHICS_BODY_STYLE.emptyFontColor) },
            size: 11,
          },
        },
      ],
    };
  }

  const richText: ExcelJS.RichText[] = [];

  qualifiers.forEach((qualifier, index) => {
    if (index > 0) {
      richText.push({
        text: ", ",
        font: {
          color: { argb: argb(PASSENGER_DEMOGRAPHICS_BODY_STYLE.textFontColor) },
          size: 11,
        },
      });
    }

    const style = PASSENGER_QUALIFIER_EXPORT_STYLES[qualifier] ?? PASSENGER_QUALIFIER_EXPORT_DEFAULT_STYLE;
    richText.push({
      text: qualifier,
      font: {
        bold: true,
        color: { argb: argb(style.fontColor) },
        size: 10,
      },
    });
  });

  return { richText };
}

export function buildPassengerDemographicsExportValues(
  rows: PassengerDemographicsRow[],
): Array<[string, string, string, string, string, string]> {
  if (rows.length === 0) {
    return [EMPTY_ROW as [string, string, string, string, string, string]];
  }

  return rows.map((row) => [
    row.passenger_name,
    row.date_of_birth ? formatDate(row.date_of_birth) : "—",
    row.state_of_residence ?? "—",
    formatExportPhone(row.contact_phone),
    row.email_address ?? "—",
    "",
  ]);
}

function applyHeaderRow(headerRow: ExcelJS.Row): void {
  headerRow.height = 22;

  for (let column = 1; column <= COLUMN_COUNT; column += 1) {
    const cell = headerRow.getCell(column);

    cell.fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: argb(PASSENGER_DEMOGRAPHICS_HEADER_STYLE.fill) },
    };
    cell.font = {
      bold: true,
      color: { argb: argb(PASSENGER_DEMOGRAPHICS_HEADER_STYLE.fontColor) },
      size: 11,
    };
    cell.alignment = {
      vertical: "middle",
      horizontal: "left",
      wrapText: true,
    };
    cell.border = {
      bottom: buildBorder(PASSENGER_DEMOGRAPHICS_HEADER_STYLE.bottomBorder),
      ...(column < COLUMN_COUNT ? { right: buildBorder(PASSENGER_DEMOGRAPHICS_BODY_STYLE.border) } : {}),
    };
  }
}

function applyBodyRow(row: ExcelJS.Row, sourceRow: PassengerDemographicsRow | null, isEmptyState: boolean): void {
  row.height = 18;

  for (let column = 1; column <= COLUMN_COUNT; column += 1) {
    const cell = row.getCell(column);
    const isNameColumn = column === 1;
    const isQualifierColumn = column === COLUMN_COUNT;

    cell.fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: argb(PASSENGER_DEMOGRAPHICS_BODY_STYLE.fill) },
    };
    cell.font = {
      bold: isNameColumn && !isEmptyState,
      color: {
        argb: argb(
          isEmptyState
            ? PASSENGER_DEMOGRAPHICS_BODY_STYLE.emptyFontColor
            : isNameColumn
              ? PASSENGER_DEMOGRAPHICS_BODY_STYLE.nameFontColor
              : PASSENGER_DEMOGRAPHICS_BODY_STYLE.textFontColor,
        ),
      },
      size: isEmptyState ? 11 : 11,
    };
    cell.alignment = {
      vertical: "middle",
      horizontal: isEmptyState && column === 1 ? "center" : "left",
      wrapText: true,
    };
    cell.border = {
      bottom: buildBorder(PASSENGER_DEMOGRAPHICS_BODY_STYLE.border),
      ...(column < COLUMN_COUNT ? { right: buildBorder(PASSENGER_DEMOGRAPHICS_BODY_STYLE.border) } : {}),
    };

    if (isQualifierColumn && sourceRow) {
      cell.value = buildQualifierRichText(sourceRow.qualifiers);
    }
  }

  if (isEmptyState) {
    row.getCell(1).alignment = { vertical: "middle", horizontal: "center", wrapText: true };
    worksheetMergeEmptyRow(row);
  }
}

function worksheetMergeEmptyRow(row: ExcelJS.Row): void {
  const worksheet = row.worksheet;
  worksheet.mergeCells(row.number, 1, row.number, COLUMN_COUNT);
}

export async function downloadPassengerDemographicsXlsx(
  filename: string,
  rows: PassengerDemographicsRow[],
): Promise<void> {
  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet("Passenger Demographics");

  COLUMN_WIDTHS.forEach((width, index) => {
    worksheet.getColumn(index + 1).width = width;
  });

  applyHeaderRow(worksheet.addRow([...PASSENGER_DEMOGRAPHICS_EXPORT_HEADERS]));

  if (rows.length === 0) {
    const emptyRow = worksheet.addRow(EMPTY_ROW);
    applyBodyRow(emptyRow, null, true);
  } else {
    rows.forEach((sourceRow) => {
      const values = buildPassengerDemographicsExportValues([sourceRow])[0];
      const row = worksheet.addRow(values);
      applyBodyRow(row, sourceRow, false);
    });
  }

  worksheet.views = [{ state: "frozen", ySplit: 1, activeCell: "A2" }];
  await downloadWorkbookBuffer(workbook, filename);
}
