DESTINATIONS = [
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
]

CABIN_TYPES = ["Interior", "Ocean View", "Balcony", "Suite"]

CRUISE_LINES = [
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
]

LEGACY_CRUISE_LINE_ALIASES = {
    "Celebrity": "Celebrity Cruises",
    "Carnival": "Carnival Cruise Lines",
    "Royal Caribbean": "Royal Caribbean International",
    "Norwegian": "Norwegian Cruise Line",
    "Princess": "Princess Cruises",
    "Holland America": "Holland America Line",
    "Disney": "Disney Cruise Lines",
    "MSC": "MSC Cruises",
    "Virgin": "Virgin Voyages",
    "Windstar": "Windstar Cruises",
    "Silversea": "Silversea Cruises",
    "Seabourn": "Seabourn",
    "Oceania": "Oceania Cruises",
    "Azamara": "Azamara Cruises",
    "Costa": "Costa Cruises",
    "Crystal": "Crystal Cruises",
    "Viking": "Viking Cruises",
    "Unknown": "Royal Caribbean International",
}

QUALIFIERS = ["Military", "Educator", "First Responder", "55+ (Senior)"]

CARIBBEAN_REGIONS = ["Eastern", "Western", "Southern", "South Eastern"]

ALASKA_OPTIONS = [
    "RT Seattle",
    "RT Vancouver",
    "Northern One Way",
    "Southern One Way",
    "Cruise tour",
]

ASIA_OPTIONS = ["Japan", "SE Asia", "French Polynesia"]

EUROPE_REGIONS = [
    "Eastern Med - Greece",
    "Eastern Med - Adriatic",
    "Western Med",
    "Northern - UK",
    "Northern Norway",
    "Northern Baltic",
    "Northern Iceland/Greenland",
]

US_STATES = [
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
]

CANADIAN_PROVINCES = [
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
]

RESIDENCY_REGIONS = US_STATES + CANADIAN_PROVINCES

REQUEST_STATUS_OPEN = "Open"
REQUEST_STATUS_CLOSED = "Closed"
REQUEST_STATUSES = [REQUEST_STATUS_OPEN, REQUEST_STATUS_CLOSED]

PRIMARY_CLOSE_REASON = "Purchased - Trip Created"

CLOSE_REASONS = [
    PRIMARY_CLOSE_REASON,
    "Cost - Went with Competitor",
    "Communication - Went with Competitor",
    "Changed Vacation Plans",
    "General Inquiry - Fishing",
]

STALE_DAYS = 3

MARKETING_CAMPAIGN_TYPES = [
    "Facebook/Instagram",
    "Google AdSense",
    "Print",
    "Radio",
    "TV",
    "YouTube",
    "Email Newsletter",
    "Local Event",
]

LEAD_SOURCE_REPEAT_CUSTOMER = "Repeat Customer"
LEAD_SOURCE_REFERRAL = "Referral"
LEAD_SOURCE_GOOGLE_SEARCH = "Google Search"
LEAD_SOURCE_AI_SUGGESTION = "AI Suggestion"
LEAD_SOURCE_MARKETING_CAMPAIGN = "Marketing Campaign"
LEAD_SOURCES = [
    LEAD_SOURCE_REPEAT_CUSTOMER,
    LEAD_SOURCE_REFERRAL,
    LEAD_SOURCE_GOOGLE_SEARCH,
    LEAD_SOURCE_AI_SUGGESTION,
    LEAD_SOURCE_MARKETING_CAMPAIGN,
]

PROPOSED_CRUISE_STATUS_PROPOSED = "Proposed"
PROPOSED_CRUISE_STATUS_ACCEPTED = "Accepted"
PROPOSED_CRUISE_STATUS_DEPOSITED = "Deposited"
PROPOSED_CRUISE_STATUS_REJECTED = "Rejected"
PROPOSED_CRUISE_STATUSES = [
    PROPOSED_CRUISE_STATUS_PROPOSED,
    PROPOSED_CRUISE_STATUS_ACCEPTED,
    PROPOSED_CRUISE_STATUS_DEPOSITED,
    PROPOSED_CRUISE_STATUS_REJECTED,
]
BOOKED_CRUISE_STATUSES = (
    PROPOSED_CRUISE_STATUS_ACCEPTED,
    PROPOSED_CRUISE_STATUS_DEPOSITED,
)
ACTIVE_PIPELINE_QUOTE_STATUSES = (
    PROPOSED_CRUISE_STATUS_PROPOSED,
    PROPOSED_CRUISE_STATUS_ACCEPTED,
    PROPOSED_CRUISE_STATUS_DEPOSITED,
)

