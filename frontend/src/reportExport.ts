import ExcelJS from "exceljs";

export function buildExcelFilename(reportSlug: string): string {
  const stamp = new Date().toISOString().slice(0, 10);
  return `${reportSlug}-${stamp}.xlsx`;
}

export async function downloadWorkbookBuffer(workbook: ExcelJS.Workbook, filename: string): Promise<void> {
  const buffer = await workbook.xlsx.writeBuffer();
  const blob = new Blob([buffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
