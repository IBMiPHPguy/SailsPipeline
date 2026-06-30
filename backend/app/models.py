from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, event, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.tenant_constants import DEFAULT_AGENCY_ID
from app.tenant_roles import (
    DEFAULT_INVITATION_ROLE,
    SUBSCRIPTION_STATE_ACTIVE,
    USER_ROLE_PLATFORM_SUPER_ADMIN,
    USER_ROLE_TENANT_AGENT,
)


class Agency(Base):
    __tablename__ = "agencies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    organization_handle: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    subscription_state: Mapped[str] = mapped_column(
        String(40), nullable=False, default=SUBSCRIPTION_STATE_ACTIVE, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    users: Mapped[list["User"]] = relationship(back_populates="agency")
    agency_invitations: Mapped[list["AgencyInvitation"]] = relationship(back_populates="agency")
    dashboard_rollup: Mapped["AgencyDashboardRollup | None"] = relationship(
        back_populates="agency",
        uselist=False,
    )
    report_metadata_cache: Mapped["AgencyReportMetadataCache | None"] = relationship(
        back_populates="agency",
        uselist=False,
    )
    marketing_campaigns: Mapped[list["MarketingCampaign"]] = relationship(back_populates="agency")


class MarketingCampaign(Base):
    __tablename__ = "marketing_campaigns"
    __table_args__ = (Index("idx_marketing_campaigns_agency_start", "agency_id", "start_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agency_id: Mapped[str] = mapped_column(String(36), ForeignKey("agencies.id"), nullable=False, index=True)
    campaign_name: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign_type: Mapped[str] = mapped_column(String(100), nullable=False)
    monthly_spend: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    agency: Mapped["Agency"] = relationship(back_populates="marketing_campaigns")
    travel_requests: Mapped[list["TravelRequest"]] = relationship(back_populates="marketing_campaign")


class AgencyDashboardRollup(Base):
    __tablename__ = "agency_dashboard_rollups"

    agency_id: Mapped[str] = mapped_column(String(36), ForeignKey("agencies.id"), primary_key=True)
    open_leads_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    proposals_pending_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_bookings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_volume_booked: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    total_commission_booked: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    stale_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    closed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    purchased_closed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_pipeline_value: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    marketing_active_monthly_budget: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    marketing_top_roi_campaign_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    marketing_top_roi_percent: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    marketing_total_attributed_volume: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    last_refreshed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    agency: Mapped["Agency"] = relationship(back_populates="dashboard_rollup")


class AgencyReportMetadataCache(Base):
    __tablename__ = "agency_report_metadata_caches"

    agency_id: Mapped[str] = mapped_column(String(36), ForeignKey("agencies.id"), primary_key=True)
    active_advisor_names: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    active_residence_states: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    last_refreshed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    agency: Mapped["Agency"] = relationship(back_populates="report_metadata_cache")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("agency_id", "email", name="uq_users_agency_email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agency_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agencies.id"), nullable=True, index=True
    )
    username: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default=USER_ROLE_TENANT_AGENT, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    can_view_all_agency_leads: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    agency: Mapped["Agency | None"] = relationship(back_populates="users")


@event.listens_for(User, "before_insert")
def assign_default_agency_for_tenant_users(_mapper, _connection, target: User) -> None:
    if target.role == USER_ROLE_PLATFORM_SUPER_ADMIN:
        return
    if target.agency_id is None:
        target.agency_id = DEFAULT_AGENCY_ID


class PlatformInvitation(Base):
    """The Bridge — platform-level tenant provisioning invitations."""

    __tablename__ = "platform_invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    target_agency_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_organization_handle: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    invite_email: Mapped[str] = mapped_column(String(255), nullable=False)
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AgencyInvitation(Base):
    """Tenant-scoped team invitations issued by a tenant super user."""

    __tablename__ = "agency_invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agency_id: Mapped[str] = mapped_column(String(36), ForeignKey("agencies.id"), nullable=False, index=True)
    invite_email: Mapped[str] = mapped_column(String(255), nullable=False)
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default=DEFAULT_INVITATION_ROLE)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    agency: Mapped[Agency] = relationship(back_populates="agency_invitations")


