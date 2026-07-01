import { formatMoney } from "./cabinPricing";
import EditIcon from "./EditIcon";
import IconTooltip from "./IconTooltip";
import TrashIcon from "./TrashIcon";
import type { AgencyGroup, AgencyGroupInventory } from "./types";
import { formatDate } from "./utils";

export function formatInventoryDescription(item: AgencyGroupInventory): string {
  const category = item.cabin_category.trim();
  const description = item.cabin_description?.trim() ?? "";

  if (description && category) {
    return `${description} (${category})`;
  }
  if (description) {
    return description;
  }
  return category || "—";
}

type GroupDetailReadOnlyProps = {
  group: AgencyGroup;
  showActions?: boolean;
  deletingInventoryId?: string | null;
  onEditInventory?: (item: AgencyGroupInventory) => void;
  onDeleteInventory?: (item: AgencyGroupInventory) => void;
};

export default function GroupDetailReadOnly({
  group,
  showActions = false,
  deletingInventoryId = null,
  onEditInventory,
  onDeleteInventory,
}: GroupDetailReadOnlyProps) {
  return (
    <section className="group-detail-readonly" aria-label="Group block details">
      <dl className="group-detail-readonly-grid">
        <div>
          <dt>Cruise line</dt>
          <dd>{group.cruise_line}</dd>
        </div>
        <div>
          <dt>Ship</dt>
          <dd>{group.ship_name}</dd>
        </div>
        <div>
          <dt>Sailing</dt>
          <dd>{formatDate(group.sailing_date)}</dd>
        </div>
        <div>
          <dt>Disembarkation</dt>
          <dd>{formatDate(group.disembarkation_date)}</dd>
        </div>
        <div>
          <dt>Group ID code</dt>
          <dd>{group.group_id_code || "—"}</dd>
        </div>
        <div>
          <dt>TC ratio</dt>
          <dd>{group.tc_ratio || "—"}</dd>
        </div>
      </dl>
      {group.group_amenities ? (
        <div className="group-detail-readonly-amenities">
          <h4>Group amenities</h4>
          <p>{group.group_amenities}</p>
        </div>
      ) : null}
      <div className="group-detail-readonly-summary">
        <span>
          <strong>{group.summary.total_cabins_allocated}</strong> allocated
        </span>
        <span>
          <strong>{group.summary.total_cabins_reserved}</strong> reserved
        </span>
        <span>
          <strong>{group.summary.total_cabins_remaining}</strong> remaining
        </span>
      </div>
      <div className="open-requests-table-wrap group-inventory-table-wrap">
        <table
          className={`open-requests-table group-inventory-table${showActions ? " group-inventory-table--actions" : ""}`}
        >
          <colgroup>
            <col className="group-inventory-col group-inventory-col--description" />
            <col className="group-inventory-col group-inventory-col--type" />
            <col className="group-inventory-col group-inventory-col--price" />
            <col className="group-inventory-col group-inventory-col--alloc" />
            <col className="group-inventory-col group-inventory-col--reserved" />
            <col className="group-inventory-col group-inventory-col--remaining" />
            {showActions ? <col className="group-inventory-col group-inventory-col--actions" /> : null}
          </colgroup>
          <thead>
            <tr>
              <th>Description</th>
              <th>Type</th>
              <th className="group-inventory-table-price-heading">Price</th>
              <th className="group-inventory-table-numeric group-inventory-col--alloc">Allocated</th>
              <th className="group-inventory-table-numeric group-inventory-col--reserved">Reserved</th>
              <th className="group-inventory-table-numeric group-inventory-col--remaining">Remaining</th>
              {showActions ? <th className="group-inventory-table-actions-heading">Actions</th> : null}
            </tr>
          </thead>
          <tbody>
            {group.inventory_items.length === 0 ? (
              <tr>
                <td colSpan={showActions ? 7 : 6} className="meta">
                  No inventory rows yet.
                </td>
              </tr>
            ) : (
              group.inventory_items.map((item) => (
                <tr key={item.id}>
                  <td className="group-inventory-table-description">{formatInventoryDescription(item)}</td>
                  <td>{item.cabin_type}</td>
                  <td className="group-inventory-table-numeric">{formatMoney(item.price_per_cabin)}</td>
                  <td className="group-inventory-table-numeric group-inventory-col--alloc">{item.cabins_allocated}</td>
                  <td className="group-inventory-table-numeric group-inventory-col--reserved">{item.cabins_reserved}</td>
                  <td className="group-inventory-table-numeric group-inventory-col--remaining">{item.cabins_remaining}</td>
                  {showActions ? (
                    <td className="dashboard-table-actions-cell">
                      <div className="dashboard-table-actions">
                        <IconTooltip label="Edit inventory row">
                          <button
                            type="button"
                            className="icon-button"
                            aria-label="Edit inventory row"
                            onClick={() => onEditInventory?.(item)}
                          >
                            <EditIcon />
                          </button>
                        </IconTooltip>
                        <IconTooltip label="Remove inventory row">
                          <button
                            type="button"
                            className="icon-button icon-button-danger"
                            aria-label="Remove inventory row"
                            disabled={deletingInventoryId === item.id}
                            onClick={() => onDeleteInventory?.(item)}
                          >
                            <TrashIcon />
                          </button>
                        </IconTooltip>
                      </div>
                    </td>
                  ) : null}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
