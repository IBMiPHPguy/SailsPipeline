from datetime import date, datetime
from decimal import Decimal
import re
from typing import Any, Literal

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


class PublicRegisterRequest(BaseModel):
    agency_name: str = Field(min_length=2, max_length=120)
    admin_email: EmailStr
    admin_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=11, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        validate_password(value)
        return value


class ForgotPasswordRequest(BaseModel):
    organization_handle: str = Field(min_length=1, max_length=50, pattern=r"^\S+$")
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=11, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        validate_password(value)
        return value


class MessageResponse(BaseModel):
    message: str


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


class AgencyProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    organization_handle: str
    business_address_line_1: str | None = None
    business_address_line_2: str | None = None
    business_city: str | None = None
    business_state_or_province: str | None = None
    business_postal_code: str | None = None
    business_country: str | None = None


class AgencyBusinessAddressUpdate(BaseModel):
    business_address_line_1: str | None = Field(default=None, max_length=120)
    business_address_line_2: str | None = Field(default=None, max_length=120)
    business_city: str | None = Field(default=None, max_length=80)
    business_state_or_province: str | None = Field(default=None, max_length=50)
    business_postal_code: str | None = Field(default=None, max_length=20)
    business_country: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "AgencyBusinessAddressUpdate":
        if not any(
            value is not None
            for value in (
                self.business_address_line_1,
                self.business_address_line_2,
                self.business_city,
                self.business_state_or_province,
                self.business_postal_code,
                self.business_country,
            )
        ):
            raise ValueError("At least one business address field must be provided.")
        return self


class AgencySettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agency_id: str
    agency_name: str
    brand_logo_url: str | None = None
    primary_color: str
    secondary_color: str
    custom_master_tc: str | None = None
    email_signature_block: str | None = None
    business_address: str | None = None
    business_phone: str | None = None


class AgencySettingsUpdate(BaseModel):
    agency_name: str | None = Field(default=None, min_length=1, max_length=255)
    primary_color: str | None = Field(default=None, max_length=7)
    secondary_color: str | None = Field(default=None, max_length=7)
    custom_master_tc: str | None = None
    email_signature_block: str | None = None
    business_address: str | None = Field(default=None, max_length=512)
    business_phone: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "AgencySettingsUpdate":
        if not any(
            value is not None
            for value in (
                self.agency_name,
                self.primary_color,
                self.secondary_color,
                self.custom_master_tc,
                self.email_signature_block,
                self.business_address,
                self.business_phone,
            )
        ):
            raise ValueError("At least one settings field must be provided.")
        return self


class AgencyBrandingChromeRead(BaseModel):
    agency_name: str
    brand_logo_url: str | None = None
    primary_color: str
    secondary_color: str


class AgencyPublicBrandingRead(BaseModel):
    agency_id: str
    agency_name: str
    brand_logo_url: str | None = None
    primary_color: str
    secondary_color: str
    business_address: str | None = None
    business_phone: str | None = None
    custom_master_tc: str | None = None


class AgencyAiSettingsRead(BaseModel):
    configured: bool


class AgencyAiStatusRead(BaseModel):
    configured: bool
    can_manage: bool
    uses_tenant_key: bool


class AgencyAiSettingsUpdate(BaseModel):
    gemini_api_key: str = Field(min_length=20, max_length=512)


class AgencySettingsLogoUploadResponse(BaseModel):
    brand_logo_url: str
    message: str = "Brand logo uploaded."


class AgencySignatureImageUploadResponse(BaseModel):
    image_url: str
    message: str = "Signature image uploaded."


class PortalBrandingPayload(BaseModel):
    agency_name: str
    brand_logo_url: str | None = None
    primary_color: str
    secondary_color: str
    business_address: str | None = None
    business_phone: str | None = None


