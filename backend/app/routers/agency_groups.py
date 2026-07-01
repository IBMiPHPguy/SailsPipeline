from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_tenant_super_user
from app.models import User
from app.schemas import (
    AgencyGroupCreate,
    AgencyGroupInventoryCreate,
    AgencyGroupInventoryUpdate,
    AgencyGroupListItemRead,
    AgencyGroupListPageRead,
    AgencyGroupRead,
    AgencyGroupUpdate,
)
from app.services.agency_group_service import (
    AGENCY_GROUPS_PAGE_SIZE_DEFAULT,
    AGENCY_GROUPS_PAGE_SIZE_MAX,
    agency_groups_total_pages,
    archive_agency_group,
    create_agency_group,
    create_agency_group_inventory,
    delete_agency_group_inventory,
    get_agency_group_detail,
    group_to_list_item_payload,
    group_to_read_payload,
    list_agency_groups_page,
    update_agency_group,
    update_agency_group_inventory,
)

router = APIRouter(prefix="/api/agency-groups", tags=["agency-groups"])


def _require_agency_id(current_user: User) -> str:
    if current_user.agency_id is None:
        raise HTTPException(status_code=403, detail="Tenant membership required.")
    return current_user.agency_id


def _parse_is_active_filter(value: str) -> bool | None:
    if value == "all":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    raise HTTPException(status_code=400, detail="Invalid is_active filter. Use true, false, or all.")


@router.get("", response_model=AgencyGroupListPageRead)
def list_agency_groups_route(
    is_active: str = Query(default="all"),
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=AGENCY_GROUPS_PAGE_SIZE_DEFAULT, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyGroupListPageRead:
    agency_id = _require_agency_id(current_user)
    normalized_page_size = max(1, min(page_size, AGENCY_GROUPS_PAGE_SIZE_MAX))
    groups, total = list_agency_groups_page(
        db,
        agency_id=agency_id,
        is_active=_parse_is_active_filter(is_active),
        query=q,
        page=page,
        page_size=normalized_page_size,
    )
    return AgencyGroupListPageRead(
        items=[AgencyGroupListItemRead.model_validate(group_to_list_item_payload(group)) for group in groups],
        total=total,
        page=page,
        page_size=normalized_page_size,
        total_pages=agency_groups_total_pages(total, normalized_page_size),
    )


@router.post("", response_model=AgencyGroupRead, status_code=201)
def create_agency_group_route(
    payload: AgencyGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyGroupRead:
    agency_id = _require_agency_id(current_user)
    inventory_items = [item.model_dump() for item in payload.inventory_items]
    group = create_agency_group(
        db,
        agency_id=agency_id,
        group_name=payload.group_name,
        cruise_line=payload.cruise_line,
        ship_name=payload.ship_name,
        sailing_date=payload.sailing_date,
        disembarkation_date=payload.disembarkation_date,
        group_id_code=payload.group_id_code,
        group_amenities=payload.group_amenities,
        tc_ratio=payload.tc_ratio,
        is_active=payload.is_active,
        inventory_items=inventory_items,
    )
    return AgencyGroupRead.model_validate(group_to_read_payload(group))


@router.get("/{group_id}", response_model=AgencyGroupRead)
def get_agency_group_route(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgencyGroupRead:
    agency_id = _require_agency_id(current_user)
    group = get_agency_group_detail(db, agency_id=agency_id, group_id=group_id)
    return AgencyGroupRead.model_validate(group_to_read_payload(group))


@router.patch("/{group_id}", response_model=AgencyGroupRead)
def update_agency_group_route(
    group_id: str,
    payload: AgencyGroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyGroupRead:
    agency_id = _require_agency_id(current_user)
    updates = payload.model_dump(exclude_unset=True)
    group = update_agency_group(db, agency_id=agency_id, group_id=group_id, updates=updates)
    return AgencyGroupRead.model_validate(group_to_read_payload(group))


@router.post("/{group_id}/archive", response_model=AgencyGroupRead)
def archive_agency_group_route(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyGroupRead:
    agency_id = _require_agency_id(current_user)
    group = archive_agency_group(db, agency_id=agency_id, group_id=group_id)
    return AgencyGroupRead.model_validate(group_to_read_payload(group))


@router.post("/{group_id}/inventory", response_model=AgencyGroupRead, status_code=201)
def create_agency_group_inventory_route(
    group_id: str,
    payload: AgencyGroupInventoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyGroupRead:
    agency_id = _require_agency_id(current_user)
    group = create_agency_group_inventory(
        db,
        agency_id=agency_id,
        group_id=group_id,
        cabin_category=payload.cabin_category,
        cabin_type=payload.cabin_type,
        cabin_description=payload.cabin_description,
        price_per_cabin=payload.price_per_cabin,
        cabins_allocated=payload.cabins_allocated,
        cabins_reserved=payload.cabins_reserved,
    )
    return AgencyGroupRead.model_validate(group_to_read_payload(group))


@router.patch("/inventory/{inventory_id}", response_model=AgencyGroupRead)
def update_agency_group_inventory_route(
    inventory_id: str,
    payload: AgencyGroupInventoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyGroupRead:
    agency_id = _require_agency_id(current_user)
    updates = payload.model_dump(exclude_unset=True)
    group = update_agency_group_inventory(
        db,
        agency_id=agency_id,
        inventory_id=inventory_id,
        updates=updates,
    )
    return AgencyGroupRead.model_validate(group_to_read_payload(group))


@router.delete("/inventory/{inventory_id}", response_model=AgencyGroupRead)
def delete_agency_group_inventory_route(
    inventory_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyGroupRead:
    agency_id = _require_agency_id(current_user)
    group = delete_agency_group_inventory(db, agency_id=agency_id, inventory_id=inventory_id)
    return AgencyGroupRead.model_validate(group_to_read_payload(group))
