package sla;

import java.time.*;
import java.util.*;

/**
 * Deterministic business-hours calendar.
 * Business hours: M-F [09:00, 18:00) in a configurable timezone.
 * Excludes holidays and ON_HOLD intervals.
 * All timestamps are {@link ZonedDateTime} with a consistent zone.
 */
public class BusinessCalendar {

    private final ZoneId zone;
    private final Set<LocalDate> holidays;
    private static final LocalTime OPEN = LocalTime.of(9, 0);
    private static final LocalTime CLOSE = LocalTime.of(18, 0);
    private static final int DAY_MINUTES = 9 * 60; // 540

    public BusinessCalendar(ZoneId zone, Set<LocalDate> holidays) {
        this.zone = Objects.requireNonNull(zone);
        this.holidays = Set.copyOf(holidays);
    }

    /** Is the given date a working day? */
    public boolean isWorkday(LocalDate d) {
        return d.getDayOfWeek().getValue() <= 5 && !holidays.contains(d);
    }

    /** Next workday strictly after {@code d}. */
    public LocalDate nextWorkday(LocalDate d) {
        do { d = d.plusDays(1); } while (!isWorkday(d));
        return d;
    }

    /** Previous workday strictly before {@code d}. */
    public LocalDate prevWorkday(LocalDate d) {
        do { d = d.minusDays(1); } while (!isWorkday(d));
        return d;
    }

    public ZonedDateTime dayStart(LocalDate d) {
        return ZonedDateTime.of(d, OPEN, zone);
    }

    public ZonedDateTime dayEnd(LocalDate d) {
        return ZonedDateTime.of(d, CLOSE, zone);
    }

    // ── Active business minutes between two instants ──────────────────────

    /**
     * Business minutes in [{@code start}, {@code end}) excluding hold intervals.
     * Holds are treated as closed-exclusive: an instant on a hold boundary
     * does NOT count as active time.
     */
    public long activeMinutes(ZonedDateTime start, ZonedDateTime end,
                              List<HoldInterval> holds) {
        if (!start.isBefore(end)) return 0;
        var merged = mergeHolds(holds);
        var cursor = start;
        long total = 0;
        for (var h : merged) {
            if (!h.end().isAfter(cursor)) continue;   // entirely before cursor
            if (!h.start().isBefore(end)) break;       // entirely after range
            total += businessMinutesBetween(cursor, minDateTime(h.start(), end));
            cursor = maxDateTime(cursor, h.end());
            if (!cursor.isBefore(end)) break;
        }
        if (cursor.isBefore(end))
            total += businessMinutesBetween(cursor, end);
        return total;
    }

    private long businessMinutesBetween(ZonedDateTime a, ZonedDateTime b) {
        if (!a.isBefore(b)) return 0;
        var al = a.withZoneSameInstant(zone);
        var bl = b.withZoneSameInstant(zone);
        LocalDate ad = al.toLocalDate(), bd = bl.toLocalDate();
        if (ad.equals(bd)) return sameDayMinutes(al, bl);

        long total = sameDayMinutes(al, dayEnd(ad));
        LocalDate d = nextWorkday(ad);
        while (d.isBefore(bd)) {
            if (isWorkday(d)) total += DAY_MINUTES;
            d = d.plusDays(1);
        }
        if (isWorkday(bd)) total += sameDayMinutes(dayStart(bd), bl);
        return total;
    }

    private long sameDayMinutes(ZonedDateTime al, ZonedDateTime bl) {
        if (!isWorkday(al.toLocalDate())) return 0;
        var effStart = maxDateTime(al, dayStart(al.toLocalDate()));
        var effEnd = minDateTime(bl, dayEnd(bl.toLocalDate()));
        return effStart.isBefore(effEnd) ? Duration.between(effStart, effEnd).toMinutes() : 0;
    }

    // ── Advance through business time ─────────────────────────────────────

