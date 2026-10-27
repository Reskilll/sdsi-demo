import { describe, it, expect } from "vitest";
import { calculateSla } from "@/services/sla-calculator";
import { buildCalendarConfig } from "@/services/business-calendar";
import type { StatusEvent } from "@/types";

function makeEvent(
  dateStr: string,
  status: string,
  reason = "",
): StatusEvent {
  return {
    status: status as any,
    timestamp: new Date(dateStr),
    reason,
  };
}

describe("SLA Calculator Integration Tests", () => {
  const calendarConfig = buildCalendarConfig([]);

  describe("Real-world scenarios", () => {
    it("complete ticket lifecycle: OPEN -> IN_PROGRESS -> ON_HOLD -> IN_PROGRESS -> RESOLVED", () => {
      // Mon 09:00 IST = 2026-10-26T03:30:00Z
      // 09:00 OPEN -> 09:30 IN_PROGRESS -> 10:30 ON_HOLD -> 12:30 IN_PROGRESS -> 14:00 RESOLVED
      // Active time: 09:00-10:30 (90 min) + 12:30-14:00 (90 min) = 180 min
      // Hold: 10:30-12:30 (120 real min)
      const history = [
        makeEvent("2026-10-26T03:30:00.000Z", "OPEN", "created"),
        makeEvent("2026-10-26T04:00:00.000Z", "IN_PROGRESS", "started"),
        makeEvent("2026-10-26T05:00:00.000Z", "ON_HOLD", "waiting vendor"),
        makeEvent("2026-10-26T07:00:00.000Z", "IN_PROGRESS", "vendor responded"),
        makeEvent("2026-10-26T08:30:00.000Z", "RESOLVED", "fixed"),
      ];

      const result = calculateSla(
        history,
        "P1",
        "RESOLVED",
        new Date("2026-10-26T08:30:00.000Z"),
        new Date("2026-10-26T08:30:00.000Z"),
        undefined,
        calendarConfig,
      );

      expect(result.elapsedBusinessMinutes).toBe(180); // 90 + 90
      expect(result.slaTargetMinutes).toBe(240); // P1
      expect(result.isBreached).toBe(false); // 180 < 240
      expect(result.slaStatus).toBe("RESOLVED");
      expect(result.breachMinutes).toBe(0);
    });

    it("multi-day ticket with weekend and ON_HOLD", () => {
      // Fri 16:00 OPEN -> Fri 17:00 ON_HOLD -> Mon 10:00 IN_PROGRESS -> Mon 12:00 RESOLVED
      // Active: Fri 16:00-17:00 (60 min) + Mon 10:00-12:00 (120 min) = 180 min
      // Hold covers: Fri 17:00 through Mon 10:00
      // But only Mon 09:00-10:00 was business time during hold period
      const history = [
        makeEvent("2026-10-30T10:30:00.000Z", "OPEN", "created"),
        makeEvent("2026-10-30T11:30:00.000Z", "ON_HOLD", "weekend"),
        makeEvent("2026-11-02T04:30:00.000Z", "IN_PROGRESS", "monday morning"),
        makeEvent("2026-11-02T06:30:00.000Z", "RESOLVED", "done"),
      ];

      const result = calculateSla(
        history,
        "P2",
        "RESOLVED",
        new Date("2026-11-02T06:30:00.000Z"),
        new Date("2026-11-02T06:30:00.000Z"),
        undefined,
        calendarConfig,
      );

      expect(result.elapsedBusinessMinutes).toBe(180); // 60 + 120
      expect(result.isBreached).toBe(false); // 180 < 480 (P2)
    });

    it("ticket that exceeds P1 SLA while ON_HOLD", () => {
      // Mon 09:00 OPEN -> Mon 10:00 ON_HOLD (still on hold at calculation time)
      // Active: 09:00-10:00 = 60 min
      const history = [
        makeEvent("2026-10-26T03:30:00.000Z", "OPEN", "created"),
        makeEvent("2026-10-26T04:30:00.000Z", "ON_HOLD", "waiting"),
      ];

      // Calculate at Tue 10:00 (after 1 day on hold)
      const result = calculateSla(
        history,
        "P1",
        "ON_HOLD",
        null,
        new Date("2026-10-27T04:30:00.000Z"),
        undefined,
        calendarConfig,
      );

      expect(result.slaStatus).toBe("PAUSED");
      expect(result.isProvisional).toBe(true);
      expect(result.elapsedBusinessMinutes).toBe(60);
      expect(result.isBreached).toBe(false); // 60 < 240, not breached yet
    });

    it("ticket resolved exactly at deadline is not breached", () => {
      // 09:00 + 240 min = 13:00 (P1 deadline)
      const history = [
        makeEvent("2026-10-26T03:30:00.000Z", "OPEN", "created"),
        makeEvent("2026-10-26T07:30:00.000Z", "RESOLVED", "done exactly at deadline"),
      ];

      const result = calculateSla(
        history,
        "P1",
        "RESOLVED",
        new Date("2026-10-26T07:30:00.000Z"),
        new Date("2026-10-26T07:30:00.000Z"),
        undefined,
        calendarConfig,
      );

      // 09:00-13:00 = 240 min = P1 target
      expect(result.elapsedBusinessMinutes).toBe(240);
      expect(result.isBreached).toBe(false);
      expect(result.breachMinutes).toBe(0);
    });

    it("imported ticket with minimal status history (only created)", () => {
      const history = [
        makeEvent("2026-10-26T03:30:00.000Z", "OPEN", "imported"),
      ];

      // Calculate at 14:00 same day
      const result = calculateSla(
        history,
        "P2",
        "OPEN",
        null,
        new Date("2026-10-26T08:30:00.000Z"),
        undefined,
        calendarConfig,
      );

      // 09:00-14:00 = 5 hours = 300 min
      expect(result.elapsedBusinessMinutes).toBe(300);
      expect(result.isBreached).toBe(false); // 300 < 480 (P2)
    });
  });

  describe("Edge cases", () => {
    it("empty history returns safe defaults", () => {
      const result = calculateSla([], "P1", "OPEN", null);
      expect(result.elapsedBusinessMinutes).toBe(0);
      expect(result.isBreached).toBe(false);
    });

    it("multiple consecutive ON_HOLD entries are treated as one", () => {
      const history = [
        makeEvent("2026-10-26T03:30:00.000Z", "OPEN", "created"),
        makeEvent("2026-10-26T04:00:00.000Z", "ON_HOLD", "hold 1"),
        makeEvent("2026-10-26T04:30:00.000Z", "ON_HOLD", "hold 2"),
        makeEvent("2026-10-26T05:30:00.000Z", "IN_PROGRESS", "resumed"),
        makeEvent("2026-10-26T06:30:00.000Z", "RESOLVED", "done"),
      ];

      const result = calculateSla(
        history,
        "P1",
        "RESOLVED",
        new Date("2026-10-26T06:30:00.000Z"),
        new Date("2026-10-26T06:30:00.000Z"),
        undefined,
        calendarConfig,
      );

      // Active: 09:00-09:30 (30 min) + 11:00-12:00 (60 min) = 90 min
      expect(result.elapsedBusinessMinutes).toBe(90);
    });

    it("AT_RISK threshold at 25% remaining", () => {
      // P1 target = 240 min. AT_RISK when remaining <= 60 min (25% of 240)
      // So AT_RISK when elapsed >= 180 min
      const history = [
        makeEvent("2026-10-26T03:30:00.000Z", "OPEN", "created"),
      ];

      // Calculate at 12:35 (215 min elapsed, 25 remaining)
      const result = calculateSla(
        history,
        "P1",
        "OPEN",
        null,
        new Date("2026-10-26T07:05:00.000Z"),
        undefined,
        calendarConfig,
      );

      expect(result.slaStatus).toBe("AT_RISK");
      expect(result.remainingBusinessMinutes).toBe(25);
    });
  });
});