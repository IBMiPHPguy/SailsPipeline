import type { TravelRequest } from "./types";

export function formatDestinationSummary(request: TravelRequest): string {
  const details = request.destination_details;
  if (!details) {
    return request.destination;
  }

  const subregions =
    details.caribbean_regions ??
    details.alaska_options ??
    details.asia_regions ??
    details.europe_regions;

  if (subregions?.length) {
    return `${request.destination} (${subregions.join(", ")})`;
  }

  return request.destination;
}

export function formatTimestamp(value: string): string {
  return new Date(value).toLocaleString();
}

export function formatWaiverTimeRemaining(expiresAt: string, now = new Date()): string {
  const expiresMs = new Date(expiresAt).getTime();
  if (Number.isNaN(expiresMs)) {
    return "—";
  }

  const remainingMs = expiresMs - now.getTime();
  if (remainingMs <= 0) {
    return "expired";
  }

  const totalMinutes = Math.ceil(remainingMs / (1000 * 60));
  const days = Math.floor(totalMinutes / (60 * 24));
  const hours = Math.floor((totalMinutes % (60 * 24)) / 60);
  const minutes = totalMinutes % 60;

  if (days > 0) {
    return hours > 0 ? `${days} day${days === 1 ? "" : "s"} ${hours} hr` : `${days} day${days === 1 ? "" : "s"}`;
  }
  if (hours > 0) {
    return minutes > 0 ? `${hours} hr ${minutes} min` : `${hours} hr`;
  }
  return `${minutes} min`;
}

export function formatDate(value: string): string {
  const isoMatch = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (isoMatch) {
    const [, year, month, day] = isoMatch;
    return `${month}/${day}/${year}`;
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  const month = String(parsed.getMonth() + 1).padStart(2, "0");
  const day = String(parsed.getDate()).padStart(2, "0");
  const year = parsed.getFullYear();
  return `${month}/${day}/${year}`;
}

export function addDaysToIsoDate(dateStr: string, days: number): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(dateStr);
  if (!match) {
    return dateStr;
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const date = new Date(year, month - 1, day + days);
  const nextYear = date.getFullYear();
  const nextMonth = String(date.getMonth() + 1).padStart(2, "0");
  const nextDay = String(date.getDate()).padStart(2, "0");
  return `${nextYear}-${nextMonth}-${nextDay}`;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function isRequestStale(updatedAt: string): boolean {
  const updated = new Date(updatedAt).getTime();
  const threshold = Date.now() - 3 * 24 * 60 * 60 * 1000;
  return updated < threshold;
}

export async function copyTextToClipboard(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "absolute";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
}

export function isHtmlCommunicationBody(body: string): boolean {
  const trimmed = body.trim().toLowerCase();
  return trimmed.startsWith("<!doctype html") || trimmed.startsWith("<html");
}

export async function copyCommunicationBodyToClipboard(body: string): Promise<void> {
  if (isHtmlCommunicationBody(body) && navigator.clipboard?.write && typeof ClipboardItem !== "undefined") {
    const plainText =
      new DOMParser().parseFromString(body, "text/html").body.textContent?.trim() ?? body;
    await navigator.clipboard.write([
      new ClipboardItem({
        "text/html": new Blob([body], { type: "text/html" }),
        "text/plain": new Blob([plainText], { type: "text/plain" }),
      }),
    ]);
    return;
  }

  await copyTextToClipboard(body);
}
