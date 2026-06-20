import { FormEvent, useEffect, useMemo, useState } from "react";
import { createRequest, addNote, fetchDashboard } from "./api";
import { fetchCurrentUser, logout } from "./authApi";
import { getToken } from "./authStorage";
import Dashboard from "./Dashboard";
import ClosedRequestsPage from "./ClosedRequestsPage";
import ClientsPage from "./ClientsPage";
import SalesAnalytics from "./SalesAnalytics";
import AppSidebar, { activeNavItemForView } from "./AppSidebar";
import Login from "./Login";
import RequestForm, { emptyRequestForm, isReturnAfterDeparture } from "./RequestForm";
import ReportViewPage from "./ReportViewPage";
import ReportsPage from "./ReportsPage";
import RequestWorkspace from "./RequestWorkspace";
import { formatCruiseLines } from "./CruiseLineMultiSelect";
import { buildQuickNoteInput } from "./noteForm";
import { BRAND_APP_TITLE, brandedDocumentTitle, REQUEST_DASHBOARD_PAGE_TITLE } from "./branding";
import type { AppView, DashboardData, TravelRequest, TravelRequestInput, User } from "./types";
import { formatDate, formatDestinationSummary } from "./utils";
import "./App.css";

function formToSummaryPreview(form: TravelRequestInput): TravelRequest {
  return {
    id: 0,
    first_name: form.first_name,
    last_name: form.last_name,
    email: form.email,
    phone: form.phone,
    cruise_lines: form.cruise_lines,
    excluded_cruise_lines: form.excluded_cruise_lines ?? [],
    destination: form.destination,
    destination_details: ["Caribbean", "Alaska", "Asia", "Europe"].includes(form.destination)
      ? form.destination_details ?? null
      : null,
    departure_date: form.departure_date,
    return_date: form.return_date,
    cabin_types: form.cabin_types,
    passengers: form.passengers,
    cabins_needed: form.cabins_needed,
    cabin_hold_reservation_ids: [],
    status: "Open",
    close_reason: null,
    created_by: { id: 0, username: "" },
    updated_by: { id: 0, username: "" },
    created_at: "",
    updated_at: "",
  };
}

