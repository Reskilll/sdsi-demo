import { describe, it, expect } from "vitest";
import {
  calculateSla,
  DEFAULT_SLA_TARGETS,
  isValidTransition,
} from "@/services/sla-calculator";
import {
  isWeekend,
  isBusinessHour,
  nextBusinessStart,
  calculateBusinessMinutes,
  addBusinessMinutes,
  toBusinessDateString,
  buildCalendarConfig,
} from "@/services/business-calendar";
import type { StatusEvent, BusinessCalendarConfig } from "@/types";

/** Fixed calendar config: UTC+5:30 (Asia/Kolkata), 9-18, no holidays */
function testCalendarConfig(overrides?: Partial<BusinessCalendarConfig>): BusinessCalendarConfig {
  return {
    timezone: "Asia/Kolkata",
    businessStartHour: 9,
    businessEndHour: 18,
    holidays: [],
    ...overrides,
  };
}

function s(dateStr: string, status: string, reason = ""): StatusEvent {
  return { status: status as any, timestamp: new Date(dateStr), reason };
}

// ============================================================================
// Business Calendar Tests
// ============================================================================

describe("BusinessCalendar", () => {
  describe("toBusinessDateString", () => {
    it("converts a date to the business timezone date string", () => {
      // 2026-10-27 04:00 UTC = 2026-10-27 09:30 IST
      const date = new Date("2026-10-27T04:00:00.000Z");
      expect(toBusinessDateString(date, "Asia/Kolkata")).toBe("2026-10-27");
    });
  });

  describe("isWeekend", () => {
    it("identifies Saturday", () => {
      // 2026-10-31 is Saturday
      const saturday = new Date("2026-10-31T06:00:00.000Z");
      expect(isWeekend(saturday, "Asia/Kolkata")).toBe(true);
    });

    it("identifies Sunday", () => {
      // 2026-11-01 is Sunday
      const sunday = new Date("2026-11-01T06:00:00.000Z");
      expect(isWeekend(sunday, "Asia/Kolkata")).toBe(true);
    });

    it("identifies Monday as working day", () => {
      // 2026-10-26 is Monday
      const monday = new Date("2026-10-26T06:00:00.000Z");
      expect(isWeekend(monday, "Asia/Kolkata")).toBe(false);
    });
  });

  describe("isBusinessHour", () => {
    it("returns true during business hours on a weekday", () => {
      // Monday 10:00 IST = 2026-10-26T04:30:00.000Z
      const date = new Date("2026-10-26T04:30:00.000Z");
      expect(isBusinessHour(date, testCalendarConfig())).toBe(true);
    });

    it("returns false before business hours", () => {
      // Monday 08:00 IST = 2026-10-26T02:30:00.000Z
      const date = new Date("2026-10-26T02:30:00.000Z");
      expect(isBusinessHour(date, testCalendarConfig())).toBe(false);
    });

    it("returns false after business hours", () => {
      // Monday 19:00 IST = 2026-10-26T13:30:00.000Z
      const date = new Date("2026-10-26T13:30:00.000Z");
      expect(isBusinessHour(date, testCalendarConfig())).toBe(false);
    });

    it("returns false on Saturday", () => {
      const date = new Date("2026-10-31T06:00:00.000Z");
      expect(isBusinessHour(date, testCalendarConfig())).toBe(false);
    });
  });

  describe("nextBusinessStart", () => {
    it("returns same day start when before business hours", () => {
      // Monday 07:00 IST
      const date = new Date("2026-10-26T01:30:00.000Z");
      const result = nextBusinessStart(date, testCalendarConfig());
      // Should be Monday 09:00 IST
      expect(toBusinessDateString(result, "Asia/Kolkata")).toBe("2026-10-26");
    });

    it("returns next day start when after business hours", () => {
      // Monday 20:00 IST
      const date = new Date("2026-10-26T14:30:00.000Z");
      const result = nextBusinessStart(date, testCalendarConfig());
      // Should be Tuesday 09:00 IST
      expect(toBusinessDateString(result, "Asia/Kolkata")).toBe("2026-10-27");
    });

    it("returns Monday when given a Saturday", () => {
      const saturday = new Date("2026-10-31T10:00:00.000Z");
      const result = nextBusinessStart(saturday, testCalendarConfig());
      // Should be Monday 2026-11-02
      expect(toBusinessDateString(result, "Asia/Kolkata")).toBe("2026-11-02");
    });
  });

  describe("calculateBusinessMinutes", () => {
    it("returns 0 when end <= start", () => {
      const start = new Date("2026-10-26T06:00:00.000Z");
      const end = new Date("2026-10-26T06:00:00.000Z");
      expect(calculateBusinessMinutes(start, end, testCalendarConfig())).toBe(0);
    });

    it("calculates minutes for a simple working day interval", () => {
      // Mon 09:00 IST to Mon 12:00 IST = 3 hours = 180 min
      const start = new Date("2026-10-26T03:30:00.000Z");
      const end = new Date("2026-10-26T06:30:00.000Z");
      const mins = calculateBusinessMinutes(start, end, testCalendarConfig());
      expect(mins).toBe(180);
    });

    it("skips non-business hours overnight", () => {
      // Mon 17:00 IST to Tue 10:00 IST
      // Mon: 17:00-18:00 = 60 min
      // Tue: 09:00-10:00 = 60 min
      // Total = 120 min
      const start = new Date("2026-10-26T11:30:00.000Z");
      const end = new Date("2026-10-27T04:30:00.000Z");
      const mins = calculateBusinessMinutes(start, end, testCalendarConfig());
      expect(mins).toBe(120);
    });

    it("skips weekends entirely", () => {
      // Fri 17:00 IST to Mon 10:00 IST
      // Fri: 17:00-18:00 = 60 min
      // Mon: 09:00-10:00 = 60 min
      // Total = 120 min
      const start = new Date("2026-10-30T11:30:00.000Z");
      const end = new Date("2026-11-02T04:30:00.000Z");
      const mins = calculateBusinessMinutes(start, end, testCalendarConfig());
      expect(mins).toBe(120);
    });
  });

  describe("addBusinessMinutes", () => {
    it("adds business minutes within same day", () => {
      // Mon 09:00 IST + 120 min = Mon 11:00 IST
      const start = new Date("2026-10-26T03:30:00.000Z");
      const result = addBusinessMinutes(start, 120, testCalendarConfig());
      expect(toBusinessDateString(result, "Asia/Kolkata")).toBe("2026-10-26");
    });

    it("crosses to next day when exceeding business hours", () => {
      // Mon 15:00 IST + 240 min (4 hours)
      // Mon: 15:00-18:00 = 180 min
      // Tue: 09:00-10:00 = 60 min -> Tue 10:00 IST
      const start = new Date("2026-10-26T09:30:00.000Z");
      const result = addBusinessMinutes(start, 240, testCalendarConfig());
      expect(toBusinessDateString(result, "Asia/Kolkata")).toBe("2026-10-27");
    });
  });
});

