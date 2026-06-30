import type { ReportId } from "./reportsCatalog";
import type { UserRole } from "./tenantRoles";

export type User = {
  id: number;
  agency_id: string | null;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  can_view_all_agency_leads: boolean;
};

export type UserAudit = {
  id: number;
  username: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type LoginInput = {
  organization_handle: string;
  username: string;
  password: string;
};

export type BridgeLoginInput = {
  username: string;
  password: string;
};

export type BridgeAgencySummary = {
  id: string;
  name: string;
  organization_handle: string;
  subscription_state: string;
  is_active: boolean;
  created_at: string;
};

export type BridgeInvitationSummary = {
  id: string;
  target_agency_name: string;
  target_organization_handle: string;
  invite_email: string;
  expires_at: string;
  is_used: boolean;
  token_status: string;
};

export type BridgeSummary = {
  agencies: BridgeAgencySummary[];
  invitations: BridgeInvitationSummary[];
};

export type BridgeTenantUser = {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
};

export type BridgeTenantDetail = {
  agency: BridgeAgencySummary;
  users: BridgeTenantUser[];
};

export type BridgeTenantUpdate = {
  name: string;
  organization_handle: string;
  subscription_state: string;
};

export type PlatformInviteCreate = {
  target_agency_name: string;
  target_organization_handle: string;
  invite_email: string;
};

export type PlatformInviteCreated = {
  invitation_id: string;
  onboarding_path: string;
  expires_at: string;
};

export type OnboardingInvite = {
  target_agency_name: string;
  organization_handle: string;
  invite_email: string;
  expires_at: string;
};

export type OnboardingAcceptInput = {
  token: string;
  full_name: string;
  password: string;
};

export type AgencyTeamMember = {
  id: number;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
};

export type AgencyPendingInvite = {
  id: string;
  invite_email: string;
  role: string;
  expires_at: string;
  token_status: string;
};

export type AgencyTeamSummary = {
  users: AgencyTeamMember[];
  invitations: AgencyPendingInvite[];
};

export type AgencyInviteCreate = {
  invite_email: string;
  role?: UserRole;
};

export type AgencyInviteCreated = {
  invitation_id: string;
  onboarding_path: string;
  expires_at: string;
};

export type AgencyUserUpdate = {
  role?: UserRole;
  is_active?: boolean;
  email?: string;
};

export type AgentInvite = {
  agency_name: string;
  organization_handle: string;
  invite_email: string;
  role: string;
  expires_at: string;
};

export type DestinationDetails = {
  caribbean_regions?: string[];
  alaska_options?: string[];
  asia_regions?: string[];
  europe_regions?: string[];
};

export type DestinationDetailField = keyof DestinationDetails;

export type Attachment = {
  id: number;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  created_by: UserAudit;
  created_at: string;
};

export type AttachmentKind = "transcripts" | "chats";

export type PassengerProfile = {
  id: number;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
  date_of_birth: string | null;
  qualifiers: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ClientListItem = {
  id: number;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
  date_of_birth: string | null;
  qualifiers: string[];
  is_active: boolean;
  request_count: number;
};

export type ClientsPage = {
  items: ClientListItem[];
  total: number;
  registry_count: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type ClientDetail = PassengerProfile & {
  address_line_1: string | null;
  address_line_2: string | null;
  city: string | null;
  state_or_province: string | null;
  postal_code: string | null;
  country: string | null;
  request_count?: number;
};

export type ClientUpdateInput = {
  first_name?: string;
  last_name?: string;
  email?: string | null;
  phone?: string | null;
  date_of_birth?: string | null;
  address_line_1?: string | null;
  address_line_2?: string | null;
  city?: string | null;
  state_or_province?: string | null;
  postal_code?: string | null;
  country?: string | null;
  qualifiers?: string[];
};

export type ClientCreateInput = {
  first_name: string;
  last_name: string;
  email?: string | null;
  phone?: string | null;
  date_of_birth?: string | null;
  address_line_1?: string | null;
  address_line_2?: string | null;
  city?: string | null;
  state_or_province?: string | null;
  postal_code?: string | null;
  country?: string | null;
  qualifiers?: string[];
};

export type RequestPassenger = {
  id: number;
  passenger_id: number;
  is_primary: boolean;
  passenger_is_active: boolean;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
  date_of_birth: string | null;
  address_line_1: string | null;
  address_line_2: string | null;
  city: string | null;
  state_or_province: string | null;
  postal_code: string | null;
  country: string | null;
  qualifiers: string[];
  created_at: string;
  updated_at: string;
};

export type RequestPassengerInput = {
  passenger_id?: number;
  first_name?: string;
  last_name?: string;
  email?: string | null;
  phone?: string | null;
  date_of_birth?: string | null;
  address_line_1?: string | null;
  address_line_2?: string | null;
  city?: string | null;
  state_or_province?: string | null;
  postal_code?: string | null;
  country?: string | null;
  qualifiers?: string[];
};

export type RequestNoteAudit = {
  id: number;
  from_summary: string | null;
  to_summary: string | null;
  from_content: string | null;
  to_content: string | null;
  changed_by: UserAudit;
  changed_at: string;
};

export type TravelRequestAudit = {
  id: number;
  field_name: string;
  from_value: string | null;
  to_value: string | null;
  changed_by: UserAudit;
  changed_at: string;
};

export type RequestPassengerAudit = {
  id: number;
  request_passenger_id: number | null;
  passenger_label: string | null;
  field_name: string;
  from_value: string | null;
  to_value: string | null;
  changed_by: UserAudit;
  changed_at: string;
};

export type RequestNote = {
  id: number;
  summary: string;
  content: string;
  created_by: UserAudit;
  updated_by: UserAudit;
  created_at: string;
  updated_at: string;
  audits: RequestNoteAudit[];
};

export type RequestNoteSummary = Omit<RequestNote, "content" | "audits">;

export type RequestNoteInput = {
  summary: string;
  content: string;
};

export type NamedInclude = {
  included: boolean;
  name?: string | null;
};

export type CreditInclude = {
  included: boolean;
  amount?: number | null;
};

export type CabinPricingEntry = {
  deposit_amount: number;
  cost: number;
};

export type ProposedCruiseIncludes = {
  drink_package: NamedInclude;
  wifi: NamedInclude;
  excursion_credit: CreditInclude;
  onboard_credit: CreditInclude;
  gift_obc: CreditInclude;
  tips: boolean;
  excursion: boolean;
};

export type ProposedCruiseRoom = {
  room_category: string;
  room_number: string;
  passengers_in_room: number;
  deposit_amount: number;
  commission: number;
  cost: number;
  includes: ProposedCruiseIncludes;
};

export type ProposedCruise = {
  id: number;
  departure_date: string;
  cruise_line: string;
  ship: string;
  number_of_nights: number;
  itinerary_name: string;
  itinerary_details?: string | null;
  room_category: string;
  room_number: string;
  passengers_in_room: number;
  deposit_amount: number;
  deposit_due_date: string;
  final_payment_due_date: string;
  cost: number;
  cabin_pricing: CabinPricingEntry[];
  cabin_rooms: ProposedCruiseRoom[];
  cabin_hold_reservation_ids?: string[][];
  includes: ProposedCruiseIncludes;
  status: string;
  rejection_reason?: string | null;
  rejection_reason_detail?: string | null;
  passengers: RequestPassenger[];
  room_passengers: RequestPassenger[][];
  created_by: UserAudit;
  updated_by: UserAudit;
  created_at: string;
  updated_at: string;
};

export type GeneratedProposedCruisesResponse = {
  research_document_id: number;
  research_document_filename: string;
  model: string;
  cruises: ProposedCruiseInput[];
};

export type GeneratedResearchCommunicationResponse = {
  model: string;
  proposed_cruise_count: number;
  subject: string;
  email_subject: string;
  body: string;
  communication: RequestCommunication;
};

export type ProposedCruiseInput = {
  departure_date: string;
  cruise_line: string;
  ship: string;
  number_of_nights: number;
  itinerary_name: string;
  itinerary_details?: string | null;
  room_category: string;
  room_number: string;
  passengers_in_room: number;
  deposit_amount: number;
  deposit_due_date: string;
  final_payment_due_date: string;
  cost: number;
  cabin_pricing?: CabinPricingEntry[];
  cabin_rooms?: ProposedCruiseRoom[];
  cabin_hold_reservation_ids?: string[][];
  includes: ProposedCruiseIncludes;
  room_passenger_ids: number[][];
  passenger_ids: number[];
  status?: string;
  rejection_reason?: string;
  rejection_reason_detail?: string;
};

export type QuotedInsurance = {
  id: number;
  carrier: string;
  premium_cost: number;
  plan_name: string;
  cancellation_coverage: number;
  medical_coverage: number;
  medical_evac_coverage: number;
  status: string;
  declined_at: string | null;
  created_by: UserAudit;
  updated_by: UserAudit;
  created_at: string;
  updated_at: string;
};

export type QuotedInsuranceInput = {
  carrier: string;
  premium_cost: number;
  plan_name: string;
  cancellation_coverage: number;
  medical_coverage: number;
  medical_evac_coverage: number;
  status?: string;
};

export type TravelRequest = {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  cruise_lines: string[];
  excluded_cruise_lines: string[];
  destination: string;
  destination_details: DestinationDetails | null;
  departure_date: string;
  return_date: string;
  cabin_types: string[];
  passengers: number;
  cabins_needed: number;
  cabin_hold_reservation_ids: string[][];
  status: string;
  close_reason: string | null;
  lead_source: string | null;
  referral_source_name: string | null;
  marketing_campaign_id: string | null;
  created_by: UserAudit;
  updated_by: UserAudit;
  created_at: string;
  updated_at: string;
};

export type ResearchDocument = {
  id: number;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  uploaded_by: UserAudit;
  created_at: string;
};

export type RequestTask = {
  id: string;
  task_key: string;
  title: string;
  description: string | null;
  status: string;
  sort_order: number;
  action_type: string;
  is_completed: boolean;
  due_at: string | null;
  completed_at: string | null;
  completed_by: UserAudit | null;
  result: Record<string, unknown> | null;
  prerequisite_task_keys: string[] | null;
  created_at: string;
  updated_at: string;
};

export type RequestWorkflow = {
  id: string;
  workflow_type: string;
  workflow_name: string;
  status: string;
  parent_workflow_id: string | null;
  context: Record<string, unknown> | null;
  started_by: UserAudit;
  completed_by: UserAudit | null;
  tasks: RequestTask[];
  created_at: string;
  updated_at: string;
  completed_at: string | null;
};

export type RequestCommunication = {
  id: number;
  communication_type: string;
  subject: string;
  body: string;
  status: string;
  request_workflow_id: string | null;
  sent_at: string | null;
  created_by: UserAudit;
  updated_by: UserAudit;
  created_at: string;
  updated_at: string;
};

export type RequestCommunicationSummary = Omit<RequestCommunication, "body">;

export type RequestChangeHistory = {
  request_audits: TravelRequestAudit[];
  passenger_audits: RequestPassengerAudit[];
};

export type WorkflowTemplate = {
  id: string;
  workflow_type: string;
  name: string;
  description: string;
};

export type AgencyTaskTemplate = {
  id: string;
  task_title: string;
  sequence_order: number;
  action_type: string;
  target_field: string | null;
  task_key: string | null;
  description: string | null;
  prerequisite_task_keys: string[] | null;
};

export type AgencyWorkflowTemplate = {
  id: string;
  workflow_name: string;
  description: string | null;
  workflow_type_key: string | null;
  successor_template_id: string | null;
  created_at: string;
  task_templates: AgencyTaskTemplate[];
};

export type AgencyTaskCatalogItem = {
  task_key: string;
  task_title: string;
  description: string;
  action_type: string;
  prerequisite_task_keys: string[];
};

export type AgencyTaskAvailability = {
  available_tasks: AgencyTaskCatalogItem[];
  placed_task_keys: string[];
  available_count: number;
};

export type RequestCommunicationInput = {
  communication_type: string;
  subject: string;
  body: string;
  request_workflow_id?: string | null;
  status?: string;
};

export type ClosedRequestsPage = {
  items: TravelRequest[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type OpenRequestsPage = {
  items: DashboardOpenRequest[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type TravelRequestDetail = TravelRequest & {
  last_worked_at: string;
  last_worked_by: UserAudit;
  request_passengers: RequestPassenger[];
  request_notes: RequestNoteSummary[];
  call_transcripts: Attachment[];
  chat_logs: Attachment[];
  proposed_cruises: ProposedCruise[];
  quoted_insurance: QuotedInsurance[];
  request_workflows: RequestWorkflow[];
  request_communications: RequestCommunicationSummary[];
  research_documents: ResearchDocument[];
};

export type DashboardNextOpenTask = {
  id: string;
  task_key: string;
  title: string;
  workflow_type: string;
  workflow_name: string;
};

export type DashboardOpenRequest = TravelRequest & {
  is_stale: boolean;
  next_open_task: DashboardNextOpenTask | null;
  last_worked_at: string;
  last_worked_by: UserAudit;
};

export type DashboardData = {
  open_count: number;
  stale_count: number;
  closed_count: number;
  purchased_closed_count: number;
  other_closed_count: number;
  successful_sales_close_rate: number | null;
  total_pipeline_value: number;
};

export type TravelRequestInput = {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  cruise_lines: string[];
  excluded_cruise_lines?: string[];
  destination: string;
  destination_details?: DestinationDetails | null;
  departure_date: string;
  return_date: string;
  cabin_types: string[];
  passengers: number;
  cabins_needed: number;
  first_passenger_date_of_birth?: string;
  primary_passenger_id?: number;
  /** Primary passenger discounts; set at create time only, not edited on the request form. */
  qualifiers?: string[];
  lead_source?: string;
  referral_source_name?: string;
  marketing_campaign_id?: string;
};

export type TravelRequestUpdateInput = Partial<TravelRequestInput> & {
  status?: string;
  close_reason?: string | null;
  cabin_hold_reservation_ids?: string[][] | null;
};

export type RegisterInput = {
  username: string;
  email: string;
  password: string;
};


export type AppView =
  | { type: "dashboard" }
  | { type: "sales-analytics" }
  | { type: "marketing-campaigns" }
  | { type: "workflows" }
  | { type: "clients" }
  | { type: "reports" }
  | { type: "report"; reportId: ReportId }
  | { type: "team" }
  | { type: "closed" }
  | { type: "new" }
  | { type: "edit"; requestId: number };

export type AppNavItem =
  | "dashboard"
  | "sales-analytics"
  | "marketing-campaigns"
  | "workflows"
  | "clients"
  | "reports"
  | "team";

export type MarketingCampaign = {
  id: string;
  agency_id: string;
  campaign_name: string;
  campaign_type: string;
  monthly_spend: number;
  start_date: string;
  end_date: string | null;
  created_at: string;
};

export type MarketingCampaignInput = {
  campaign_name: string;
  campaign_type: string;
  monthly_spend: number;
  start_date: string;
  end_date?: string;
};

export type MarketingCampaignUpdateInput = Partial<MarketingCampaignInput> & {
  end_date?: string | null;
};

export type MarketingCampaignTimeframe = "all" | "active" | "past";

export type MarketingCampaignSummary = {
  active_monthly_budget: number;
  top_roi_campaign_name: string | null;
  top_roi_percent: number | null;
  total_attributed_volume: number;
};

export type SalesAnalyticsMonthCommission = {
  month_key: string;
  label: string;
  total_commission: number;
  booking_count: number;
};

export type SalesAnalyticsFunnelStage = {
  label: string;
  count: number;
};

export type SalesAnalyticsRejectionReason = {
  segment: string;
  reason: string;
  count: number;
};

export type SalesAnalyticsCruiseLineShare = {
  cruise_line: string;
  booking_count: number;
  share_percent: number;
  total_booking_amount: number;
  total_commission: number;
  median_booking_amount: number;
  commission_rate_percent: number;
};

export type SalesAnalyticsYearSummary = {
  year: number;
  total_sales_booked: number;
  total_sales_lost: number;
  average_commission_rate_percent: number | null;
  win_rate_percent: number | null;
};

export type SalesAnalyticsData = {
  commission_timeline: SalesAnalyticsMonthCommission[];
  funnel_stages: SalesAnalyticsFunnelStage[];
  win_rate_percent: number | null;
  rejection_reasons: SalesAnalyticsRejectionReason[];
  cruise_line_shares: SalesAnalyticsCruiseLineShare[];
  current_year_summary: SalesAnalyticsYearSummary;
  key_metrics_prior_years: number[];
  total_commission_forecast: number;
  available_years: number[];
};

export type ClientImportTargetField = {
  field_name: string;
  required: boolean;
  description: string;
};

export type ClientImportParseResponse = {
  filename: string;
  sheet_name: string | null;
  source_columns: string[];
  preview_rows: string[][];
  target_fields: ClientImportTargetField[];
  suggested_mapping: Record<string, string | null>;
};

export type ClientImportRowError = {
  row_number: number;
  record_label: string;
  message: string;
};

export type ClientImportResult = {
  imported_count: number;
  skipped_count: number;
  errors: ClientImportRowError[];
};

export type ReportWorkflowTaskOption = {
  value: string;
  label: string;
};

export type ReportWorkflowTaskGroup = {
  workflow_type: string;
  workflow_name: string;
  tasks: ReportWorkflowTaskOption[];
};

export type ReportMeta = {
  workflow_task_groups: ReportWorkflowTaskGroup[];
  advisor_names: string[];
  residence_states: string[];
};

export type ReportManifestRow = {
  request_id: number;
  request_status: string;
  pipeline_status: string;
  close_reason: string | null;
  primary_passenger: string;
  destination: string;
  cruise_line: string;
  sailing_month_year: string;
  estimated_gross_booking_total: number;
  projected_commission_target: number;
  owner_agent: string;
  current_task: DashboardNextOpenTask | null;
};

export type SalesManifestPage = {
  items: ReportManifestRow[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type ReportSupplierLedgerRow = {
  cruise_line: string;
  active_booking_count: number;
  total_volume: number;
  total_commission_booked: number;
  median_price_per_room: number;
  average_commission_rate_percent: number;
  share_percent: number;
};

export type SupplierLedgerPage = {
  items: ReportSupplierLedgerRow[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type FunnelLeakRow = {
  request_id: number;
  client_name: string;
  quoted_cruise_line: string;
  quoted_destination: string;
  estimated_value_lost: number;
  primary_rejection_reason: string;
  loss_segment: string;
};

export type FunnelLeakPage = {
  items: FunnelLeakRow[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type AdvisorScorecardRow = {
  advisor_name: string;
  active_lead_count: number;
  proposals_pending: number;
  completed_bookings: number;
  avg_pipeline_velocity_days: number | null;
  request_to_close_ratio_percent: number | null;
};

export type AdvisorScorecardPage = {
  items: AdvisorScorecardRow[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type PassengerDemographicsRow = {
  passenger_id: number;
  passenger_name: string;
  date_of_birth: string | null;
  state_of_residence: string | null;
  contact_phone: string | null;
  email_address: string | null;
  qualifiers: string[];
};

export type PassengerDemographicsPage = {
  items: PassengerDemographicsRow[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};
