/** Feature flags, read from the environment on the server. Each defaults to on. */

function flag(value: string | undefined, fallback = true): boolean {
  if (value === undefined || value.trim() === "") return fallback;
  return !["false", "0", "off", "no"].includes(value.trim().toLowerCase());
}

/** The recall quiz, the "Still remember?" card and the Listen placeholder in the masthead. */
export function quizEnabled(env: Record<string, string | undefined> = process.env): boolean {
  return flag(env.QUIZ_ENABLED);
}