    /**
     * Advance {@code start} by exactly {@code businessMinutes} of active clock time,
     * skipping weekends, holidays, and hold intervals.
     * Due-by calculation — deterministic integer-minute arithmetic.
     */
    public ZonedDateTime advance(ZonedDateTime start, long businessMinutes,
                                  List<HoldInterval> holds) {
        var cursor = start;
        long remaining = businessMinutes;
        var merged = mergeHolds(holds);
        int h = 0;

        while (remaining > 0) {
            cursor = skipInactiveForward(cursor);
            while (h < merged.size() && !merged.get(h).end().isAfter(cursor)) h++;

            ZonedDateTime nextInactive = nextInactiveStart(cursor, merged, h);
            if (nextInactive == null) {
                return advanceBusiness(cursor, remaining);
            }
            long avail = businessMinutesBetween(cursor, nextInactive);
            if (avail >= remaining) {
                return advanceBusiness(cursor, remaining);
            }
            remaining -= avail;
            cursor = nextInactive;
            if (h < merged.size() && !merged.get(h).start().isAfter(cursor)
                    && merged.get(h).end().isAfter(cursor)) {
                cursor = merged.get(h).end();
                h++;
            }
        }
        return cursor;
    }

    /** Due-by: shorthand for {@code advance(created, slaMinutes, holds)}. */
    public ZonedDateTime dueBy(ZonedDateTime created, long slaMinutes,
                                List<HoldInterval> holds) {
        return advance(created, slaMinutes, holds);
    }

    // ── Internal helpers ──────────────────────────────────────────────────

    private ZonedDateTime advanceBusiness(ZonedDateTime start, long minutes) {
        if (minutes <= 0) return start;
        var s = skipInactiveForward(start);
        var loc = s.withZoneSameInstant(zone);
        long rem = minutes;

        if (isWorkday(loc.toLocalDate()) && loc.toLocalTime().isBefore(CLOSE)) {
            var eod = dayEnd(loc.toLocalDate());
            long avail = Duration.between(loc, eod).toMinutes();
            if (avail >= rem) return s.plusMinutes(rem);
            rem -= avail;
        }
        LocalDate d = nextWorkday(loc.toLocalDate());
        while (isWorkday(d)) {
            if (rem <= DAY_MINUTES) return dayStart(d).plusMinutes(rem);
            rem -= DAY_MINUTES;
            d = nextWorkday(d);
        }
        throw new IllegalStateException("Infinite loop in advanceBusiness");
    }

    private ZonedDateTime skipInactiveForward(ZonedDateTime dt) {
        var loc = dt.withZoneSameInstant(zone);
        boolean changed;
        do {
            changed = false;
            if (isWorkday(loc.toLocalDate()) && !loc.toLocalTime().isBefore(CLOSE)) {
                loc = dayStart(nextWorkday(loc.toLocalDate()));
                changed = true;
            } else if (!isWorkday(loc.toLocalDate())) {
                loc = dayStart(nextWorkday(loc.toLocalDate()));
                changed = true;
            } else if (loc.toLocalTime().isBefore(OPEN)) {
                loc = dayStart(loc.toLocalDate());
                changed = true;
            }
        } while (changed);
        return loc;
    }

    private ZonedDateTime nextInactiveStart(ZonedDateTime dt,
                                             List<HoldInterval> merged, int hi) {
        var loc = dt.withZoneSameInstant(zone);
        ZonedDateTime best = null;
        // next hold start
        while (hi < merged.size() && !merged.get(hi).start().isAfter(dt)) hi++;
        if (hi < merged.size()) best = merged.get(hi).start();
        // end of current business day
        if (isWorkday(loc.toLocalDate())) {
            var eod = dayEnd(loc.toLocalDate());
            if (eod.isAfter(dt)) best = (best == null) ? eod : minDateTime(best, eod);
        }
        return best;
    }

    static List<HoldInterval> mergeHolds(List<HoldInterval> intervals) {
        if (intervals.isEmpty()) return List.of();
        var sorted = new ArrayList<>(intervals);
        sorted.sort(Comparator.comparing(HoldInterval::start));
        List<HoldInterval> out = new ArrayList<>();
        for (var iv : sorted) {
            if (!iv.start().isBefore(iv.end())) continue;
            if (!out.isEmpty() && !out.getLast().end().isBefore(iv.start())) {
                out.set(out.size() - 1,
                    new HoldInterval(out.getLast().start(),
                        maxDateTime(out.getLast().end(), iv.end())));
            } else {
                out.add(iv);
            }
        }
        return out;
    }

    static ZonedDateTime minDateTime(ZonedDateTime a, ZonedDateTime b) {
        return a.isBefore(b) ? a : b;
    }

    static ZonedDateTime maxDateTime(ZonedDateTime a, ZonedDateTime b) {
        return a.isAfter(b) ? a : b;
    }

    /** Immutable hold interval. */
    public record HoldInterval(ZonedDateTime start, ZonedDateTime end) {}
}