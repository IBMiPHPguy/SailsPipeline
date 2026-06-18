import { formatCruiseLines } from "./CruiseLineMultiSelect";
import type { RequestNote, TravelRequestDetail, TravelRequestInput } from "./types";
import { formatDate, formatDestinationSummary } from "./utils";

function line(label: string, value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return `${label}: —`;
  }
  return `${label}: ${value}`;
}

export function buildResearchBriefText(
  request: TravelRequestDetail,
  form: TravelRequestInput,
  notesWithContent: Pick<RequestNote, "summary" | "content">[] = [],
): string {
  const summaryRequest = {
    ...request,
    first_name: form.first_name,
    last_name: form.last_name,
    email: form.email,
    phone: form.phone,
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

  const sections: string[] = [
    "Cruise Travel Now — Research Brief",
    line("Request", `#${request.id}`),
    line("Generated", new Date().toLocaleString()),
    "",
    "CLIENT",
    line("Name", `${form.first_name} ${form.last_name}`.trim()),
    line("Email", form.email),
    line("Phone", form.phone),
    "",
    "CRUISE PREFERENCES",
    line("Preferred cruise lines", formatCruiseLines(form.cruise_lines)),
    line("Cruise lines to avoid", formatCruiseLines(form.excluded_cruise_lines)),
    line("Destination", formatDestinationSummary(summaryRequest)),
    line("Departure date", formatDate(form.departure_date)),
    line("Return date", formatDate(form.return_date)),
    line("Cabin types", form.cabin_types.join(", ") || null),
    line("Passenger count", form.passengers),
    line("Cabins needed", form.cabins_needed),
    "",
    "PASSENGERS",
    ...(request.request_passengers.length === 0
      ? ["  (none)"]
      : request.request_passengers.map((passenger, index) => {
          const name = `${passenger.first_name} ${passenger.last_name}`.trim();
          const dob = passenger.date_of_birth ? `DOB ${formatDate(passenger.date_of_birth)}` : "DOB not set";
          const state = passenger.state_or_province?.trim();
          const address = state ? ` · ${state}` : "";
          const discounts =
            passenger.qualifiers?.length > 0 ? ` · Discounts: ${passenger.qualifiers.join(", ")}` : "";
          return `  ${index + 1}. ${name} — ${dob} — ${passenger.email} — ${passenger.phone}${address}${discounts}`;
        })),
    "",
    "NOTES",
    ...(notesWithContent.length === 0
      ? ["  (none)"]
      : notesWithContent.map((note) => {
          const summary = note.summary.trim();
          const preview = note.content.trim().replace(/\s+/g, " ");
          const content = preview.length > 200 ? `${preview.slice(0, 200)}…` : preview;
          return summary ? `  - ${summary}: ${content}` : `  - ${content}`;
        })),
    "",
    "ATTACHMENTS ON FILE",
    line(
      "Call transcripts",
      request.call_transcripts.map((item) => item.original_filename).join(", ") || null,
    ),
    line("Chat logs", request.chat_logs.map((item) => item.original_filename).join(", ") || null),
    line(
      "Research documents",
      request.research_documents.map((item) => item.original_filename).join(", ") || null,
    ),
  ];

  return sections.join("\n");
}

export function downloadResearchBrief(
  request: TravelRequestDetail,
  form: TravelRequestInput,
  notesWithContent: Pick<RequestNote, "summary" | "content">[] = [],
): void {
  const content = buildResearchBriefText(request, form, notesWithContent);
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `request-${request.id}-research-brief.txt`;
  anchor.click();
  URL.revokeObjectURL(url);
}
