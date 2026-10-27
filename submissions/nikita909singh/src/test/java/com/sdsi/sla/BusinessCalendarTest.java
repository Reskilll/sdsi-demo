package com.sdsi.sla;

import com.sdsi.sla.core.BusinessCalendar;
import com.sdsi.sla.core.ValidationException;
import com.sdsi.sla.model.SlaPolicy;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.time.DayOfWeek;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZoneId;
import java.util.EnumSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

/** 2026-10-01 is a Thursday; 2026-10-02 (Friday) is a holiday in these tests. */
class BusinessCalendarTest {

    private static final ZoneId IST = ZoneId.of("Asia/Kolkata");
    private final BusinessCalendar cal = new BusinessCalendar(SlaPolicy.defaults(IST), Set.of(LocalDate.of(2026, 10, 2)));

    private static Instant t(String local) {
        return LocalDateTime.parse(local).atZone(IST).toInstant();
    }

    private long minutes(String from, String to) {
        return cal.businessSeconds(t(from), t(to)) / 60;
    }

    @ParameterizedTest(name = "{0} -> {1} = {2} min")
    @CsvSource({
            "2026-10-05T10:00, 2026-10-05T13:00, 180",   // same day
            "2026-10-05T07:00, 2026-10-05T10:00, 60",    // starts before opening
            "2026-10-05T17:00, 2026-10-05T22:00, 60",    // ends after closing
            "2026-10-05T19:00, 2026-10-06T08:00, 0",     // overnight, no business time
            "2026-10-05T17:00, 2026-10-06T10:00, 120",   // across a night
            "2026-10-09T17:00, 2026-10-12T10:00, 120",   // across a weekend
            "2026-10-01T17:00, 2026-10-05T10:00, 120",   // Thu -> Mon across holiday + weekend
            "2026-10-10T10:00, 2026-10-11T15:00, 0",     // entirely in a weekend
            "2026-10-02T10:00, 2026-10-02T15:00, 0",     // entirely on a holiday
            "2026-10-05T09:00, 2026-10-12T09:00, 2700",  // one full week = 5 x 540
            "2026-10-05T13:00, 2026-10-05T13:00, 0",     // empty interval
            "2026-10-05T13:00, 2026-10-05T12:00, 0",     // reversed interval
    })
    void businessMinutes(String from, String to, long expected) {
        assertEquals(expected, minutes(from, to));
    }

    @Test
    void secondsArePreserved() {
        assertEquals(90, cal.businessSeconds(t("2026-10-05T09:00:00"), t("2026-10-05T09:01:30")));
    }

    @ParameterizedTest(name = "{0} + {1} min = {2}")
    @CsvSource({
            "2026-10-05T10:00, 60,   2026-10-05T11:00",
            "2026-10-05T07:00, 60,   2026-10-05T10:00",  // starts counting at opening
            "2026-10-05T17:00, 60,   2026-10-05T18:00",  // runs out exactly at closing: 18:00, not next 09:00
            "2026-10-05T17:00, 61,   2026-10-06T09:01",
            "2026-10-09T17:00, 120,  2026-10-12T10:00",  // over a weekend
            "2026-10-01T17:00, 120,  2026-10-05T10:00",  // over holiday + weekend
            "2026-10-05T20:00, 0,    2026-10-05T20:00",  // zero minutes: unchanged
            "2026-10-05T09:00, 2700, 2026-10-09T18:00",  // a full working week
    })
    void addBusinessMinutes(String from, long mins, String expected) {
        assertEquals(t(expected), cal.addBusinessSeconds(t(from), mins * 60));
    }

    @Test
    void handlesDaylightSavingTime() {
        ZoneId ny = ZoneId.of("America/New_York");
        BusinessCalendar us = new BusinessCalendar(SlaPolicy.defaults(ny), Set.of());
        // DST began Sunday 2026-03-08. Fri 17:00 EST -> Mon 10:00 EDT is 2 business hours, not 1 or 3.
        Instant fri = LocalDateTime.parse("2026-03-06T17:00").atZone(ny).toInstant();
        Instant mon = LocalDateTime.parse("2026-03-09T10:00").atZone(ny).toInstant();
        assertEquals(120, us.businessSeconds(fri, mon) / 60);
        assertEquals(mon, us.addBusinessSeconds(fri, 120 * 60));
    }

    @Test
    void customWorkWeekAndHours() {
        SlaPolicy d = SlaPolicy.defaults(IST);
        SlaPolicy sixDay = new SlaPolicy(IST, EnumSet.range(DayOfWeek.MONDAY, DayOfWeek.SATURDAY),
                LocalTime.of(10, 0), LocalTime.of(14, 0), d.targets(), d.runningStatuses(), d.pausedStatuses(),
                d.stoppedStatuses(), d.atRiskFraction());
        BusinessCalendar c = new BusinessCalendar(sixDay, Set.of());
        assertEquals(240, c.businessSeconds(t("2026-10-10T00:00"), t("2026-10-11T23:00")) / 60); // Sat only
    }

    @Test
    void rejectsImpossibleCalendars() {
        SlaPolicy d = SlaPolicy.defaults(IST);
        assertThrows(ValidationException.class, () -> new BusinessCalendar(new SlaPolicy(IST, Set.of(),
                d.dayStart(), d.dayEnd(), d.targets(), d.runningStatuses(), d.pausedStatuses(), d.stoppedStatuses(), 0.25), Set.of()));
        assertThrows(ValidationException.class, () -> new BusinessCalendar(new SlaPolicy(IST, d.workDays(),
                LocalTime.of(18, 0), LocalTime.of(9, 0), d.targets(), d.runningStatuses(), d.pausedStatuses(), d.stoppedStatuses(), 0.25), Set.of()));
        assertThrows(IllegalArgumentException.class, () -> cal.addBusinessSeconds(t("2026-10-05T10:00"), -1));
    }
}
