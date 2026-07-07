import type { CSSProperties } from "react";
import { BRAND_APP_TITLE } from "./branding";
import {
  hasAgencyBrandLogo,
  portalAgencyName,
  portalBrandingStyle,
  resolveBrandLogoUrl,
  type PortalBranding,
} from "./portalBranding";

type PortalBrandingHeaderProps = {
  branding?: PortalBranding | null;
  agencyNameFallback?: string;
  title: string;
  subtitle?: string;
  className?: string;
};

export default function PortalBrandingHeader({
  branding,
  agencyNameFallback,
  title,
  subtitle,
  className = "",
}: PortalBrandingHeaderProps) {
  const agencyName = portalAgencyName(branding, agencyNameFallback?.trim() || "Your travel agency");
  const style = portalBrandingStyle(branding);

  return (
    <header
      className={`portal-branding-header ${className}`.trim()}
      style={style as CSSProperties}
    >
      <div className="portal-branding-header-inner">
        {hasAgencyBrandLogo(branding) ? (
          <img
            src={resolveBrandLogoUrl(branding?.brand_logo_url)}
            alt={`${agencyName} logo`}
            className="portal-branding-logo"
          />
        ) : (
          <div className="portal-branding-agency-name">{agencyName}</div>
        )}
        <div className="portal-branding-copy">
          <h1>{title}</h1>
          <p className="portal-branding-subtitle">{subtitle ?? `Secure client portal · ${agencyName}`}</p>
          {branding?.business_phone || branding?.business_address ? (
            <p className="portal-branding-contact">
              {[branding.business_phone, branding.business_address].filter(Boolean).join(" · ")}
            </p>
          ) : null}
        </div>
      </div>
      <p className="portal-branding-powered">Powered by {BRAND_APP_TITLE}</p>
    </header>
  );
}