// ============================================================================
// SLA Calculator Tests
// ============================================================================

describe("SlaCalculator", () => {
  describe("M1: SLA Targets by Priority", () => {
    it("P1 has 240 minute target", () => {
      expect(DEFAULT_SLA_TARGETS.P1).toBe(240);
    });

    it("P2 has 480 minute target", () => {
      expect(DEFAULT_SLA_TARGETS.P2).toBe(480);
    });

    it("P3 has 1440 minute target", () => {
      expect(DEFAULT_SLA_TARGETS.P3).toBe(1440);
    });

    it("P4 has 4320 minute target", () => {
      expect(DEFAULT_SLA_TARGETS.P4).toBe(4320);
    });
  });

  describe("M2: Business Calendar", () => {
    it("simple P1 ticket completed within SLA (3 business hours)", () => {
      // Mon 09:00 to Mon 12:00 = 180 business min (< 240)
      const history = [
        s("2026-10-26T03:30:00.000Z", "OPEN", "created"),
        s("2026-10-26T03:35:00.000Z", "IN_PROGRESS", "started"),
        s("2026-10-26T06:30:00.000Z", "RESOLVED", "done"),
      ];
      const result = calculateSla(history, "P1", "RESOLVED", new Date("2026-10-26T06:30:00.000Z"),
        new Date("2026-10-26T06:30:00.000Z"), undefined, testCalendarConfig());

      // No hold intervals, so 09:00-12:00 = 180 minutes
      expect(result.elapsedBusinessMinutes).toBe(180);
      expect(result.isBreached).toBe(false);
      expect(result.slaStatus).toBe("RESOLVED");
    });

    it("P1 ticket breached (resolved after 5 business hours)", () => {
      // Mon 09:00 to Mon 15:00, no hold
      // 09:00-15:00 = 6 hours = 360 min > 240 target
      const history = [
        s("2026-10-26T03:30:00.000Z", "OPEN", "created"),
        s("2026-10-26T10:00:00.000Z", "RESOLVED", "done"),
      ];
      const now = new Date("2026-10-26T10:00:00.000Z");
      const result = calculateSla(history, "P1", "RESOLVED", now, now, undefined, testCalendarConfig());

      // 09:00-15:30 IST = 6.5 hours = 390 min
      // Actually 09:00 to 15:30 = 6.5h = 390 min
      expect(result.elapsedBusinessMinutes).toBeGreaterThan(300);
      expect(result.isBreached).toBe(true);
      expect(result.breachMinutes).toBeGreaterThan(0);
    });

    it("ticket created before business hours starts at 09:00", () => {
      // Mon 07:00 IST creation -> clock starts at 09:00
      const history = [
        s("2026-10-26T01:30:00.000Z", "OPEN", "created"),
        s("2026-10-26T04:30:00.000Z", "RESOLVED", "done"),
      ];
      const now = new Date("2026-10-26T04:30:00.000Z");
      const result = calculateSla(history, "P1", "RESOLVED", now, now, undefined, testCalendarConfig());

      // Resolution at 10:00 IST, so 09:00-10:00 = 60 min
      expect(result.elapsedBusinessMinutes).toBe(60);
      expect(result.isBreached).toBe(false);
    });

    it("ticket created exactly at 09:00 works correctly", () => {
      const history = [
        s("2026-10-26T03:30:00.000Z", "OPEN", "created"),
        s("2026-10-26T04:30:00.000Z", "RESOLVED", "done"),
      ];
      const now = new Date("2026-10-26T04:30:00.000Z");
      const result = calculateSla(history, "P1", "RESOLVED", now, now, undefined, testCalendarConfig());

      // 09:00-10:00 = 60 min
      expect(result.elapsedBusinessMinutes).toBe(60);
    });

    it("ticket created at 18:00 or later starts next business day", () => {
      // Mon 18:00 IST -> next business start is Tue 09:00
      const history = [
        s("2026-10-26T12:30:00.000Z", "OPEN", "created"),
        s("2026-10-27T04:30:00.000Z", "RESOLVED", "done"),
      ];
      const now = new Date("2026-10-27T04:30:00.000Z");
      const result = calculateSla(history, "P1", "RESOLVED", now, now, undefined, testCalendarConfig());

      // Tue 09:00-10:00 = 60 min
      expect(result.elapsedBusinessMinutes).toBe(60);
    });

    it("ticket crossing Friday to Monday only counts Friday and Monday hours", () => {
      // Fri 16:00 to Mon 10:00
      // Fri 16:00-18:00 = 120 min; Mon 09:00-10:00 = 60 min; total = 180 min
      const history = [
        s("2026-10-30T10:30:00.000Z", "OPEN", "created"),
        s("2026-11-02T04:30:00.000Z", "RESOLVED", "done"),
      ];
      const now = new Date("2026-11-02T04:30:00.000Z");
      const result = calculateSla(history, "P1", "RESOLVED", now, now, undefined, testCalendarConfig());

      expect(result.elapsedBusinessMinutes).toBe(180);
      expect(result.isBreached).toBe(false); // 180 < 240
    });
  });

  describe("M3: ON_HOLD pauses SLA", () => {
    it("single ON_HOLD interval is excluded", () => {
      // Mon 09:00 OPEN -> 09:30 ON_HOLD -> 11:00 IN_PROGRESS -> 12:00 RESOLVED
      // Running: 09:00-09:30 (30 min) + 11:00-12:00 (60 min) = 90 min
      const history = [
        s("2026-10-26T03:30:00.000Z", "OPEN", "created"),
        s("2026-10-26T04:00:00.000Z", "ON_HOLD", "waiting"),
        s("2026-10-26T05:30:00.000Z", "IN_PROGRESS", "resumed"),
        s("2026-10-26T06:30:00.000Z", "RESOLVED", "done"),
      ];
      const now = new Date("2026-10-26T06:30:00.000Z");
      const result = calculateSla(history, "P1", "RESOLVED", now, now, undefined, testCalendarConfig());

      expect(result.elapsedBusinessMinutes).toBe(90);
      expect(result.isBreached).toBe(false);
    });

    it("multiple ON_HOLD intervals are excluded", () => {
      // 09:00 OPEN -> 09:30 ON_HOLD (hold 1) -> 11:00 IN_PROGRESS -> 11:30 ON_HOLD (hold 2) -> 12:30 IN_PROGRESS -> 13:30 RESOLVED
      // Active: 09:00-09:30 (30) + 11:00-11:30 (30) + 12:30-13:30 (60) = 120 min
      const history = [
        s("2026-10-26T03:30:00.000Z", "OPEN", "created"),
        s("2026-10-26T04:00:00.000Z", "ON_HOLD", "hold 1"),
        s("2026-10-26T05:30:00.000Z", "IN_PROGRESS", "resume 1"),
        s("2026-10-26T06:00:00.000Z", "ON_HOLD", "hold 2"),
        s("2026-10-26T07:00:00.000Z", "IN_PROGRESS", "resume 2"),
        s("2026-10-26T08:00:00.000Z", "RESOLVED", "done"),
      ];
      const now = new Date("2026-10-26T08:00:00.000Z");
      const result = calculateSla(history, "P1", "RESOLVED", now, now, undefined, testCalendarConfig());

      expect(result.elapsedBusinessMinutes).toBe(120);
    });

    it("ticket currently ON_HOLD shows PAUSED status", () => {
      const history = [
        s("2026-10-26T03:30:00.000Z", "OPEN", "created"),
        s("2026-10-26T04:30:00.000Z", "ON_HOLD", "waiting"),
      ];
      const now = new Date("2026-10-26T05:00:00.000Z");
      const result = calculateSla(history, "P1", "ON_HOLD", null, now, undefined, testCalendarConfig());

      expect(result.slaStatus).toBe("PAUSED");
      expect(result.isProvisional).toBe(true);
      // Elapsed: 09:00-10:00 = 60 min
      expect(result.elapsedBusinessMinutes).toBe(60);
    });

    it("ticket resolved while on hold is handled", () => {
      const history = [
        s("2026-10-26T03:30:00.000Z", "OPEN", "created"),
        s("2026-10-26T04:30:00.000Z", "ON_HOLD", "waiting"),
        s("2026-10-26T06:30:00.000Z", "RESOLVED", "resolved on hold"),
      ];
      const now = new Date("2026-10-26T06:30:00.000Z");
      const result = calculateSla(history, "P1", "RESOLVED", now, now, undefined, testCalendarConfig());

      // Elapsed: 09:00-10:00 = 60 min (hold excluded)
      expect(result.elapsedBusinessMinutes).toBe(60);
      expect(result.slaStatus).toBe("RESOLVED");
    });
  });

  describe("M4: SLA Status Calculation", () => {
    it("ON_TRACK when well within SLA", () => {
      const history = [
        s("2026-10-26T03:30:00.000Z", "OPEN", "created"),
      ];
      const now = new Date("2026-10-26T04:30:00.000Z"); // 10:00 IST = 1 hour elapsed
      const result = calculateSla(history, "P3", "OPEN", null, now, undefined, testCalendarConfig());

      // 1 hour = 60 min out of 1440 -> ON_TRACK
      expect(result.slaStatus).toBe("ON_TRACK");
    });

    it("AT_RISK when within 25% of SLA target remaining", () => {
      const history = [
        s("2026-10-26T03:30:00.000Z", "OPEN", "created"),
      ];
      // For P1, 25% of 240 = 60. AT_RISK when remaining <= 60, i.e. elapsed >= 180
      // 09:00 + 185 min = 12:05 IST -> elapsed ~185 min, remaining ~55 min (within 25%)
      const now = new Date("2026-10-26T06:35:00.000Z"); // ~12:05 IST
      const result = calculateSla(history, "P1", "OPEN", null, now, undefined, testCalendarConfig());
      expect(result.slaStatus).toBe("AT_RISK");
    });

    it("BREACHED when elapsed exceeds target", () => {
      const history = [
        s("2026-10-26T03:30:00.000Z", "OPEN", "created"),
      ];
      const now = new Date("2026-10-27T04:00:00.000Z"); // Next day
      const result = calculateSla(history, "P1", "OPEN", null, now, undefined, testCalendarConfig());

      expect(result.slaStatus).toBe("BREACHED");
      expect(result.isBreached).toBe(true);
    });

    it("resolved exactly at deadline is not breached", () => {
      const history = [
        s("2026-10-26T03:30:00.000Z", "OPEN", "created"),
        // 09:00 + 240 business min = 13:00 same day. Resolved at 13:00.
        s("2026-10-26T07:30:00.000Z", "RESOLVED", "done"),
      ];
      const now = new Date("2026-10-26T07:30:00.000Z");
      const result = calculateSla(history, "P1", "RESOLVED", now, now, undefined, testCalendarConfig());

      // 09:00-13:00 = 240 min exactly
      expect(result.elapsedBusinessMinutes).toBe(240);
      expect(result.isBreached).toBe(false);
    });

    it("never reports negative breach minutes", () => {
      const history = [
        s("2026-10-26T03:30:00.000Z", "OPEN", "created"),
        s("2026-10-26T04:30:00.000Z", "RESOLVED", "done"),
      ];
      const now = new Date("2026-10-26T04:30:00.000Z");
      const result = calculateSla(history, "P1", "RESOLVED", now, now, undefined, testCalendarConfig());

      expect(result.breachMinutes).toBeGreaterThanOrEqual(0);
    });
  });

  describe("Edge cases", () => {
    it("empty status history returns safe defaults", () => {
      const result = calculateSla([], "P1", "OPEN", null);
      expect(result.elapsedBusinessMinutes).toBe(0);
      expect(result.isBreached).toBe(false);
      expect(result.slaStatus).toBe("ON_TRACK");
    });

    it("invalid priority returns safe defaults", () => {
      const history = [s("2026-10-26T03:30:00.000Z", "OPEN", "created")];
      const result = calculateSla(history, "INVALID" as any, "OPEN", null);
      expect(result.elapsedBusinessMinutes).toBe(0);
    });

    it("zero-duration ticket (created and resolved same instant)", () => {
      const history = [
        s("2026-10-26T03:30:00.000Z", "OPEN", "created"),
        s("2026-10-26T03:30:00.000Z", "RESOLVED", "done"),
      ];
      const now = new Date("2026-10-26T03:30:00.000Z");
      const result = calculateSla(history, "P1", "RESOLVED", now, now, undefined, testCalendarConfig());

      expect(result.elapsedBusinessMinutes).toBe(0);
      expect(result.isBreached).toBe(false);
    });

    it("unresolved ticket calculates at current time", () => {
      const history = [s("2026-10-26T03:30:00.000Z", "OPEN", "created")];
      // 11:00 IST = 2 hours elapsed
      const now = new Date("2026-10-26T05:30:00.000Z");
      const result = calculateSla(history, "P1", "OPEN", null, now, undefined, testCalendarConfig());

      // 09:00-11:00 = 120 min
      expect(result.elapsedBusinessMinutes).toBe(120);
      // remaining: 240 - 120 = 120
      expect(result.remainingBusinessMinutes).toBe(120);
    });

    it("custom policies override defaults", () => {
      const history = [
        s("2026-10-26T03:30:00.000Z", "OPEN", "created"),
        s("2026-10-26T04:30:00.000Z", "RESOLVED", "done"),
      ];
      const now = new Date("2026-10-26T04:30:00.000Z");
      const result = calculateSla(history, "P1", "RESOLVED", now, now,
        { P1: 60, P2: 480, P3: 1440, P4: 4320 },
        testCalendarConfig());

      // 60 min elapsed, target 60
      expect(result.elapsedBusinessMinutes).toBe(60);
      expect(result.slaTargetMinutes).toBe(60);
      // Resolved exactly at deadline = not breached
      expect(result.isBreached).toBe(false);
    });

    it("holiday exclusion works", () => {
      // 2026-10-27 is a regular Tuesday. Let's make it a holiday.
      const holidayConfig: BusinessCalendarConfig = {
        timezone: "Asia/Kolkata",
        businessStartHour: 9,
        businessEndHour: 18,
        holidays: [new Date("2026-10-27T00:00:00.000Z")],
      };

      const history = [
        s("2026-10-26T12:30:00.000Z", "OPEN", "created"), // Mon 18:00 IST
        s("2026-10-28T03:30:00.000Z", "RESOLVED", "done"), // Wed 09:00 IST
      ];
      const now = new Date("2026-10-28T03:30:00.000Z");
      const result = calculateSla(history, "P1", "RESOLVED", now, now, undefined, holidayConfig);

      // Tue is a holiday -> no business hours
      // Mon 18:00 -> next business start = Wed 09:00
      // Wed 09:00-09:00 = 0 min
      expect(result.elapsedBusinessMinutes).toBe(0);
    });
  });

  describe("Status transitions", () => {
    it("allows OPEN -> IN_PROGRESS", () => {
      expect(isValidTransition("OPEN", "IN_PROGRESS")).toBe(true);
    });

    it("allows OPEN -> ON_HOLD", () => {
      expect(isValidTransition("OPEN", "ON_HOLD")).toBe(true);
    });

    it("allows ON_HOLD -> IN_PROGRESS", () => {
      expect(isValidTransition("ON_HOLD", "IN_PROGRESS")).toBe(true);
    });

    it("disallows RESOLVED -> anything", () => {
      expect(isValidTransition("RESOLVED", "OPEN")).toBe(false);
      expect(isValidTransition("RESOLVED", "IN_PROGRESS")).toBe(false);
      expect(isValidTransition("RESOLVED", "ON_HOLD")).toBe(false);
    });
  });
});