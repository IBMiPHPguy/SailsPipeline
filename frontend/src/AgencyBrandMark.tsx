import type { PortalBranding } from "./portalBranding";
import {
  contrastTextColor,
  hasAgencyBrandLogo,
  portalAgencyName,
  resolveBrandLogoUrl,
} from "./portalBranding";

type AgencyBrandMarkProps = {
  branding?: PortalBranding | null;
  className?: string;
  textClassName?: string;
};

export default function AgencyBrandMark({
  branding,
  className = "",
  textClassName = "agency-brand-text",
}: AgencyBrandMarkProps) {
  const agencyName = portalAgencyName(branding);

  if (hasAgencyBrandLogo(branding)) {
    return (
      <img
        src={resolveBrandLogoUrl(branding?.brand_logo_url)}
        alt={`${agencyName} logo`}
        className={className}
      />
    );
  }

  const primary = branding?.primary_color ?? "#0d5c75";
  return (
    <div
      className={textClassName}
      style={{ color: primary, ["--agency-brand-contrast" as string]: contrastTextColor(primary) }}
    >
      {agencyName}
    </div>
  );
}
