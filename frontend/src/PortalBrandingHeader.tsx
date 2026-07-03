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
  title: string;
  subtitle?: string;
  className?: string;
};

export default function PortalBrandingHeader({
  branding,
  title,
  subtitle,
  className = "",
}: PortalBrandingHeaderProps) {
  const agencyName = portalAgencyName(branding);
  const style = portalBrandingStyle(branding);
  const primaryColor = branding?.primary_color ?? "#0d5c75";

  return (
    <header
      className={`bridge-card-header portal-branding-header ${className}`.trim()}
      style={style as CSSProperties}
    >
      <div className="portal-branding-header-inner">
        {hasAgencyBrandLogo(branding) ? (
          <img
            src={resolveBrandLogoUrl(branding?.brand_logo_url)}
            alt={`${agencyName} logo`}
            className="auth-logo portal-branding-logo"
          />
        ) : (
          <div className="portal-branding-agency-name" style={{ color: primaryColor }}>
            {agencyName}
          </div>
        )}
        <div className="portal-branding-copy">
          <h1>{title}</h1>
          <p className="portal-branding-subtitle">{subtitle ?? `Secure client portal · ${agencyName}`}</p>
          {branding?.business_phone || branding?.business_address ? (
            <p className="portal-branding-contact muted">
              {[branding.business_phone, branding.business_address].filter(Boolean).join(" · ")}
            </p>
          ) : null}
        </div>
      </div>
      <p className="portal-branding-powered muted">Powered by {BRAND_APP_TITLE}</p>
    </header>
  );
}
