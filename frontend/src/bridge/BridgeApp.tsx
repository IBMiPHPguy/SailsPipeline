import { useCallback, useEffect, useState } from "react";
import { logout } from "../authApi";
import { BRAND_APP_TITLE } from "../branding";
import BridgeCaptainIcon from "./BridgeCaptainIcon";
import BridgeGuard from "./BridgeGuard";
import BridgePage from "./BridgePage";
import BridgeTenantEditPage from "./BridgeTenantEditPage";
import "../App.css";
import "../bridge-portal.css";

type BridgeView =
  | { type: "dashboard" }
  | { type: "tenant-edit"; agencyId: string };

function parseBridgeView(pathname: string): BridgeView {
  const tenantMatch = pathname.match(/^\/bridge\/tenant\/([^/]+)$/);
  if (tenantMatch) {
    return { type: "tenant-edit", agencyId: decodeURIComponent(tenantMatch[1]) };
  }
  return { type: "dashboard" };
}

export default function BridgeApp() {
  const [view, setView] = useState<BridgeView>(() => parseBridgeView(window.location.pathname));

  useEffect(() => {
    const onPopState = () => setView(parseBridgeView(window.location.pathname));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const openTenantEdit = useCallback((agencyId: string) => {
    const nextPath = `/bridge/tenant/${encodeURIComponent(agencyId)}`;
    window.history.pushState({}, "", nextPath);
    setView({ type: "tenant-edit", agencyId });
  }, []);

  const backToDashboard = useCallback(() => {
    window.history.pushState({}, "", "/bridge");
    setView({ type: "dashboard" });
  }, []);

  return (
    <BridgeGuard>
      {(operator) => {
        function handleLogout() {
          logout("bridge");
          window.location.replace("/bridge");
        }

        return (
          <main className="page bridge-page">
            <section className="hero bridge-hero">
              <div className="hero-top">
                <div className="hero-brand bridge-hero-brand">
                  <img
                    src="/sailspipeline-logo.png"
                    alt={BRAND_APP_TITLE}
                    className="app-logo bridge-app-logo"
                  />
                  <div className="bridge-hero-title">
                    <BridgeCaptainIcon size={36} className="bridge-hero-icon" />
                    <div>
                      <h1 className="bridge-hero-heading">The Bridge</h1>
                      <p className="bridge-hero-subtitle">Platform Management</p>
                    </div>
                  </div>
                </div>
                <div className="user-panel bridge-user-panel">
                  <span>Signed in as {operator.username}</span>
                  <button type="button" className="secondary-button" onClick={handleLogout}>
                    Sign out
                  </button>
                </div>
              </div>
            </section>

            {view.type === "tenant-edit" ? (
              <BridgeTenantEditPage agencyId={view.agencyId} onBack={backToDashboard} />
            ) : (
              <BridgePage onEditTenant={openTenantEdit} />
            )}
          </main>
        );
      }}
    </BridgeGuard>
  );
}
