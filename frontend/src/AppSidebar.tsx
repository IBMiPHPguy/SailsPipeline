import type { ReactNode } from "react";
import AgencyBrandMark from "./AgencyBrandMark";
import { REQUEST_DASHBOARD_PAGE_TITLE } from "./branding";
import type { PortalBranding } from "./portalBranding";
import {
  BarChartNavIcon,
  CruiseShipNavIcon,
  FunnelNavIcon,
  GroupBlocksNavIcon,
  PersonNavIcon,
  ReportsNavIcon,
  TeamNavIcon,
  WorkflowsNavIcon,
  SettingsNavIcon,
} from "./SidebarNavIcons";
import { isTenantSuperUser } from "./tenantRoles";
import type { AppNavItem, User } from "./types";

type AppSidebarProps = {
  activeItem: AppNavItem | null;
  currentUser: User;
  agencyBranding?: PortalBranding | null;
  onNavigate: (item: AppNavItem) => void;
};

type NavEntry = {
  id: AppNavItem;
  label: string;
  icon: () => ReactNode;
};

const ALWAYS_NAV_ITEMS: NavEntry[] = [
  { id: "dashboard", label: REQUEST_DASHBOARD_PAGE_TITLE, icon: CruiseShipNavIcon },
  { id: "sales-analytics", label: "Sales Analytics", icon: BarChartNavIcon },
  { id: "clients", label: "Clients", icon: PersonNavIcon },
  { id: "reports", label: "Reports", icon: ReportsNavIcon },
];

const MARKETING_NAV_ITEM: NavEntry = {
  id: "marketing-campaigns",
  label: "Marketing Campaigns",
  icon: FunnelNavIcon,
};

const TEAM_NAV_ITEM: NavEntry = {
  id: "team",
  label: "Team",
  icon: TeamNavIcon,
};

const AGENCY_SETTINGS_NAV_ITEM: NavEntry = {
  id: "agency-settings",
  label: "Agency Settings",
  icon: SettingsNavIcon,
};

const WORKFLOWS_NAV_ITEM: NavEntry = {
  id: "workflows",
  label: "Workflows & Tasks",
  icon: WorkflowsNavIcon,
};

const GROUP_BLOCKS_NAV_ITEM: NavEntry = {
  id: "group-blocks",
  label: "Group Blocks",
  icon: GroupBlocksNavIcon,
};

function buildTenantNavItems(currentUser: User): NavEntry[] {
  const caps = currentUser.capabilities;
  const items: NavEntry[] = [
    ALWAYS_NAV_ITEMS[0], // dashboard
    ALWAYS_NAV_ITEMS[1], // sales-analytics
  ];

  const includeMarketing = caps
    ? caps.show_marketing_campaigns_tab || caps.is_unrestricted
    : isTenantSuperUser(currentUser.role);
  if (includeMarketing) {
    items.push(MARKETING_NAV_ITEM);
  }

  items.push(ALWAYS_NAV_ITEMS[2], ALWAYS_NAV_ITEMS[3]); // clients, reports

  if (caps) {
    if (caps.show_workflows_tab || caps.is_unrestricted) {
      items.push(WORKFLOWS_NAV_ITEM);
    }
    if (caps.show_group_blocks_tab || caps.is_unrestricted) {
      items.push(GROUP_BLOCKS_NAV_ITEM);
    }
    if (caps.show_agency_settings_tab || caps.is_unrestricted) {
      items.push(AGENCY_SETTINGS_NAV_ITEM);
    }
    if (caps.show_team_tab || caps.is_unrestricted) {
      items.push(TEAM_NAV_ITEM);
    }
    return items;
  }

  // Safe fallback when capabilities are missing: preserve prior super-user tabs;
  // agents only get the always-visible base (no marketing/workflows/groups/settings/team).
  if (isTenantSuperUser(currentUser.role)) {
    return [
      ...ALWAYS_NAV_ITEMS.slice(0, 2),
      MARKETING_NAV_ITEM,
      ...ALWAYS_NAV_ITEMS.slice(2),
      WORKFLOWS_NAV_ITEM,
      GROUP_BLOCKS_NAV_ITEM,
      AGENCY_SETTINGS_NAV_ITEM,
      TEAM_NAV_ITEM,
    ];
  }

  return items;
}

export default function AppSidebar({ activeItem, currentUser, agencyBranding, onNavigate }: AppSidebarProps) {
  const navItems = buildTenantNavItems(currentUser);

  return (
    <nav className="app-sidebar" aria-label="Main navigation">
      <div className="app-sidebar-brand">
        <AgencyBrandMark branding={agencyBranding} className="app-sidebar-brand-logo" />
      </div>
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
  if (viewType === "agency-settings") {
    return "agency-settings";
  }
  if (viewType === "workflows" || viewType === "tasks") {
    return "workflows";
  }
  if (viewType === "group-blocks") {
    return "group-blocks";
  }
  return null;
}
