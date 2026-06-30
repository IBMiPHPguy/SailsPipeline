import type { AgencyTaskInventoryItem, AgencyWorkflowTemplate } from "./types";
import { getWorkflowPillClass } from "./workflowPill";

export type WorkflowFilterValue = "all" | "available" | string;

export type TaskInventorySection = {
  key: string;
  label: string;
  kind: "available" | "workflow";
  pillClass: string;
  tasks: AgencyTaskInventoryItem[];
};

export function matchesWorkflowFilter(item: AgencyTaskInventoryItem, filter: WorkflowFilterValue): boolean {
  if (filter === "all") {
    return true;
  }
  if (filter === "available") {
    return !item.workflow_template_id;
  }
  return item.workflow_template_id === filter;
}

export function sortSectionTasks(
  tasks: AgencyTaskInventoryItem[],
  kind: TaskInventorySection["kind"],
): AgencyTaskInventoryItem[] {
  return [...tasks].sort((left, right) => {
    if (kind === "workflow") {
      const leftSequence = left.sequence_order ?? Number.MAX_SAFE_INTEGER;
      const rightSequence = right.sequence_order ?? Number.MAX_SAFE_INTEGER;
      if (leftSequence !== rightSequence) {
        return leftSequence - rightSequence;
      }
    }
    return left.task_title.localeCompare(right.task_title, undefined, { sensitivity: "base" });
  });
}

export function buildTaskInventorySections(
  inventory: AgencyTaskInventoryItem[],
  filter: WorkflowFilterValue,
  workflows: AgencyWorkflowTemplate[],
): TaskInventorySection[] {
  const filtered = inventory.filter((item) => matchesWorkflowFilter(item, filter));

  if (filter === "available") {
    const tasks = sortSectionTasks(
      filtered.filter((item) => !item.workflow_template_id),
      "available",
    );
    return [{ key: "available", label: "Available", kind: "available", pillClass: "tasks-inventory-section-available", tasks }];
  }

  if (filter !== "all") {
    const workflow = workflows.find((template) => template.id === filter);
    const tasks = sortSectionTasks(
      filtered.filter((item) => item.workflow_template_id === filter),
      "workflow",
    );
    return [
      {
        key: filter,
        label: workflow?.workflow_name ?? tasks[0]?.workflow_name ?? "Workflow",
        kind: "workflow",
        pillClass: getWorkflowPillClass(filter),
        tasks,
      },
    ];
  }

  const sections: TaskInventorySection[] = [];
  const availableTasks = sortSectionTasks(
    filtered.filter((item) => !item.workflow_template_id),
    "available",
  );
  if (availableTasks.length > 0) {
    sections.push({
      key: "available",
      label: "Available",
      kind: "available",
      pillClass: "tasks-inventory-section-available",
      tasks: availableTasks,
    });
  }

  const tasksByWorkflowId = new Map<string, AgencyTaskInventoryItem[]>();
  for (const item of filtered) {
    if (!item.workflow_template_id) {
      continue;
    }
    const existing = tasksByWorkflowId.get(item.workflow_template_id) ?? [];
    existing.push(item);
    tasksByWorkflowId.set(item.workflow_template_id, existing);
  }

  const workflowIds = [...tasksByWorkflowId.keys()].sort((leftId, rightId) => {
    const leftName = tasksByWorkflowId.get(leftId)?.[0]?.workflow_name ?? "";
    const rightName = tasksByWorkflowId.get(rightId)?.[0]?.workflow_name ?? "";
    return leftName.localeCompare(rightName, undefined, { sensitivity: "base" });
  });

  for (const workflowId of workflowIds) {
    const tasks = sortSectionTasks(tasksByWorkflowId.get(workflowId) ?? [], "workflow");
    sections.push({
      key: workflowId,
      label: tasks[0]?.workflow_name ?? "Workflow",
      kind: "workflow",
      pillClass: getWorkflowPillClass(workflowId),
      tasks,
    });
  }

  return sections;
}
