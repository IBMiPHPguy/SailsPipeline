import {
  normalizeCabinPricing,
  sumCabinPricing,
  type CabinPricing,
} from "./cabinPricing";

type CabinPricingFieldsProps = {
  cabinsNeeded: number;
  value: CabinPricing;
  onChange: (value: CabinPricing) => void;
  disabled: boolean;
  readOnly?: boolean;
};

export default function CabinPricingFields({
  cabinsNeeded,
  value,
  onChange,
  disabled,
  readOnly = false,
}: CabinPricingFieldsProps) {
  const pricing = normalizeCabinPricing(value, cabinsNeeded);
  const fieldsDisabled = disabled || readOnly;
  const totals = sumCabinPricing(pricing);

  function updateEntry(cabinIndex: number, field: "deposit_amount" | "cost", nextValue: string) {
    const nextPricing = pricing.map((entry, index) =>
      index === cabinIndex
        ? {
            ...entry,
            [field]: nextValue === "" ? 0 : Number(nextValue),
          }
        : entry,
    );
    onChange(nextPricing);
  }

  return (
    <div className="cabin-pricing-fields">
      <p className="field-hint">
        Enter deposit and total cost for each cabin required on this request. Due dates on the cruise apply to all
        cabins.
      </p>

      <div className="cabin-pricing-list">
        {pricing.map((entry, cabinIndex) => (
          <article className="cabin-pricing-item" key={`cabin-pricing-${cabinIndex + 1}`}>
            <h4>{cabinsNeeded === 1 ? "Cabin pricing" : `Cabin ${cabinIndex + 1} pricing`}</h4>
            <div className="field-row">
              <label>
                Deposit amount
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  disabled={fieldsDisabled}
                  value={entry.deposit_amount}
                  onChange={(event) => updateEntry(cabinIndex, "deposit_amount", event.target.value)}
                />
              </label>
              <label>
                Total cost
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  disabled={fieldsDisabled}
                  value={entry.cost}
                  onChange={(event) => updateEntry(cabinIndex, "cost", event.target.value)}
                />
              </label>
            </div>
          </article>
        ))}
      </div>

      <p className="meta cabin-pricing-totals">
        Combined deposit: ${totals.deposit_amount.toFixed(2)} · Combined total cost: ${totals.cost.toFixed(2)}
      </p>
    </div>
  );
}
