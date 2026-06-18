export const DESTINATIONS = [
  "Caribbean",
  "Alaska",
  "New England/Canada",
  "Panama Canal",
  "South America",
  "Mexican Riviera",
  "Transatlantic",
  "Transpacific",
  "Hawaii",
  "Asia",
  "Australia",
  "Europe",
  "Galapagos",
  "Antarctica",
] as const;

export const CABIN_TYPES = ["Interior", "Ocean View", "Balcony", "Suite"] as const;

export const CRUISE_LINES = [
  "AmaWaterways",
  "American Cruise Lines",
  "Atlas Ocean Voyages",
  "Avalon Waterways",
  "Azamara Cruises",
  "Carnival Cruise Lines",
  "Celebrity Cruises",
  "Costa Cruises",
  "Crystal Cruises",
  "Cunard",
  "Disney Cruise Lines",
  "Emerald Cruise",
  "Explora Journeys",
  "Holland America Line",
  "Hurtigruten",
  "Margaritaville at Sea",
  "MSC Cruises",
  "National Geographic",
  "Norwegian Cruise Line",
  "Oceania Cruises",
  "Princess Cruises",
  "Regent Seven Seas",
  "Ritz Carlton Yacht Collection",
  "Royal Caribbean International",
  "Scenic Cruises",
  "Seabourn",
  "Seadream Yacht Club",
  "Silversea Cruises",
  "Star Clippers",
  "TAUCK",
  "Uniworld River Cruise",
  "Viking Cruises",
  "Virgin Voyages",
  "Windstar Cruises",
] as const;

export const LEGACY_CRUISE_LINE_ALIASES: Record<string, (typeof CRUISE_LINES)[number]> = {
  Celebrity: "Celebrity Cruises",
  Carnival: "Carnival Cruise Lines",
  "Royal Caribbean": "Royal Caribbean International",
  Norwegian: "Norwegian Cruise Line",
  Princess: "Princess Cruises",
  "Holland America": "Holland America Line",
  Disney: "Disney Cruise Lines",
  MSC: "MSC Cruises",
  Virgin: "Virgin Voyages",
  Windstar: "Windstar Cruises",
  Silversea: "Silversea Cruises",
  Seabourn: "Seabourn",
  Oceania: "Oceania Cruises",
  Azamara: "Azamara Cruises",
  Costa: "Costa Cruises",
  Crystal: "Crystal Cruises",
  Viking: "Viking Cruises",
  Unknown: "Royal Caribbean International",
};

export function normalizeCruiseLineValue(value: string): string {
  const stripped = value.trim();
  if (!stripped) {
    return stripped;
  }
  if ((CRUISE_LINES as readonly string[]).includes(stripped)) {
    return stripped;
  }

  const lowered = stripped.toLowerCase();
  for (const line of CRUISE_LINES) {
    if (line.toLowerCase() === lowered) {
      return line;
    }
  }

  const legacy = LEGACY_CRUISE_LINE_ALIASES[stripped];
  if (legacy) {
    return legacy;
  }

  const prefixMatches = CRUISE_LINES.filter((line) => line.toLowerCase().startsWith(lowered));
  if (prefixMatches.length === 1) {
    return prefixMatches[0];
  }

  const containsMatches = CRUISE_LINES.filter((line) => line.toLowerCase().includes(lowered));
  if (containsMatches.length === 1) {
    return containsMatches[0];
  }

  return stripped;
}

export const QUALIFIERS = [
  "Military",
  "Educator",
  "First Responder",
  "55+ (Senior)",
] as const;

export const CARIBBEAN_REGIONS = ["Eastern", "Western", "Southern", "South Eastern"] as const;

export const ALASKA_OPTIONS = [
  "RT Seattle",
  "RT Vancouver",
  "Northern One Way",
  "Southern One Way",
  "Cruise tour",
] as const;

export const ASIA_OPTIONS = ["Japan", "SE Asia", "French Polynesia"] as const;

export const EUROPE_REGIONS = [
  "Eastern Med - Greece",
  "Eastern Med - Adriatic",
  "Western Med",
  "Northern - UK",
  "Northern Norway",
  "Northern Baltic",
  "Northern Iceland/Greenland",
] as const;

export const US_STATES = [
  "Alabama",
  "Alaska",
  "Arizona",
  "Arkansas",
  "California",
  "Colorado",
  "Connecticut",
  "Delaware",
  "District of Columbia",
  "Florida",
  "Georgia",
  "Hawaii",
  "Idaho",
  "Illinois",
  "Indiana",
  "Iowa",
  "Kansas",
  "Kentucky",
  "Louisiana",
  "Maine",
  "Maryland",
  "Massachusetts",
  "Michigan",
  "Minnesota",
  "Mississippi",
  "Missouri",
  "Montana",
  "Nebraska",
  "Nevada",
  "New Hampshire",
  "New Jersey",
  "New Mexico",
  "New York",
  "North Carolina",
  "North Dakota",
  "Ohio",
  "Oklahoma",
  "Oregon",
  "Pennsylvania",
  "Rhode Island",
  "South Carolina",
  "South Dakota",
  "Tennessee",
  "Texas",
  "Utah",
  "Vermont",
  "Virginia",
  "Washington",
  "West Virginia",
  "Wisconsin",
  "Wyoming",
] as const;

