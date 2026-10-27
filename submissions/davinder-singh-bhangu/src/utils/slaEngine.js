/**
 * SLA Engine — computes elapsed business minutes, breach status, and due-by time.
 *
 * Rules (M1–M4):
 *  - M1: SLA targets by priority (P1=4h, P2=8h, P3=24h, P4=72h), business hours only.
 *  - M2: Holidays are excluded from SLA time.
 *  - M3: ON_HOLD status pauses the SLA clock.
 *  - M4: Per ticket — elapsed business minutes, due-by time, breach yes/no, breach minutes.
 */

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

/** Parse "HH:mm" to minutes-from-midnight. */
function timeToMinutes(timeStr) {
  const [h, m] = timeStr.split(':').map(Number);
  return h * 60 + m;
}

/** Format a Date as YYYY-MM-DD (local). */
function toDateKey(d) {
  return d.toISOString().slice(0, 10);
}

/** True if `date` is a holiday according to the holidays array. */
function isHoliday(date, holidaySet) {
  return holidaySet.has(toDateKey(date));
}

/** True if `date` is a business day (Mon–Fri, index 1–5, and not a holiday). */
function isBusinessDay(date, holidaySet) {
  const dow = date.getDay();
  return dow >= 1 && dow <= 5 && !isHoliday(date, holidaySet);
}

/**
 * Returns the **next** business-day start (09:00) on or after `date`.
 * If `date` is already at or before 09:00 on a business day, returns that day at 09:00.
 */
function nextBusinessStart(date, holidaySet, bhStart) {
  const d = new Date(date);
  d.setSeconds(0, 0);
  // If time is before business start, clamp to start of same day
  if (d.getHours() * 60 + d.getMinutes() < bhStart) {
    d.setHours(Math.floor(bhStart / 60), bhStart % 60, 0, 0);
  }
  while (!isBusinessDay(d, holidaySet)) {
    d.setDate(d.getDate() + 1);
    d.setHours(Math.floor(bhStart / 60), bhStart % 60, 0, 0);
  }
  return d;
}

// ---------------------------------------------------------------------------
// core SLA calculation
// ---------------------------------------------------------------------------

/**
 * Compute the number of **business minutes** that elapsed between two dates,
 * given a business-hours window and a set of holidays.
 *
 * The clock ONLY ticks Mon–Fri 09:00–18:00 (configurable), excluding holidays.
 */
function businessMinutesBetween(start, end, bhStartMin, bhEndMin, holidaySet) {
  if (start >= end) return 0;

  let total = 0;
  let cursor = new Date(start);

  while (cursor < end) {
    // Skip non-business days
    if (!isBusinessDay(cursor, holidaySet)) {
      cursor.setDate(cursor.getDate() + 1);
      cursor.setHours(0, 0, 0, 0);
      continue;
    }

    const dayStart = new Date(cursor);
    dayStart.setHours(Math.floor(bhStartMin / 60), bhStartMin % 60, 0, 0);

    const dayEnd = new Date(cursor);
    dayEnd.setHours(Math.floor(bhEndMin / 60), bhEndMin % 60, 0, 0);

    // Effective start for this day
    const effStart = cursor < dayStart ? dayStart : cursor;
    // Effective end for this day (cap to dayEnd and overall end)
    const effEnd = end < dayEnd ? end : dayEnd;

    if (effStart < effEnd) {
      total += (effEnd - effStart) / 60000; // ms → minutes
    }

    // Advance to next day
    cursor.setDate(cursor.getDate() + 1);
    cursor.setHours(0, 0, 0, 0);
  }

  return Math.round(total);
}

/**
 * Given a ticket, compute:
 *   - dueBy:      Date the ticket must be resolved (createdAt + SLA target in biz minutes)
 *   - elapsedMin: business minutes between createdAt and resolvedAt (or now)
 *   - breach:     true if elapsed > target
 *   - breachMin:  elapsed – target (or 0 if not breached)
 */
