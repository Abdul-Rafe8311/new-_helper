import { NextResponse, type NextRequest } from "next/server";

const SESSION_COOKIE = "dp_session";

/**
 * Optimistic gate for signed-in pages: without a session cookie, go to /login and come back.
 * The real check (is the cookie valid?) happens server-side in the (app) layout via /auth/me.
 */
export function proxy(request: NextRequest) {
  if (request.cookies.has(SESSION_COOKIE)) return NextResponse.next();
  const login = new URL("/login", request.url);
  login.searchParams.set("next", request.nextUrl.pathname + request.nextUrl.search);
  return NextResponse.redirect(login);
}

export const config = {
  matcher: [
    "/today/:path*",
    "/paper/:path*",
    "/archive/:path*",
    "/saved/:path*",
    "/interests/:path*",
    "/settings/:path*",
    "/onboarding/:path*",
  ],
};
