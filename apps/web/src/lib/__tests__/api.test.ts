import { describe, expect, it, vi } from "vitest";

import { ApiError, createApiClient } from "../api";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const user = {
  id: "7b0c6f7e-2b1c-4a8e-9a43-1f2d3c4b5a69",
  email: "ada@example.com",
  display_name: "Ada",
  timezone: "Asia/Karachi",
  city: null,
  onboarding_completed: false,
};

describe("api client", () => {
  it("posts JSON to relative /api paths by default", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, user));
    const api = createApiClient({ fetch: fetchMock });

    await expect(api.auth.login({ email: "ada@example.com", password: "pw" })).resolves.toEqual(user);

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/auth/login");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("same-origin");
    expect(JSON.parse(init.body as string)).toEqual({ email: "ada@example.com", password: "pw" });
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("uses a custom base URL and headers (server-side calls)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, user));
    const api = createApiClient({
      baseUrl: "http://api.internal",
      headers: { Cookie: "dp_session=abc" },
      fetch: fetchMock,
    });

    await api.auth.me();

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://api.internal/auth/me");
    expect(init.method).toBe("GET");
    expect(init.body).toBeUndefined();
    expect((init.headers as Record<string, string>).Cookie).toBe("dp_session=abc");
  });

  it("turns the API error shape into an ApiError", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        jsonResponse(401, { error: { code: "invalid_credentials", message: "Email or password is incorrect" } }),
      );
    const api = createApiClient({ fetch: fetchMock });

    const error = await api.auth.login({ email: "a@b.co", password: "x" }).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 401, code: "invalid_credentials", message: "Email or password is incorrect" });
  });

  it("handles non-JSON errors, network failures and 204s", async () => {
    const api = createApiClient({
      fetch: vi
        .fn()
        .mockResolvedValueOnce(new Response("<html>bad gateway</html>", { status: 502, statusText: "Bad Gateway" }))
        .mockRejectedValueOnce(new TypeError("Failed to fetch"))
        .mockResolvedValueOnce(new Response(null, { status: 204 })),
    });

    await expect(api.auth.me()).rejects.toMatchObject({ status: 502, code: "http_error" });
    await expect(api.auth.me()).rejects.toMatchObject({ status: 0, code: "network_error" });
    await expect(api.auth.logout()).resolves.toBeUndefined();
  });
});
