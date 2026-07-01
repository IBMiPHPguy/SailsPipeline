import { useState } from "react";
import { deleteAgencyGroupInventory, fetchAgencyGroup } from "./api";
import ChickenSwitchModal from "./ChickenSwitchModal";
import GroupDetailReadOnly, { formatInventoryDescription } from "./GroupDetailReadOnly";
import GroupInventoryEditModal from "./GroupInventoryEditModal";
import type { AgencyGroup, AgencyGroupInventory } from "./types";
import type { TopStatusBarVariant } from "./TopStatusBar";

type GroupInventoryLedgerProps = {
  group: AgencyGroup;
  readOnly?: boolean;
  onGroupUpdated: (group: AgencyGroup) => void;
  showStatus: (message: string, variant: TopStatusBarVariant) => void;
};

export default function GroupInventoryLedger({
  group,
  readOnly = false,
  onGroupUpdated,
  showStatus,
}: GroupInventoryLedgerProps) {
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editingInventory, setEditingInventory] = useState<AgencyGroupInventory | null>(null);
  const [deletingInventory, setDeletingInventory] = useState<AgencyGroupInventory | null>(null);
  const [deletingInventoryId, setDeletingInventoryId] = useState<string | null>(null);

  async function confirmDeleteInventory() {
    if (!deletingInventory) {
      return;
    }

    setDeletingInventoryId(deletingInventory.id);
    try {
      const updated = await deleteAgencyGroupInventory(deletingInventory.id);
      showStatus("Inventory row removed.", "delete");
      setDeletingInventory(null);
      onGroupUpdated(updated);
    } catch (deleteError) {
      showStatus(deleteError instanceof Error ? deleteError.message : "Unable to remove inventory row.", "error");
    } finally {
      setDeletingInventoryId(null);
    }
  }

  if (readOnly) {
    return <GroupDetailReadOnly group={group} />;
  }

  return (
    <>
      <header className="group-inventory-ledger-toolbar">
        <p className="meta group-inventory-panel-meta">
          {group.summary.inventory_row_count} inventory rows · {group.summary.total_cabins_remaining} cabins remaining
        </p>
        {group.is_active ? (
          <button type="button" className="agency-workflows-create-button" onClick={() => setCreateModalOpen(true)}>
            + Add inventory row
          </button>
        ) : null}
      </header>

      <GroupDetailReadOnly
        group={group}
        showActions={group.is_active}
        deletingInventoryId={deletingInventoryId}
        onEditInventory={(item) => setEditingInventory(item)}
        onDeleteInventory={(item) => setDeletingInventory(item)}
      />

      {!group.is_active ? <p className="meta group-inventory-archived-note">This group block is archived.</p> : null}

      <GroupInventoryEditModal
        open={createModalOpen}
        mode="create"
        groupId={group.id}
        inventory={null}
        onClose={() => setCreateModalOpen(false)}
        onSaved={async () => {
          showStatus("Inventory row added.", "success");
          onGroupUpdated(await fetchAgencyGroup(group.id));
        }}
      />

      <GroupInventoryEditModal
        open={editingInventory !== null}
        mode="edit"
        groupId={group.id}
        inventory={editingInventory}
        onClose={() => setEditingInventory(null)}
        onSaved={async () => {
          showStatus("Inventory row updated.", "success");
          onGroupUpdated(await fetchAgencyGroup(group.id));
        }}
      />

      <ChickenSwitchModal
        open={deletingInventory !== null}
        title="Remove inventory row?"
        description={`Remove ${deletingInventory ? formatInventoryDescription(deletingInventory) : "this inventory row"} from this group block?`}
        switchLabel="Yes, remove this inventory row"
        confirmLabel="Remove row"
        confirmingLabel="Removing..."
        hint="Rows with reserved cabins cannot be removed."
        confirming={deletingInventory !== null && deletingInventoryId === deletingInventory.id}
        onCancel={() => setDeletingInventory(null)}
        onConfirm={() => void confirmDeleteInventory()}
      />
    </>
  );
}
