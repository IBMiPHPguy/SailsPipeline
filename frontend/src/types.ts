export type User = {
  id: number;
  username: string;
  email: string;
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
  is_active: boolean;
  request_count: number;
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
  includes: ProposedCruiseIncludes;
  status: string;
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
  includes: ProposedCruiseIncludes;
  room_passenger_ids: number[][];
  passenger_ids: number[];
  status?: string;
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
  id: number;
  task_key: string;
  title: string;
  description: string | null;
  status: string;
  sort_order: number;
  due_at: string | null;
  completed_at: string | null;
  completed_by: UserAudit | null;
  result: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type RequestWorkflow = {
  id: number;
  workflow_type: string;
  status: string;
  parent_workflow_id: number | null;
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
  request_workflow_id: number | null;
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
  workflow_type: string;
  name: string;
  description: string;
};

export type RequestCommunicationInput = {
  communication_type: string;
  subject: string;
  body: string;
  request_workflow_id?: number | null;
  status?: string;
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
  id: number;
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
  open_requests: DashboardOpenRequest[];
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
  | { type: "clients" }
  | { type: "closed" }
  | { type: "new" }
  | { type: "edit"; requestId: number };

export type AppNavItem = "dashboard" | "clients";
