import { StrictMode, lazy, Suspense } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

const BridgeApp = lazy(() => import("./bridge/BridgeApp"));
const OnboardingRegisterPage = lazy(() => import("./OnboardingRegisterPage"));
const RegisterAgentPage = lazy(() => import("./RegisterAgentPage"));
const SubscriptionRestorePage = lazy(() => import("./SubscriptionRestorePage"));

function resolvePathname(): string {
  return window.location.pathname.replace(/\/+$/, "") || "/";
}

function RouteFallback() {
  return (
    <main className="page auth-page">
      <section className="card auth-card">
        <p className="muted">Loading…</p>
      </section>
    </main>
  );
}

function RootRouter() {
  const path = resolvePathname();

  if (path === "/bridge" || path.startsWith("/bridge/")) {
    return (
      <Suspense fallback={<RouteFallback />}>
        <BridgeApp />
      </Suspense>
    );
  }

  if (path === "/register") {
    return (
      <Suspense fallback={<RouteFallback />}>
        <OnboardingRegisterPage />
      </Suspense>
    );
  }

  if (path === "/register-agent") {
    return (
      <Suspense fallback={<RouteFallback />}>
        <RegisterAgentPage />
      </Suspense>
    );
  }

  if (path === "/subscription-restore") {
    return (
      <Suspense fallback={<RouteFallback />}>
        <SubscriptionRestorePage />
      </Suspense>
    );
  }

  return <App />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RootRouter />
  </StrictMode>,
);
