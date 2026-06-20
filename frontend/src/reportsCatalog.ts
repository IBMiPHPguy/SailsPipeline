export type ReportId =
  | "sales-volume-target-manifest"
  | "supplier-share-volume-ledger"
  | "funnel-leak-lost-business"
  | "advisor-productivity-quota"
  | "passenger-demographics-qualifier";

export type ReportCategoryId = "sales-financial" | "efficiency-performance" | "client-marketing";

export type ReportDefinition = {
  id: ReportId;
  title: string;
  description: string;
  categoryId: ReportCategoryId;
  columns: string[];
};

export type ReportCategory = {
  id: ReportCategoryId;
  title: string;
};

export const REPORT_CATEGORIES: ReportCategory[] = [
  { id: "sales-financial", title: "Sales & Financial Reporting" },
  { id: "efficiency-performance", title: "Efficiency & Performance" },
  { id: "client-marketing", title: "Client Marketing Intelligence" },
];

export const REPORT_DEFINITIONS: ReportDefinition[] = [
  {
    id: "sales-volume-target-manifest",
    title: "Sales Volume & Target Manifest",
    description:
      "Gross booked sales volume, estimated pipeline commission targets, and departure timelines.",
    categoryId: "sales-financial",
    columns: ["Departure window", "Booked volume", "Pipeline target", "Estimated commission", "Open requests"],
  },
  {
    id: "supplier-share-volume-ledger",
    title: "Supplier Share & Volume Ledger",
    description: "Comprehensive market share distribution and pricing metrics grouped by cruise line partner.",
    categoryId: "sales-financial",
    columns: ["Cruise line", "Quote count", "Booked count", "Share %", "Avg. cabin value"],
  },
  {
    id: "funnel-leak-lost-business",
    title: "Funnel Leak & Lost Business Analysis",
    description: "Diagnostic breakdown of rejected quotes, price resistance, and pipeline drop-off reasons.",
    categoryId: "efficiency-performance",
    columns: ["Reason segment", "Rejection reason", "Count", "Share %", "Last 90 days"],
  },
  {
    id: "advisor-productivity-quota",
    title: "Advisor Productivity & Quota Scorecard",
    description: "Matrix tracking request lifecycle velocity, closing ratios, and lead handling volume by agent.",
    categoryId: "efficiency-performance",
    columns: ["Advisor", "Open requests", "Closed won", "Close rate", "Avg. days to close"],
  },
  {
    id: "passenger-demographics-qualifier",
    title: "Passenger Demographics & Qualifier Ledger",
    description: "Targeted marketing audience sheets grouped by high-value qualifier tags and geography.",
    categoryId: "client-marketing",
    columns: ["Qualifier", "State / region", "Client count", "Active requests", "Last departure"],
  },
];

export function getReportById(reportId: ReportId): ReportDefinition | undefined {
  return REPORT_DEFINITIONS.find((report) => report.id === reportId);
}

export function getReportsByCategory(categoryId: ReportCategoryId): ReportDefinition[] {
  return REPORT_DEFINITIONS.filter((report) => report.categoryId === categoryId);
}
