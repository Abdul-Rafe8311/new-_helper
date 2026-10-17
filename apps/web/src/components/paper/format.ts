/** Date formatting with an explicit time zone, so server and client render the same text. */
export function formatDateLine(date: Date | string, timeZone = "Asia/Karachi"): string {
  // Built from parts: ICU versions disagree on punctuation ("Saturday, 17 October" vs "Saturday 17 October").
  const parts = new Intl.DateTimeFormat("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone,
  }).formatToParts(new Date(date));
  const get = (type: Intl.DateTimeFormatPartTypes) => parts.find((p) => p.type === type)?.value ?? "";
  return `${get("weekday")}, ${get("day")} ${get("month")} ${get("year")}`;
}

export function formatShortDate(date: Date | string, timeZone = "UTC"): string {
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone }).format(
    new Date(date),
  );
}