export function computeSLA(ticket, slaPolicy, holidays) {
  const holidaySet = new Set(holidays.map(h => h.date));

  const bhStart = slaPolicy.businessHours.start;
  const bhEnd = slaPolicy.businessHours.end;
  const bhStartMin = timeToMinutes(bhStart);
  const bhEndMin = timeToMinutes(bhEnd);

  const targetHours = slaPolicy.slaTargets[ticket.priority] || 0;
  const targetMin = targetHours * 60;

  const createdAt = new Date(ticket.createdAt);
  const resolvedAt = ticket.resolvedAt ? new Date(ticket.resolvedAt) : new Date();

  // --- M3: build active intervals (exclude ON_HOLD periods) ---
  const intervals = buildActiveIntervals(ticket, resolvedAt);

  // Sum business minutes across all active intervals
  let elapsedMin = 0;
  for (const [segStart, segEnd] of intervals) {
    elapsedMin += businessMinutesBetween(segStart, segEnd, bhStartMin, bhEndMin, holidaySet);
  }

  // --- due-by: createdAt + target minutes in business time ---
  const dueBy = addBusinessMinutes(new Date(createdAt), targetMin, bhStartMin, bhEndMin, holidaySet);

  const breach = elapsedMin > targetMin;
  const breachMin = breach ? elapsedMin - targetMin : 0;

  return {
    elapsedMin,
    dueBy,
    breach,
    breachMin,
    targetMin,
  };
}

/**
 * Build contiguous active-time intervals for a ticket, splitting at each
 * ON_HOLD boundary.
 */
function buildActiveIntervals(ticket, resolvedAt) {
  const history = ticket.statusHistory || [];
  if (history.length === 0) {
    return [[new Date(ticket.createdAt), resolvedAt]];
  }

  const intervals = [];
  let activeSince = null;

  for (let i = 0; i < history.length; i++) {
    const entry = history[i];
    const ts = new Date(entry.from);

    if (entry.status === 'ON_HOLD') {
      if (activeSince !== null) {
        intervals.push([activeSince, ts]);
        activeSince = null;
      }
    } else {
      // OPEN, IN_PROGRESS, RESOLVED — these are "active"
      if (activeSince === null) {
        activeSince = ts;
      }
    }
  }

  // Close the last interval if still active
  if (activeSince !== null) {
    intervals.push([activeSince, resolvedAt]);
  }

  return intervals;
}

/**
 * Add `minutes` of business time to a start date, returning the due-by Date.
 */
export function addBusinessMinutes(start, minutes, bhStartMin, bhEndMin, holidaySet) {
  let remaining = minutes;
  let cursor = nextBusinessStart(start, holidaySet, bhStartMin);

  while (remaining > 0) {
    const dayStart = new Date(cursor);
    dayStart.setHours(Math.floor(bhStartMin / 60), bhStartMin % 60, 0, 0);
    const dayEnd = new Date(cursor);
    dayEnd.setHours(Math.floor(bhEndMin / 60), bhEndMin % 60, 0, 0);

    const bhMinToday = (dayEnd - dayStart) / 60000;

    const usedToday = Math.min(remaining, bhMinToday);
    remaining -= usedToday;
    cursor = new Date(dayStart.getTime() + usedToday * 60000);

    if (remaining > 0) {
      cursor.setDate(cursor.getDate() + 1);
      cursor = nextBusinessStart(cursor, holidaySet, bhStartMin);
    }
  }

  return cursor;
}

// ---------------------------------------------------------------------------
// summary (M5)
// ---------------------------------------------------------------------------

/**
 * Build summary: breach % per priority and per assignee group.
 */
export function computeSummary(results) {
  const byPriority = {};
  const byGroup = {};

  for (const r of results) {
    // by priority
    if (!byPriority[r.priority]) {
      byPriority[r.priority] = { total: 0, breached: 0 };
    }
    byPriority[r.priority].total++;
    if (r.breach) byPriority[r.priority].breached++;

    // by group
    if (!byGroup[r.assigneeGroup]) {
      byGroup[r.assigneeGroup] = { total: 0, breached: 0 };
    }
    byGroup[r.assigneeGroup].total++;
    if (r.breach) byGroup[r.assigneeGroup].breached++;
  }

  const formatPct = (breached, total) =>
    total > 0 ? Math.round((breached / total) * 1000) / 10 : 0;

  const prioritySummary = Object.entries(byPriority).map(([priority, data]) => ({
    priority,
    total: data.total,
    breached: data.breached,
    breachPct: formatPct(data.breached, data.total),
  }));

  const groupSummary = Object.entries(byGroup).map(([group, data]) => ({
    group,
    total: data.total,
    breached: data.breached,
    breachPct: formatPct(data.breached, data.total),
  }));

  return { prioritySummary, groupSummary };
}