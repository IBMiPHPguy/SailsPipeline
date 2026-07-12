from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import (
    MarketingCampaignCreate,
    MarketingCampaignRead,
    MarketingCampaignSummaryRead,
    MarketingCampaignUpdate,
)
from app.services.agency_service import get_marketing_campaign_for_agency
from app.services.agent_capability_service import (
    assert_can_manage_marketing_campaigns,
    get_capabilities_for_user,
)
from app.services.marketing_campaign_service import (
    create_marketing_campaign,
    delete_marketing_campaign,
    get_marketing_campaign_summary,
    list_marketing_campaigns,
    update_marketing_campaign,
)

router = APIRouter(prefix="/api/marketing-campaigns", tags=["marketing-campaigns"])


@router.get("", response_model=list[MarketingCampaignRead])
def list_marketing_campaigns_route(
    timeframe: str = "all",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MarketingCampaignRead]:
    if current_user.agency_id is None:
        raise HTTPException(status_code=403, detail="Tenant membership required.")
    if timeframe not in {"all", "active", "past"}:
        raise HTTPException(status_code=400, detail="Invalid timeframe filter.")
    campaigns = list_marketing_campaigns(db, agency_id=current_user.agency_id, timeframe=timeframe)
    return [MarketingCampaignRead.model_validate(campaign) for campaign in campaigns]


@router.get("/summary", response_model=MarketingCampaignSummaryRead)
def get_marketing_campaign_summary_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarketingCampaignSummaryRead:
    if current_user.agency_id is None:
        raise HTTPException(status_code=403, detail="Tenant membership required.")
    caps = get_capabilities_for_user(db, current_user)
    assert_can_manage_marketing_campaigns(caps)
    summary = get_marketing_campaign_summary(db, current_user.agency_id)
    return MarketingCampaignSummaryRead.model_validate(summary)


@router.post("", response_model=MarketingCampaignRead, status_code=201)
def create_marketing_campaign_route(
    payload: MarketingCampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarketingCampaignRead:
    if current_user.agency_id is None:
        raise HTTPException(status_code=403, detail="Tenant membership required.")
    caps = get_capabilities_for_user(db, current_user)
    assert_can_manage_marketing_campaigns(caps)
    campaign = create_marketing_campaign(
        db,
        agency_id=current_user.agency_id,
        campaign_name=payload.campaign_name,
        campaign_type=payload.campaign_type,
        monthly_spend=payload.monthly_spend,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    return MarketingCampaignRead.model_validate(campaign)


@router.get("/{campaign_id}", response_model=MarketingCampaignRead)
def get_marketing_campaign_route(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarketingCampaignRead:
    if current_user.agency_id is None:
        raise HTTPException(status_code=403, detail="Tenant membership required.")
    campaign = get_marketing_campaign_for_agency(db, campaign_id, current_user.agency_id)
    return MarketingCampaignRead.model_validate(campaign)


@router.patch("/{campaign_id}", response_model=MarketingCampaignRead)
def update_marketing_campaign_route(
    campaign_id: str,
    payload: MarketingCampaignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarketingCampaignRead:
    if current_user.agency_id is None:
        raise HTTPException(status_code=403, detail="Tenant membership required.")
    caps = get_capabilities_for_user(db, current_user)
    assert_can_manage_marketing_campaigns(caps)
    updates = payload.model_dump(exclude_unset=True)
    campaign = update_marketing_campaign(
        db,
        agency_id=current_user.agency_id,
        campaign_id=campaign_id,
        updates=updates,
    )
    return MarketingCampaignRead.model_validate(campaign)


@router.delete("/{campaign_id}", status_code=204)
def delete_marketing_campaign_route(
    campaign_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    if current_user.agency_id is None:
        raise HTTPException(status_code=403, detail="Tenant membership required.")
    caps = get_capabilities_for_user(db, current_user)
    assert_can_manage_marketing_campaigns(caps)
    delete_marketing_campaign(db, agency_id=current_user.agency_id, campaign_id=campaign_id)
