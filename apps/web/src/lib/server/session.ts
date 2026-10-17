import "server-only";

import { cookies } from "next/headers";

import { ApiError, createApiClient, type Profile, type User } from "@/lib/api";

export const SESSION_COOKIE = "dp_session";

export function apiUrl(): string {
  return process.env.API_URL ?? "http://localhost:8000";
}

export type Session = { user: User; profile: Profile };

/** An API client that acts as the signed-in reader (or anonymously if there is no cookie). */
export async function serverApi() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  return createApiClient({
    baseUrl: apiUrl(),
    headers: token ? { Cookie: `${SESSION_COOKIE}=${token}` } : {},
  });
}

/** The signed-in reader, or null. Reads the request cookie, so call it inside <Suspense>. */
export async function getSession(): Promise<Session | null> {
  if (!(await cookies()).get(SESSION_COOKIE)?.value) return null;
  const client = await serverApi();
  try {
    const [user, profile] = await Promise.all([client.auth.me(), client.profile.get()]);
    return { user, profile };
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}
