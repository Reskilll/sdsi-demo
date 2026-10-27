import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getEnv } from "@/lib/env";

const publicPaths = ["/login", "/api/auth/login", "/api/auth/session"];

/**
 * Global middleware: protect all dashboard routes behind authentication.
 */
export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const env = getEnv();

  // Allow public paths
  if (publicPaths.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Allow static assets and Next.js internals
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/static") ||
    pathname.startsWith("/favicon.ico") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  // Check for session cookie
  const sessionCookie = request.cookies.get(env.SESSION_COOKIE_NAME);

  // If not authenticated and trying to access dashboard, redirect to login
  if (!sessionCookie && !pathname.startsWith("/api/")) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // API routes: let the route handler check authentication
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};