class PasswordResetValidateResponse(BaseModel):
    branding: PortalBrandingPayload
    organization_handle: str


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
    intake_mode: str | None = Field(default=None, max_length=100)
    intake_social_platform: str | None = Field(default=None, max_length=50)
    ship_name: str | None = Field(default=None, max_length=100)
    group_id: str | None = Field(default=None, max_length=36)
    group_inventory_id: str | None = Field(default=None, max_length=36)

    @field_validator("lead_source")
    @classmethod
    def validate_lead_source(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        from app.constants import LEAD_SOURCES

        if value not in LEAD_SOURCES:
            raise ValueError("Invalid lead source selected.")
        return value

    @field_validator("intake_mode")
    @classmethod
    def validate_intake_mode(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        from app.constants import INTAKE_MODES

        if value not in INTAKE_MODES:
            raise ValueError("Invalid intake mode selected.")
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
    def validate_intake_attribution(self) -> "TravelRequestBase":
        from app.intake_attribution import normalize_intake_attribution

        mode, platform = normalize_intake_attribution(
            intake_mode=self.intake_mode,
            intake_social_platform=self.intake_social_platform,
        )
        self.intake_mode = mode
        self.intake_social_platform = platform
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
    group_bookings: list["TravelRequestGroupBookingInput"] = Field(default_factory=list)


class TravelRequestGroupBookingInput(BaseModel):
    group_inventory_id: str = Field(min_length=1, max_length=36)
    cabins_requested: int = Field(ge=1, le=10)


class PassengerLoyaltyNumberInput(BaseModel):
    cruise_line: str = Field(min_length=1, max_length=100)
    loyalty_number: str = Field(min_length=1, max_length=80)

    @field_validator("cruise_line")
    @classmethod
    def validate_cruise_line(cls, value: str) -> str:
        return validate_cruise_line_values([value], require_at_least_one=True)[0]


class PassengerLoyaltyNumberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cruise_line: str
    loyalty_number: str


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
    has_annual_insurance: bool = False
    annual_insurance_expires_at: date | None = None
    annual_insurance_policy_number: str | None = None
    cruise_loyalty_numbers: list[PassengerLoyaltyNumberRead] = Field(default_factory=list)
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
    has_annual_insurance: bool = False
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
    has_annual_insurance: bool | None = None
    annual_insurance_expires_at: date | None = None
    annual_insurance_policy_number: str | None = Field(default=None, max_length=80)
    cruise_loyalty_numbers: list[PassengerLoyaltyNumberInput] | None = None

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
    has_annual_insurance: bool = False
    annual_insurance_expires_at: date | None = None
    annual_insurance_policy_number: str | None = Field(default=None, max_length=80)
    cruise_loyalty_numbers: list[PassengerLoyaltyNumberInput] = Field(default_factory=list)

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
    has_annual_insurance: bool = False
    annual_insurance_expires_at: date | None = None
    annual_insurance_policy_number: str | None = None
    cruise_loyalty_numbers: list[PassengerLoyaltyNumberRead] = Field(default_factory=list)

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
    has_annual_insurance: bool | None = None
    annual_insurance_expires_at: date | None = None
    annual_insurance_policy_number: str | None = Field(default=None, max_length=80)
    cruise_loyalty_numbers: list[PassengerLoyaltyNumberInput] | None = None

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
    intake_mode: str | None = Field(default=None, max_length=100)
    intake_social_platform: str | None = Field(default=None, max_length=50)
    ship_name: str | None = Field(default=None, max_length=100)
    group_id: str | None = Field(default=None, max_length=36)
    group_inventory_id: str | None = Field(default=None, max_length=36)
    group_bookings: list[TravelRequestGroupBookingInput] | None = None

    @field_validator("lead_source")
    @classmethod
    def validate_update_lead_source(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        from app.constants import LEAD_SOURCES

        if value not in LEAD_SOURCES:
            raise ValueError("Invalid lead source selected.")
        return value

    @field_validator("intake_mode")
    @classmethod
    def validate_update_intake_mode(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        from app.constants import INTAKE_MODES

        if value not in INTAKE_MODES:
            raise ValueError("Invalid intake mode selected.")
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

    @model_validator(mode="after")
    def validate_update_intake_attribution(self) -> "TravelRequestUpdate":
        if self.intake_mode is None and self.intake_social_platform is None:
            return self
        from app.intake_attribution import normalize_intake_attribution

        mode, platform = normalize_intake_attribution(
            intake_mode=self.intake_mode,
            intake_social_platform=self.intake_social_platform,
        )
        self.intake_mode = mode
        self.intake_social_platform = platform
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
    quote_mailed: bool | None = None

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
    quote_mailed: bool = False
    created_by: UserAudit
    updated_by: UserAudit
    created_at: datetime
    updated_at: datetime


class TravelRequestRead(TravelRequestBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    close_reason: str | None = None
    group_inventory_reservation_applied: bool = False
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
    group_summary: "AgencyGroupIntakeSummaryRead | None" = None
    group_bookings: list["TravelRequestGroupBookingRead"] = Field(default_factory=list)
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
    sender_email: EmailStr | None = None
    received_at: datetime | None = None
    is_response_to_agent: bool = False

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

    @model_validator(mode="after")
    def validate_inbound_email_fields(self) -> "RequestCommunicationCreate":
        from app.constants import COMMUNICATION_STATUS_RECEIVED, COMMUNICATION_TYPE_INBOUND_EMAIL

        if self.communication_type != COMMUNICATION_TYPE_INBOUND_EMAIL:
            return self
        if self.status != COMMUNICATION_STATUS_RECEIVED:
            raise ValueError("Inbound emails must use the Received status.")
        if not self.sender_email:
            raise ValueError("Sender email is required for inbound emails.")
        if self.received_at is None:
            raise ValueError("Received date and time are required for inbound emails.")
        return self


class RequestCommunicationUpdate(BaseModel):
    communication_type: str | None = Field(default=None, min_length=1, max_length=40)
    subject: str | None = Field(default=None, min_length=1, max_length=255)
    body: str | None = Field(default=None, min_length=1)
    status: str | None = Field(default=None, min_length=1, max_length=40)
    sender_email: EmailStr | None = None
    received_at: datetime | None = None
    is_response_to_agent: bool | None = None

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
    sender_email: EmailStr | None = None
    request_workflow_id: str | None = Field(default=None, validation_alias="request_workflow_live_id")
    sent_at: datetime | None = None
    received_at: datetime | None = None
    is_response_to_agent: bool = False
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
    sender_email: EmailStr | None = None
    request_workflow_id: str | None = Field(default=None, validation_alias="request_workflow_live_id")
    sent_at: datetime | None = None
    received_at: datetime | None = None
    is_response_to_agent: bool = False
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


class SendResearchCommunicationResponse(BaseModel):
    message: str
    communication: RequestCommunicationRead


class SendCcAuthEmailRequest(BaseModel):
    travel_request_id: int = Field(gt=0)


class SendCcAuthEmailResponse(BaseModel):
    message: str
    portal_url: str
    email_sent: bool
    recipient: str
    total_deposit_due: str
    accepted_cruise_count: int


class CcAuthPortalCruiseRead(BaseModel):
    cruise_line: str
    ship: str
    sailing_date: date
    cabin_type: str
    deposit_amount: str
    final_payment_due_date: date
    itinerary_name: str
    number_of_nights: int


class CcAuthValidateResponse(BaseModel):
    valid: bool = True
    passenger_name: str
    passenger_email: str
    agency_name: str
    cruises: list[CcAuthPortalCruiseRead]
    total_deposit_due: str
    expires_at: datetime
    authorization_id: str


class CcAuthCompleteResponse(BaseModel):
    message: str
    status: str
    completed_at: datetime
    authorization_id: str


class CcAuthCardPayload(BaseModel):
    cardholder_name: str = Field(min_length=2, max_length=120)
    card_number: str = Field(min_length=13, max_length=23)
    expiration: str = Field(min_length=5, max_length=7)
    security_code: str = Field(min_length=3, max_length=4)

    @field_validator("cardholder_name")
    @classmethod
    def validate_cardholder_name(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 2:
            raise ValueError("Cardholder name is required.")
        return stripped

    @field_validator("card_number")
    @classmethod
    def validate_card_number(cls, value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if len(digits) < 13 or len(digits) > 19:
            raise ValueError("Enter a valid card number.")
        return digits

    @field_validator("expiration")
    @classmethod
    def validate_expiration(cls, value: str) -> str:
        stripped = value.strip()
        match = re.fullmatch(r"(\d{2})\s*/\s*(\d{2})", stripped)
        if not match:
            raise ValueError("Expiration must use MM/YY format.")
        month = int(match.group(1))
        if month < 1 or month > 12:
            raise ValueError("Expiration month must be between 01 and 12.")
        return f"{match.group(1)}/{match.group(2)}"

    @field_validator("security_code")
    @classmethod
    def validate_security_code(cls, value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if len(digits) not in {3, 4}:
            raise ValueError("Security code must be 3 or 4 digits.")
        return digits


class CcAuthVaultAccessRequest(BaseModel):
    vault_access_key: str = Field(min_length=1, max_length=255)


class CcAuthSummaryRead(BaseModel):
    id: str
    status: str
    created_at: datetime
    completed_at: datetime | None
    expires_at: datetime
    has_card_data: bool
    card_data_purged: bool


class CcAuthRevealedCardRead(BaseModel):
    cardholder_name: str
    card_number: str
    expiration: str
    security_code: str


class CcAuthRevealResponse(BaseModel):
    authorization_id: str
    card: CcAuthRevealedCardRead


class CcAuthPurgeResponse(BaseModel):
    message: str
    authorization_id: str
    status: str
    card_data_purged: bool


class SendMasterTermsEmailRequest(BaseModel):
    travel_request_id: int = Field(gt=0)


class SendMasterTermsEmailResponse(BaseModel):
    message: str
    portal_url: str
    email_sent: bool
    recipient: str


class TermsValidateResponse(BaseModel):
    valid: bool
    passenger_name: str
    passenger_email: str
    agency_name: str
    terms_text: str
    expires_at: str
    request_id: str


class TermsAcceptResponse(BaseModel):
    message: str
    accepted: bool


class TermsRequestStatusResponse(BaseModel):
    on_file: bool
    client_id: int
    agency_id: str
    travel_request_id: int | None = None
    accepted_at: str | None = None
    version_hash: str | None = None
    ip_address: str | None = None
    task_auto_completed: bool = False


class AnnualInsuranceUpdate(BaseModel):
    has_annual_insurance: bool | None = None
    annual_insurance_expires_at: date | None = None
    annual_insurance_policy_number: str | None = Field(default=None, max_length=80)


class InsuranceTrackingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    insurance_status: str
    waiver_signed_at: datetime | None = None
    waiver_ip: str | None = None


class InsuranceRequestStatusResponse(BaseModel):
    travel_request_id: int
    insurance_status: str
    waiver_signed: bool
    waiver_signed_at: str | None = None
    waiver_request_status: str = "none"
    waiver_sent_at: str | None = None
    waiver_expires_at: str | None = None
    has_annual_insurance: bool
    annual_insurance_expires_at: date | None = None
    annual_insurance_policy_number: str | None = None
    annual_insurance_is_valid: bool = False
    annual_insurance_is_expired: bool = False
    primary_passenger_id: int | None = None
    client_name: str = ""
    client_registry_passenger_id: int | None = None
    has_accepted_quote: bool = False
    all_quotes_declined: bool = False
    has_proposed_quotes: bool = False
    can_complete_task: bool = False
    completion_blocked_reason: str | None = None


class SendInsuranceWaiverEmailRequest(BaseModel):
    travel_request_id: int = Field(gt=0)


class SendInsuranceWaiverEmailResponse(BaseModel):
    message: str
    portal_url: str
    email_sent: bool
    recipient: str


class InsuranceWaiverValidateResponse(BaseModel):
    valid: bool
    passenger_name: str
    passenger_email: str
    agency_name: str
    waiver_text: str
    expires_at: str
    request_id: int


class InsuranceWaiverSignResponse(BaseModel):
    message: str
    signed: bool


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
    task_count: int = 0
    is_recommended: bool = False


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
    description: str | None = None
    sequence_order: int | None = Field(default=None, ge=1)


class AgencyWorkflowTemplateResetRead(BaseModel):
    template: AgencyWorkflowTemplateRead
    message: str


class AgencyTaskTemplateMove(BaseModel):
    target_workflow_template_id: str = Field(min_length=1)
    sequence_order: int | None = Field(default=None, ge=1)


class AgencyTaskTemplateMoveResult(BaseModel):
    source_workflow_template: AgencyWorkflowTemplateRead
    target_workflow_template: AgencyWorkflowTemplateRead


class AgencyTaskCatalogItemRead(BaseModel):
    task_key: str
    task_title: str
    description: str
    action_type: str
    prerequisite_task_keys: list[str] = Field(default_factory=list)
    on_complete_schedule_follow_up_task_key: str | None = None
    follow_up_due_days: int | None = None
    allows_reached_out: bool = False


class AgencyCustomTaskDefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_key: str
    task_title: str
    description: str | None = None
    action_type: str
    created_at: datetime
    updated_at: datetime


class AgencyCustomTaskDefinitionCreate(BaseModel):
    task_title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)


class AgencyCustomTaskDefinitionUpdate(BaseModel):
    task_title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)


class AgencyTaskFromCustomDefinitionCreate(BaseModel):
    task_key: str = Field(min_length=1, max_length=128)
    sequence_order: int | None = Field(default=None, ge=1)


class AgencyTaskAvailabilityRead(BaseModel):
    available_tasks: list[AgencyTaskCatalogItemRead]
    available_custom_tasks: list[AgencyTaskCatalogItemRead] = Field(default_factory=list)
    custom_task_definitions: list[AgencyCustomTaskDefinitionRead] = Field(default_factory=list)
    placed_task_keys: list[str]
    available_count: int


class AgencyTaskInventoryItemRead(BaseModel):
    task_key: str
    task_title: str
    description: str
    task_type: Literal["builtin", "library"]
    definition_id: str | None = None
    task_template_id: str | None = None
    workflow_template_id: str | None = None
    workflow_name: str | None = None
    sequence_order: int | None = None

    model_config = ConfigDict(from_attributes=True)


class AgencyTaskFromCatalogCreate(BaseModel):
    task_key: str = Field(min_length=1, max_length=128)
    task_title: str | None = Field(default=None, min_length=1, max_length=255)
    sequence_order: int | None = Field(default=None, ge=1)


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


class AgencyGroupInventoryBase(BaseModel):
    cabin_category: str = Field(min_length=1, max_length=50)
    cabin_type: str = Field(min_length=1, max_length=100)
    cabin_description: str | None = None
    price_per_cabin: float = Field(ge=0, default=0)
    deposit_per_cabin: float = Field(ge=0, default=0)
    cabins_allocated: int = Field(ge=0, default=0)


class AgencyGroupInventoryCreate(AgencyGroupInventoryBase):
    cabins_reserved: int = Field(ge=0, default=0)


class AgencyGroupInventoryUpdate(BaseModel):
    cabin_category: str | None = Field(default=None, min_length=1, max_length=50)
    cabin_type: str | None = Field(default=None, min_length=1, max_length=100)
    cabin_description: str | None = None
    price_per_cabin: float | None = Field(default=None, ge=0)
    deposit_per_cabin: float | None = Field(default=None, ge=0)
    cabins_allocated: int | None = Field(default=None, ge=0)
    cabins_reserved: int | None = Field(default=None, ge=0)


class AgencyGroupInventoryRead(AgencyGroupInventoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    group_id: str
    cabins_reserved: int
    cabins_remaining: int
    created_at: datetime
    updated_at: datetime


class AgencyGroupBase(BaseModel):
    group_name: str = Field(min_length=1, max_length=255)
    cruise_line: str = Field(min_length=1, max_length=100)
    ship_name: str = Field(min_length=1, max_length=100)
    sailing_date: date
    disembarkation_date: date
    group_id_code: str | None = Field(default=None, max_length=100)
    group_amenities: str | None = None
    tc_ratio: str | None = Field(default="1:16", max_length=50)
    is_active: bool = True


class AgencyGroupCreate(AgencyGroupBase):
    inventory_items: list[AgencyGroupInventoryCreate] = Field(default_factory=list)


class AgencyGroupUpdate(BaseModel):
    group_name: str | None = Field(default=None, min_length=1, max_length=255)
    cruise_line: str | None = Field(default=None, min_length=1, max_length=100)
    ship_name: str | None = Field(default=None, min_length=1, max_length=100)
    sailing_date: date | None = None
    disembarkation_date: date | None = None
    group_id_code: str | None = Field(default=None, max_length=100)
    group_amenities: str | None = None
    tc_ratio: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None


class AgencyGroupSummaryRead(BaseModel):
    inventory_row_count: int
    total_cabins_allocated: int
    total_cabins_reserved: int
    total_cabins_remaining: int


class AgencyGroupRead(AgencyGroupBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agency_id: str
    inventory_items: list[AgencyGroupInventoryRead] = Field(default_factory=list)
    summary: AgencyGroupSummaryRead
    created_at: datetime
    updated_at: datetime


class AgencyGroupListItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agency_id: str
    group_name: str
    cruise_line: str
    ship_name: str
    sailing_date: date
    disembarkation_date: date
    group_id_code: str | None = None
    is_active: bool
    summary: AgencyGroupSummaryRead
    created_at: datetime
    updated_at: datetime


class AgencyGroupListPageRead(BaseModel):
    items: list[AgencyGroupListItemRead]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_pages: int = Field(ge=0)


class AgencyGroupPickerItemRead(BaseModel):
    id: str
    group_name: str
    cruise_line: str
    ship_name: str
    sailing_date: date
    disembarkation_date: date


class AgencyGroupInventoryOptionRead(BaseModel):
    id: str
    cabin_category: str
    cabin_type: str
    cabin_description: str | None = None
    price_per_cabin: float
    deposit_per_cabin: float
    cabins_remaining: int
    label: str
    is_selectable: bool


class AgencyGroupIntakeSummaryRead(BaseModel):
    id: str
    group_name: str
    cruise_line: str
    ship_name: str
    sailing_date: date
    disembarkation_date: date
    group_id_code: str | None = None
    group_amenities: str | None = None


class TravelRequestGroupBookingRead(BaseModel):
    id: str
    group_inventory_id: str
    cabins_requested: int
    cabin_category: str
    cabin_type: str
    cabin_description: str | None = None
    price_per_cabin: float
    cabins_remaining: int


class AgencyGroupInventoryMetricsRead(BaseModel):
    inventory_id: str
    cabin_category: str
    cabins_allocated: int
    cabins_reserved: int
    cabins_remaining: int
    max_gross_yield: float
    accrued_gross_yield: float
    liquidation_percent: float
    liquidation_tone: str


class AgencyGroupMetricsTotalsRead(BaseModel):
    cabins_allocated: int
    cabins_reserved: int
    cabins_remaining: int
    max_gross_yield: float
    accrued_gross_yield: float
    remaining_gross_yield: float
    liquidation_percent: float
    liquidation_tone: str


class AgencyGroupTourConductorMetricsRead(BaseModel):
    ratio_label: str
    berths_per_credit: int
    tc_per_credit: int
    used_default_ratio: bool
    total_cabins_reserved: int
    total_berths_reserved: int
    tc_credits_earned: int
    berths_until_next_tc: int
    cabins_until_next_tc: int
    message: str


class AgencyGroupMetricsRead(BaseModel):
    group_id: str
    linked_request_count: int
    totals: AgencyGroupMetricsTotalsRead
    inventory_rows: list[AgencyGroupInventoryMetricsRead]
    tour_conductor: AgencyGroupTourConductorMetricsRead