function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [view, setView] = useState<AppView>({ type: "dashboard" });
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [form, setForm] = useState<TravelRequestInput>(emptyRequestForm);
  const [message, setMessage] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [creationNote, setCreationNote] = useState("");

  const newRequestSummary = useMemo(() => formToSummaryPreview(form), [form]);

  async function loadDashboard() {
    setDashboardLoading(true);
    try {
      const data = await fetchDashboard();
      setDashboard(data);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : `Unable to load ${REQUEST_DASHBOARD_PAGE_TITLE.toLowerCase()}.`);
    } finally {
      setDashboardLoading(false);
    }
  }

  useEffect(() => {
    async function bootstrap() {
      if (!getToken()) {
        setAuthLoading(false);
        return;
      }

      try {
        const user = await fetchCurrentUser();
        setCurrentUser(user);
        void loadDashboard();
      } catch {
        setCurrentUser(null);
      } finally {
        setAuthLoading(false);
      }
    }

    void bootstrap();
  }, []);

  useEffect(() => {
    if (!currentUser) {
      document.title = BRAND_APP_TITLE;
      return;
    }
    if (view.type === "dashboard" || view.type === "closed") {
      document.title = brandedDocumentTitle(REQUEST_DASHBOARD_PAGE_TITLE);
      return;
    }
    if (view.type === "reports" || view.type === "report") {
      document.title = brandedDocumentTitle("Reports");
      return;
    }
    document.title = BRAND_APP_TITLE;
  }, [currentUser, view.type]);

  function handleLogout() {
    logout();
    setCurrentUser(null);
    setDashboard(null);
    setView({ type: "dashboard" });
    setMessage("");
    setError("");
  }

  function handleAuthenticated(user: User) {
    setCurrentUser(user);
    setView({ type: "dashboard" });
    setError("");
    loadDashboard().catch(() => setError(`Unable to load ${REQUEST_DASHBOARD_PAGE_TITLE.toLowerCase()}.`));
  }

  async function handleCreateRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");
    setError("");

    if (form.cabin_types.length === 0) {
      setError("Select at least one cabin type.");
      setSubmitting(false);
      return;
    }

    if (form.cruise_lines.length === 0) {
      setError("Select at least one preferred cruise line.");
      setSubmitting(false);
      return;
    }

    if (!isReturnAfterDeparture(form.departure_date, form.return_date)) {
      setError("Return date must be after the departure date.");
      setSubmitting(false);
      return;
    }

    const payload: TravelRequestInput = {
      ...form,
      excluded_cruise_lines: form.excluded_cruise_lines ?? [],
      destination_details: ["Caribbean", "Alaska", "Asia", "Europe"].includes(form.destination)
        ? form.destination_details
        : null,
      first_passenger_date_of_birth: form.first_passenger_date_of_birth?.trim() || undefined,
      primary_passenger_id: form.primary_passenger_id,
    };

    try {
      const created = await createRequest(payload);
      const trimmedNote = creationNote.trim();

      if (trimmedNote) {
        try {
          await addNote(created.id, buildQuickNoteInput(trimmedNote));
        } catch (noteError) {
          setForm(emptyRequestForm);
          setCreationNote("");
          await loadDashboard();
          setView({ type: "edit", requestId: created.id });
          setError(
            noteError instanceof Error
              ? `Request was created, but the note could not be saved: ${noteError.message}`
              : "Request was created, but the note could not be saved.",
          );
          return;
        }
      }

      setForm(emptyRequestForm);
      setCreationNote("");
      setMessage(trimmedNote ? "Travel request and note created." : "Travel request created.");
      await loadDashboard();
      setView({ type: "edit", requestId: created.id });
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  }

  if (authLoading) {
    return (
      <main className="page auth-page">
        <section className="card auth-card">
          <p>Loading...</p>
        </section>
      </main>
    );
  }

  if (!currentUser) {
    return <Login onAuthenticated={handleAuthenticated} />;
  }

  const hideSidebar = view.type === "new" || view.type === "edit";

  return (
    <main className={`page${hideSidebar ? " page-workspace" : ""}`}>
      <section className="hero">
        <div className="hero-top">
          <div className="hero-brand">
            <img
              src="/sailspipeline-logo.png"
              alt={BRAND_APP_TITLE}
              className="app-logo"
            />
          </div>
          <div className="user-panel">
            <span>Signed in as {currentUser.username}</span>
            <button type="button" className="secondary-button" onClick={handleLogout}>
              Sign out
            </button>
          </div>
        </div>
      </section>

      <div className={`app-layout${hideSidebar ? " app-layout-no-sidebar" : ""}`}>
        {!hideSidebar ? (
          <AppSidebar
            activeItem={activeNavItemForView(view.type)}
            onNavigate={(item) => {
              setMessage("");
              setError("");
              if (item === "dashboard") {
                setView({ type: "dashboard" });
                loadDashboard().catch(() => undefined);
                return;
              }
              if (item === "sales-analytics") {
                setView({ type: "sales-analytics" });
                return;
              }
              if (item === "reports") {
                setView({ type: "reports" });
                return;
              }
              setView({ type: "clients" });
            }}
          />
        ) : null}

        <div className="app-main">
      {view.type === "dashboard" ? (
        dashboardLoading && !dashboard ? (
          <section className="card">
            <p>Loading {REQUEST_DASHBOARD_PAGE_TITLE.toLowerCase()}...</p>
          </section>
        ) : dashboard ? (
          <Dashboard
            dashboard={dashboard}
            onNewRequest={() => {
              setForm(emptyRequestForm);
              setCreationNote("");
              setMessage("");
              setError("");
              setView({ type: "new" });
            }}
            onOpenRequest={(requestId) => {
              setMessage("");
              setError("");
              setView({ type: "edit", requestId });
            }}
            onOpenClosedRequests={() => {
              setMessage("");
              setError("");
              setView({ type: "closed" });
            }}
            onDashboardRefresh={() => {
              loadDashboard().catch(() => undefined);
            }}
          />
        ) : (
          <section className="card">
            <p>{error || `Unable to load ${REQUEST_DASHBOARD_PAGE_TITLE.toLowerCase()}.`}</p>
          </section>
        )
      ) : null}

      {view.type === "sales-analytics" ? (
        <SalesAnalytics
          onError={(message) => {
            setError(message);
          }}
        />
      ) : null}

      {view.type === "clients" ? <ClientsPage /> : null}

      {view.type === "reports" ? (
        <ReportsPage
          onViewReport={(reportId) => {
            setMessage("");
            setError("");
            setView({ type: "report", reportId });
          }}
        />
      ) : null}

      {view.type === "report" ? (
        <ReportViewPage
          reportId={view.reportId}
          onBack={() => {
            setMessage("");
            setError("");
            setView({ type: "reports" });
          }}
        />
      ) : null}

      {view.type === "closed" ? (
        <ClosedRequestsPage
          closedCount={dashboard?.closed_count ?? 0}
          onOpenRequest={(requestId) => {
            setMessage("");
            setError("");
            setView({ type: "edit", requestId });
          }}
          onReopened={() => {
            loadDashboard().catch(() => undefined);
          }}
        />
      ) : null}

      {view.type === "new" ? (
        <div className="workspace workspace-tabbed">
          <section className="request-summary-card request-summary-card-compact">
            <div className="request-summary-compact-row">
              <button
                type="button"
                className="back-button"
                onClick={() => {
                  setView({ type: "dashboard" });
                  loadDashboard().catch(() => undefined);
                }}
              >
                Back
              </button>

              <div className="request-summary-compact-title">
                <h2>New Cruise Request</h2>
                <p className="request-summary-compact-client">
                  {form.first_name || form.last_name
                    ? `${form.first_name} ${form.last_name}`.trim()
                    : "Enter client and trip details"}
                </p>
                <span className="status-badge status-badge-open">New</span>
              </div>

              <div className="request-summary-compact-actions">
                <button type="submit" form="request-create-form" disabled={submitting}>
                  {submitting ? "Creating..." : "Create Request"}
                </button>
              </div>
            </div>

            <div className="request-summary-compact-meta">
              {form.destination ? <span>{formatDestinationSummary(newRequestSummary)}</span> : null}
              {form.cruise_lines.length > 0 ? <span>{formatCruiseLines(form.cruise_lines)}</span> : null}
              {form.departure_date || form.return_date ? (
                <span>
                  {formatDate(form.departure_date)} – {formatDate(form.return_date)}
                </span>
              ) : null}
            </div>
          </section>

          {message || error ? (
            <div className="workspace-status-messages">
              {message ? <p className="status success">{message}</p> : null}
              {error ? <p className="status error">{error}</p> : null}
            </div>
          ) : null}

          <section className="section-card section-tabs-card workspace-tabs-card">
            <div className="section-tablist workspace-tablist" role="tablist" aria-label="New request">
              <button
                type="button"
                role="tab"
                id="new-request-tab-details"
                aria-selected
                aria-controls="new-request-panel-details"
                className="section-tab is-active"
              >
                Request detail
              </button>
            </div>

            <div className="section-card-body section-tab-body workspace-tab-body">
              <div
                role="tabpanel"
                id="new-request-panel-details"
                aria-labelledby="new-request-tab-details"
                className="workspace-tab-panel"
              >
                <RequestForm
                  formId="request-create-form"
                  hideActions
                  layout="workspace"
                  form={form}
                  setForm={setForm}
                  onSubmit={handleCreateRequest}
                  submitting={submitting}
                  submitLabel="Create Request"
                  creationNote={creationNote}
                  onCreationNoteChange={setCreationNote}
                />
              </div>
            </div>
          </section>
        </div>
      ) : null}

      {view.type === "edit" ? (
        <RequestWorkspace
          requestId={view.requestId}
          onBack={() => {
            setView({ type: "dashboard" });
            loadDashboard().catch(() => undefined);
          }}
          onClosed={() => {
            setView({ type: "dashboard" });
            loadDashboard().catch(() => undefined);
          }}
        />
      ) : null}
        </div>
      </div>
    </main>
  );
}

export default App;
