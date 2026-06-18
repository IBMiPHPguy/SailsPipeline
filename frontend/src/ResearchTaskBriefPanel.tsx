import { formatCruiseLines } from "./CruiseLineMultiSelect";
import { useEffect, useState } from "react";
import { fetchRequestNotes } from "./api";
import type { RequestNote, TravelRequestDetail, TravelRequestInput } from "./types";
import { formatDate, formatDestinationSummary } from "./utils";
import { downloadResearchBrief } from "./researchBrief";
import { isInactiveClient } from "./passengerDisplay";

type ResearchTaskBriefPanelProps = {
  request: TravelRequestDetail;
  form: TravelRequestInput;
};

export default function ResearchTaskBriefPanel({ request, form }: ResearchTaskBriefPanelProps) {
  const [notesWithContent, setNotesWithContent] = useState<RequestNote[]>([]);

  useEffect(() => {
    let cancelled = false;

    fetchRequestNotes(request.id)
      .then((notes) => {
        if (!cancelled) {
          setNotesWithContent(notes);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setNotesWithContent([]);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [request.id]);

  const summaryRequest = {
    ...request,
    first_name: form.first_name,
    last_name: form.last_name,
    cruise_lines: form.cruise_lines,
    excluded_cruise_lines: form.excluded_cruise_lines ?? [],
    destination: form.destination,
    destination_details: ["Caribbean", "Alaska", "Asia", "Europe"].includes(form.destination)
      ? form.destination_details ?? null
      : null,
    departure_date: form.departure_date,
    return_date: form.return_date,
    cabin_types: form.cabin_types,
    passengers: form.passengers,
    cabins_needed: form.cabins_needed,
  };

  return (
    <div className="research-task-brief">
      <p className="research-task-brief-intro meta">
        Use the request details below while researching cruise options. Download the brief to work offline
        or share with AI tools.
      </p>

      <dl className="research-task-brief-grid">
        <div>
          <dt>Client</dt>
          <dd>
            {form.first_name} {form.last_name}
          </dd>
        </div>
        <div>
          <dt>Contact</dt>
          <dd>
            {form.email}
            <br />
            {form.phone}
          </dd>
        </div>
        <div>
          <dt>Preferred cruise lines</dt>
          <dd>{formatCruiseLines(form.cruise_lines)}</dd>
        </div>
        {form.excluded_cruise_lines?.length ? (
          <div>
            <dt>Cruise lines to avoid</dt>
            <dd>{formatCruiseLines(form.excluded_cruise_lines)}</dd>
          </div>
        ) : null}
        <div>
          <dt>Destination</dt>
          <dd>{formatDestinationSummary(summaryRequest)}</dd>
        </div>
        <div>
          <dt>Travel dates</dt>
          <dd>
            {formatDate(form.departure_date)} to {formatDate(form.return_date)}
          </dd>
        </div>
        <div>
          <dt>Cabin types</dt>
          <dd>{form.cabin_types.length > 0 ? form.cabin_types.join(", ") : "—"}</dd>
        </div>
        <div>
          <dt>Passengers / cabins</dt>
          <dd>
            {form.passengers} passenger{form.passengers === 1 ? "" : "s"}, {form.cabins_needed} cabin
            {form.cabins_needed === 1 ? "" : "s"}
          </dd>
        </div>
      </dl>

      {request.request_passengers.length > 0 ? (
        <div className="research-task-brief-block">
          <h5>Passengers</h5>
          <ul className="research-task-brief-list">
            {request.request_passengers.map((passenger) => (
              <li key={passenger.id}>
                {passenger.first_name} {passenger.last_name}
                {isInactiveClient(passenger) ? " · Inactive client" : ""}
                {passenger.date_of_birth ? ` · DOB ${formatDate(passenger.date_of_birth)}` : ""}
                {passenger.qualifiers?.length
                  ? ` · Discounts: ${passenger.qualifiers.join(", ")}`
                  : ""}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {notesWithContent.length > 0 ? (
        <div className="research-task-brief-block">
          <h5>Notes</h5>
          <ul className="research-task-brief-list">
            {notesWithContent.map((note) => (
              <li key={note.id}>
                {note.summary ? <strong>{note.summary}: </strong> : null}
                {note.content}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {(request.call_transcripts.length > 0 || request.chat_logs.length > 0) && (
        <div className="research-task-brief-block">
          <h5>Related files</h5>
          <ul className="research-task-brief-list">
            {request.call_transcripts.map((item) => (
              <li key={`transcript-${item.id}`}>Call transcript: {item.original_filename}</li>
            ))}
            {request.chat_logs.map((item) => (
              <li key={`chat-${item.id}`}>Chat log: {item.original_filename}</li>
            ))}
          </ul>
        </div>
      )}

      <button
        type="button"
        className="modal-secondary"
        onClick={() => downloadResearchBrief(request, form, notesWithContent)}
      >
        Download research brief
      </button>
    </div>
  );
}
