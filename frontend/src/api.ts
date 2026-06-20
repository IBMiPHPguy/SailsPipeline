import { authHeaders, parseApiError } from "./apiClient";
import type {
  Attachment,
  AttachmentKind,
  ClientCreateInput,
  ClientDetail,
  ClientImportParseResponse,
  ClientImportResult,
  ClientListItem,
  ClientsPage,
  ClientUpdateInput,
  ClosedRequestsPage,
  DashboardData,
  DashboardOpenRequest,
  OpenRequestsPage,
  ReportMeta,
  SalesManifestPage,
  SupplierLedgerPage,
  FunnelLeakPage,
  AdvisorScorecardPage,
  PassengerDemographicsPage,
  SalesAnalyticsData,
  SalesAnalyticsYearSummary,
  RequestNote,
  RequestNoteInput,
  RequestPassenger,
  RequestPassengerInput,
  TravelRequest,
  TravelRequestDetail,
  TravelRequestInput,
  TravelRequestUpdateInput,
  PassengerProfile,
  ProposedCruise,
  ProposedCruiseInput,
  GeneratedProposedCruisesResponse,
  GeneratedResearchCommunicationResponse,
  QuotedInsurance,
  QuotedInsuranceInput,
  RequestCommunication,
  RequestCommunicationInput,
  RequestChangeHistory,
  RequestWorkflow,
  ResearchDocument,
  WorkflowTemplate,
} from "./types";

import { API_BASE } from "./apiClient";
import {
  advisorScorecardFiltersToQuery,
  funnelLeakFiltersToQuery,
  ledgerFiltersToQuery,
  passengerDemographicsFiltersToQuery,
  reportFiltersToQuery,
  type ReportFilterState,
} from "./reportFilters";

export async function fetchDashboard(): Promise<DashboardData> {
  const response = await fetch(`${API_BASE}/dashboard`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load request dashboard."));
  }
  return response.json();
}

export async function fetchSalesAnalytics(): Promise<SalesAnalyticsData> {
  const response = await fetch(`${API_BASE}/analytics/sales`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load sales analytics."));
  }
  return response.json();
}

export async function fetchReportMeta(): Promise<ReportMeta> {
  const response = await fetch(`${API_BASE}/reports/meta`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load report filters."));
  }
  return response.json();
}

export async function fetchSalesManifest(
  filters: ReportFilterState,
  page = filters.page,
): Promise<SalesManifestPage> {
  const params = reportFiltersToQuery({ ...filters, page });
  const response = await fetch(`${API_BASE}/reports/sales-manifest?${params.toString()}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load sales manifest report."));
  }
  return response.json();
}

export async function fetchSupplierLedger(
  filters: ReportFilterState,
  page = filters.page,
): Promise<SupplierLedgerPage> {
  const params = ledgerFiltersToQuery({ ...filters, page });
  const response = await fetch(`${API_BASE}/reports/supplier-ledger?${params.toString()}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load supplier ledger report."));
  }
  return response.json();
}

export async function fetchFunnelLeakReport(
  filters: ReportFilterState,
  page = filters.page,
): Promise<FunnelLeakPage> {
  const params = funnelLeakFiltersToQuery({ ...filters, page });
  const response = await fetch(`${API_BASE}/reports/funnel-leak?${params.toString()}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load funnel leak report."));
  }
  return response.json();
}

export async function fetchAdvisorScorecard(
  filters: ReportFilterState,
  page = filters.page,
): Promise<AdvisorScorecardPage> {
  const params = advisorScorecardFiltersToQuery({ ...filters, page });
  const response = await fetch(`${API_BASE}/reports/advisor-scorecard?${params.toString()}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load advisor scorecard report."));
  }
  return response.json();
}

export async function fetchPassengerDemographics(
  filters: ReportFilterState,
  page = filters.page,
): Promise<PassengerDemographicsPage> {
  const params = passengerDemographicsFiltersToQuery({ ...filters, page });
  const response = await fetch(`${API_BASE}/reports/passenger-demographics?${params.toString()}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load passenger demographics report."));
  }
  return response.json();
}

export async function fetchSalesAnalyticsKeyMetrics(year: number): Promise<SalesAnalyticsYearSummary> {
  const response = await fetch(`${API_BASE}/analytics/sales/key-metrics/${year}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, `Unable to load ${year} key metrics.`));
  }
  return response.json();
}

