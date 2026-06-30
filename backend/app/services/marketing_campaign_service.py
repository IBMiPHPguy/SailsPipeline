from __future__ import annotations

import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.constants import MARKETING_CAMPAIGN_TYPES
from app.models import MarketingCampaign, TravelRequest
from app.services.agency_rollup_service import get_or_refresh_dashboard_rollup, refresh_agency_dashboard_rollups
from app.services.agency_service import get_marketing_campaign_for_agency

def list_marketing_campaigns(
    db: Session,
    *,
    agency_id: str,
    timeframe: str = "all",
) -> list[MarketingCampaign]:
    query = (
        db.query(MarketingCampaign)
        .filter(MarketingCampaign.agency_id == agency_id)
        .order_by(MarketingCampaign.start_date.desc(), MarketingCampaign.campaign_name.asc())
    )
    today = date.today()
    if timeframe == "active":
        query = query.filter(
            MarketingCampaign.start_date <= today,
            (MarketingCampaign.end_date.is_(None) | (MarketingCampaign.end_date >= today)),
        )
    elif timeframe == "past":
        query = query.filter(
            MarketingCampaign.end_date.isnot(None),
            MarketingCampaign.end_date < today,
        )
    return query.all()


def _refresh_marketing_dashboard_rollups(db: Session, agency_id: str) -> None:
    refresh_agency_dashboard_rollups(db, agency_id)


def create_marketing_campaign(
    db: Session,
    *,
    agency_id: str,
    campaign_name: str,
    campaign_type: str,
    monthly_spend: float,
    start_date: date,
    end_date: date | None,
) -> MarketingCampaign:
    if campaign_type not in MARKETING_CAMPAIGN_TYPES:
        raise HTTPException(status_code=400, detail="Invalid campaign type selected.")
    if end_date is not None and end_date < start_date:
        raise HTTPException(status_code=400, detail="End date must be on or after the start date.")

    campaign = MarketingCampaign(
        id=str(uuid.uuid4()),
        agency_id=agency_id,
        campaign_name=campaign_name.strip(),
        campaign_type=campaign_type,
        monthly_spend=monthly_spend,
        start_date=start_date,
        end_date=end_date,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    _refresh_marketing_dashboard_rollups(db, agency_id)
    return campaign


def update_marketing_campaign(
    db: Session,
    *,
    agency_id: str,
    campaign_id: str,
    updates: dict,
) -> MarketingCampaign:
    campaign = get_marketing_campaign_for_agency(db, campaign_id, agency_id)

    if "campaign_type" in updates and updates["campaign_type"] not in MARKETING_CAMPAIGN_TYPES:
        raise HTTPException(status_code=400, detail="Invalid campaign type selected.")

    start_date = updates.get("start_date", campaign.start_date)
    end_date = updates.get("end_date", campaign.end_date)
    if end_date is not None and end_date < start_date:
        raise HTTPException(status_code=400, detail="End date must be on or after the start date.")

    for field, value in updates.items():
        if field == "campaign_name" and isinstance(value, str):
            value = value.strip()
        setattr(campaign, field, value)

    db.commit()
    db.refresh(campaign)
    _refresh_marketing_dashboard_rollups(db, agency_id)
    return campaign


def delete_marketing_campaign(db: Session, *, agency_id: str, campaign_id: str) -> None:
    campaign = get_marketing_campaign_for_agency(db, campaign_id, agency_id)
    (
        db.query(TravelRequest)
        .filter(
            TravelRequest.agency_id == agency_id,
            TravelRequest.marketing_campaign_id == campaign_id,
        )
        .update(
            {
                TravelRequest.lead_source: None,
                TravelRequest.marketing_campaign_id: None,
            },
            synchronize_session=False,
        )
    )
    db.delete(campaign)
    db.commit()
    _refresh_marketing_dashboard_rollups(db, agency_id)


def get_marketing_campaign_summary(db: Session, agency_id: str) -> dict[str, float | str | None]:
    rollup = get_or_refresh_dashboard_rollup(db, agency_id)
    return {
        "active_monthly_budget": float(rollup.marketing_active_monthly_budget or 0),
        "top_roi_campaign_name": rollup.marketing_top_roi_campaign_name,
        "top_roi_percent": float(rollup.marketing_top_roi_percent)
        if rollup.marketing_top_roi_percent is not None
        else None,
        "total_attributed_volume": float(rollup.marketing_total_attributed_volume or 0),
    }
