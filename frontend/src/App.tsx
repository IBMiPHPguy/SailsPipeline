import { FormEvent, useEffect, useMemo, useState } from "react";
import { createRequest, addNote, fetchAgencyGroup, fetchDashboard } from "./api";
import { fetchCurrentUser, logout } from "./authApi";
import { getToken } from "./authStorage";
import Dashboard from "./Dashboard";
import ClosedRequestsPage from "./ClosedRequestsPage";
import ClientsPage from "./ClientsPage";
import SalesAnalytics from "./SalesAnalytics";
import MarketingCampaignsPage from "./MarketingCampaignsPage";
import AppSidebar, { activeNavItemForView } from "./AppSidebar";
import Login from "./Login";
import RequestForm, { emptyRequestForm, isReturnAfterDeparture } from "./RequestForm";
import ReportViewPage from "./ReportViewPage";
import ReportsPage from "./ReportsPage";
import RequestWorkspace from "./RequestWorkspace";
import WorkflowsPage from "./WorkflowsPage";
import GroupBlocksPage from "./GroupBlocksPage";
import GroupBlockPickerModal from "./GroupBlockPickerModal";
import GroupBlockRequestPromptModal from "./GroupBlockRequestPromptModal";
import GroupInventoryBookingModal from "./GroupInventoryBookingModal";
import TeamPage from "./TeamPage";
import { formatCruiseLines } from "./CruiseLineMultiSelect";
import {
  LEAD_SOURCE_MARKETING_CAMPAIGN,
  LEAD_SOURCE_REFERRAL,
} from "./formOptions";
import { buildQuickNoteInput } from "./noteForm";
import { BRAND_APP_TITLE, brandedDocumentTitle, REQUEST_DASHBOARD_PAGE_TITLE } from "./branding";
import type {
  AgencyGroupInventoryOption,
  AgencyGroupPickerItem,
  AppView,
  DashboardData,
  GroupIntakeDraft,
  TravelRequest,
  TravelRequestGroupBookingInput,
  TravelRequestInput,
  User,
} from "./types";
import { isTenantSuperUser } from "./tenantRoles";
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
  const [groupIntakeDraft, setGroupIntakeDraft] = useState<GroupIntakeDraft | null>(null);
  const [groupRequestPromptOpen, setGroupRequestPromptOpen] = useState(false);
  const [groupPickerOpen, setGroupPickerOpen] = useState(false);
  const [groupInventoryOpen, setGroupInventoryOpen] = useState(false);
  const [selectedPickerGroup, setSelectedPickerGroup] = useState<AgencyGroupPickerItem | null>(null);

  const newRequestSummary = useMemo(() => formToSummaryPreview(form), [form]);

  function beginStandardNewRequest() {
    setGroupIntakeDraft(null);
    setForm(emptyRequestForm);
    setCreationNote("");
    setMessage("");
    setError("");
    setView({ type: "new" });
  }

  function applyGroupIntakeToForm(draft: GroupIntakeDraft) {
    const optionById = new Map(draft.inventoryOptions.map((option) => [option.id, option]));
    const cabinTypes = [
      ...new Set(
        draft.bookings
          .map((booking) => optionById.get(booking.group_inventory_id)?.cabin_type)
          .filter((value): value is string => Boolean(value)),
      ),
    ];
    const totalCabins = draft.bookings.reduce((sum, booking) => sum + booking.cabins_requested, 0);

    setForm({
      ...emptyRequestForm,
      group_id: draft.groupId,
      group_bookings: draft.bookings,
      cruise_lines: [draft.groupSummary.cruise_line],
      ship_name: draft.groupSummary.ship_name,
      departure_date: draft.groupSummary.sailing_date,
      return_date: draft.groupSummary.disembarkation_date,
      cabin_types: cabinTypes,
      cabins_needed: totalCabins,
      passengers: Math.max(2, totalCabins * 2),
    });
  }

  async function handleGroupInventoryConfirm(
    bookings: TravelRequestGroupBookingInput[],
    options: AgencyGroupInventoryOption[],
  ) {
    if (!selectedPickerGroup) {
      return;
    }

    try {
      const groupDetail = await fetchAgencyGroup(selectedPickerGroup.id);
      const draft: GroupIntakeDraft = {
        groupId: selectedPickerGroup.id,
        groupSummary: selectedPickerGroup,
        groupAmenities: groupDetail.group_amenities,
        bookings,
        inventoryOptions: options,
      };
      setGroupIntakeDraft(draft);
      applyGroupIntakeToForm(draft);
      setGroupInventoryOpen(false);
      setSelectedPickerGroup(null);
      setMessage("");
      setError("");
      setCreationNote("");
      setView({ type: "new" });
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load group block details.");
    }
  }

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
      if (!getToken("crm")) {
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
    if (view.type === "tasks") {
      setView({ type: "workflows" });
    }
  }, [view.type]);

  useEffect(() => {
    if (
      (view.type === "team" || view.type === "workflows" || view.type === "group-blocks") &&
      currentUser &&
      !isTenantSuperUser(currentUser.role)
    ) {
      setView({ type: "dashboard" });
    }
  }, [currentUser, view.type]);

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
    if (view.type === "team") {
      document.title = brandedDocumentTitle("Team");
      return;
    }
    if (view.type === "workflows") {
      document.title = brandedDocumentTitle("Workflows & Tasks");
      return;
    }
    if (view.type === "group-blocks") {
      document.title = brandedDocumentTitle("Group Blocks");
      return;
    }
    if (view.type === "marketing-campaigns") {
      document.title = brandedDocumentTitle("Marketing Campaigns");
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

    const leadSource = form.lead_source?.trim() || undefined;
    const payload: TravelRequestInput = {
      ...form,
      excluded_cruise_lines: form.excluded_cruise_lines ?? [],
      destination_details: ["Caribbean", "Alaska", "Asia", "Europe"].includes(form.destination)
        ? form.destination_details
        : null,
      first_passenger_date_of_birth: form.first_passenger_date_of_birth?.trim() || undefined,
      primary_passenger_id: form.primary_passenger_id,
      lead_source: leadSource,
      referral_source_name:
        leadSource === LEAD_SOURCE_REFERRAL ? form.referral_source_name?.trim() || undefined : undefined,
      marketing_campaign_id:
        leadSource === LEAD_SOURCE_MARKETING_CAMPAIGN
          ? form.marketing_campaign_id?.trim() || undefined
          : undefined,
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
          setGroupIntakeDraft(null);
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
      setGroupIntakeDraft(null);
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
            currentUser={currentUser}
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
              if (item === "marketing-campaigns") {
                setView({ type: "marketing-campaigns" });
                return;
              }
              if (item === "reports") {
                setView({ type: "reports" });
                return;
              }
              if (item === "team") {
                setView({ type: "team" });
                return;
              }
              if (item === "workflows") {
                setView({ type: "workflows" });
                return;
              }
              if (item === "group-blocks") {
                setView({ type: "group-blocks" });
                return;
              }
              if (item === "clients") {
                setView({ type: "clients" });
                return;
              }
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
              setGroupRequestPromptOpen(true);
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

      {view.type === "marketing-campaigns" ? <MarketingCampaignsPage /> : null}

      {view.type === "workflows" && currentUser ? <WorkflowsPage /> : null}

      {view.type === "group-blocks" && currentUser ? <GroupBlocksPage /> : null}

      {view.type === "clients" ? <ClientsPage /> : null}

      {view.type === "team" && currentUser ? <TeamPage currentUser={currentUser} /> : null}

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
                  showLeadAttribution
                  groupIntakeDraft={groupIntakeDraft}
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

      <GroupBlockRequestPromptModal
        open={groupRequestPromptOpen}
        onCancel={() => setGroupRequestPromptOpen(false)}
        onChooseStandard={() => {
          setGroupRequestPromptOpen(false);
          beginStandardNewRequest();
        }}
        onChooseGroupBlock={() => {
          setGroupRequestPromptOpen(false);
          setGroupPickerOpen(true);
        }}
      />

      <GroupBlockPickerModal
        open={groupPickerOpen}
        onClose={() => {
          setGroupPickerOpen(false);
          setGroupRequestPromptOpen(true);
        }}
        onSelect={(group) => {
          setSelectedPickerGroup(group);
          setGroupPickerOpen(false);
          setGroupInventoryOpen(true);
        }}
      />

      <GroupInventoryBookingModal
        open={groupInventoryOpen}
        group={selectedPickerGroup}
        onClose={() => {
          setGroupInventoryOpen(false);
          setGroupPickerOpen(true);
        }}
        onConfirm={(bookings, options) => {
          void handleGroupInventoryConfirm(bookings, options);
        }}
      />
        </div>
      </div>
    </main>
  );
}

export default App;