class TravelRequest(Base):
    __tablename__ = "travel_requests"
    __table_args__ = (
        Index("idx_travel_requests_status_created", "status", "created_at"),
        Index("idx_travel_requests_agency_status", "agency_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agency_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agencies.id"), nullable=False, default=DEFAULT_AGENCY_ID, index=True
    )
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    cruise_lines: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    excluded_cruise_lines: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    destination: Mapped[str] = mapped_column(String(120), nullable=False)
    destination_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    departure_date: Mapped[date] = mapped_column(Date, nullable=False)
    return_date: Mapped[date] = mapped_column(Date, nullable=False)
    cabin_types: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    qualifiers: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    passengers: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cabins_needed: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cabin_hold_reservation_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Open", index=True)
    close_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lead_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    referral_source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    marketing_campaign_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("marketing_campaigns.id"), nullable=True, index=True
    )
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    updated_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])
    updated_by: Mapped[User] = relationship(foreign_keys=[updated_by_id])
    marketing_campaign: Mapped["MarketingCampaign | None"] = relationship(back_populates="travel_requests")
    call_transcripts: Mapped[list["CallTranscript"]] = relationship(
        back_populates="travel_request",
        cascade="all, delete-orphan",
    )
    chat_logs: Mapped[list["ChatLog"]] = relationship(
        back_populates="travel_request",
        cascade="all, delete-orphan",
    )
    request_passengers: Mapped[list["RequestPassenger"]] = relationship(
        back_populates="travel_request",
        cascade="all, delete-orphan",
        order_by="RequestPassenger.id",
    )
    request_notes: Mapped[list["RequestNote"]] = relationship(
        back_populates="travel_request",
        cascade="all, delete-orphan",
        order_by="RequestNote.id.desc()",
    )
    request_audits: Mapped[list["TravelRequestAudit"]] = relationship(
        back_populates="travel_request",
        cascade="all, delete-orphan",
        order_by="TravelRequestAudit.changed_at.asc()",
    )
    passenger_audits: Mapped[list["RequestPassengerAudit"]] = relationship(
        cascade="all, delete-orphan",
        order_by="RequestPassengerAudit.changed_at.asc()",
    )
    proposed_cruises: Mapped[list["ProposedCruise"]] = relationship(
        back_populates="travel_request",
        cascade="all, delete-orphan",
        order_by="ProposedCruise.id.desc()",
    )
    quoted_insurance: Mapped[list["QuotedInsurance"]] = relationship(
        back_populates="travel_request",
        cascade="all, delete-orphan",
        order_by="QuotedInsurance.id.desc()",
    )
    request_workflows: Mapped[list["RequestWorkflow"]] = relationship(
        back_populates="travel_request",
        cascade="all, delete-orphan",
        order_by="RequestWorkflow.id.desc()",
    )
    request_workflows_live: Mapped[list["RequestWorkflowLive"]] = relationship(
        back_populates="travel_request",
        cascade="all, delete-orphan",
        order_by="RequestWorkflowLive.started_at.desc()",
    )
    request_communications: Mapped[list["RequestCommunication"]] = relationship(
        back_populates="travel_request",
        cascade="all, delete-orphan",
        order_by="RequestCommunication.id.desc()",
    )
    research_documents: Mapped[list["RequestResearchDocument"]] = relationship(
        back_populates="travel_request",
        cascade="all, delete-orphan",
        order_by="RequestResearchDocument.id.desc()",
    )


class Passenger(Base):
    __tablename__ = "passengers"
    __table_args__ = (
        Index("idx_passengers_last_first", "last_name", "first_name"),
        Index("idx_passengers_agency_active", "agency_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agency_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agencies.id"), nullable=False, default=DEFAULT_AGENCY_ID, index=True
    )
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    address_line_1: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address_line_2: Mapped[str | None] = mapped_column(String(120), nullable=True)
    city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    state_or_province: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(80), nullable=True)
    qualifiers: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_id])
    request_links: Mapped[list["RequestPassenger"]] = relationship(back_populates="passenger")


