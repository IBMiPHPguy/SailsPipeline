import { StrictMode, lazy, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { readCcAuthTokenFromPath } from "./ccAuthApi";
import { readInsuranceTokenFromPath } from "./insuranceApi";
import { readTermsTokenFromPath } from "./termsApi";
import App from "./App";
import "./index.css";

const BridgeApp = lazy(() => import("./bridge/BridgeApp"));
const OnboardingRegisterPage = lazy(() => import("./OnboardingRegisterPage"));
const RegisterPage = lazy(() => import("./RegisterPage"));
const ForgotPasswordPage = lazy(() => import("./ForgotPasswordPage"));
const ResetPasswordPage = lazy(() => import("./ResetPasswordPage"));
const RegisterAgentPage = lazy(() => import("./RegisterAgentPage"));
const SubscriptionRestorePage = lazy(() => import("./SubscriptionRestorePage"));
const CcAuthPortalPage = lazy(() => import("./CcAuthPortalPage"));
const InsurancePortalPage = lazy(() => import("./InsurancePortalPage"));
const TermsPortalPage = lazy(() => import("./TermsPortalPage"));

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
        <RegisterPage />
      </Suspense>
    );
  }

  if (path === "/forgot-password") {
    return (
      <Suspense fallback={<RouteFallback />}>
        <ForgotPasswordPage />
      </Suspense>
    );
  }

  if (path === "/reset-password") {
    return (
      <Suspense fallback={<RouteFallback />}>
        <ResetPasswordPage />
      </Suspense>
    );
  }

  if (path === "/onboarding") {
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

  if (path.startsWith("/accept-terms/")) {
    const token = readTermsTokenFromPath(path);
    return (
      <Suspense fallback={<RouteFallback />}>
        <TermsPortalPage token={token} />
      </Suspense>
    );
  }

  if (path.startsWith("/insurance-auth/")) {
    const token = readInsuranceTokenFromPath(path);
    return (
      <Suspense fallback={<RouteFallback />}>
        <InsurancePortalPage token={token} />
      </Suspense>
    );
  }

  if (path.startsWith("/cc-auth/")) {
    const token = readCcAuthTokenFromPath(path);
    return (
      <Suspense fallback={<RouteFallback />}>
        <CcAuthPortalPage token={token} />
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
