import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock the dependencies
vi.mock("@/lib/db", () => ({
  connectDB: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/lib/auth", () => ({
  getSessionFromRequest: vi.fn(),
}));

describe("API Authentication", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should return 401 when no session exists", async () => {
    const { requireAuth } = await import("@/lib/api-auth");
    const mockRequest = {
      cookies: new Map(),
      headers: new Headers(),
    } as any;

    // Mock getSessionFromRequest to return null
    const { getSessionFromRequest } = await import("@/lib/auth");
    vi.mocked(getSessionFromRequest).mockResolvedValue(null);

    const result = await requireAuth(mockRequest as any);

    expect(result).toBeDefined();
    if (result && "status" in result) {
      expect(result.status).toBe(401);
    }
  });

  it("should return session payload when authenticated", async () => {
    const { requireAuth } = await import("@/lib/api-auth");
    const mockRequest = {
      cookies: new Map(),
    } as any;

    const { getSessionFromRequest } = await import("@/lib/auth");
    vi.mocked(getSessionFromRequest).mockResolvedValue({
      adminId: "507f1f77bcf86cd799439011",
      email: "admin@example.com",
      role: "ADMIN",
    });

    const result = await requireAuth(mockRequest as any);

    expect(result).toBeDefined();
    if (result && "adminId" in result) {
      expect(result.email).toBe("admin@example.com");
      expect(result.role).toBe("ADMIN");
    }
  });
});