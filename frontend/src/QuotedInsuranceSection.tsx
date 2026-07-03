import { forwardRef, useImperativeHandle, useState } from "react";

import { addQuotedInsurance, updateQuotedInsurance } from "./api";

import QuotedInsuranceModal from "./QuotedInsuranceModal";
import { QuoteMailedBadge } from "./QuoteMailedToggle";

import { formatMoney, quotedInsuranceStatusClass } from "./quotedInsuranceForm";

import type { QuotedInsurance, QuotedInsuranceInput } from "./types";

import { formatDate } from "./utils";

import "./insurance-portal.css";



type QuotedInsuranceSectionProps = {

  requestId: number;

  quotes: QuotedInsurance[];

  disabled: boolean;

  onChanged: () => Promise<void>;

  onError: (message: string) => void;

  embedded?: boolean;
};

export type QuotedInsuranceSectionHandle = {
  openCreateModal: () => void;
};



function EditIcon() {

  return (

    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2">

      <path d="M12 20h9" />

      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />

    </svg>

  );

}



function declinedOnDate(quote: QuotedInsurance): string | null {

  if (quote.status !== "Declined") {

    return null;

  }

  return quote.declined_at ?? quote.updated_at;

}



export default forwardRef<QuotedInsuranceSectionHandle, QuotedInsuranceSectionProps>(
  function QuotedInsuranceSection(
  {
  requestId,
  quotes,
  disabled,
  onChanged,
  onError,
  embedded = false,
}: QuotedInsuranceSectionProps,
  ref,
) {

  const [modalOpen, setModalOpen] = useState(false);

  const [editingQuote, setEditingQuote] = useState<QuotedInsurance | null>(null);

  const [saving, setSaving] = useState(false);

  function openCreateModal() {
    setEditingQuote(null);
    setModalOpen(true);
  }

  useImperativeHandle(ref, () => ({ openCreateModal }), []);



  function openEditModal(quote: QuotedInsurance) {

    setEditingQuote(quote);

    setModalOpen(true);

  }



  async function handleSave(payload: QuotedInsuranceInput) {

    setSaving(true);

    onError("");

    try {

      if (editingQuote) {

        await updateQuotedInsurance(requestId, editingQuote.id, payload);

      } else {

        await addQuotedInsurance(requestId, payload);

      }

      setModalOpen(false);

      setEditingQuote(null);

      await onChanged();

    } catch (saveError) {

      onError(saveError instanceof Error ? saveError.message : "Unable to save insurance quote.");

    } finally {

      setSaving(false);

    }

  }



  const body = (
    <>
      <div className="quoted-insurance-list">
        {quotes.length === 0 ? (
          <p className="meta">No insurance quotes yet.</p>
        ) : (
          quotes.map((quote) => {
            const declinedDate = declinedOnDate(quote);

            return (
              <article className="quoted-insurance-item" key={quote.id}>
                <div className="quoted-insurance-item-header">
                  <div>
                    <strong>
                      {quote.carrier} · {quote.plan_name}
                    </strong>
                    <div className="meta">Premium {formatMoney(quote.premium_cost)}</div>
                    <div className="meta">
                      Cancellation {formatMoney(quote.cancellation_coverage)} · Medical{" "}
                      {formatMoney(quote.medical_coverage)} · Evac {formatMoney(quote.medical_evac_coverage)}
                    </div>
                    {declinedDate ? <div className="meta">Declined {formatDate(declinedDate)}</div> : null}
                  </div>
                  <div className="quoted-insurance-item-actions">
                    <span className={`quote-status ${quotedInsuranceStatusClass(quote.status)}`}>{quote.status}</span>
                    {quote.quote_mailed ? <QuoteMailedBadge /> : null}
                    {!disabled ? (
                      <button
                        type="button"
                        className="icon-button"
                        aria-label={`Edit ${quote.carrier} ${quote.plan_name}`}
                        onClick={() => openEditModal(quote)}
                      >
                        <EditIcon />
                      </button>
                    ) : null}
                  </div>
                </div>
              </article>
            );
          })
        )}
      </div>
    </>
  );

  return (
    <>
      {embedded ? (
        body
      ) : (
        <section className="section-card quoted-insurance-card">
          <header className="section-card-header">
            <h3>Quoted Insurance</h3>
          </header>
          <div className="section-card-body">{body}</div>
        </section>
      )}

      <QuotedInsuranceModal

        open={modalOpen}

        quote={editingQuote}

        saving={saving}

        disabled={disabled}

        onCancel={() => {

          setModalOpen(false);

          setEditingQuote(null);

        }}

        onSave={handleSave}

      />

    </>

  );
},
);


