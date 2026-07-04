from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, with_loader_criteria

from app.config import settings
from app.tenant_context import (
    TenantContextRequiredError,
    get_current_agency_id,
    is_tenant_scoping_required,
)

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
        db.close()


def _statement_targets_tenant_scoped_models(execute_state) -> bool:
    if not TENANT_SCOPED_MODELS:
        return False

    scoped_mappers = {model.__mapper__ for model in TENANT_SCOPED_MODELS}
    scoped_table_names = {model.__tablename__ for model in TENANT_SCOPED_MODELS}
    statement = execute_state.statement

    if hasattr(statement, "column_descriptions"):
        for desc in statement.column_descriptions:
            entity = desc.get("entity")
            if entity is None:
                continue
            mapper = getattr(entity, "mapper", None)
            if mapper is None and hasattr(entity, "class_"):
                mapper = getattr(entity.class_, "__mapper__", None)
            if mapper in scoped_mappers:
                return True

    try:
        for from_clause in statement.get_final_froms():
            mapper = getattr(from_clause, "entity_namespace", None)
            if mapper in scoped_mappers:
                return True
            table_name = getattr(from_clause, "name", None)
            if table_name in scoped_table_names:
                return True
    except Exception:
        return True

    return False


def _model_has_agency_id_column(model: type) -> bool:
    return "agency_id" in model.__mapper__.columns


def configure_tenant_session() -> None:
    """Install a global ORM execute hook that air-gaps SELECT queries by agency_id."""
    global TENANT_SCOPED_MODELS
    from app.models import (
        AgencyCustomTaskDefinition,
        AgencyEmailLog,
        AgencyGroup,
        AgencyInvitation,
        AgencyWorkflowTemplate,
        CallTranscript,
        ChatLog,
        ClientTermsAgreement,
        ClientTermsRequest,
        CreditCardAuthorization,
        InsuranceWaiverRequest,
        MarketingCampaign,
        Passenger,
        ProposedCruise,
        QuotedInsurance,
        RequestCommunication,
        RequestInsuranceTracking,
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
        CreditCardAuthorization,
        AgencyGroup,
        AgencyCustomTaskDefinition,
        ClientTermsAgreement,
        ClientTermsRequest,
        InsuranceWaiverRequest,
        RequestInsuranceTracking,
        AgencyInvitation,
    )

    @event.listens_for(Session, "do_orm_execute")
    def _apply_tenant_criteria(execute_state):
        if not execute_state.is_select:
            return

        targets_tenant_data = _statement_targets_tenant_scoped_models(execute_state)
        agency_id = get_current_agency_id()

        if is_tenant_scoping_required() and agency_id is None and targets_tenant_data:
            raise TenantContextRequiredError(
                "Tenant-scoped ORM access on a CRM route requires agency_id in context."
            )

        if agency_id is None:
            return

        if not targets_tenant_data:
            return

        for model in TENANT_SCOPED_MODELS:
            if not _model_has_agency_id_column(model):
                continue
            execute_state.statement = execute_state.statement.options(
                with_loader_criteria(
                    model,
                    lambda cls, _agency_id=agency_id: cls.agency_id == _agency_id,
                    include_aliases=True,
                )
            )


configure_tenant_session()
