/**
 * KnoxFlow SLA Tracker Agent
 * Calculates aging, remaining SLA runway, breach status, and turnaround metrics.
 */

function formatDuration(hours) {
  if (hours < 0) hours = 0;
  const totalMinutes = Math.round(hours * 60);
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  if (h === 0) return `${m}m`;
  return `${h}h ${m}m`;
}

function calculateSLA(email, referenceTime = new Date()) {
  const receivedAt = new Date(email.received_at);
  const now = new Date(referenceTime);

  // Informational emails do not have SLA requirements
  if (email.category === 'General Information') {
    return {
      status: 'Informational',
      status_label: 'N/A (Informational)',
      badge_color: 'gray',
      aging_hours: (now - receivedAt) / (1000 * 60 * 60),
      aging_formatted: formatDuration((now - receivedAt) / (1000 * 60 * 60)),
      time_remaining_formatted: 'No SLA required',
      is_breached: false
    };
  }

  const targetHours = email.sla_target_hours || 24;

  if (email.is_responded && email.response_info) {
    const respondedAt = new Date(email.response_info.responded_at || now);
    const turnaroundHours = email.response_info.response_time_hours || ((respondedAt - receivedAt) / (1000 * 60 * 60));
    const metSla = turnaroundHours <= targetHours;

    return {
      status: metSla ? 'Resolved Within SLA' : 'Resolved Past SLA',
      status_label: metSla ? 'Met SLA' : 'Breached SLA',
      badge_color: metSla ? 'green' : 'amber',
      aging_hours: turnaroundHours,
      aging_formatted: formatDuration(turnaroundHours),
      turnaround_hours: turnaroundHours,
      turnaround_formatted: formatDuration(turnaroundHours),
      is_breached: !metSla
    };
  }

  // Pending email calculation
  const elapsedHours = (now - receivedAt) / (1000 * 60 * 60);
  const remainingHours = targetHours - elapsedHours;
  const breachRatio = elapsedHours / targetHours;

  let status = 'Within SLA';
  let badge_color = 'green';
  let is_breached = false;

  if (elapsedHours > targetHours) {
    status = 'Breached SLA';
    badge_color = 'red';
    is_breached = true;
  } else if (breachRatio >= 0.75) {
    status = 'Approaching Breach';
    badge_color = 'amber';
  }

  return {
    status,
    status_label: status,
    badge_color,
    aging_hours: elapsedHours,
    aging_formatted: formatDuration(elapsedHours),
    remaining_hours: remainingHours,
    time_remaining_formatted: remainingHours > 0 ? `${formatDuration(remainingHours)} left` : `${formatDuration(Math.abs(remainingHours))} overdue`,
    is_breached
  };
}

module.exports = { calculateSLA, formatDuration };
