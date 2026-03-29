import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";

export default auth((req) => {
  const { pathname } = req.nextUrl;

  // Allow login page and auth API routes
  if (pathname.startsWith("/login") || pathname.startsWith("/auth-error") || pathname.startsWith("/api/auth")) {
    return NextResponse.next();
  }

  // Check if any auth provider is configured
  const hasGoogle = !!(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET);
  const hasCredentials = !!(process.env.UI_USERNAME && process.env.UI_PASSWORD);

  // No auth configured — block all access
  if (!hasGoogle && !hasCredentials) {
    return NextResponse.redirect(new URL("/login", req.url));
  }

  // Not authenticated — redirect to login
  if (!req.auth) {
    return NextResponse.redirect(new URL("/login", req.url));
  }

  return NextResponse.next();
});

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|logo.*\\.svg).*)"],
};
