import "server-only";

import { ApiError, type Edition } from "@/lib/api";
import { serverApi } from "@/lib/server/session";

/** An edition, or null if the reader has none for that day yet. */
export async function loadEdition(date: "today" | string): Promise<Edition | null> {
  const api = await serverApi();
  try {
    return date === "today" ? await api.editions.today() : await api.editions.byDate(date);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}