export async function downloadClientImportTemplate(): Promise<void> {
  const response = await fetch(`${API_BASE}/analytics/sales/client-import/template`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to download the client migration template."));
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filenameMatch = disposition.match(/filename="([^"]+)"/i);
  const filename = filenameMatch?.[1] ?? "SailsPipeline-Client-Migration-Template.xlsx";
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(objectUrl);
}

export async function parseClientImportFile(file: File): Promise<ClientImportParseResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/analytics/sales/client-import/parse`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to read the uploaded spreadsheet."));
  }
  return response.json();
}

export async function importClientSpreadsheet(
  file: File,
  mapping: Record<string, string | null>,
): Promise<ClientImportResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("mapping", JSON.stringify(mapping));

  const response = await fetch(`${API_BASE}/analytics/sales/client-import`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to import clients."));
  }
  return response.json();
}

export async function askSalesCopilot(question: string): Promise<string> {
  const response = await fetch(`${API_BASE}/analytics/sales/copilot`, {
    method: "POST",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to get a copilot answer."));
  }
  const payload = (await response.json()) as { answer: string };
  return payload.answer;
}

export type OpenRequestsQuery = {
  q?: string;
  page?: number;
  pageSize?: number;
};

export async function fetchOpenRequests(query: OpenRequestsQuery = {}): Promise<OpenRequestsPage> {
  const params = new URLSearchParams();
  const trimmedQuery = query.q?.trim();
  if (trimmedQuery) {
    params.set("q", trimmedQuery);
  }
  if (query.page && query.page > 1) {
    params.set("page", String(query.page));
  }
  if (query.pageSize) {
    params.set("page_size", String(query.pageSize));
  }

  const suffix = params.toString() ? `?${params.toString()}` : "";
  const response = await fetch(`${API_BASE}/requests/open${suffix}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load open requests."));
  }
  return response.json();
}

export async function fetchRequests(): Promise<TravelRequest[]> {
  const response = await fetch(`${API_BASE}/requests`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load travel requests."));
  }
  return response.json();
}

export type ClosedRequestsQuery = {
  q?: string;
  page?: number;
  pageSize?: number;
};

export async function fetchClosedRequests(query: ClosedRequestsQuery = {}): Promise<ClosedRequestsPage> {
  const params = new URLSearchParams();
  const trimmedQuery = query.q?.trim();
  if (trimmedQuery) {
    params.set("q", trimmedQuery);
  }
  if (query.page && query.page > 1) {
    params.set("page", String(query.page));
  }
  if (query.pageSize) {
    params.set("page_size", String(query.pageSize));
  }

  const suffix = params.toString() ? `?${params.toString()}` : "";
  const response = await fetch(`${API_BASE}/requests/closed${suffix}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load closed requests."));
  }
  return response.json();
}

export async function reopenRequest(requestId: number): Promise<TravelRequest> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/reopen`, {
    method: "POST",
    headers: authHeaders(true),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to reopen request."));
  }
  return response.json();
}

export async function fetchRequest(requestId: number): Promise<TravelRequestDetail> {
  const response = await fetch(`${API_BASE}/requests/${requestId}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load travel request."));
  }
  return response.json();
}

export async function fetchRequestChangeHistory(requestId: number): Promise<RequestChangeHistory> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/change-history`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load change history."));
  }
  return response.json();
}

export async function fetchRequestNotes(requestId: number): Promise<RequestNote[]> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/notes`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load notes."));
  }
  return response.json();
}

export async function fetchNote(requestId: number, noteId: number): Promise<RequestNote> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/notes/${noteId}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load note."));
  }
  return response.json();
}

export async function fetchCommunication(
  requestId: number,
  communicationId: number,
): Promise<RequestCommunication> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/communications/${communicationId}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load communication."));
  }
  return response.json();
}

export async function createRequest(payload: TravelRequestInput): Promise<TravelRequest> {
  const response = await fetch(`${API_BASE}/requests`, {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Request failed."));
  }

  return response.json();
}

export async function updateRequest(
  requestId: number,
  payload: TravelRequestUpdateInput,
): Promise<TravelRequestDetail> {
  const response = await fetch(`${API_BASE}/requests/${requestId}`, {
    method: "PATCH",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Update failed."));
  }

  return response.json();
}

export async function uploadTranscript(requestId: number, file: File): Promise<Attachment> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/requests/${requestId}/transcripts`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to upload call transcript."));
  }

  return response.json();
}

