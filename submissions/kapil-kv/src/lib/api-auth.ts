import { NextRequest } from "next/server";
import { getSessionFromRequest, SessionPayload } from "./auth";
import { unauthorizedResponse } from "./api-response";

/**
 * Authenticate an API request. Returns the session payload or an error response.
 */
export async function requireAuth(
  request: NextRequest,
): Promise<SessionPayload | ReturnType<typeof unauthorizedResponse>> {
  const session = await getSessionFromRequest(request);
  if (!session) {
    return unauthorizedResponse();
  }
  return session;
}