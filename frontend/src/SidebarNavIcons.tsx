import type { ReactNode } from "react";
import type { ReportCategoryId } from "./reportsCatalog";

type NavStrokeIconProps = {
  className?: string;
  children: ReactNode;
};

export function NavStrokeIcon({ className, children }: NavStrokeIconProps) {
  return (
    <span className={`nav-stroke-icon${className ? ` ${className}` : ""}`} aria-hidden="true">
      {children}
    </span>
  );
}

function SidebarIcon({ children }: { children: ReactNode }) {
  return <NavStrokeIcon className="app-sidebar-link-icon">{children}</NavStrokeIcon>;
}

export function CruiseShipNavIcon() {
  return (
    <SidebarIcon>
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.75">
        <path d="M4 18h16" strokeLinecap="round" />
        <path d="M6 14h12l1-4H5l1 4Z" strokeLinejoin="round" />
        <path d="M8 10V7l4-3 4 3v3" strokeLinejoin="round" />
        <path d="M12 4v2" strokeLinecap="round" />
      </svg>
    </SidebarIcon>
  );
}

export function BarChartNavIcon() {
  return (
    <SidebarIcon>
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.75">
        <path d="M4 19V5" strokeLinecap="round" />
        <path d="M4 19h16" strokeLinecap="round" />
        <rect x="7" y="11" width="3" height="8" rx="0.75" />
        <rect x="12" y="8" width="3" height="11" rx="0.75" />
        <rect x="17" y="13" width="3" height="6" rx="0.75" />
      </svg>
    </SidebarIcon>
  );
}

export function PersonNavIcon() {
  return (
    <SidebarIcon>
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.75">
        <circle cx="12" cy="8" r="3.25" />
        <path d="M5.5 19c.9-3.1 3.4-5 6.5-5s5.6 1.9 6.5 5" strokeLinecap="round" />
      </svg>
    </SidebarIcon>
  );
}

export function ReportsNavIcon() {
  return (
    <SidebarIcon>
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.75">
        <path d="M5 5.5A2.5 2.5 0 0 1 7.5 3H14l5 5v11.5A2.5 2.5 0 0 1 16.5 22h-9A2.5 2.5 0 0 1 5 19.5V5.5Z" strokeLinejoin="round" />
        <path d="M14 3v5h5" strokeLinejoin="round" />
        <path d="M8.5 13.5h7" strokeLinecap="round" />
        <path d="M8.5 17h5" strokeLinecap="round" />
      </svg>
    </SidebarIcon>
  );
}

export function SalesFinancialCategoryIcon() {
  return (
    <NavStrokeIcon className="reports-category-icon">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.75">
        <path d="M4 19V5" strokeLinecap="round" />
        <path d="M4 19h16" strokeLinecap="round" />
        <rect x="7" y="11" width="3" height="8" rx="0.75" />
        <rect x="12" y="8" width="3" height="11" rx="0.75" />
        <rect x="17" y="13" width="3" height="6" rx="0.75" />
      </svg>
    </NavStrokeIcon>
  );
}

export function EfficiencyCategoryIcon() {
  return (
    <NavStrokeIcon className="reports-category-icon">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.75">
        <path d="M5 5h14l-2 6H7L5 5Z" strokeLinejoin="round" />
        <path d="M9 11v3" strokeLinecap="round" />
        <path d="M12 11v6" strokeLinecap="round" />
        <path d="M15 11v4" strokeLinecap="round" />
        <path d="M7 20h10" strokeLinecap="round" />
      </svg>
    </NavStrokeIcon>
  );
}

export function MarketingCategoryIcon() {
  return (
    <NavStrokeIcon className="reports-category-icon">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.75">
        <circle cx="9" cy="8" r="2.75" />
        <circle cx="16.5" cy="9.5" r="2.25" />
        <path d="M4.5 18.5c.8-2.4 2.6-3.8 4.5-3.8s3.7 1.4 4.5 3.8" strokeLinecap="round" />
        <path d="M14.5 17.5c.5-1.6 1.6-2.5 2.8-2.5" strokeLinecap="round" />
      </svg>
    </NavStrokeIcon>
  );
}

export const REPORT_CATEGORY_ICONS: Record<ReportCategoryId, () => ReactNode> = {
  "sales-financial": SalesFinancialCategoryIcon,
  "efficiency-performance": EfficiencyCategoryIcon,
  "client-marketing": MarketingCategoryIcon,
};
