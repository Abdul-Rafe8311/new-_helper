/** A same-site path from ?next=, or the fallback. Blocks open redirects like //evil.com. */
export function safeNext(value: string | null | undefined, fallback = "/today"): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) {
    return fallback;
  }
  return value;
}
