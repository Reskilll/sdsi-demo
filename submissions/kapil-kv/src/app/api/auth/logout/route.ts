import { destroySession } from "@/lib/auth";
import { successResponse, errorResponse } from "@/lib/api-response";
import { logger } from "@/lib/logger";

export async function POST() {
  try {
    await destroySession();
    logger.info("Admin logged out");
    return successResponse({ message: "Logged out successfully." });
  } catch (e) {
    logger.error("Logout error", { error: (e as Error).message });
    return errorResponse("SERVER_ERROR", "An unexpected error occurred.", 500);
  }
}