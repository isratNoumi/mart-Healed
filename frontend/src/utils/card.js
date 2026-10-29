export function digitsOnly(value) {
  return String(value || "").replace(/\D/g, "");
}

export function luhnValid(digits) {
  let total = 0;
  digits.split("").reverse().forEach((char, index) => {
    let value = Number(char);
    if (index % 2 === 1) {
      value *= 2;
      if (value > 9) value -= 9;
    }
    total += value;
  });
  return total % 10 === 0;
}

export function cardBrand(digits) {
  if (/^4/.test(digits)) return "VISA";
  const first2 = Number(digits.slice(0, 2));
  const first3 = Number(digits.slice(0, 3));
  const first4 = Number(digits.slice(0, 4));
  if ((first2 >= 51 && first2 <= 55) || (first4 >= 2221 && first4 <= 2720)) return "MASTERCARD";
  if (/^3[47]/.test(digits)) return "AMEX";
  if (/^(6011|65)/.test(digits) || (first3 >= 644 && first3 <= 649)) return "DISCOVER";
  return null;
}

export function formatCardNumber(value) {
  return digitsOnly(value).slice(0, 19).replace(/(\d{4})(?=\d)/g, "$1 ");
}

export function validateCardForm(card, now = new Date()) {
  const errors = {};
  const digits = digitsOnly(card.card_number);
  const brand = cardBrand(digits);

  if (!card.cardholder_name.trim()) errors.cardholder_name = "Enter the name on the card.";

  if (digits.length < 12 || digits.length > 19 || !luhnValid(digits)) {
    errors.card_number = "Enter a valid card number.";
  } else if (!brand) {
    errors.card_number = "We accept Visa, Mastercard, American Express and Discover.";
  }

  const month = Number(card.expiry_month);
  const year = Number(card.expiry_year);
  if (!month || !year) {
    errors.expiry = "Choose the expiration date.";
  } else if (year < now.getFullYear() || (year === now.getFullYear() && month < now.getMonth() + 1)) {
    errors.expiry = "This card has expired.";
  }

  const cvvLength = brand === "AMEX" ? 4 : 3;
  if (!new RegExp(`^\\d{${cvvLength}}$`).test(card.cvv)) errors.cvv = `Enter the ${cvvLength}-digit security code.`;
  return errors;
}

export function toCardPayload(card) {
  return {
    cardholder_name: card.cardholder_name.trim(),
    card_number: digitsOnly(card.card_number),
    expiry_month: Number(card.expiry_month),
    expiry_year: Number(card.expiry_year),
    cvv: card.cvv
  };
}
