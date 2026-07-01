import type { AgencyGroupInventoryMetrics, GroupLiquidationTone } from "./types";

export function metricsForInventoryId(
  metrics: { inventory_rows: AgencyGroupInventoryMetrics[] } | null | undefined,
  inventoryId: string,
): AgencyGroupInventoryMetrics | null {
  if (!metrics) {
    return null;
  }
  return metrics.inventory_rows.find((row) => row.inventory_id === inventoryId) ?? null;
}

export function liquidationToneLabel(tone: GroupLiquidationTone): string {
  if (tone === "sold_out") {
    return "Sold out";
  }
  if (tone === "nearing_sellout") {
    return "Nearing sellout";
  }
  return "Healthy";
}
