from app.task_behavior import get_task_behavior, task_behavior_to_catalog_fields


def test_send_research_communication_schedules_follow_up_metadata():
    behavior = get_task_behavior("send_research_communication")
    assert behavior is not None
    assert behavior.on_complete_schedule_follow_up_task_key == "follow_up_research"
    assert behavior.follow_up_due_days == 3


def test_follow_up_research_allows_reached_out():
    behavior = get_task_behavior("follow_up_research")
    assert behavior is not None
    assert behavior.allows_reached_out is True


def test_task_behavior_to_catalog_fields():
    fields = task_behavior_to_catalog_fields("send_research_communication")
    assert fields == {
        "on_complete_schedule_follow_up_task_key": "follow_up_research",
        "follow_up_due_days": 3,
    }
