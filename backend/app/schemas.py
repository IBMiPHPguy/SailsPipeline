from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.constants import (
    ALASKA_OPTIONS,
    ASIA_OPTIONS,
    CABIN_TYPES,
    CARIBBEAN_REGIONS,
    CLOSE_REASONS,
    CRUISE_LINES,
    DESTINATIONS,
    EUROPE_REGIONS,
    LEGACY_CRUISE_LINE_ALIASES,
    PROPOSED_CRUISE_REJECTION_REASONS,
    PROPOSED_CRUISE_STATUSES,
    QUALIFIERS,
    QUOTED_INSURANCE_STATUSES,
    REQUEST_STATUS_CLOSED,
    REQUEST_STATUS_OPEN,
    REQUEST_STATUSES,
)
from app.security import validate_password


def validate_qualifier_values(value: list[str]) -> list[str]:
    invalid = [item for item in value if item not in QUALIFIERS]
    if invalid:
        raise ValueError("Invalid qualifier selected.")
    return value


def normalize_cruise_line_value(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return stripped
    if stripped in CRUISE_LINES:
        return stripped

    lowered = stripped.lower()
    for line in CRUISE_LINES:
        if line.lower() == lowered:
            return line

    legacy = LEGACY_CRUISE_LINE_ALIASES.get(stripped)
    if legacy is not None:
        return legacy

    prefix_matches = [line for line in CRUISE_LINES if line.lower().startswith(lowered)]
    if len(prefix_matches) == 1:
        return prefix_matches[0]

    contains_matches = [line for line in CRUISE_LINES if lowered in line.lower()]
    if len(contains_matches) == 1:
        return contains_matches[0]

    return stripped


def normalize_cruise_line_list(values: list[str] | str | None) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        line = normalize_cruise_line_value(value)
        if line and line not in seen:
            seen.add(line)
            normalized.append(line)
    return normalized


def validate_cruise_line_values(value: list[str], *, require_at_least_one: bool = False) -> list[str]:
    normalized = normalize_cruise_line_list(value)
    if require_at_least_one and not normalized:
        raise ValueError("Select at least one cruise line.")
    invalid = [item for item in normalized if item not in CRUISE_LINES]
    if invalid:
        raise ValueError("Invalid cruise line selected.")
    return normalized


def validate_single_cruise_line_field(value: str) -> str:
    normalized = normalize_cruise_line_value(value)
    if not normalized:
        raise ValueError("Select a cruise line.")
    if normalized not in CRUISE_LINES:
        raise ValueError("Invalid cruise line selected.")
    return normalized


class DestinationDetails(BaseModel):
    caribbean_regions: list[str] | None = None
    alaska_options: list[str] | None = None
    asia_regions: list[str] | None = None
    europe_regions: list[str] | None = None


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^\S+$")
    email: EmailStr
    password: str = Field(min_length=11, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        validate_password(value)
        return value


class UserLogin(BaseModel):
    organization_handle: str = Field(min_length=1, max_length=50, pattern=r"^\S+$")
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)


class BridgeLogin(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agency_id: str | None
    username: str
    email: EmailStr
    role: str
    is_active: bool
    can_view_all_agency_leads: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class BridgeAgencySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    organization_handle: str
    subscription_state: str
    is_active: bool
    created_at: datetime


class BridgeInvitationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    target_agency_name: str
    target_organization_handle: str
    invite_email: str
    expires_at: datetime
    is_used: bool
    token_status: str


class BridgeSummaryResponse(BaseModel):
    agencies: list[BridgeAgencySummary]
    invitations: list[BridgeInvitationSummary]


class BridgeTenantUserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    role: str
    is_active: bool


class BridgeTenantDetail(BaseModel):
    agency: BridgeAgencySummary
    users: list[BridgeTenantUserSummary]


class BridgeTenantUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    organization_handle: str = Field(min_length=2, max_length=50, pattern=r"^\S+$")
    subscription_state: str = Field(min_length=1, max_length=40)


class PlatformInviteCreate(BaseModel):
    target_agency_name: str = Field(min_length=1, max_length=255)
    target_organization_handle: str = Field(min_length=2, max_length=50, pattern=r"^\S+$")
    invite_email: EmailStr


class PlatformInviteCreated(BaseModel):
    invitation_id: str
    onboarding_path: str
    expires_at: datetime


class OnboardingInviteRead(BaseModel):
    target_agency_name: str
    organization_handle: str
    invite_email: EmailStr
    expires_at: datetime


class OnboardingAccept(BaseModel):
    token: str = Field(min_length=1, max_length=255)
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=11, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        validate_password(value)
        return value


class AgencyInviteCreate(BaseModel):
    invite_email: EmailStr
    role: str = Field(default="tenant_agent", min_length=1, max_length=50)


class AgencyInviteCreated(BaseModel):
    invitation_id: str
    onboarding_path: str
    expires_at: datetime


class AgencyTeamMember(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    role: str
    is_active: bool


class AgencyPendingInvite(BaseModel):
    id: str
    invite_email: EmailStr
    role: str
    expires_at: datetime
    token_status: str


class AgencyTeamSummary(BaseModel):
    users: list[AgencyTeamMember]
    invitations: list[AgencyPendingInvite]


class AgentInviteRead(BaseModel):
    agency_name: str
    organization_handle: str
    invite_email: EmailStr
    role: str
    expires_at: datetime


class AgencyUserUpdate(BaseModel):
    role: str | None = Field(default=None, min_length=1, max_length=50)
    is_active: bool | None = None
    email: EmailStr | None = None

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "AgencyUserUpdate":
        if self.role is None and self.is_active is None and self.email is None:
            raise ValueError("At least one field must be provided.")
        return self


class UserAudit(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class TravelRequestBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=30)
    cruise_lines: list[str] = Field(min_length=1)
    excluded_cruise_lines: list[str] = Field(default_factory=list)
    destination: str = Field(min_length=1, max_length=120)
    destination_details: DestinationDetails | None = None
    departure_date: date
    return_date: date
    cabin_types: list[str] = Field(min_length=1)
    qualifiers: list[str] = Field(default_factory=list)
    passengers: int = Field(ge=1, le=20)
    cabins_needed: int = Field(ge=1, le=10, default=1)
    lead_source: str | None = Field(default=None, max_length=100)
    referral_source_name: str | None = Field(default=None, max_length=255)
    marketing_campaign_id: str | None = Field(default=None, max_length=36)

    @field_validator("lead_source")
    @classmethod
    def validate_lead_source(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        from app.constants import LEAD_SOURCES

        if value not in LEAD_SOURCES:
            raise ValueError("Invalid lead source selected.")
        return value

    @model_validator(mode="after")
    def validate_lead_attribution(self) -> "TravelRequestBase":
        from app.lead_attribution import normalize_lead_attribution

        source, referral, campaign_id = normalize_lead_attribution(
            lead_source=self.lead_source,
            referral_source_name=self.referral_source_name,
            marketing_campaign_id=self.marketing_campaign_id,
        )
        self.lead_source = source
        self.referral_source_name = referral
        self.marketing_campaign_id = campaign_id
        return self

    @model_validator(mode="after")
    def validate_travel_dates(self) -> "TravelRequestBase":
        if self.return_date <= self.departure_date:
            raise ValueError("Return date must be after departure date.")
        return self

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, value: str) -> str:
        if value not in DESTINATIONS:
            raise ValueError("Invalid destination selected.")
        return value

    @field_validator("cabin_types")
    @classmethod
    def validate_cabin_types(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("Select at least one cabin type.")
        invalid = [item for item in value if item not in CABIN_TYPES]
        if invalid:
            raise ValueError("Invalid cabin type selected.")
        return value

    @field_validator("cruise_lines")
    @classmethod
    def validate_cruise_lines(cls, value: list[str]) -> list[str]:
        return validate_cruise_line_values(value, require_at_least_one=True)

    @field_validator("excluded_cruise_lines")
    @classmethod
    def validate_excluded_cruise_lines(cls, value: list[str]) -> list[str]:
        return validate_cruise_line_values(value)

    @field_validator("qualifiers")
    @classmethod
    def validate_qualifiers(cls, value: list[str]) -> list[str]:
        return validate_qualifier_values(value)

    @model_validator(mode="after")
    def validate_destination_details(self) -> "TravelRequestBase":
        details = self.destination_details or DestinationDetails()

        if self.destination == "Caribbean":
            regions = details.caribbean_regions or []
            if not regions:
                raise ValueError("Select at least one Caribbean region.")
            invalid = [item for item in regions if item not in CARIBBEAN_REGIONS]
            if invalid:
                raise ValueError("Invalid Caribbean region selected.")
        elif self.destination == "Alaska":
            options = details.alaska_options or []
            if not options:
                raise ValueError("Select at least one Alaska itinerary option.")
            invalid = [item for item in options if item not in ALASKA_OPTIONS]
            if invalid:
                raise ValueError("Invalid Alaska itinerary option selected.")
        elif self.destination == "Asia":
            regions = details.asia_regions or []
            if not regions:
                raise ValueError("Select at least one Asia region option.")
            invalid = [item for item in regions if item not in ASIA_OPTIONS]
            if invalid:
                raise ValueError("Invalid Asia region option selected.")
        elif self.destination == "Europe":
            regions = details.europe_regions or []
            if not regions:
                raise ValueError("Select at least one Europe region.")
            invalid = [item for item in regions if item not in EUROPE_REGIONS]
            if invalid:
                raise ValueError("Invalid Europe region selected.")
        else:
            self.destination_details = None

        return self


class TravelRequestCreate(TravelRequestBase):
    first_passenger_date_of_birth: date | None = None
    primary_passenger_id: int | None = None


class PassengerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: EmailStr | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state_or_province: str | None = None
    postal_code: str | None = None
    country: str | None = None
    qualifiers: list[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class PassengerListRead(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    qualifiers: list[str] = Field(default_factory=list)
    is_active: bool
    request_count: int = Field(ge=0)


class ClientsPageRead(BaseModel):
    items: list[PassengerListRead]
    total: int = Field(description="Total clients matching the search query.")
    registry_count: int = Field(description="Total clients in the registry.")
    page: int = Field(description="Current one-based page number.")
    page_size: int = Field(description="Maximum number of rows returned per page.")
    total_pages: int = Field(description="Total number of pages available for the current query.")


class PassengerUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    date_of_birth: date | None = None
    address_line_1: str | None = Field(default=None, max_length=120)
    address_line_2: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=80)
    state_or_province: str | None = Field(default=None, max_length=50)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, max_length=80)
    qualifiers: list[str] | None = None

    @field_validator("qualifiers")
    @classmethod
    def validate_passenger_qualifiers(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return validate_qualifier_values(value)

    @field_validator("email", "phone", mode="before")
    @classmethod
    def normalize_optional_contact(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class PassengerCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    date_of_birth: date | None = None
    address_line_1: str | None = Field(default=None, max_length=120)
    address_line_2: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=80)
    state_or_province: str | None = Field(default=None, max_length=50)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, max_length=80)
    qualifiers: list[str] = Field(default_factory=list)

    @field_validator("qualifiers")
    @classmethod
    def validate_passenger_qualifiers(cls, value: list[str]) -> list[str]:
        return validate_qualifier_values(value)

    @field_validator("email", "phone", mode="before")
    @classmethod
    def normalize_optional_contact(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class RequestPassengerBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    date_of_birth: date | None = None
    address_line_1: str | None = Field(default=None, max_length=120)
    address_line_2: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=80)
    state_or_province: str | None = Field(default=None, max_length=50)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, max_length=80)
    qualifiers: list[str] = Field(default_factory=list)

    @field_validator("qualifiers")
    @classmethod
    def validate_passenger_qualifiers(cls, value: list[str]) -> list[str]:
        return validate_qualifier_values(value)


class RequestPassengerCreate(BaseModel):
    passenger_id: int | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    date_of_birth: date | None = None
    qualifiers: list[str] = Field(default_factory=list)

    @field_validator("email", "phone", mode="before")
    @classmethod
    def normalize_optional_contact(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("qualifiers")
    @classmethod
    def validate_create_qualifiers(cls, value: list[str]) -> list[str]:
        return validate_qualifier_values(value)

    @model_validator(mode="after")
    def validate_create_mode(self) -> "RequestPassengerCreate":
        profile_fields = (
            self.first_name,
            self.last_name,
            self.email,
            self.phone,
            self.date_of_birth,
        )
        if self.passenger_id is not None:
            if any(value is not None for value in profile_fields):
                raise ValueError("Provide either passenger_id or passenger details, not both.")
            return self

        missing = [
            name
            for name, value in (
                ("first_name", self.first_name),
                ("last_name", self.last_name),
            )
            if value is None or (isinstance(value, str) and not value.strip())
        ]
        if missing:
            raise ValueError("New passengers require first name and last name.")
        return self


class RequestPassengerUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    date_of_birth: date | None = None
    address_line_1: str | None = Field(default=None, max_length=120)
    address_line_2: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=80)
    state_or_province: str | None = Field(default=None, max_length=50)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, max_length=80)
    qualifiers: list[str] | None = None

    @field_validator("email", "phone", mode="before")
    @classmethod
    def normalize_optional_contact(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("qualifiers")
    @classmethod
    def validate_update_qualifiers(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        return validate_qualifier_values(value)


class RequestPassengerRead(RequestPassengerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    passenger_id: int
    is_primary: bool
    passenger_is_active: bool
    created_at: datetime
    updated_at: datetime


class TravelRequestUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    cruise_lines: list[str] | None = None
    excluded_cruise_lines: list[str] | None = None
    destination: str | None = Field(default=None, min_length=1, max_length=120)
    destination_details: DestinationDetails | None = None
    departure_date: date | None = None
    return_date: date | None = None
    cabin_types: list[str] | None = None
    passengers: int | None = Field(default=None, ge=1, le=20)
    cabins_needed: int | None = Field(default=None, ge=1, le=10)
    cabin_hold_reservation_ids: list[list[str]] | None = None
    status: str | None = Field(default=None, min_length=1, max_length=40)
    close_reason: str | None = Field(default=None, max_length=120)
    lead_source: str | None = Field(default=None, max_length=100)
    referral_source_name: str | None = Field(default=None, max_length=255)
    marketing_campaign_id: str | None = Field(default=None, max_length=36)

    @field_validator("lead_source")
    @classmethod
    def validate_update_lead_source(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        from app.constants import LEAD_SOURCES

        if value not in LEAD_SOURCES:
            raise ValueError("Invalid lead source selected.")
        return value

    @model_validator(mode="after")
    def validate_update_lead_attribution(self) -> "TravelRequestUpdate":
        if (
            self.lead_source is None
            and self.referral_source_name is None
            and self.marketing_campaign_id is None
        ):
            return self
        from app.lead_attribution import normalize_lead_attribution

        source, referral, campaign_id = normalize_lead_attribution(
            lead_source=self.lead_source,
            referral_source_name=self.referral_source_name,
            marketing_campaign_id=self.marketing_campaign_id,
        )
        self.lead_source = source
        self.referral_source_name = referral
        self.marketing_campaign_id = campaign_id
        return self

    @field_validator("cabin_hold_reservation_ids", mode="before")
    @classmethod
    def normalize_cabin_hold_reservation_ids(cls, value: Any) -> list[list[str]] | None:
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError("Invalid cabin hold reservation IDs.")
        normalized: list[list[str]] = []
        for cabin_entry in value:
            if not isinstance(cabin_entry, list):
                raise ValueError("Invalid cabin hold reservation IDs.")
            ids = [str(item).strip() for item in cabin_entry if str(item).strip()]
            normalized.append(ids)
        return normalized

    @field_validator("cruise_lines")
    @classmethod
    def validate_update_cruise_lines(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return validate_cruise_line_values(value, require_at_least_one=True)

    @field_validator("excluded_cruise_lines")
    @classmethod
    def validate_update_excluded_cruise_lines(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return validate_cruise_line_values(value)

    @model_validator(mode="after")
    def validate_close(self) -> "TravelRequestUpdate":
        if self.status == REQUEST_STATUS_CLOSED:
            if not self.close_reason:
                raise ValueError("Select a close reason when closing a request.")
            if self.close_reason not in CLOSE_REASONS:
                raise ValueError("Invalid close reason selected.")
        elif self.status == REQUEST_STATUS_OPEN:
            self.close_reason = None
        elif self.close_reason is not None and self.close_reason not in CLOSE_REASONS:
            raise ValueError("Invalid close reason selected.")
        if self.status is not None and self.status not in REQUEST_STATUSES:
            raise ValueError("Invalid request status selected.")
        return self


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    mime_type: str
    size_bytes: int
    created_by: UserAudit
    created_at: datetime


class RequestNoteCreate(BaseModel):
    summary: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1)


class CommunicationAiSummaryRead(BaseModel):
    summary: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1)


class RequestNoteUpdate(BaseModel):
    summary: str | None = Field(default=None, min_length=1, max_length=160)
    content: str | None = Field(default=None, min_length=1)


class RequestNoteAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_summary: str | None = None
    to_summary: str | None = None
    from_content: str | None
    to_content: str | None
    changed_by: UserAudit
    changed_at: datetime


class TravelRequestAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_name: str
    from_value: str | None
    to_value: str | None
    changed_by: UserAudit
    changed_at: datetime


class RequestPassengerAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_passenger_id: int | None
    passenger_label: str | None = None
    field_name: str
    from_value: str | None
    to_value: str | None
    changed_by: UserAudit
    changed_at: datetime


class RequestNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    summary: str
    content: str
    created_by: UserAudit
    updated_by: UserAudit
    created_at: datetime
    updated_at: datetime
    audits: list[RequestNoteAuditRead] = Field(default_factory=list)


class RequestNoteSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    summary: str
    created_by: UserAudit
    updated_by: UserAudit
    created_at: datetime
    updated_at: datetime


class NamedInclude(BaseModel):
    included: bool = False
    name: str | None = None


class CreditInclude(BaseModel):
    included: bool = False
    amount: Decimal | None = Field(default=None, ge=0)


class ProposedCruiseIncludes(BaseModel):
    drink_package: NamedInclude = Field(default_factory=NamedInclude)
    wifi: NamedInclude = Field(default_factory=NamedInclude)
    tips: bool = False
    excursion: bool = False
    excursion_credit: CreditInclude = Field(default_factory=CreditInclude)
    onboard_credit: CreditInclude = Field(default_factory=CreditInclude)
    gift_obc: CreditInclude = Field(default_factory=CreditInclude)


class CabinPricingEntry(BaseModel):
    deposit_amount: Decimal = Field(ge=0)
    cost: Decimal = Field(ge=0)


class ProposedCruiseRoom(BaseModel):
    room_category: str = Field(min_length=1, max_length=120)
    room_number: str = Field(min_length=1, max_length=40)
    passengers_in_room: int = Field(ge=1, le=20)
    deposit_amount: Decimal = Field(ge=0)
    commission: Decimal = Field(default=Decimal("0"), ge=0)
    cost: Decimal = Field(ge=0)
    includes: ProposedCruiseIncludes = Field(default_factory=ProposedCruiseIncludes)


class ProposedCruiseBase(BaseModel):
    departure_date: date
    cruise_line: str = Field(min_length=1, max_length=120)
    ship: str = Field(min_length=1, max_length=120)
    number_of_nights: int = Field(ge=1, le=365)
    itinerary_name: str = Field(min_length=1, max_length=160)
    itinerary_details: str | None = Field(default=None, max_length=8000)
    room_category: str = Field(min_length=1, max_length=120)
    room_number: str = Field(min_length=1, max_length=40)
    passengers_in_room: int = Field(ge=1, le=20)
    deposit_amount: Decimal = Field(ge=0)
    deposit_due_date: date
    final_payment_due_date: date
    cost: Decimal = Field(ge=0)
    includes: ProposedCruiseIncludes = Field(default_factory=ProposedCruiseIncludes)
    room_passenger_ids: list[list[int]] = Field(default_factory=list)
    passenger_ids: list[int] = Field(default_factory=list)
    cabin_rooms: list[ProposedCruiseRoom] = Field(default_factory=list)

    @field_validator("cruise_line")
    @classmethod
    def validate_cruise_line(cls, value: str) -> str:
        return validate_single_cruise_line_field(value)

    @field_validator("itinerary_details", mode="before")
    @classmethod
    def normalize_itinerary_details(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return str(value).strip() or None

    @model_validator(mode="after")
    def validate_dates(self) -> "ProposedCruiseBase":
        if self.final_payment_due_date < self.deposit_due_date:
            raise ValueError("Final payment due date must be on or after the deposit due date.")

        flat_passenger_ids = [
            passenger_id
            for room in self.room_passenger_ids
            for passenger_id in room
        ] if self.room_passenger_ids else self.passenger_ids

        if len(flat_passenger_ids) != len(set(flat_passenger_ids)):
            raise ValueError("Each passenger can only be assigned to one room.")

        per_room_limits = (
            [room.passengers_in_room for room in self.cabin_rooms]
            if self.cabin_rooms
            else [self.passengers_in_room]
        )
        for cabin_index, room in enumerate(self.room_passenger_ids):
            limit = per_room_limits[cabin_index] if cabin_index < len(per_room_limits) else self.passengers_in_room
            if len(room) > limit:
                raise ValueError(f"Room {cabin_index + 1} exceeds the passengers-in-room limit.")
        if self.passengers_in_room < len(flat_passenger_ids) and not self.room_passenger_ids and not self.cabin_rooms:
            raise ValueError("Passengers in room must be at least the number of attached passengers.")
        return self


class ProposedCruiseCreate(ProposedCruiseBase):
    pass


class GenerateProposedCruisesRequest(BaseModel):
    research_document_id: int


class GenerateProposedCruisesResponse(BaseModel):
    research_document_id: int
    research_document_filename: str
    model: str
    cruises: list[ProposedCruiseCreate]


class BulkProposedCruiseCreate(BaseModel):
    cruises: list[ProposedCruiseCreate] = Field(min_length=1)


class ProposedCruiseUpdate(BaseModel):
    departure_date: date | None = None
    cruise_line: str | None = Field(default=None, min_length=1, max_length=120)
    ship: str | None = Field(default=None, min_length=1, max_length=120)
    number_of_nights: int | None = Field(default=None, ge=1, le=365)
    itinerary_name: str | None = Field(default=None, min_length=1, max_length=160)
    itinerary_details: str | None = Field(default=None, max_length=8000)
    room_category: str | None = Field(default=None, min_length=1, max_length=120)
    room_number: str | None = Field(default=None, min_length=1, max_length=40)
    passengers_in_room: int | None = Field(default=None, ge=1, le=20)
    deposit_amount: Decimal | None = Field(default=None, ge=0)
    deposit_due_date: date | None = None
    final_payment_due_date: date | None = None
    cost: Decimal | None = Field(default=None, ge=0)
    includes: ProposedCruiseIncludes | None = None
    room_passenger_ids: list[list[int]] | None = None
    passenger_ids: list[int] | None = None
    status: str | None = Field(default=None, min_length=1, max_length=40)
    rejection_reason: str | None = Field(default=None, max_length=120)
    rejection_reason_detail: str | None = Field(default=None, max_length=500)
    cabin_pricing: list[CabinPricingEntry] | None = None
    cabin_rooms: list[ProposedCruiseRoom] | None = None
    cabin_hold_reservation_ids: list[list[str]] | None = None

    @field_validator("cabin_hold_reservation_ids", mode="before")
    @classmethod
    def normalize_cabin_hold_reservation_ids(cls, value: Any) -> list[list[str]] | None:
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError("Invalid cabin hold reservation IDs.")
        normalized: list[list[str]] = []
        for cabin_entry in value:
            if not isinstance(cabin_entry, list):
                raise ValueError("Invalid cabin hold reservation IDs.")
            ids = [str(item).strip() for item in cabin_entry if str(item).strip()]
            normalized.append(ids)
        return normalized

    @field_validator("cruise_line")
    @classmethod
    def validate_update_cruise_line(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_single_cruise_line_field(value)

    @field_validator("itinerary_details", mode="before")
    @classmethod
    def normalize_update_itinerary_details(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return str(value).strip() or None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in PROPOSED_CRUISE_STATUSES:
            raise ValueError("Invalid proposed cruise status selected.")
        return value

    @field_validator("rejection_reason", mode="before")
    @classmethod
    def normalize_rejection_reason(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return str(value).strip() or None

    @field_validator("rejection_reason")
    @classmethod
    def validate_rejection_reason(cls, value: str | None) -> str | None:
        if value is not None and value not in PROPOSED_CRUISE_REJECTION_REASONS:
            raise ValueError("Invalid rejection reason selected.")
        return value

    @field_validator("rejection_reason_detail", mode="before")
    @classmethod
    def normalize_rejection_reason_detail(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return str(value).strip() or None


class ProposedCruiseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    departure_date: date
    cruise_line: str
    ship: str
    number_of_nights: int
    itinerary_name: str
    itinerary_details: str | None = None
    room_category: str
    room_number: str
    passengers_in_room: int
    deposit_amount: Decimal
    deposit_due_date: date
    final_payment_due_date: date
    cost: Decimal
    cabin_pricing: list[CabinPricingEntry] = Field(default_factory=list)
    cabin_rooms: list[ProposedCruiseRoom] = Field(default_factory=list)
    cabin_hold_reservation_ids: list[list[str]] = Field(default_factory=list)
    includes: ProposedCruiseIncludes
    status: str
    rejection_reason: str | None = None
    rejection_reason_detail: str | None = None
    passengers: list[RequestPassengerRead] = Field(default_factory=list)
    room_passengers: list[list[RequestPassengerRead]] = Field(default_factory=list)
    created_by: UserAudit
    updated_by: UserAudit
    created_at: datetime
    updated_at: datetime

    @field_validator("includes", mode="before")
    @classmethod
    def normalize_includes(cls, value: Any) -> ProposedCruiseIncludes:
        if isinstance(value, ProposedCruiseIncludes):
            return value
        return ProposedCruiseIncludes.model_validate(value or {})

    @field_validator("cabin_pricing", mode="before")
    @classmethod
    def normalize_cabin_pricing(cls, value: Any) -> list[CabinPricingEntry]:
        if value is None:
            return []
        if not isinstance(value, list):
            return []
        return [CabinPricingEntry.model_validate(item) for item in value]

    @field_validator("cabin_rooms", mode="before")
    @classmethod
    def normalize_cabin_rooms(cls, value: Any) -> list[ProposedCruiseRoom]:
        if value is None:
            return []
        if not isinstance(value, list):
            return []
        return [ProposedCruiseRoom.model_validate(item) for item in value]

    @field_validator("cabin_hold_reservation_ids", mode="before")
    @classmethod
    def normalize_cabin_hold_reservation_ids(cls, value: Any) -> list[list[str]]:
        if value is None:
            return []
        if not isinstance(value, list):
            return []
        normalized: list[list[str]] = []
        for cabin_entry in value:
            if not isinstance(cabin_entry, list):
                continue
            ids = [str(item).strip() for item in cabin_entry if str(item).strip()]
            normalized.append(ids)
        return normalized


class BulkProposedCruiseCreateResponse(BaseModel):
    cruises: list[ProposedCruiseRead]


class QuotedInsuranceBase(BaseModel):
    carrier: str = Field(min_length=1, max_length=120)
    premium_cost: Decimal = Field(ge=0)
    plan_name: str = Field(min_length=1, max_length=160)
    cancellation_coverage: Decimal = Field(ge=0)
    medical_coverage: Decimal = Field(ge=0)
    medical_evac_coverage: Decimal = Field(ge=0)


class QuotedInsuranceCreate(QuotedInsuranceBase):
    pass


class QuotedInsuranceUpdate(BaseModel):
    carrier: str | None = Field(default=None, min_length=1, max_length=120)
    premium_cost: Decimal | None = Field(default=None, ge=0)
    plan_name: str | None = Field(default=None, min_length=1, max_length=160)
    cancellation_coverage: Decimal | None = Field(default=None, ge=0)
    medical_coverage: Decimal | None = Field(default=None, ge=0)
    medical_evac_coverage: Decimal | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, min_length=1, max_length=40)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in QUOTED_INSURANCE_STATUSES:
            raise ValueError("Invalid quoted insurance status selected.")
        return value


class QuotedInsuranceRead(QuotedInsuranceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    declined_at: datetime | None = None
    created_by: UserAudit
    updated_by: UserAudit
    created_at: datetime
    updated_at: datetime


class TravelRequestRead(TravelRequestBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    close_reason: str | None = None
    cabin_hold_reservation_ids: list[list[str]] = Field(default_factory=list)
    created_by: UserAudit
    updated_by: UserAudit
    created_at: datetime
    updated_at: datetime

    @field_validator("cabin_hold_reservation_ids", mode="before")
    @classmethod
    def default_cabin_hold_reservation_ids(cls, value: Any) -> list[list[str]]:
        if value is None:
            return []
        if not isinstance(value, list):
            return []
        normalized: list[list[str]] = []
        for cabin_entry in value:
            if not isinstance(cabin_entry, list):
                continue
            ids = [str(item).strip() for item in cabin_entry if str(item).strip()]
            normalized.append(ids)
        return normalized

    @field_validator("destination_details", mode="before")
    @classmethod
    def normalize_destination_details(cls, value: Any) -> DestinationDetails | None:
        if value is None:
            return None
        if isinstance(value, DestinationDetails):
            return value
        return DestinationDetails.model_validate(value)


class ClosedRequestsPageRead(BaseModel):
    items: list[TravelRequestRead]
    total: int = Field(description="Total closed requests matching the search query.")
    page: int = Field(description="Current one-based page number.")
    page_size: int = Field(description="Maximum number of rows returned per page.")
    total_pages: int = Field(description="Total number of pages available for the current query.")


class TravelRequestDetailRead(TravelRequestRead):
    last_worked_at: datetime
    last_worked_by: UserAudit
    request_passengers: list[RequestPassengerRead] = Field(default_factory=list)
    request_notes: list[RequestNoteSummaryRead] = Field(default_factory=list)
    call_transcripts: list[AttachmentRead] = Field(default_factory=list)
    chat_logs: list[AttachmentRead] = Field(default_factory=list)
    proposed_cruises: list[ProposedCruiseRead] = Field(default_factory=list)
    quoted_insurance: list[QuotedInsuranceRead] = Field(default_factory=list)
    request_workflows: list["RequestWorkflowRead"] = Field(default_factory=list)
    request_communications: list["RequestCommunicationSummaryRead"] = Field(default_factory=list)
    research_documents: list["ResearchDocumentRead"] = Field(default_factory=list)


class RequestChangeHistoryRead(BaseModel):
    request_audits: list[TravelRequestAuditRead] = Field(default_factory=list)
    passenger_audits: list[RequestPassengerAuditRead] = Field(default_factory=list)


class RequestTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_key: str
    title: str
    description: str | None = None
    status: str
    sort_order: int
    action_type: str = "manual_check"
    is_completed: bool = False
    due_at: datetime | None = None
    completed_at: datetime | None = None
    completed_by: UserAudit | None = None
    result: dict | None = None
    prerequisite_task_keys: list[str] | None = None
    created_at: datetime
    updated_at: datetime


class RequestWorkflowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_type: str
    workflow_name: str
    status: str
    parent_workflow_id: str | None = None
    context: dict | None = None
    started_by: UserAudit
    completed_by: UserAudit | None = None
    tasks: list[RequestTaskRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class RequestWorkflowCreate(BaseModel):
    template_id: str | None = Field(default=None, min_length=36, max_length=36)
    workflow_type: str | None = Field(default=None, min_length=1, max_length=40)
    parent_workflow_id: str | None = Field(default=None, min_length=36, max_length=36)

    @field_validator("workflow_type")
    @classmethod
    def validate_workflow_type(cls, value: str | None) -> str | None:
        if value is None:
            return value
        from app.constants import WORKFLOW_TYPES

        if value not in WORKFLOW_TYPES:
            raise ValueError("Invalid workflow type selected.")
        return value

    @model_validator(mode="after")
    def validate_selector(self):
        if not self.template_id and not self.workflow_type:
            raise ValueError("Select a workflow.")
        return self


class RequestWorkflowUpdate(BaseModel):
    status: str | None = Field(default=None, min_length=1, max_length=40)
    close_reason: str | None = Field(default=None, max_length=120)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        from app.constants import WORKFLOW_STATUSES

        if value is not None and value not in WORKFLOW_STATUSES:
            raise ValueError("Invalid workflow status selected.")
        return value

    @field_validator("close_reason")
    @classmethod
    def validate_close_reason(cls, value: str | None) -> str | None:
        if value is not None and value not in CLOSE_REASONS:
            raise ValueError("Invalid close reason selected.")
        return value


class RequestTaskUpdate(BaseModel):
    status: str | None = Field(default=None, min_length=1, max_length=40)
    is_completed: bool | None = None
    due_at: datetime | None = None
    result: dict | None = None
    reached_out: bool | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        from app.constants import TASK_STATUSES

        if value is not None and value not in TASK_STATUSES:
            raise ValueError("Invalid task status selected.")
        return value


class RequestCommunicationCreate(BaseModel):
    communication_type: str = Field(min_length=1, max_length=40)
    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    request_workflow_id: str | None = None
    status: str = Field(default="Draft", min_length=1, max_length=40)

    @field_validator("communication_type")
    @classmethod
    def validate_communication_type(cls, value: str) -> str:
        from app.constants import COMMUNICATION_TYPES

        if value not in COMMUNICATION_TYPES:
            raise ValueError("Invalid communication type selected.")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        from app.constants import COMMUNICATION_STATUSES

        if value not in COMMUNICATION_STATUSES:
            raise ValueError("Invalid communication status selected.")
        return value


class RequestCommunicationUpdate(BaseModel):
    communication_type: str | None = Field(default=None, min_length=1, max_length=40)
    subject: str | None = Field(default=None, min_length=1, max_length=255)
    body: str | None = Field(default=None, min_length=1)
    status: str | None = Field(default=None, min_length=1, max_length=40)

    @field_validator("communication_type")
    @classmethod
    def validate_communication_type(cls, value: str | None) -> str | None:
        from app.constants import COMMUNICATION_TYPES

        if value is not None and value not in COMMUNICATION_TYPES:
            raise ValueError("Invalid communication type selected.")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        from app.constants import COMMUNICATION_STATUSES

        if value is not None and value not in COMMUNICATION_STATUSES:
            raise ValueError("Invalid communication status selected.")
        return value


class RequestCommunicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    communication_type: str
    subject: str
    body: str
    status: str
    request_workflow_id: str | None = Field(default=None, validation_alias="request_workflow_live_id")
    sent_at: datetime | None = None
    created_by: UserAudit
    updated_by: UserAudit
    created_at: datetime
    updated_at: datetime


class RequestCommunicationSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    communication_type: str
    subject: str
    status: str
    request_workflow_id: str | None = Field(default=None, validation_alias="request_workflow_live_id")
    sent_at: datetime | None = None
    created_by: UserAudit
    updated_by: UserAudit
    created_at: datetime
    updated_at: datetime


class GenerateResearchCommunicationRequest(BaseModel):
    request_workflow_id: str | None = None


class GenerateResearchCommunicationResponse(BaseModel):
    model: str
    proposed_cruise_count: int
    subject: str
    email_subject: str
    body: str
    communication: RequestCommunicationRead


class ResearchDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    mime_type: str
    size_bytes: int
    uploaded_by: UserAudit
    created_at: datetime


class WorkflowTemplateRead(BaseModel):
    id: str
    workflow_type: str
    name: str
    description: str


class AgencyTaskTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_title: str
    sequence_order: int
    action_type: str
    target_field: str | None = None
    task_key: str | None = None
    description: str | None = None
    prerequisite_task_keys: list[str] | None = None


class AgencyWorkflowTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_name: str
    description: str | None = None
    workflow_type_key: str | None = None
    successor_template_id: str | None = None
    created_at: datetime
    task_templates: list[AgencyTaskTemplateRead] = Field(default_factory=list)


class AgencyWorkflowTemplateCreate(BaseModel):
    workflow_name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class AgencyWorkflowTemplateUpdate(BaseModel):
    workflow_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class AgencyTaskTemplateCreate(BaseModel):
    task_title: str = Field(min_length=1, max_length=255)


class AgencyTaskTemplateUpdate(BaseModel):
    task_title: str | None = Field(default=None, min_length=1, max_length=255)


class AgencyTaskCatalogItemRead(BaseModel):
    task_key: str
    task_title: str
    description: str
    action_type: str
    prerequisite_task_keys: list[str] = Field(default_factory=list)


class AgencyTaskAvailabilityRead(BaseModel):
    available_tasks: list[AgencyTaskCatalogItemRead]
    placed_task_keys: list[str]
    available_count: int


class AgencyTaskFromCatalogCreate(BaseModel):
    task_key: str = Field(min_length=1, max_length=128)


class DashboardNextOpenTaskRead(BaseModel):
    id: str
    task_key: str
    title: str
    workflow_type: str
    workflow_name: str


class DashboardOpenRequest(TravelRequestRead):
    is_stale: bool = Field(description="True when last_worked_at is older than the stale threshold.")
    next_open_task: DashboardNextOpenTaskRead | None = None
    last_worked_at: datetime
    last_worked_by: UserAudit


class OpenRequestsPageRead(BaseModel):
    items: list[DashboardOpenRequest]
    total: int = Field(description="Total open requests matching the search query.")
    page: int = Field(description="Current one-based page number.")
    page_size: int = Field(description="Maximum number of rows returned per page.")
    total_pages: int = Field(description="Total number of pages available for the current query.")


class DashboardResponse(BaseModel):
    open_count: int
    stale_count: int = Field(description="Open requests whose last_worked_at is older than the stale threshold.")
    closed_count: int = Field(description="Requests that have been closed.")
    purchased_closed_count: int = Field(
        description="Closed requests with close reason Purchased - Trip Created."
    )
    other_closed_count: int = Field(description="Closed requests with any other close reason.")
    successful_sales_close_rate: float | None = Field(
        default=None,
        description="Purchased closed requests divided by all closed requests, as a percentage.",
    )
    total_pipeline_value: float = Field(
        default=0.0,
        description="Sum of the highest active proposed-quote cost per open request.",
    )


class SalesAnalyticsMonthCommission(BaseModel):
    month_key: str
    label: str
    total_commission: float
    booking_count: int


class SalesAnalyticsFunnelStage(BaseModel):
    label: str
    count: int


class SalesAnalyticsRejectionReason(BaseModel):
    segment: str = Field(
        description="open_active_lead for open requests, closed_lost_lead for closed requests without a booking."
    )
    reason: str
    count: int


class SalesAnalyticsCruiseLineShare(BaseModel):
    cruise_line: str
    booking_count: int
    share_percent: float
    total_booking_amount: float = 0.0
    total_commission: float = 0.0
    median_booking_amount: float = 0.0
    commission_rate_percent: float = 0.0


class SalesAnalyticsYearSummary(BaseModel):
    year: int
    total_sales_booked: float = 0.0
    total_sales_lost: float = Field(
        default=0.0,
        description=(
            "Sum of closed-lost request values for the year based on proposed cruise totals: "
            "single quote uses full value; multiple quotes use the lowest non-zero quote."
        ),
    )
    average_commission_rate_percent: float | None = Field(
        default=None,
        description="Total commission on bookings accepted in the year divided by booked sales in the year.",
    )
    win_rate_percent: float | None = Field(
        default=None,
        description=(
            "Requests booked in the year divided by closed requests that closed in the year. "
            "A closed request with a booked or deposited cruise counts as a win."
        ),
    )


class SalesAnalyticsResponse(BaseModel):
    commission_timeline: list[SalesAnalyticsMonthCommission] = Field(default_factory=list)
    funnel_stages: list[SalesAnalyticsFunnelStage] = Field(default_factory=list)
    win_rate_percent: float | None = Field(
        default=None,
        description=(
            "Closed requests with an accepted or deposited proposal divided by all closed requests."
        ),
    )
    rejection_reasons: list[SalesAnalyticsRejectionReason] = Field(default_factory=list)
    cruise_line_shares: list[SalesAnalyticsCruiseLineShare] = Field(default_factory=list)
    current_year_summary: SalesAnalyticsYearSummary
    key_metrics_prior_years: list[int] = Field(
        default_factory=list,
        description="Prior calendar years that have booked, rejected, or closed-lost key-metric activity.",
    )
    total_commission_forecast: float = 0.0
    available_years: list[int] = Field(
        default_factory=list,
        description="Years available for the pipeline revenue chart selector.",
    )


class SalesCopilotRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class SalesCopilotResponse(BaseModel):
    answer: str


class ClientImportTargetField(BaseModel):
    field_name: str
    required: bool
    description: str


class ClientImportParseResponse(BaseModel):
    filename: str
    sheet_name: str | None = None
    source_columns: list[str] = Field(default_factory=list)
    preview_rows: list[list[str]] = Field(default_factory=list)
    target_fields: list[ClientImportTargetField] = Field(default_factory=list)
    suggested_mapping: dict[str, str | None] = Field(default_factory=dict)


class ClientImportRowError(BaseModel):
    row_number: int = Field(ge=2)
    record_label: str
    message: str


class ClientImportResultResponse(BaseModel):
    imported_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    errors: list[ClientImportRowError] = Field(default_factory=list)


class ReportWorkflowTaskOption(BaseModel):
    value: str
    label: str


class ReportWorkflowTaskGroup(BaseModel):
    workflow_type: str
    workflow_name: str
    tasks: list[ReportWorkflowTaskOption]


class ReportMetaResponse(BaseModel):
    workflow_task_groups: list[ReportWorkflowTaskGroup]
    advisor_names: list[str] = Field(default_factory=list)
    residence_states: list[str] = Field(default_factory=list)


class FunnelLeakRowRead(BaseModel):
    request_id: int
    client_name: str
    quoted_cruise_line: str
    quoted_destination: str
    estimated_value_lost: float
    primary_rejection_reason: str
    loss_segment: str


class FunnelLeakPageRead(BaseModel):
    items: list[FunnelLeakRowRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdvisorScorecardRowRead(BaseModel):
    advisor_name: str
    active_lead_count: int
    proposals_pending: int
    completed_bookings: int
    avg_pipeline_velocity_days: float | None
    request_to_close_ratio_percent: float | None


class AdvisorScorecardPageRead(BaseModel):
    items: list[AdvisorScorecardRowRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class PassengerDemographicsRowRead(BaseModel):
    passenger_id: int
    passenger_name: str
    date_of_birth: str | None
    state_of_residence: str | None
    contact_phone: str | None
    email_address: str | None
    qualifiers: list[str]


class PassengerDemographicsPageRead(BaseModel):
    items: list[PassengerDemographicsRowRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class ReportManifestRowRead(BaseModel):
    request_id: int
    request_status: str
    pipeline_status: str
    close_reason: str | None = None
    primary_passenger: str
    destination: str
    cruise_line: str
    sailing_month_year: str
    estimated_gross_booking_total: float
    projected_commission_target: float
    owner_agent: str
    current_task: DashboardNextOpenTaskRead | None = None


class SalesManifestPageRead(BaseModel):
    items: list[ReportManifestRowRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class ReportSupplierLedgerRowRead(BaseModel):
    cruise_line: str
    active_booking_count: int
    total_volume: float
    total_commission_booked: float
    median_price_per_room: float
    average_commission_rate_percent: float
    share_percent: float = 0.0


class SupplierLedgerPageRead(BaseModel):
    items: list[ReportSupplierLedgerRowRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class MarketingCampaignCreate(BaseModel):
    campaign_name: str = Field(min_length=1, max_length=255)
    campaign_type: str = Field(min_length=1, max_length=100)
    monthly_spend: Decimal = Field(default=Decimal("0.00"), ge=0)
    start_date: date
    end_date: date | None = None

    @field_validator("campaign_type")
    @classmethod
    def validate_campaign_type(cls, value: str) -> str:
        from app.constants import MARKETING_CAMPAIGN_TYPES

        if value not in MARKETING_CAMPAIGN_TYPES:
            raise ValueError("Invalid campaign type selected.")
        return value

    @model_validator(mode="after")
    def validate_campaign_dates(self) -> "MarketingCampaignCreate":
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("End date must be on or after the start date.")
        return self


class MarketingCampaignUpdate(BaseModel):
    campaign_name: str | None = Field(default=None, min_length=1, max_length=255)
    campaign_type: str | None = Field(default=None, min_length=1, max_length=100)
    monthly_spend: Decimal | None = Field(default=None, ge=0)
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("campaign_type")
    @classmethod
    def validate_update_campaign_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from app.constants import MARKETING_CAMPAIGN_TYPES

        if value not in MARKETING_CAMPAIGN_TYPES:
            raise ValueError("Invalid campaign type selected.")
        return value


class MarketingCampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agency_id: str
    campaign_name: str
    campaign_type: str
    monthly_spend: float
    start_date: date
    end_date: date | None = None
    created_at: datetime


class MarketingCampaignSummaryRead(BaseModel):
    active_monthly_budget: float
    top_roi_campaign_name: str | None = None
    top_roi_percent: float | None = None
    total_attributed_volume: float