PROPOSED_CRUISE_REJECTION_REASON_PRICE = "Price"
PROPOSED_CRUISE_REJECTION_REASON_ITINERARY = "Itinerary"
PROPOSED_CRUISE_REJECTION_REASON_CRUISE_LINE = "Cruise Line"
PROPOSED_CRUISE_REJECTION_REASON_DATES = "Dates"
PROPOSED_CRUISE_REJECTION_REASON_OTHER = "Other"
PROPOSED_CRUISE_REJECTION_REASONS = [
    PROPOSED_CRUISE_REJECTION_REASON_PRICE,
    PROPOSED_CRUISE_REJECTION_REASON_ITINERARY,
    PROPOSED_CRUISE_REJECTION_REASON_CRUISE_LINE,
    PROPOSED_CRUISE_REJECTION_REASON_DATES,
    PROPOSED_CRUISE_REJECTION_REASON_OTHER,
]

SALES_REJECTION_SEGMENT_OPEN_ACTIVE = "open_active_lead"
SALES_REJECTION_SEGMENT_CLOSED_LOST = "closed_lost_lead"
SALES_REJECTION_SEGMENTS = [
    SALES_REJECTION_SEGMENT_OPEN_ACTIVE,
    SALES_REJECTION_SEGMENT_CLOSED_LOST,
]

QUOTED_INSURANCE_STATUS_PROPOSED = "Proposed"
QUOTED_INSURANCE_STATUS_DECLINED = "Declined"
QUOTED_INSURANCE_STATUS_ACCEPTED = "Accepted"
QUOTED_INSURANCE_STATUSES = [
    QUOTED_INSURANCE_STATUS_PROPOSED,
    QUOTED_INSURANCE_STATUS_DECLINED,
    QUOTED_INSURANCE_STATUS_ACCEPTED,
]

WORKFLOW_TYPE_RESEARCH = "research"
WORKFLOW_TYPE_COMMUNICATE_RESEARCH = "communicate_research"
WORKFLOW_TYPE_ENTER_TRIP_CRM = "enter_trip_crm"
WORKFLOW_TYPES = [
    WORKFLOW_TYPE_RESEARCH,
    WORKFLOW_TYPE_COMMUNICATE_RESEARCH,
    WORKFLOW_TYPE_ENTER_TRIP_CRM,
]

WORKFLOW_STATUS_ACTIVE = "Active"
WORKFLOW_STATUS_COMPLETED = "Completed"
WORKFLOW_STATUS_CANCELLED = "Cancelled"
WORKFLOW_STATUS_TERMINATED = "Terminated"
WORKFLOW_STATUSES = [
    WORKFLOW_STATUS_ACTIVE,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_CANCELLED,
    WORKFLOW_STATUS_TERMINATED,
]

TASK_ACTION_MANUAL_CHECK = "manual_check"
TASK_ACTION_FILL_FIELD = "fill_field"
TASK_ACTION_CUSTOM_PANEL = "custom_panel"
TASK_ACTION_TYPES = [
    TASK_ACTION_MANUAL_CHECK,
    TASK_ACTION_FILL_FIELD,
    TASK_ACTION_CUSTOM_PANEL,
]

TASK_STATUS_OPEN = "Open"
TASK_STATUS_DONE = "Done"
TASK_STATUS_CANCELLED = "Cancelled"
TASK_STATUS_BLOCKED = "Blocked"
TASK_STATUSES = [
    TASK_STATUS_OPEN,
    TASK_STATUS_DONE,
    TASK_STATUS_CANCELLED,
    TASK_STATUS_BLOCKED,
]

COMMUNICATION_STATUS_DRAFT = "Draft"
COMMUNICATION_STATUS_SENT = "Sent"
COMMUNICATION_STATUS_ARCHIVED = "Archived"
COMMUNICATION_STATUSES = [
    COMMUNICATION_STATUS_DRAFT,
    COMMUNICATION_STATUS_SENT,
    COMMUNICATION_STATUS_ARCHIVED,
]

COMMUNICATION_TYPE_RESEARCH_FINDINGS = "research_findings"
COMMUNICATION_TYPE_RESEARCH_PROPOSAL = "research_proposal"
COMMUNICATION_TYPE_RESEARCH_FOLLOW_UP = "research_follow_up"
COMMUNICATION_TYPE_BOOKING = "booking_confirmation"
COMMUNICATION_TYPE_AGENCY = "agency_follow_up"
COMMUNICATION_TYPES = [
    COMMUNICATION_TYPE_RESEARCH_FINDINGS,
    COMMUNICATION_TYPE_RESEARCH_PROPOSAL,
    COMMUNICATION_TYPE_RESEARCH_FOLLOW_UP,
    COMMUNICATION_TYPE_BOOKING,
    COMMUNICATION_TYPE_AGENCY,
]
