import {
  INTAKE_MODE_SOCIAL_MEDIA,
  INTAKE_MODES,
  SOCIAL_MEDIA_PLATFORMS,
} from "./formOptions";
import type { TravelRequestInput } from "./types";

type IntakeModeFieldsProps = {
  form: TravelRequestInput;
  setForm: (form: TravelRequestInput) => void;
  disabled?: boolean;
};

export default function IntakeModeFields({ form, setForm, disabled = false }: IntakeModeFieldsProps) {
  function updateIntakeMode(nextMode: string) {
    setForm({
      ...form,
      intake_mode: nextMode,
      intake_social_platform:
        nextMode === INTAKE_MODE_SOCIAL_MEDIA ? form.intake_social_platform ?? "" : "",
    });
  }

  return (
    <>
      <label>
        Mode of intake
        <select
          disabled={disabled}
          value={form.intake_mode ?? ""}
          onChange={(event) => updateIntakeMode(event.target.value)}
        >
          <option value="">Select how the request came in (optional)</option>
          {INTAKE_MODES.map((mode) => (
            <option key={mode} value={mode}>
              {mode}
            </option>
          ))}
        </select>
      </label>

      {form.intake_mode === INTAKE_MODE_SOCIAL_MEDIA ? (
        <label>
          Social media platform
          <select
            disabled={disabled}
            value={form.intake_social_platform ?? ""}
            onChange={(event) =>
              setForm({ ...form, intake_social_platform: event.target.value })
            }
          >
            <option value="">Select a platform</option>
            {SOCIAL_MEDIA_PLATFORMS.map((platform) => (
              <option key={platform} value={platform}>
                {platform}
              </option>
            ))}
          </select>
        </label>
      ) : null}
    </>
  );
}