export async function uploadChatLog(requestId: number, file: File): Promise<Attachment> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/requests/${requestId}/chats`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to upload chat log."));
  }

  return response.json();
}

export async function generateCommunicationAiSummary(
  requestId: number,
  kind: AttachmentKind,
  attachmentId: number,
): Promise<RequestNoteInput> {
  const response = await fetch(
    `${API_BASE}/requests/${requestId}/${kind}/${attachmentId}/ai-summary`,
    {
      method: "POST",
      headers: authHeaders(),
    },
  );

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to generate AI summary."));
  }

  return response.json();
}

export async function fetchAttachmentContent(
  requestId: number,
  kind: AttachmentKind,
  attachmentId: number,
): Promise<string> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/${kind}/${attachmentId}/content`, {
    headers: authHeaders(),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load attachment."));
  }

  return response.text();
}

export async function searchPassengers(query = "", limit = 20): Promise<PassengerProfile[]> {
  const params = new URLSearchParams();
  if (query.trim()) {
    params.set("q", query.trim());
  }
  params.set("limit", String(limit));

  const response = await fetch(`${API_BASE}/passengers/search?${params.toString()}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to search passengers."));
  }
  return response.json();
}

export type ClientsQuery = {
  q?: string;
  page?: number;
  pageSize?: number;
};

export async function fetchClients(query: ClientsQuery = {}): Promise<ClientsPage> {
  const params = new URLSearchParams();
  const trimmedQuery = query.q?.trim();
  if (trimmedQuery) {
    params.set("q", trimmedQuery);
  }
  if (query.page && query.page > 1) {
    params.set("page", String(query.page));
  }
  if (query.pageSize) {
    params.set("page_size", String(query.pageSize));
  }

  const suffix = params.toString() ? `?${params.toString()}` : "";
  const response = await fetch(`${API_BASE}/passengers${suffix}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load clients."));
  }
  return response.json();
}

export async function fetchClient(clientId: number): Promise<ClientDetail> {
  const response = await fetch(`${API_BASE}/passengers/${clientId}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load client."));
  }
  return response.json();
}

export async function createClient(payload: ClientCreateInput): Promise<ClientDetail> {
  const response = await fetch(`${API_BASE}/passengers`, {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to add client."));
  }
  return response.json();
}

export async function updateClient(clientId: number, payload: ClientUpdateInput): Promise<ClientDetail> {
  const response = await fetch(`${API_BASE}/passengers/${clientId}`, {
    method: "PATCH",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to update client."));
  }
  return response.json();
}

export async function deactivateClient(clientId: number): Promise<ClientDetail> {
  const response = await fetch(`${API_BASE}/passengers/${clientId}/deactivate`, {
    method: "POST",
    headers: authHeaders(true),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to deactivate client."));
  }
  return response.json();
}

export async function activateClient(clientId: number): Promise<ClientDetail> {
  const response = await fetch(`${API_BASE}/passengers/${clientId}/activate`, {
    method: "POST",
    headers: authHeaders(true),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to reactivate client."));
  }
  return response.json();
}

export async function addPassenger(
  requestId: number,
  payload: RequestPassengerInput,
): Promise<RequestPassenger> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/passengers`, {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to add passenger."));
  }

  return response.json();
}

export async function updatePassenger(
  requestId: number,
  passengerId: number,
  payload: RequestPassengerInput,
): Promise<RequestPassenger> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/passengers/${passengerId}`, {
    method: "PATCH",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to update passenger."));
  }

  return response.json();
}

export async function deletePassenger(requestId: number, passengerId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/passengers/${passengerId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to delete passenger."));
  }
}

export async function addNote(requestId: number, payload: RequestNoteInput): Promise<RequestNote> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/notes`, {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to add note."));
  }

  return response.json();
}

export async function updateNote(
  requestId: number,
  noteId: number,
  payload: RequestNoteInput,
): Promise<RequestNote> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/notes/${noteId}`, {
    method: "PATCH",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to update note."));
  }

  return response.json();
}

export async function addProposedCruise(
  requestId: number,
  payload: ProposedCruiseInput,
): Promise<ProposedCruise> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/proposed-cruises`, {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to add proposed cruise."));
  }

  return response.json();
}

