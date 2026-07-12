export type PortalBranding = {
  agency_name: string;
  brand_logo_url?: string | null;
  primary_color: string;
  secondary_color: string;
  business_address?: string | null;
  business_phone?: string | null;
};

const DEFAULT_PRIMARY = "#0d5c75";
const DEFAULT_SECONDARY = "#17a2b8";
const FALLBACK_LOGO = "/sailspipeline-logo.png";

export function contrastTextColor(hexColor: string): "#111111" | "#ffffff" {
  const normalized = hexColor.trim().replace("#", "");
  if (normalized.length !== 6) {
    return "#ffffff";
  }
  const red = Number.parseInt(normalized.slice(0, 2), 16);
  const green = Number.parseInt(normalized.slice(2, 4), 16);
  const blue = Number.parseInt(normalized.slice(4, 6), 16);
  if ([red, green, blue].some((channel) => Number.isNaN(channel))) {
    return "#ffffff";
  }
  const yiq = (red * 299 + green * 587 + blue * 114) / 1000;
  return yiq >= 128 ? "#111111" : "#ffffff";
}

export function resolveBrandLogoUrl(logoUrl?: string | null): string {
  if (!logoUrl) {
    return FALLBACK_LOGO;
  }
  return resolveStaticAssetUrl(logoUrl) ?? FALLBACK_LOGO;
}

/** Resolve a hosted /static/... path for display; returns null when unset. */
export function resolveStaticAssetUrl(assetUrl?: string | null): string | null {
  if (!assetUrl?.trim()) {
    return null;
  }
  if (assetUrl.startsWith("http://") || assetUrl.startsWith("https://")) {
    return assetUrl;
  }
  const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";
  if (apiBase.startsWith("http")) {
    try {
      return `${new URL(apiBase).origin}${assetUrl.startsWith("/") ? assetUrl : `/${assetUrl}`}`;
    } catch {
      return assetUrl;
    }
  }
  return assetUrl;
}

export type AgencyBrandingChrome = PortalBranding;

export function hasAgencyBrandLogo(branding?: PortalBranding | null): boolean {
  return Boolean(branding?.brand_logo_url?.trim());
}

export function applyCrmBrandingStyles(branding?: PortalBranding | null): void {
  const root = document.documentElement;
  const primary = branding?.primary_color ?? DEFAULT_PRIMARY;
  const secondary = branding?.secondary_color ?? DEFAULT_SECONDARY;
  const primaryText = contrastTextColor(primary);

  root.style.setProperty("--app-brand-primary", primary);
  root.style.setProperty("--app-brand-secondary", secondary);
  root.style.setProperty("--app-brand-primary-text", primaryText);
  root.style.setProperty("--app-nav-active-accent", primary);
  root.style.setProperty("--app-nav-active-border", secondary);
  root.style.setProperty("--app-nav-active-bg", `color-mix(in srgb, ${primary} 16%, #ffffff)`);
  root.style.setProperty("--app-section-header-border", primary);
  root.style.setProperty("--app-action-bg", primary);
  root.style.setProperty("--app-action-text", primaryText);
}

export function portalBrandingStyle(branding?: PortalBranding | null): {
  "--portal-primary": string;
  "--portal-secondary": string;
  "--portal-primary-text": "#111111" | "#ffffff";
  "--portal-secondary-text": "#111111" | "#ffffff";
} {
  const primary = branding?.primary_color ?? DEFAULT_PRIMARY;
  const secondary = branding?.secondary_color ?? DEFAULT_SECONDARY;
  return {
    "--portal-primary": primary,
    "--portal-secondary": secondary,
    "--portal-primary-text": contrastTextColor(primary),
    "--portal-secondary-text": contrastTextColor(secondary),
  };
}

export function portalAgencyName(branding?: PortalBranding | null, fallback = "Your travel agency"): string {
  return branding?.agency_name?.trim() || fallback;
}
