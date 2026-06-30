import pytest


@pytest.mark.integration
def test_custom_task_definitions_crud_and_place(client, auth_headers, db):
    create_response = client.post(
        "/api/agency-custom-task-definitions",
        headers=auth_headers,
        json={
            "task_title": "Collect passport copies",
            "description": "Request passport scans from each traveler.",
        },
    )
    assert create_response.status_code == 201
    definition = create_response.json()
    assert definition["task_key"].startswith("custom_")

    list_response = client.get("/api/agency-custom-task-definitions", headers=auth_headers)
    assert list_response.status_code == 200
    assert any(item["id"] == definition["id"] for item in list_response.json())

    availability = client.get("/api/agency-task-catalog/availability", headers=auth_headers)
    assert availability.status_code == 200
    availability_payload = availability.json()
    assert definition["task_key"] in [item["task_key"] for item in availability_payload["available_custom_tasks"]]

    workflows = client.get("/api/agency-workflow-templates", headers=auth_headers)
    template_id = workflows.json()[0]["id"]

    place_response = client.post(
        f"/api/agency-workflow-templates/{template_id}/custom-tasks",
        headers=auth_headers,
        json={"task_key": definition["task_key"]},
    )
    assert place_response.status_code == 201
    placed_template = place_response.json()
    assert any(task["task_key"] == definition["task_key"] for task in placed_template["task_templates"])

    update_response = client.patch(
        f"/api/agency-custom-task-definitions/{definition['id']}",
        headers=auth_headers,
        json={"task_title": "Updated while placed"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["task_title"] == "Updated while placed"

    workflows_after_update = client.get("/api/agency-workflow-templates", headers=auth_headers)
    updated_template = next(
        workflow
        for workflow in workflows_after_update.json()
        if workflow["id"] == template_id
    )
    placed_task = next(
        task for task in updated_template["task_templates"] if task["task_key"] == definition["task_key"]
    )
    assert placed_task["task_title"] == "Updated while placed"

    delete_response = client.delete(
        f"/api/agency-custom-task-definitions/{definition['id']}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 204

    inventory = client.get("/api/agency-task-catalog/inventory", headers=auth_headers)
    assert inventory.status_code == 200
    assert definition["task_key"] not in [item["task_key"] for item in inventory.json()]

    workflows_after_delete = client.get("/api/agency-workflow-templates", headers=auth_headers)
    placed_template_after_delete = workflows_after_delete.json()[0]
    assert not any(task["task_key"] == definition["task_key"] for task in placed_template_after_delete["task_templates"])
