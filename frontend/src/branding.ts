/** Official product name (PascalCase). Use in emails and general references. */
export const BRAND_NAME = "SailsPipeline";

/** Full app title for login, browser tab, and dashboard chrome. */
export const BRAND_APP_TITLE = "SailsPipeline CRM";

export const BRAND_TAGLINE = "Manage cruise travel requests from intake through close.";

export function brandedDocumentTitle(page?: string): string {
  if (!page?.trim()) {
    return BRAND_APP_TITLE;
  }
  return `${page.trim()} · ${BRAND_APP_TITLE}`;
}
