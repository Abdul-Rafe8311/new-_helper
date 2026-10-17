/**
 * Typed client for the NewsHelper API.
 *
 * In the browser it calls relative `/api/*` paths, which Next.js rewrites to the API, so
 * the `dp_session` cookie stays first-party. On the server, pass `baseUrl` (the API's own
 * URL) and forward the cookie in `headers`; see `lib/server/session.ts`.
 */
import type { components } from "./api-schema";

type Schemas = components["schemas"];
export type User = Schemas["UserOut"];
export type Profile = Schemas["ProfileOut"];
export type ProfileUpdate = Schemas["ProfileUpdate"];
export type RegisterBody = Schemas["RegisterIn"];
export type LoginBody = Schemas["LoginIn"];
export type Taxonomy = Schemas["TaxonomyOut"];
export type Topic = Schemas["TopicOut"];
export type OnboardingState = Schemas["OnboardingStateOut"];
export type ParsedInterests = Schemas["ParsedInterests"];
export type Headline = Schemas["HeadlineOut"];
export type EditionStatus = Schemas["EditionStatusOut"];
export type NameStep = Schemas["NameStep"];
export type BeatsStep = Schemas["BeatsStep"];
export type WordsStep = Schemas["WordsStep"];
export type TasteStep = Schemas["TasteStep"];
export type ReadingStep = Schemas["ReadingStep"];
export type Edition = Schemas["EditionOut"];
export type EditionItem = Schemas["EditionItemOut"];
export type EditionSummary = Schemas["EditionSummary"];
export type ItemState = Schemas["ItemState"];
export type SavedItem = Schemas["SavedItem"];
export type Story = Schemas["StoryOut"];
export type StoryImage = Schemas["StoryImage"];
export type StorySource = Schemas["StorySource"];
export type QuizStreak = Schemas["QuizStreakOut"];
export type Interests = {
  topics: { slug: string; label: string; weight: number }[];
  entities: { id: string; kind: string; name: string; pinned: boolean }[];
  blocked: { topic: string; label: string }[];
  /** True until the paper has learned or been told anything. */
  is_new: boolean;
};
export type Timeline = {
  days: { date: string; entries: { id: string; at: string; kind: string; text: string }[] }[];
};
export type StepBody = NameStep | BeatsStep | WordsStep | TasteStep | ReadingStep;

/** Every API failure, carrying the `{"error": {"code", "message"}}` body. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export type ApiClientOptions = {
  baseUrl?: string;
  headers?: Record<string, string>;
  fetch?: typeof fetch;
};

type Method = "GET" | "POST" | "PUT" | "DELETE";

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const body: unknown = await response.json();
    const error = (body as { error?: { code?: unknown; message?: unknown } }).error;
    if (error && typeof error.code === "string" && typeof error.message === "string") {
      return new ApiError(response.status, error.code, error.message);
    }
  } catch {
    // not JSON: fall through
  }
  return new ApiError(response.status, "http_error", response.statusText || "Request failed");
}

export function createApiClient({ baseUrl = "/api", headers = {}, fetch: fetchImpl }: ApiClientOptions = {}) {
  async function request<T>(method: Method, path: string, body?: unknown): Promise<T> {
    const doFetch = fetchImpl ?? fetch;
    let response: Response;
    try {
      response = await doFetch(`${baseUrl}${path}`, {
        method,
        headers: {
          Accept: "application/json",
          ...(body === undefined ? {} : { "Content-Type": "application/json" }),
          ...headers,
        },
        body: body === undefined ? undefined : JSON.stringify(body),
        credentials: "same-origin",
        cache: "no-store",
      });
    } catch {
      throw new ApiError(0, "network_error", "Could not reach NewsHelper. Check your connection.");
    }
    if (!response.ok) throw await toApiError(response);
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  return {
    auth: {
      register: (body: RegisterBody) => request<User>("POST", "/auth/register", body),
      login: (body: LoginBody) => request<User>("POST", "/auth/login", body),
      demo: () => request<User>("POST", "/auth/demo"),
      logout: () => request<void>("POST", "/auth/logout"),
      me: () => request<User>("GET", "/auth/me"),
    },
    profile: {
      get: () => request<Profile>("GET", "/me/profile"),
      update: (changes: ProfileUpdate) => request<Profile>("PUT", "/me/profile", changes),
    },
    quizStreak: () => request<QuizStreak>("GET", "/me/quiz-streak"),
    interests: {
      get: () => request<Interests>("GET", "/me/interests"),
      timeline: () => request<Timeline>("GET", "/me/interests/timeline"),
      setTopics: (topics: Record<string, number>) => request<Interests>("PUT", "/me/interests/topics", { topics }),
      pin: (id: string, pinned: boolean) => request<Interests>("POST", `/me/interests/entities/${id}/pin`, { pinned }),
      removeEntity: (id: string) => request<Interests>("DELETE", `/me/interests/entities/${id}`),
      block: (topic: string) => request<Interests>("POST", "/me/interests/blocked", { topic }),
      unblock: (topic: string) => request<Interests>("DELETE", `/me/interests/blocked/${encodeURIComponent(topic)}`),
      reset: () => request<Interests>("POST", "/me/interests/reset"),
    },
    editions: {
      today: () => request<Edition>("GET", "/editions/today"),
      byDate: (date: string) => request<Edition>("GET", `/editions/${date}`),
      list: ({ before, limit }: { before?: string; limit?: number } = {}) => {
        const query = new URLSearchParams();
        if (before) query.set("before", before);
        if (limit) query.set("limit", String(limit));
        const qs = query.toString();
        return request<EditionSummary[]>("GET", `/editions${qs ? `?${qs}` : ""}`);
      },
      /** Start (or restart) building today's paper; poll `today()` for the result. */
      regenerate: () => request<Edition>("POST", "/editions/today/regenerate"),
    },
    saved: () => request<SavedItem[]>("GET", "/saved"),
    story: (itemId: string) => request<Story>("GET", `/stories/${itemId}`),
    taxonomy: () => request<Taxonomy>("GET", "/taxonomy"),
    onboarding: {
      state: () => request<OnboardingState>("GET", "/onboarding/state"),
      saveStep: (number: number, body: StepBody) =>
        request<OnboardingState>("PUT", `/onboarding/step/${number}`, body),
      suggestions: (topic: string) =>
        request<Schemas["SuggestionsOut"]>("GET", `/onboarding/suggestions?topic=${encodeURIComponent(topic)}`),
      parse: (text: string) => request<ParsedInterests>("POST", "/onboarding/parse", { text }),
      headlines: () => request<Schemas["HeadlinesOut"]>("GET", "/onboarding/headlines"),
      answer: (articleId: string, interested: boolean) =>
        request<void>("POST", "/onboarding/taste", { article_id: articleId, interested }),
      complete: () => request<Schemas["CompleteOut"]>("POST", "/onboarding/complete"),
      status: () => request<EditionStatus>("GET", "/onboarding/status"),
    },
  };
}

/** The PDF download for a day (a plain link: the session cookie rides along). */
export const pdfHref = (date: string) => `/api/editions/${date}/pdf`;

/** "Read original": logs an open event, then redirects to the source. */
export const originalHref = (itemId: string) => `/api/r/${itemId}`;

export type ApiClient = ReturnType<typeof createApiClient>;

/** Browser client (relative `/api/*` paths). */
export const api = createApiClient();
