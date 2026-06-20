export type ManifestExportRowStyle =
  | "empty"
  | "status-open"
  | "status-closed"
  | "workflow-research"
  | "workflow-communicate"
  | "workflow-crm"
  | "workflow-default"
  | "task-research"
  | "task-communicate"
  | "task-crm"
  | "task-default"
  | "closed-reason"
  | "closed-reason-purchased"
  | "request";

type ManifestRowStyleConfig = {
  fill: string;
  fontColor: string;
  bold?: boolean;
  leftBorder?: string;
  topBorder?: string;
  bottomBorder?: string;
};

function hex(value: string): string {
  return value.replace("#", "").toUpperCase();
}

export const MANIFEST_HEADER_STYLE = {
  fill: hex("#edf7fb"),
  fontColor: hex("#1864ab"),
  bottomBorder: hex("#1864ab"),
} as const;

export const MANIFEST_ROW_STYLES: Record<ManifestExportRowStyle, ManifestRowStyleConfig> = {
  empty: {
    fill: hex("#ffffff"),
    fontColor: hex("#627d98"),
  },
  "status-open": {
    fill: hex("#d0ebff"),
    fontColor: hex("#1864ab"),
    bold: true,
    topBorder: hex("#a5d8ff"),
    bottomBorder: hex("#74c0fc"),
  },
  "status-closed": {
    fill: hex("#dbe4ef"),
    fontColor: hex("#334e68"),
    bold: true,
    topBorder: hex("#bcccdc"),
    bottomBorder: hex("#9fb3c8"),
  },
  "workflow-research": {
    fill: hex("#e7f5ff"),
    fontColor: hex("#1864ab"),
    bold: true,
    leftBorder: hex("#339af0"),
    bottomBorder: hex("#d0ebff"),
  },
  "workflow-communicate": {
    fill: hex("#fff4e6"),
    fontColor: hex("#d9480f"),
    bold: true,
    leftBorder: hex("#ff922b"),
    bottomBorder: hex("#ffd8a8"),
  },
  "workflow-crm": {
    fill: hex("#f3f0ff"),
    fontColor: hex("#6741d9"),
    bold: true,
    leftBorder: hex("#845ef7"),
    bottomBorder: hex("#e5dbff"),
  },
  "workflow-default": {
    fill: hex("#f8fafc"),
    fontColor: hex("#486581"),
    bold: true,
    leftBorder: hex("#94a3b8"),
    bottomBorder: hex("#e2e8f0"),
  },
  "task-research": {
    fill: hex("#f4faff"),
    fontColor: hex("#339af0"),
    bold: true,
    leftBorder: hex("#a5d8ff"),
    bottomBorder: hex("#e7f5ff"),
  },
  "task-communicate": {
    fill: hex("#fff9f0"),
    fontColor: hex("#f76707"),
    bold: true,
    leftBorder: hex("#ffc078"),
    bottomBorder: hex("#fff4e6"),
  },
  "task-crm": {
    fill: hex("#faf5ff"),
    fontColor: hex("#7950f2"),
    bold: true,
    leftBorder: hex("#d0bfff"),
    bottomBorder: hex("#f3f0ff"),
  },
  "task-default": {
    fill: hex("#fbfdff"),
    fontColor: hex("#627d98"),
    bold: true,
    leftBorder: hex("#cbd5e1"),
    bottomBorder: hex("#f1f5f9"),
  },
  "closed-reason": {
    fill: hex("#fffaf9"),
    fontColor: hex("#a61e4d"),
    bold: true,
    leftBorder: hex("#ff8787"),
    bottomBorder: hex("#ffe3e3"),
  },
  "closed-reason-purchased": {
    fill: hex("#f4fff8"),
    fontColor: hex("#087f5b"),
    bold: true,
    leftBorder: hex("#40c057"),
    bottomBorder: hex("#c3fae8"),
  },
  request: {
    fill: hex("#ffffff"),
    fontColor: hex("#243b53"),
  },
};

export function workflowStyleSuffix(workflowType?: string): "research" | "communicate" | "crm" | "default" {
  if (workflowType === "research") {
    return "research";
  }
  if (workflowType === "communicate_research") {
    return "communicate";
  }
  if (workflowType === "enter_trip_crm") {
    return "crm";
  }
  return "default";
}
