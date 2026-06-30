from app.services.agency_custom_task_service import create_agency_custom_task_definition
from app.services.agency_task_inventory_service import list_agency_task_inventory
from app.services.workflow_task_catalog_service import build_system_task_catalog
from app.tenant_constants import DEFAULT_AGENCY_ID


def test_list_agency_task_inventory_includes_builtin_and_library(db):
    definition = create_agency_custom_task_definition(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        task_title="Inventory library task",
    )
    inventory = list_agency_task_inventory(db, agency_id=DEFAULT_AGENCY_ID)

    assert len(inventory) == len(build_system_task_catalog()) + 1
    library_item = next(item for item in inventory if item["task_key"] == definition.task_key)
    assert library_item["task_type"] == "library"
    assert library_item["definition_id"] == definition.id
    assert library_item["workflow_name"] is None
    assert library_item["sequence_order"] is None
    assert library_item["task_template_id"] is None

    builtin_item = next(item for item in inventory if item["task_type"] == "builtin")
    assert builtin_item["definition_id"] is None