class RequestPassenger(Base):
    __tablename__ = "request_passengers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    travel_request_id: Mapped[int] = mapped_column(
        ForeignKey("travel_requests.id"), nullable=False, index=True
    )
    passenger_id: Mapped[int] = mapped_column(ForeignKey("passengers.id"), nullable=False, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    qualifiers: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    travel_request: Mapped[TravelRequest] = relationship(back_populates="request_passengers")
    passenger: Mapped[Passenger] = relationship(back_populates="request_links")

    @property
    def first_name(self) -> str:
        return self.passenger.first_name

    @first_name.setter
    def first_name(self, value: str) -> None:
        self.passenger.first_name = value

    @property
    def last_name(self) -> str:
        return self.passenger.last_name

    @last_name.setter
    def last_name(self, value: str) -> None:
        self.passenger.last_name = value

    @property
    def email(self) -> str | None:
        return self.passenger.email

    @email.setter
    def email(self, value: str | None) -> None:
        self.passenger.email = value

    @property
    def phone(self) -> str | None:
        return self.passenger.phone

    @phone.setter
    def phone(self, value: str | None) -> None:
        self.passenger.phone = value

    @property
    def date_of_birth(self) -> date | None:
        return self.passenger.date_of_birth

    @date_of_birth.setter
    def date_of_birth(self, value: date | None) -> None:
        self.passenger.date_of_birth = value

    @property
    def address_line_1(self) -> str | None:
        return self.passenger.address_line_1

    @address_line_1.setter
    def address_line_1(self, value: str | None) -> None:
        self.passenger.address_line_1 = value

    @property
    def address_line_2(self) -> str | None:
        return self.passenger.address_line_2

    @address_line_2.setter
    def address_line_2(self, value: str | None) -> None:
        self.passenger.address_line_2 = value

    @property
    def city(self) -> str | None:
        return self.passenger.city

    @city.setter
    def city(self, value: str | None) -> None:
        self.passenger.city = value

    @property
    def state_or_province(self) -> str | None:
        return self.passenger.state_or_province

    @state_or_province.setter
    def state_or_province(self, value: str | None) -> None:
        self.passenger.state_or_province = value

    @property
    def postal_code(self) -> str | None:
        return self.passenger.postal_code

    @postal_code.setter
    def postal_code(self, value: str | None) -> None:
        self.passenger.postal_code = value

    @property
    def country(self) -> str | None:
        return self.passenger.country

    @country.setter
    def country(self, value: str | None) -> None:
        self.passenger.country = value

    @property
    def passenger_is_active(self) -> bool:
        return self.passenger.is_active


class TravelRequestAudit(Base):
    __tablename__ = "travel_request_audits"
    __table_args__ = (Index("idx_tra_request_field", "travel_request_id", "field_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    travel_request_id: Mapped[int] = mapped_column(ForeignKey("travel_requests.id"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(80), nullable=False)
    from_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    to_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    travel_request: Mapped[TravelRequest] = relationship(back_populates="request_audits")
    changed_by: Mapped[User] = relationship(foreign_keys=[changed_by_id])


class RequestPassengerAudit(Base):
    __tablename__ = "request_passenger_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    travel_request_id: Mapped[int] = mapped_column(ForeignKey("travel_requests.id"), nullable=False)
    request_passenger_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passenger_label: Mapped[str | None] = mapped_column(String(161), nullable=True)
    field_name: Mapped[str] = mapped_column(String(80), nullable=False)
    from_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    to_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    travel_request: Mapped[TravelRequest] = relationship(back_populates="passenger_audits")
    changed_by: Mapped[User] = relationship(foreign_keys=[changed_by_id])


class RequestNote(Base):
    __tablename__ = "request_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agency_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agencies.id"), nullable=False, default=DEFAULT_AGENCY_ID, index=True
    )
    travel_request_id: Mapped[int] = mapped_column(ForeignKey("travel_requests.id"), nullable=False)
    summary: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    travel_request: Mapped[TravelRequest] = relationship(back_populates="request_notes")
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])
    updated_by: Mapped[User] = relationship(foreign_keys=[updated_by_id])
    audits: Mapped[list["RequestNoteAudit"]] = relationship(
        back_populates="request_note",
        cascade="all, delete-orphan",
        order_by="RequestNoteAudit.changed_at.asc()",
    )


