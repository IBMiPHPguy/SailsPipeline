from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import DashboardResponse
from app.services.dashboard_service import get_dashboard

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardResponse:
    if current_user.agency_id is None:
        raise HTTPException(status_code=403, detail="Tenant membership required.")
    return get_dashboard(db, current_user.agency_id, current_user=current_user)
