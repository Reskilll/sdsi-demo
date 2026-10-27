import { SignJWT, jwtVerify } from "jose";
import { cookies } from "next/headers";
import { NextRequest } from "next/server";
import { getEnv } from "./env";

const SESSION_DURATION_SECONDS = 86400; // 24 hours

function getSecretKey(): Uint8Array {
  const env = getEnv();
  return new TextEncoder().encode(env.SESSION_SECRET);
}

export interface SessionPayload {
  adminId: string;
  email: string;
  role: string;
}

export async function createSession(payload: SessionPayload): Promise<string> {
  const env = getEnv();
  const secret = getSecretKey();

  const jwt = await new SignJWT(payload as unknown as Record<string, unknown>)
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime(`${SESSION_DURATION_SECONDS}s`)
    .sign(secret);

  const cookieStore = await cookies();

  cookieStore.set(env.SESSION_COOKIE_NAME, jwt, {
    httpOnly: true,
    secure: env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_DURATION_SECONDS,
  });

  return jwt;
}

export async function getSession(): Promise<SessionPayload | null> {
  const env = getEnv();
  const cookieStore = await cookies();
  const token = cookieStore.get(env.SESSION_COOKIE_NAME)?.value;

  if (!token) return null;

  try {
    const secret = getSecretKey();
    const { payload } = await jwtVerify(token, secret);
    return {
      adminId: payload.adminId as string,
      email: payload.email as string,
      role: payload.role as string,
    };
  } catch {
    return null;
  }
}

export async function destroySession(): Promise<void> {
  const env = getEnv();
  const cookieStore = await cookies();
  cookieStore.set(env.SESSION_COOKIE_NAME, "", {
    httpOnly: true,
    secure: env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
}

export async function getSessionFromRequest(
  request: NextRequest,
): Promise<SessionPayload | null> {
  const env = getEnv();
  const token = request.cookies.get(env.SESSION_COOKIE_NAME)?.value;

  if (!token) return null;

  try {
    const secret = getSecretKey();
    const { payload } = await jwtVerify(token, secret);
    return {
      adminId: payload.adminId as string,
      email: payload.email as string,
      role: payload.role as string,
    };
  } catch {
    return null;
  }
}