class RequestNoteAudit(Base):
    __tablename__ = "request_note_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_note_id: Mapped[int] = mapped_column(ForeignKey("request_notes.id"), nullable=False)
    from_summary: Mapped[str | None] = mapped_column(String(160), nullable=True)
    to_summary: Mapped[str | None] = mapped_column(String(160), nullable=True)
    from_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    to_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    request_note: Mapped[RequestNote] = relationship(back_populates="audits")
    changed_by: Mapped[User] = relationship(foreign_keys=[changed_by_id])


class CallTranscript(Base):
    __tablename__ = "call_transcripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agency_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agencies.id"), nullable=False, default=DEFAULT_AGENCY_ID, index=True
    )
    travel_request_id: Mapped[int] = mapped_column(ForeignKey("travel_requests.id"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    travel_request: Mapped[TravelRequest] = relationship(back_populates="call_transcripts")
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])


class ChatLog(Base):
    __tablename__ = "chat_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agency_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agencies.id"), nullable=False, default=DEFAULT_AGENCY_ID, index=True
    )
    travel_request_id: Mapped[int] = mapped_column(ForeignKey("travel_requests.id"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    travel_request: Mapped[TravelRequest] = relationship(back_populates="chat_logs")
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])


def default_proposed_cruise_includes() -> dict:
    return {
        "drink_package": {"included": False, "name": None},
        "wifi": {"included": False, "name": None},
        "tips": False,
        "excursion": False,
        "excursion_credit": {"included": False, "amount": None},
        "onboard_credit": {"included": False, "amount": None},
        "gift_obc": {"included": False, "amount": None},
    }


class ProposedCruise(Base):
    __tablename__ = "proposed_cruises"
    __table_args__ = (Index("idx_proposed_cruises_request_status", "travel_request_id", "status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agency_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agencies.id"), nullable=False, default=DEFAULT_AGENCY_ID, index=True
    )
    travel_request_id: Mapped[int] = mapped_column(ForeignKey("travel_requests.id"), nullable=False)
    departure_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    cruise_line: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    ship: Mapped[str] = mapped_column(String(120), nullable=False)
    number_of_nights: Mapped[int] = mapped_column(Integer, nullable=False)
    itinerary_name: Mapped[str] = mapped_column(String(160), nullable=False)
    itinerary_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    room_category: Mapped[str] = mapped_column(String(120), nullable=False)
    room_number: Mapped[str] = mapped_column(String(40), nullable=False)
    passengers_in_room: Mapped[int] = mapped_column(Integer, nullable=False)
    deposit_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    deposit_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    final_payment_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    cabin_pricing: Mapped[list | None] = mapped_column(JSON, nullable=True)
    cabin_rooms: Mapped[list | None] = mapped_column(JSON, nullable=True)
    cabin_hold_reservation_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    includes: Mapped[dict] = mapped_column(JSON, nullable=False, default=default_proposed_cruise_includes)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Proposed", index=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rejection_reason_detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    travel_request: Mapped[TravelRequest] = relationship(back_populates="proposed_cruises")
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])
    updated_by: Mapped[User] = relationship(foreign_keys=[updated_by_id])
    passenger_links: Mapped[list["ProposedCruisePassenger"]] = relationship(
        back_populates="proposed_cruise",
        cascade="all, delete-orphan",
    )


