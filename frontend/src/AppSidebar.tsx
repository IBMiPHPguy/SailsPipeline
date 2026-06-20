import type { ReactNode } from "react";
import { REQUEST_DASHBOARD_PAGE_TITLE } from "./branding";
import {
  BarChartNavIcon,
  CruiseShipNavIcon,
  PersonNavIcon,
  ReportsNavIcon,
} from "./SidebarNavIcons";
import type { AppNavItem } from "./types";

type AppSidebarProps = {
  activeItem: AppNavItem | null;
  onNavigate: (item: AppNavItem) => void;
};

const NAV_ITEMS: Array<{
  id: AppNavItem;
  label: string;
  icon: () => ReactNode;
}> = [
  { id: "dashboard", label: REQUEST_DASHBOARD_PAGE_TITLE, icon: CruiseShipNavIcon },
  { id: "sales-analytics", label: "Sales Analytics", icon: BarChartNavIcon },
  { id: "clients", label: "Clients", icon: PersonNavIcon },
  { id: "reports", label: "Reports", icon: ReportsNavIcon },
];

export default function AppSidebar({ activeItem, onNavigate }: AppSidebarProps) {
  return (
    <nav className="app-sidebar" aria-label="Main navigation">
      <ul className="app-sidebar-list">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeItem === item.id;

          return (
            <li key={item.id}>
              <button
                type="button"
                className={`app-sidebar-link${isActive ? " is-active" : ""}`}
                aria-current={isActive ? "page" : undefined}
                onClick={() => onNavigate(item.id)}
              >
                <Icon />
                <span className="app-sidebar-link-label">{item.label}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function activeNavItemForView(viewType: string): AppNavItem | null {
  if (viewType === "dashboard" || viewType === "closed") {
    return "dashboard";
  }
  if (viewType === "sales-analytics") {
    return "sales-analytics";
  }
  if (viewType === "clients") {
    return "clients";
  }
  if (viewType === "reports" || viewType === "report") {
    return "reports";
  }
  return null;
}