export const CANADIAN_PROVINCES = [
  "Alberta",
  "British Columbia",
  "Manitoba",
  "New Brunswick",
  "Newfoundland and Labrador",
  "Northwest Territories",
  "Nova Scotia",
  "Nunavut",
  "Ontario",
  "Prince Edward Island",
  "Quebec",
  "Saskatchewan",
  "Yukon",
] as const;

export const PRIMARY_CLOSE_REASON = "Purchased - Trip Created";

export const OTHER_CLOSE_REASONS = [
  "Cost - Went with Competitor",
  "Communication - Went with Competitor",
  "Changed Vacation Plans",
  "General Inquiry - Fishing",
] as const;

export const CLOSE_REASONS = [PRIMARY_CLOSE_REASON, ...OTHER_CLOSE_REASONS] as const;

export const REQUEST_STATUS_OPEN = "Open";
export const REQUEST_STATUS_CLOSED = "Closed";

export const PROPOSED_CRUISE_STATUS_PROPOSED = "Proposed";
export const PROPOSED_CRUISE_STATUS_ACCEPTED = "Accepted";
export const PROPOSED_CRUISE_STATUS_DEPOSITED = "Deposited";
export const PROPOSED_CRUISE_STATUS_REJECTED = "Rejected";
export const PROPOSED_CRUISE_STATUSES = [
  PROPOSED_CRUISE_STATUS_PROPOSED,
  PROPOSED_CRUISE_STATUS_ACCEPTED,
  PROPOSED_CRUISE_STATUS_DEPOSITED,
  PROPOSED_CRUISE_STATUS_REJECTED,
] as const;

export const QUOTED_INSURANCE_STATUS_PROPOSED = "Proposed";
export const QUOTED_INSURANCE_STATUS_DECLINED = "Declined";
export const QUOTED_INSURANCE_STATUS_ACCEPTED = "Accepted";
export const QUOTED_INSURANCE_STATUSES = [
  QUOTED_INSURANCE_STATUS_PROPOSED,
  QUOTED_INSURANCE_STATUS_DECLINED,
  QUOTED_INSURANCE_STATUS_ACCEPTED,
] as const;

export const WORKFLOW_TYPE_RESEARCH = "research";
export const WORKFLOW_TYPE_COMMUNICATE_RESEARCH = "communicate_research";
export const WORKFLOW_TYPE_ENTER_TRIP_CRM = "enter_trip_crm";

export const WORKFLOW_STATUS_ACTIVE = "Active";
export const WORKFLOW_STATUS_COMPLETED = "Completed";
export const WORKFLOW_STATUS_CANCELLED = "Cancelled";

export const TASK_STATUS_OPEN = "Open";
export const TASK_STATUS_DONE = "Done";
export const TASK_DISPLAY_STATUS_LATE = "Late";

export const FOLLOW_UP_DUE_DAYS = 3;

export const TASK_KEY_RESEARCH_CRUISE_OPTIONS = "research_cruise_options";
export const TASK_KEY_UPLOAD_RESEARCH_DOCUMENT = "upload_research_document";
export const TASK_KEY_CREATE_PROPOSED_CRUISES = "create_proposed_cruises";
export const TASK_KEY_DRAFT_RESEARCH_COMMUNICATION = "draft_research_communication";
export const TASK_KEY_SEND_RESEARCH_COMMUNICATION = "send_research_communication";
export const TASK_KEY_FOLLOW_UP_RESEARCH = "follow_up_research";
export const TASK_KEY_CLIENT_RESPONSE = "client_response";
export const TASK_KEY_VERIFY_PASSENGER_DETAILS = "verify_passenger_details";
export const TASK_KEY_COLLECT_PASSENGER_ADDRESSES = "collect_passenger_addresses";
export const TASK_KEY_CREATE_CABIN_HOLDS = "create_cabin_holds";
export const TASK_KEY_COLLECT_PAYMENT_AND_SEND_BOOKING = "collect_payment_and_send_booking_communication";
export const TASK_KEY_CREATE_TRIP_IN_CRM = "create_trip_in_crm";
export const LEGACY_TASK_KEY_COLLECT_LEAD_PASSENGER_ADDRESSES = "collect_lead_passenger_addresses";

export const COMMUNICATION_STATUS_DRAFT = "Draft";
export const COMMUNICATION_STATUS_SENT = "Sent";
export const COMMUNICATION_STATUS_ARCHIVED = "Archived";

export const COMMUNICATION_TYPE_RESEARCH_FINDINGS = "research_findings";
export const COMMUNICATION_TYPE_RESEARCH_PROPOSAL = "research_proposal";
export const COMMUNICATION_TYPE_RESEARCH_FOLLOW_UP = "research_follow_up";
export const COMMUNICATION_TYPE_BOOKING = "booking_confirmation";
export const COMMUNICATION_TYPE_AGENCY = "agency_follow_up";