class ProposedCruisePassenger(Base):
    __tablename__ = "proposed_cruise_passengers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proposed_cruise_id: Mapped[int] = mapped_column(ForeignKey("proposed_cruises.id"), nullable=False)
    request_passenger_id: Mapped[int] = mapped_column(
        ForeignKey("request_passengers.id"), nullable=False
    )
    cabin_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    proposed_cruise: Mapped[ProposedCruise] = relationship(back_populates="passenger_links")
    request_passenger: Mapped[RequestPassenger] = relationship()


class QuotedInsurance(Base):
    __tablename__ = "quoted_insurance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agency_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agencies.id"), nullable=False, default=DEFAULT_AGENCY_ID, index=True
    )
    travel_request_id: Mapped[int] = mapped_column(ForeignKey("travel_requests.id"), nullable=False)
    carrier: Mapped[str] = mapped_column(String(120), nullable=False)
    premium_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    plan_name: Mapped[str] = mapped_column(String(160), nullable=False)
    cancellation_coverage: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    medical_coverage: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    medical_evac_coverage: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Proposed")
    declined_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    travel_request: Mapped[TravelRequest] = relationship(back_populates="quoted_insurance")
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])
    updated_by: Mapped[User] = relationship(foreign_keys=[updated_by_id])


class RequestWorkflow(Base):
    __tablename__ = "request_workflows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agency_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agencies.id"), nullable=False, default=DEFAULT_AGENCY_ID, index=True
    )
    travel_request_id: Mapped[int] = mapped_column(ForeignKey("travel_requests.id"), nullable=False)
    workflow_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Active")
    parent_workflow_id: Mapped[int | None] = mapped_column(ForeignKey("request_workflows.id"), nullable=True)
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    completed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    travel_request: Mapped[TravelRequest] = relationship(back_populates="request_workflows")
    started_by: Mapped[User] = relationship(foreign_keys=[started_by_id])
    completed_by: Mapped[User] = relationship(foreign_keys=[completed_by_id])
    parent_workflow: Mapped["RequestWorkflow | None"] = relationship(
        remote_side="RequestWorkflow.id",
        foreign_keys=[parent_workflow_id],
    )
    tasks: Mapped[list["RequestTask"]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="RequestTask.sort_order.asc()",
    )


class RequestTask(Base):
    __tablename__ = "request_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agency_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agencies.id"), nullable=False, default=DEFAULT_AGENCY_ID, index=True
    )
    request_workflow_id: Mapped[int] = mapped_column(ForeignKey("request_workflows.id"), nullable=False)
    travel_request_id: Mapped[int] = mapped_column(ForeignKey("travel_requests.id"), nullable=False)
    task_key: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Open")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    workflow: Mapped[RequestWorkflow] = relationship(back_populates="tasks")
    travel_request: Mapped[TravelRequest] = relationship()
    completed_by: Mapped[User | None] = relationship(foreign_keys=[completed_by_id])


class RequestCommunication(Base):
    __tablename__ = "request_communications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agency_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agencies.id"), nullable=False, default=DEFAULT_AGENCY_ID, index=True
    )
    travel_request_id: Mapped[int] = mapped_column(ForeignKey("travel_requests.id"), nullable=False)
    request_workflow_id: Mapped[int | None] = mapped_column(ForeignKey("request_workflows.id"), nullable=True)
    request_workflow_live_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("request_workflows_live.id"), nullable=True
    )
    communication_type: Mapped[str] = mapped_column(String(40), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Draft")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    travel_request: Mapped[TravelRequest] = relationship(back_populates="request_communications")
    workflow: Mapped[RequestWorkflow | None] = relationship()
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])
    updated_by: Mapped[User] = relationship(foreign_keys=[updated_by_id])


