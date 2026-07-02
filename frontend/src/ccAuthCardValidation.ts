export type CcAuthCardForm = {
  cardholderName: string;
  cardNumber: string;
  expiration: string;
  securityCode: string;
};

export function digitsOnly(value: string): string {
  return value.replace(/\D/g, "");
}

export function formatCardNumberInput(value: string): string {
  const digits = digitsOnly(value).slice(0, 19);
  return digits.replace(/(\d{4})(?=\d)/g, "$1 ").trim();
}

export function formatExpirationInput(value: string): string {
  const digits = digitsOnly(value).slice(0, 4);
  if (digits.length <= 2) {
    return digits;
  }
  return `${digits.slice(0, 2)}/${digits.slice(2)}`;
}

function luhnCheck(cardNumber: string): boolean {
  let sum = 0;
  let shouldDouble = false;
  for (let index = cardNumber.length - 1; index >= 0; index -= 1) {
    let digit = Number(cardNumber[index]);
    if (shouldDouble) {
      digit *= 2;
      if (digit > 9) {
        digit -= 9;
      }
    }
    sum += digit;
    shouldDouble = !shouldDouble;
  }
  return sum % 10 === 0;
}

function isExpirationValid(expiration: string): boolean {
  const match = /^(\d{2})\/(\d{2})$/.exec(expiration.trim());
  if (!match) {
    return false;
  }
  const month = Number(match[1]);
  const year = Number(match[2]);
  if (month < 1 || month > 12) {
    return false;
  }
  const now = new Date();
  const expiry = new Date(2000 + year, month, 0, 23, 59, 59);
  return expiry >= new Date(now.getFullYear(), now.getMonth(), 1);
}

export function validateCcAuthCardForm(form: CcAuthCardForm): string | null {
  const cardholderName = form.cardholderName.trim();
  if (cardholderName.length < 2) {
    return "Enter the name as it appears on the card.";
  }

  const cardNumber = digitsOnly(form.cardNumber);
  if (cardNumber.length < 13 || cardNumber.length > 19) {
    return "Enter a valid card number.";
  }
  if (!luhnCheck(cardNumber)) {
    return "Enter a valid card number.";
  }

  const expiration = formatExpirationInput(form.expiration);
  if (!isExpirationValid(expiration)) {
    return "Enter a valid expiration date in MM/YY format.";
  }

  const securityCode = digitsOnly(form.securityCode);
  if (securityCode.length < 3 || securityCode.length > 4) {
    return "Enter a valid security code.";
  }

  return null;
}

export function toCcAuthCardPayload(form: CcAuthCardForm) {
  return {
    cardholder_name: form.cardholderName.trim(),
    card_number: digitsOnly(form.cardNumber),
    expiration: formatExpirationInput(form.expiration),
    security_code: digitsOnly(form.securityCode),
  };
}
