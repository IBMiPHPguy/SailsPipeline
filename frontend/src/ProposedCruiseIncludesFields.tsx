import type { ProposedCruiseIncludes } from "./types";

type ProposedCruiseIncludesFieldsProps = {
  value: ProposedCruiseIncludes;
  onChange: (value: ProposedCruiseIncludes) => void;
  disabled: boolean;
};

export default function ProposedCruiseIncludesFields({
  value,
  onChange,
  disabled,
}: ProposedCruiseIncludesFieldsProps) {
  return (
    <fieldset className="proposed-cruise-includes">
      <legend className="field-label">Includes</legend>
      <div className="checkbox-group">
        <label className="checkbox-inline">
          <input
            type="checkbox"
            disabled={disabled}
            checked={value.drink_package.included}
            onChange={(event) =>
              onChange({
                ...value,
                drink_package: { ...value.drink_package, included: event.target.checked },
              })
            }
          />
          Drink package
        </label>
        {value.drink_package.included ? (
          <label>
            Drink package name
            <input
              disabled={disabled}
              value={value.drink_package.name ?? ""}
              onChange={(event) =>
                onChange({
                  ...value,
                  drink_package: { ...value.drink_package, name: event.target.value },
                })
              }
            />
          </label>
        ) : null}

        <label className="checkbox-inline">
          <input
            type="checkbox"
            disabled={disabled}
            checked={value.wifi.included}
            onChange={(event) =>
              onChange({
                ...value,
                wifi: { ...value.wifi, included: event.target.checked },
              })
            }
          />
          Wi-Fi
        </label>
        {value.wifi.included ? (
          <label>
            Wi-Fi package name
            <input
              disabled={disabled}
              value={value.wifi.name ?? ""}
              onChange={(event) =>
                onChange({
                  ...value,
                  wifi: { ...value.wifi, name: event.target.value },
                })
              }
            />
          </label>
        ) : null}

        <label className="checkbox-inline">
          <input
            type="checkbox"
            disabled={disabled}
            checked={value.tips}
            onChange={(event) => onChange({ ...value, tips: event.target.checked })}
          />
          Tips
        </label>

        <label className="checkbox-inline">
          <input
            type="checkbox"
            disabled={disabled}
            checked={value.excursion}
            onChange={(event) => onChange({ ...value, excursion: event.target.checked })}
          />
          Excursion
        </label>

        <label className="checkbox-inline">
          <input
            type="checkbox"
            disabled={disabled}
            checked={value.excursion_credit.included}
            onChange={(event) =>
              onChange({
                ...value,
                excursion_credit: {
                  ...value.excursion_credit,
                  included: event.target.checked,
                  amount: event.target.checked ? (value.excursion_credit.amount ?? 0) : null,
                },
              })
            }
          />
          Excursion credit
        </label>
        {value.excursion_credit.included ? (
          <label>
            Excursion credit amount
            <input
              disabled={disabled}
              type="number"
              min={0}
              step="0.01"
              value={value.excursion_credit.amount ?? ""}
              onChange={(event) =>
                onChange({
                  ...value,
                  excursion_credit: {
                    ...value.excursion_credit,
                    amount: event.target.value ? Number(event.target.value) : null,
                  },
                })
              }
            />
          </label>
        ) : null}

        <label className="checkbox-inline">
          <input
            type="checkbox"
            disabled={disabled}
            checked={value.onboard_credit.included}
            onChange={(event) =>
              onChange({
                ...value,
                onboard_credit: {
                  ...value.onboard_credit,
                  included: event.target.checked,
                  amount: event.target.checked ? (value.onboard_credit.amount ?? 0) : null,
                },
              })
            }
          />
          Cruise line OBC
        </label>
        {value.onboard_credit.included ? (
          <label>
            Cruise line OBC amount
            <input
              disabled={disabled}
              type="number"
              min={0}
              step="0.01"
              value={value.onboard_credit.amount ?? ""}
              onChange={(event) =>
                onChange({
                  ...value,
                  onboard_credit: {
                    ...value.onboard_credit,
                    amount: event.target.value ? Number(event.target.value) : null,
                  },
                })
              }
            />
          </label>
        ) : null}

        <label className="checkbox-inline">
          <input
            type="checkbox"
            disabled={disabled}
            checked={value.gift_obc.included}
            onChange={(event) =>
              onChange({
                ...value,
                gift_obc: {
                  ...value.gift_obc,
                  included: event.target.checked,
                  amount: event.target.checked ? (value.gift_obc.amount ?? 0) : null,
                },
              })
            }
          />
          Gift OBC
        </label>
        {value.gift_obc.included ? (
          <label>
            Gift OBC amount
            <input
              disabled={disabled}
              type="number"
              min={0}
              step="0.01"
              value={value.gift_obc.amount ?? ""}
              onChange={(event) =>
                onChange({
                  ...value,
                  gift_obc: {
                    ...value.gift_obc,
                    amount: event.target.value ? Number(event.target.value) : null,
                  },
                })
              }
            />
          </label>
        ) : null}
      </div>
    </fieldset>
  );
}
