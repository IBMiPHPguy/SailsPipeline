import type { AppNavItem } from "./types";

type AppSidebarProps = {
  activeItem: AppNavItem | null;
  onNavigate: (item: AppNavItem) => void;
};

export default function AppSidebar({ activeItem, onNavigate }: AppSidebarProps) {
  return (
    <nav className="app-sidebar" aria-label="Main navigation">
      <ul className="app-sidebar-list">
        <li>
          <button
            type="button"
            className={`app-sidebar-link${activeItem === "dashboard" ? " is-active" : ""}`}
            aria-current={activeItem === "dashboard" ? "page" : undefined}
            onClick={() => onNavigate("dashboard")}
          >
            Dashboard
          </button>
        </li>
        <li>
          <button
            type="button"
            className={`app-sidebar-link${activeItem === "clients" ? " is-active" : ""}`}
            aria-current={activeItem === "clients" ? "page" : undefined}
            onClick={() => onNavigate("clients")}
          >
            Clients
          </button>
        </li>
      </ul>
    </nav>
  );
}

export function activeNavItemForView(viewType: string): AppNavItem | null {
  if (viewType === "dashboard" || viewType === "closed") {
    return "dashboard";
  }
  if (viewType === "clients") {
    return "clients";
  }
  return null;
}
