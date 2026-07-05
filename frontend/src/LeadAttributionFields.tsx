import { useEffect, useState } from "react";
import { fetchMarketingCampaigns } from "./api";
import IntakeModeFields from "./IntakeModeFields";
import {
  LEAD_SOURCE_MARKETING_CAMPAIGN,
  LEAD_SOURCE_REFERRAL,
  LEAD_SOURCES,
} from "./formOptions";
import type { MarketingCampaign, TravelRequestInput } from "./types";

type LeadAttributionFieldsProps = {
  form: TravelRequestInput;
  setForm: (form: TravelRequestInput) => void;
  disabled?: boolean;
};

export default function LeadAttributionFields({ form, setForm, disabled = false }: LeadAttributionFieldsProps) {
  const [campaigns, setCampaigns] = useState<MarketingCampaign[]>([]);
  const [campaignsLoading, setCampaignsLoading] = useState(false);
  const [campaignsError, setCampaignsError] = useState("");

  useEffect(() => {
    if (form.lead_source !== LEAD_SOURCE_MARKETING_CAMPAIGN) {
      return;
    }

    let cancelled = false;
    setCampaignsLoading(true);
    setCampaignsError("");
    void fetchMarketingCampaigns("all")
      .then((items) => {
        if (!cancelled) {
          setCampaigns(items);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setCampaignsError(error instanceof Error ? error.message : "Unable to load campaigns.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setCampaignsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [form.lead_source]);

  function updateLeadSource(nextSource: string) {
    setForm({
      ...form,
      lead_source: nextSource,
      referral_source_name: nextSource === LEAD_SOURCE_REFERRAL ? form.referral_source_name ?? "" : "",
      marketing_campaign_id:
        nextSource === LEAD_SOURCE_MARKETING_CAMPAIGN ? form.marketing_campaign_id ?? "" : "",
    });
  }

  return (
    <section className="request-form-band" aria-label="Lead source and intake">
      <div className="request-form-zone">
        <div className="request-form-zone-panel request-form-zone-panel-full">
          <div className="request-form-panel-body lead-attribution-fields">
            <label>
              Source
              <select
                disabled={disabled}
                value={form.lead_source ?? ""}
                onChange={(event) => updateLeadSource(event.target.value)}
              >
                <option value="">Select a source (optional)</option>
                {LEAD_SOURCES.map((source) => (
                  <option key={source} value={source}>
                    {source}
                  </option>
                ))}
              </select>
            </label>

            {form.lead_source === LEAD_SOURCE_REFERRAL ? (
              <label>
                Who referred this client?
                <input
                  type="text"
                  disabled={disabled}
                  value={form.referral_source_name ?? ""}
                  onChange={(event) =>
                    setForm({ ...form, referral_source_name: event.target.value })
                  }
                  placeholder="Referrer name or relationship"
                />
              </label>
            ) : null}

            {form.lead_source === LEAD_SOURCE_MARKETING_CAMPAIGN ? (
              <label>
                Marketing campaign
                {campaignsLoading ? <span className="field-hint">Loading campaigns...</span> : null}
                {campaignsError ? <span className="field-hint status error">{campaignsError}</span> : null}
                <select
                  disabled={disabled || campaignsLoading}
                  value={form.marketing_campaign_id ?? ""}
                  onChange={(event) =>
                    setForm({ ...form, marketing_campaign_id: event.target.value || undefined })
                  }
                >
                  <option value="">Select a campaign</option>
                  {campaigns.map((campaign) => (
                    <option key={campaign.id} value={campaign.id}>
                      {campaign.campaign_name} · {campaign.campaign_type}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}

            <IntakeModeFields form={form} setForm={setForm} disabled={disabled} />
          </div>
        </div>
      </div>
    </section>
  );
}