export async function updateProposedCruise(
  requestId: number,
  cruiseId: number,
  payload: Partial<ProposedCruiseInput>,
): Promise<ProposedCruise> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/proposed-cruises/${cruiseId}`, {
    method: "PATCH",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to update proposed cruise."));
  }

  return response.json();
}

export async function addQuotedInsurance(
  requestId: number,
  payload: QuotedInsuranceInput,
): Promise<QuotedInsurance> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/quoted-insurance`, {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to add insurance quote."));
  }

  return response.json();
}

export async function updateQuotedInsurance(
  requestId: number,
  quoteId: number,
  payload: QuotedInsuranceInput,
): Promise<QuotedInsurance> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/quoted-insurance/${quoteId}`, {
    method: "PATCH",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to update insurance quote."));
  }

  return response.json();
}

export async function fetchWorkflowTemplates(): Promise<WorkflowTemplate[]> {
  const response = await fetch(`${API_BASE}/workflow-templates`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load workflow templates."));
  }
  return response.json();
}

export async function startWorkflow(
  requestId: number,
  workflowType: string,
  parentWorkflowId?: number | null,
): Promise<RequestWorkflow> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/workflows`, {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify({
      workflow_type: workflowType,
      parent_workflow_id: parentWorkflowId ?? null,
    }),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to start workflow."));
  }
  return response.json();
}

export async function updateWorkflow(
  requestId: number,
  workflowId: number,
  payload: {
    status: string;
    close_reason?: string;
  },
): Promise<RequestWorkflow> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/workflows/${workflowId}`, {
    method: "PATCH",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to update workflow."));
  }
  return response.json();
}

export async function updateTask(
  requestId: number,
  taskId: number,
  payload: {
    status?: string;
    due_at?: string | null;
    result?: Record<string, unknown> | null;
    reached_out?: boolean;
  },
): Promise<RequestWorkflow> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/tasks/${taskId}`, {
    method: "PATCH",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to update task."));
  }
  return response.json();
}

export async function addCommunication(
  requestId: number,
  payload: RequestCommunicationInput,
): Promise<RequestCommunication> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/communications`, {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to save communication."));
  }
  return response.json();
}

export async function updateCommunication(
  requestId: number,
  communicationId: number,
  payload: Partial<RequestCommunicationInput>,
): Promise<RequestCommunication> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/communications/${communicationId}`, {
    method: "PATCH",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to update communication."));
  }
  return response.json();
}

export async function deleteCommunication(requestId: number, communicationId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/communications/${communicationId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to delete communication."));
  }
}

export async function uploadResearchDocument(requestId: number, file: File): Promise<ResearchDocument> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/requests/${requestId}/research-documents`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to upload research document."));
  }
  return response.json();
}

export async function fetchResearchDocumentContent(requestId: number, documentId: number): Promise<string> {
  const response = await fetch(
    `${API_BASE}/requests/${requestId}/research-documents/${documentId}/content`,
    { headers: authHeaders() },
  );
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load research document."));
  }
  return response.text();
}

export async function generateProposedCruisesFromResearch(
  requestId: number,
  researchDocumentId: number,
): Promise<GeneratedProposedCruisesResponse> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/proposed-cruises/generate-from-research`, {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify({ research_document_id: researchDocumentId }),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to generate proposed cruises from research."));
  }
  return response.json();
}

export async function generateResearchCommunicationFromProposals(
  requestId: number,
  requestWorkflowId: number | null,
): Promise<GeneratedResearchCommunicationResponse> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/communications/generate-from-proposals`, {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify({ request_workflow_id: requestWorkflowId }),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to generate proposal email."));
  }
  return response.json();
}

export async function addProposedCruisesBulk(
  requestId: number,
  cruises: ProposedCruiseInput[],
): Promise<ProposedCruise[]> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/proposed-cruises/bulk`, {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify({ cruises }),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to add proposed cruises."));
  }
  const payload = (await response.json()) as { cruises: ProposedCruise[] };
  return payload.cruises;
}

export async function fetchHealth(): Promise<{ status: string; service: string }> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error("API health check failed.");
  }
  return response.json();
}
