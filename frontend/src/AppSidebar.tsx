import type { ReactNode } from "react";
import { REQUEST_DASHBOARD_PAGE_TITLE } from "./branding";
import {
  BarChartNavIcon,
  CruiseShipNavIcon,
  FunnelNavIcon,
  PersonNavIcon,
  ReportsNavIcon,
  TeamNavIcon,
  WorkflowsNavIcon,
} from "./SidebarNavIcons";
import { isTenantSuperUser } from "./tenantRoles";
import type { AppNavItem, User } from "./types";

type AppSidebarProps = {
  activeItem: AppNavItem | null;
  currentUser: User;
  onNavigate: (item: AppNavItem) => void;
};

const BASE_NAV_ITEMS: Array<{
  id: AppNavItem;
  label: string;
  icon: () => ReactNode;
}> = [
  { id: "dashboard", label: REQUEST_DASHBOARD_PAGE_TITLE, icon: CruiseShipNavIcon },
  { id: "sales-analytics", label: "Sales Analytics", icon: BarChartNavIcon },
  { id: "marketing-campaigns", label: "Marketing Campaigns", icon: FunnelNavIcon },
  { id: "clients", label: "Clients", icon: PersonNavIcon },
  { id: "reports", label: "Reports", icon: ReportsNavIcon },
];

const TEAM_NAV_ITEM = {
  id: "team" as const,
  label: "Team",
  icon: TeamNavIcon,
};

const WORKFLOWS_NAV_ITEM = {
  id: "workflows" as const,
  label: "Workflows & Tasks",
  icon: WorkflowsNavIcon,
};

export default function AppSidebar({ activeItem, currentUser, onNavigate }: AppSidebarProps) {
  const navItems = isTenantSuperUser(currentUser.role)
    ? [...BASE_NAV_ITEMS, WORKFLOWS_NAV_ITEM, TEAM_NAV_ITEM]
    : BASE_NAV_ITEMS;

  return (
    <nav className="app-sidebar" aria-label="Main navigation">
      <ul className="app-sidebar-list">
        {navItems.map((item) => {
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
  if (viewType === "marketing-campaigns") {
    return "marketing-campaigns";
  }
  if (viewType === "clients") {
    return "clients";
  }
  if (viewType === "reports" || viewType === "report") {
    return "reports";
  }
  if (viewType === "team") {
    return "team";
  }
  if (viewType === "workflows" || viewType === "tasks") {
    return "workflows";
  }
  return null;
}
