from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, with_loader_criteria

from app.config import settings
from app.tenant_context import clear_current_agency_id, get_current_agency_id

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

TENANT_SCOPED_MODELS: tuple[type, ...] = ()


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        clear_current_agency_id()
        db.close()


def configure_tenant_session() -> None:
    """Install a global ORM execute hook that air-gaps SELECT queries by agency_id."""
    global TENANT_SCOPED_MODELS
    from app.models import (
        AgencyEmailLog,
        AgencyWorkflowTemplate,
        CallTranscript,
        ChatLog,
        MarketingCampaign,
        Passenger,
        ProposedCruise,
        QuotedInsurance,
        RequestCommunication,
        RequestNote,
        RequestResearchDocument,
        RequestTaskLive,
        RequestWorkflowLive,
        TravelRequest,
    )

    TENANT_SCOPED_MODELS = (
        TravelRequest,
        MarketingCampaign,
        AgencyWorkflowTemplate,
        Passenger,
        ProposedCruise,
        RequestCommunication,
        RequestTaskLive,
        RequestNote,
        RequestWorkflowLive,
        CallTranscript,
        ChatLog,
        RequestResearchDocument,
        QuotedInsurance,
        AgencyEmailLog,
    )

    @event.listens_for(Session, "do_orm_execute")
    def _apply_tenant_criteria(execute_state):
        if not execute_state.is_select:
            return

        agency_id = get_current_agency_id()
        if agency_id is None:
            return

        for model in TENANT_SCOPED_MODELS:
            execute_state.statement = execute_state.statement.options(
                with_loader_criteria(
                    model,
                    lambda cls, _agency_id=agency_id: cls.agency_id == _agency_id,
                    include_aliases=True,
                )
            )


configure_tenant_session()
