from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

from app.tenant_context import get_current_agency_id

TENANT_SCOPED_MODELS: tuple[type, ...] = ()


def configure_tenant_session() -> None:
    global TENANT_SCOPED_MODELS
    from app.models import (
        AgencyEmailLog,
        AgencyTaskTemplate,
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
                    lambda cls: cls.agency_id == agency_id,
                    include_aliases=True,
                )
            )
