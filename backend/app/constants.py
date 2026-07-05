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

INTAKE_MODE_EMAIL = "Email"
INTAKE_MODE_PHONE_CALL = "Phone Call"
INTAKE_MODE_TEXT_MESSAGE = "Text Message"
INTAKE_MODE_SOCIAL_MEDIA = "Social Media Request"
INTAKE_MODE_WEBSITE = "Website Request"
INTAKE_MODE_SURVEY = "Travel Interest Survey Form"
INTAKE_MODE_FACE_TO_FACE = "Face to Face"
INTAKE_MODE_OTHER = "Other"
INTAKE_MODES = [
    INTAKE_MODE_EMAIL,
    INTAKE_MODE_PHONE_CALL,
    INTAKE_MODE_TEXT_MESSAGE,
    INTAKE_MODE_SOCIAL_MEDIA,
    INTAKE_MODE_WEBSITE,
    INTAKE_MODE_SURVEY,
    INTAKE_MODE_FACE_TO_FACE,
    INTAKE_MODE_OTHER,
]

SOCIAL_MEDIA_FACEBOOK = "Facebook"
SOCIAL_MEDIA_INSTAGRAM = "Instagram"
SOCIAL_MEDIA_TIKTOK = "TickTok"
SOCIAL_MEDIA_YOUTUBE = "YouTube"
SOCIAL_MEDIA_OTHER = "Other"
SOCIAL_MEDIA_PLATFORMS = [
    SOCIAL_MEDIA_FACEBOOK,
    SOCIAL_MEDIA_INSTAGRAM,
    SOCIAL_MEDIA_TIKTOK,
    SOCIAL_MEDIA_YOUTUBE,
    SOCIAL_MEDIA_OTHER,
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

INSURANCE_STATUS_PENDING = "pending"
INSURANCE_STATUS_ANNUAL_CONFIRMED = "annual_confirmed"
INSURANCE_STATUS_WAIVER_SIGNED = "waiver_signed"
INSURANCE_TRACKING_STATUSES = [
    INSURANCE_STATUS_PENDING,
    INSURANCE_STATUS_ANNUAL_CONFIRMED,
    INSURANCE_STATUS_WAIVER_SIGNED,
]

INSURANCE_WAIVER_REQUEST_STATUS_PENDING = "pending"
INSURANCE_WAIVER_REQUEST_STATUS_COMPLETED = "completed"
INSURANCE_WAIVER_REQUEST_STATUS_EXPIRED = "expired"
INSURANCE_WAIVER_REQUEST_STATUSES = [
    INSURANCE_WAIVER_REQUEST_STATUS_PENDING,
    INSURANCE_WAIVER_REQUEST_STATUS_COMPLETED,
    INSURANCE_WAIVER_REQUEST_STATUS_EXPIRED,
]

INSURANCE_WAIVER_TTL_HOURS = 48
INSURANCE_WAIVER_EMAIL_SUBJECT = "Action Required: Travel Protection Declination & Liability Waiver"
COMMUNICATION_TYPE_INSURANCE_WAIVER = "insurance_waiver"

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
COMMUNICATION_STATUS_RECEIVED = "Received"
COMMUNICATION_STATUS_ARCHIVED = "Archived"
COMMUNICATION_STATUSES = [
    COMMUNICATION_STATUS_DRAFT,
    COMMUNICATION_STATUS_SENT,
    COMMUNICATION_STATUS_RECEIVED,
    COMMUNICATION_STATUS_ARCHIVED,
]

COMMUNICATION_TYPE_RESEARCH_FINDINGS = "research_findings"
COMMUNICATION_TYPE_RESEARCH_PROPOSAL = "research_proposal"
COMMUNICATION_TYPE_RESEARCH_FOLLOW_UP = "research_follow_up"
COMMUNICATION_TYPE_BOOKING = "booking_confirmation"
COMMUNICATION_TYPE_AGENCY = "agency_follow_up"
COMMUNICATION_TYPE_CC_AUTH = "cc_authorization"
COMMUNICATION_TYPE_MASTER_TERMS = "master_terms"
COMMUNICATION_TYPE_INBOUND_EMAIL = "inbound_email"
COMMUNICATION_TYPES = [
    COMMUNICATION_TYPE_RESEARCH_FINDINGS,
    COMMUNICATION_TYPE_RESEARCH_PROPOSAL,
    COMMUNICATION_TYPE_RESEARCH_FOLLOW_UP,
    COMMUNICATION_TYPE_BOOKING,
    COMMUNICATION_TYPE_AGENCY,
    COMMUNICATION_TYPE_CC_AUTH,
    COMMUNICATION_TYPE_MASTER_TERMS,
    COMMUNICATION_TYPE_INBOUND_EMAIL,
    COMMUNICATION_TYPE_INSURANCE_WAIVER,
]

CC_AUTH_STATUS_PENDING = "pending"
CC_AUTH_STATUS_COMPLETED = "completed"
CC_AUTH_STATUS_EXPIRED = "expired"
CC_AUTH_STATUSES = [
    CC_AUTH_STATUS_PENDING,
    CC_AUTH_STATUS_COMPLETED,
    CC_AUTH_STATUS_EXPIRED,
]

CC_AUTH_TTL_HOURS = 48
CC_AUTH_EMAIL_SUBJECT = "Secure Action Required: Credit Card Authorization for your upcoming sailing"

# Master Terms & Conditions (clickwrap)
TC_STATUS_ACCEPTED = "accepted"
TC_STATUS_REVOKED = "revoked"
TC_STATUSES = [TC_STATUS_ACCEPTED, TC_STATUS_REVOKED]

TC_REQUEST_STATUS_PENDING = "pending"
TC_REQUEST_STATUS_COMPLETED = "completed"
TC_REQUEST_STATUS_EXPIRED = "expired"
TC_REQUEST_STATUSES = [
    TC_REQUEST_STATUS_PENDING,
    TC_REQUEST_STATUS_COMPLETED,
    TC_REQUEST_STATUS_EXPIRED,
]

TC_TTL_HOURS = 48
TC_EMAIL_SUBJECT = "Action Required: Review and Accept Master Terms & Conditions"

MASTER_TERMS_DEFAULT_BUSINESS_NAME = "Cruise Seakers Travel LLC"
MASTER_TERMS_DEFAULT_GOVERNING_LAW_STATE = "Utah"

MASTER_TERMS_BOILERPLATE_TEMPLATE = """{business_name} — MASTER TERMS AND CONDITIONS

(Applicable to Current and All Future Cruise Bookings)

This Master Terms and Conditions Agreement (the "Agreement") constitutes a binding legal contract between {business_name} ("the Agency") and the undersigned traveler and/or booking party ("the Client").

SCOPE OF AGREEMENT: This Agreement governs all travel planning, consultation, and booking services provided by the Agency to the Client, whether for the initial booking or any subsequent cruise bookings made hereafter. By signing below, the Client explicitly agrees that these terms apply to the current transaction and shall remain in full force and effect for all future bookings made through the Agency, unless explicitly terminated or amended in writing.

1. Agency Disclosure and Role

{business_name} acts solely as an independent booking intermediary for third-party cruise lines and associated suppliers (the "Cruise Line"). The Agency does not own, manage, or operate any cruise ships, shore excursions, or ground transportation. All bookings are subject to the specific guest ticket contract, rules, policies, terms, and conditions issued by the individual Cruise Line.

2. Cruise Line Contracts and Rules

By completing a booking through the Agency, the Client acknowledges and agrees that they are independently bound by the Cruise Line's passenger ticket contract. The Cruise Line retains the absolute right to alter itineraries, change ports of call, substitute vessels, or cancel sailings at any time for any reason. {business_name} assumes no responsibility or financial liability for any such changes, schedule disruptions, or cancellations.

3. Pricing, Deposits, and Promotions

Price Volatility: Cruise pricing, cabin availability, and promotional offers change frequently. Fares and specific cabin categories are not guaranteed until the required deposit is successfully paid and fully processed by the Cruise Line.

Special Promotions: Any promotional perks (including but not limited to beverage packages, onboard credit, wifi, or pre-paid gratuities) are subject strictly to the Cruise Line's specific eligibility requirements, terms, and limitations.

{governing_law_state} Governing Law & Forum Selection: This Agreement shall be governed by, construed, and enforced in accordance with the laws of the State of {governing_law_state}. Any dispute, claim, or legal action between the Client and {business_name} shall be resolved exclusively in a court of competent jurisdiction located within the State of {governing_law_state}.

4. Fees, Schedules, and Payments

Deposits: All deposits are subject to the specific cancellation and refund policies enforced by the booked Cruise Line.

No Agency Refunds: {business_name} does not charge standalone planning or booking fees; however, the Agency is not responsible for reimbursing any funds, penalties, or losses imposed by the Cruise Line due to client cancellation or modification.

Final Payment Deadlines: Final payment deadlines are strictly enforced by the Cruise Line. Failure to remit full payment by the established deadline will result in automatic booking cancellation by the Cruise Line and the complete forfeiture of all previous payments and deposits.

5. Boarding Requirements and Travel Documents

Passport Validity: Passports must be valid for at least six (6) months beyond the scheduled cruise return date.

Closed-Loop Cruises: For cruises starting and ending at the exact same U.S. port, specific government identification rules apply (such as a certified, state-issued birth certificate alongside a government-issued photo ID). The Client is solely responsible for confirming, obtaining, and bringing the exact documentation required for their specific itinerary.

Denial of Boarding: {business_name} assumes zero financial liability or responsibility if the Cruise Line, customs officials, or port authorities deny boarding to any traveler due to invalid documentation, health status, or behavioral issues.

6. Travel Insurance Acknowledgment and Waiver

Because Cruise Line cancellation penalties are highly restrictive and strictly enforced, {business_name} strongly advises the purchase of comprehensive travel insurance. By signing below or proceeding with a booking without coverage, the Client acknowledges they have been offered travel insurance and voluntarily decline it. The Client accepts full financial responsibility for any losses resulting from trip cancellation, medical emergencies at sea, missed port connections, or lost luggage.

7. Term, Future Bookings, and Amendments

Continuous Effect: This Agreement applies to all cruise bookings, revisions, or additions requested by the Client at any time following the date of execution. A new signature is not required for each individual booking.

Client Right to Review: For each future booking, the Client will receive a booking confirmation invoice. It is the Client's responsibility to review the specific cruise line policies, payment schedules, and passport requirements tied to that specific itinerary.

Amendments: {business_name} reserves the right to amend these Master Terms at any time. If updates are made, the Agency will notify the Client via email or provide the updated terms with the next booking confirmation invoice. Continued use of the Agency's services after notification constitutes acceptance of the amended terms."""