class RequestResearchDocument(Base):
    __tablename__ = "request_research_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agency_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agencies.id"), nullable=False, default=DEFAULT_AGENCY_ID, index=True
    )
    travel_request_id: Mapped[int] = mapped_column(ForeignKey("travel_requests.id"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    travel_request: Mapped[TravelRequest] = relationship(back_populates="research_documents")
    uploaded_by: Mapped[User] = relationship(foreign_keys=[uploaded_by_id])


class AgencyWorkflowTemplate(Base):
    __tablename__ = "agency_workflow_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agency_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agencies.id"), nullable=False, index=True
    )
    workflow_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_type_key: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    successor_template_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agency_workflow_templates.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    agency: Mapped[Agency] = relationship()
    successor_template: Mapped["AgencyWorkflowTemplate | None"] = relationship(
        remote_side="AgencyWorkflowTemplate.id",
        foreign_keys=[successor_template_id],
    )
    task_templates: Mapped[list["AgencyTaskTemplate"]] = relationship(
        back_populates="workflow_template",
        cascade="all, delete-orphan",
        order_by="AgencyTaskTemplate.sequence_order.asc()",
    )


class AgencyTaskTemplate(Base):
    __tablename__ = "agency_task_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workflow_template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agency_workflow_templates.id"), nullable=False, index=True
    )
    task_title: Mapped[str] = mapped_column(String(255), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, default="manual_check")
    target_field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    task_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prerequisite_task_keys: Mapped[list | None] = mapped_column(JSON, nullable=True)

    workflow_template: Mapped[AgencyWorkflowTemplate] = relationship(back_populates="task_templates")


class AgencyCustomTaskDefinition(Base):
    __tablename__ = "agency_custom_task_definitions"
    __table_args__ = (
        UniqueConstraint("agency_id", "task_key", name="uq_agency_custom_task_definitions_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agency_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agencies.id"), nullable=False, index=True
    )
    task_key: Mapped[str] = mapped_column(String(80), nullable=False)
    task_title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, default="manual_check")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    agency: Mapped[Agency] = relationship()


class RequestWorkflowLive(Base):
    __tablename__ = "request_workflows_live"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agency_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agencies.id"), nullable=False, index=True
    )
    travel_request_id: Mapped[int] = mapped_column(ForeignKey("travel_requests.id"), nullable=False, index=True)
    template_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agency_workflow_templates.id"), nullable=True
    )
    workflow_name: Mapped[str] = mapped_column(String(255), nullable=False)
    workflow_type_key: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Active")
    parent_workflow_live_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("request_workflows_live.id"), nullable=True
    )
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    completed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    legacy_workflow_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    travel_request: Mapped[TravelRequest] = relationship(back_populates="request_workflows_live")
    template: Mapped[AgencyWorkflowTemplate | None] = relationship()
    started_by: Mapped[User] = relationship(foreign_keys=[started_by_id])
    completed_by: Mapped[User | None] = relationship(foreign_keys=[completed_by_id])
    parent_workflow: Mapped["RequestWorkflowLive | None"] = relationship(
        remote_side="RequestWorkflowLive.id",
        foreign_keys=[parent_workflow_live_id],
    )
    tasks: Mapped[list["RequestTaskLive"]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="RequestTaskLive.sequence_order.asc()",
    )


class RequestTaskLive(Base):
    __tablename__ = "request_tasks_live"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agency_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agencies.id"), nullable=False, index=True
    )
    request_workflow_live_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("request_workflows_live.id"), nullable=False, index=True
    )
    travel_request_id: Mapped[int] = mapped_column(ForeignKey("travel_requests.id"), nullable=False, index=True)
    template_task_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agency_task_templates.id"), nullable=True
    )
    task_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    task_title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, default="manual_check")
    target_field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="Open")
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    completed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    legacy_task_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    workflow: Mapped[RequestWorkflowLive] = relationship(back_populates="tasks")
    travel_request: Mapped[TravelRequest] = relationship()
    completed_by: Mapped[User | None] = relationship(foreign_keys=[completed_by_id])
    template_task: Mapped["AgencyTaskTemplate | None"] = relationship(foreign_keys=[template_task_id])
