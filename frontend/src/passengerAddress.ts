type PassengerAddressFields = {
  address_line_1?: string | null;
  address_line_2?: string | null;
  city?: string | null;
  state_or_province?: string | null;
  postal_code?: string | null;
  country?: string | null;
};

export function formatPassengerAddressLine(passenger: PassengerAddressFields): string | null {
  const segments: string[] = [];
  const line1 = passenger.address_line_1?.trim();
  const line2 = passenger.address_line_2?.trim();
  const city = passenger.city?.trim();
  const state = passenger.state_or_province?.trim();
  const postal = passenger.postal_code?.trim();
  const country = passenger.country?.trim();

  if (line1) {
    segments.push(line1);
  }
  if (line2) {
    segments.push(line2);
  }

  const statePostal = [state, postal].filter(Boolean).join(" ");
  const cityLine = [city, statePostal].filter(Boolean).join(", ");
  if (cityLine) {
    segments.push(cityLine);
  }
  if (country) {
    segments.push(country);
  }

  return segments.length > 0 ? segments.join(", ") : null;
}

export function passengerAddressToInput(passenger: PassengerAddressFields) {
  return {
    address_line_1: passenger.address_line_1 ?? "",
    address_line_2: passenger.address_line_2 ?? "",
    city: passenger.city ?? "",
    state_or_province: passenger.state_or_province ?? "",
    postal_code: passenger.postal_code ?? "",
    country: passenger.country ?? "",
  };
}

export function normalizeAddressInput(value: PassengerAddressFields) {
  return {
    address_line_1: value.address_line_1?.trim() || null,
    address_line_2: value.address_line_2?.trim() || null,
    city: value.city?.trim() || null,
    state_or_province: value.state_or_province?.trim() || null,
    postal_code: value.postal_code?.trim() || null,
    country: value.country?.trim() || null,
  };
}
