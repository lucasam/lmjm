/**
 * Convert an HTML datetime-local value (YYYY-MM-DDThh:mm) to the API format (YYYYMMDDHHmm).
 *
 * Strips dashes, the "T" separator, and the colon from the input string.
 *
 * @param datetimeLocal - A string in YYYY-MM-DDThh:mm format (from <input type="datetime-local">)
 * @returns A 12-character numeric string in YYYYMMDDHHmm format
 */
export function datetimeLocalToApi(datetimeLocal: string): string {
  return datetimeLocal.replace(/[-T:]/g, '');
}

/**
 * Return the current date and time formatted for an HTML datetime-local input (YYYY-MM-DDThh:mm).
 */
export function currentDatetimeLocal(): string {
  const now = new Date();
  const y = now.getFullYear();
  const mo = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  const h = String(now.getHours()).padStart(2, '0');
  const mi = String(now.getMinutes()).padStart(2, '0');
  return `${y}-${mo}-${d}T${h}:${mi}`;
}
