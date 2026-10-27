/**
 * Format minutes to a human-readable duration string.
 */
export function formatDuration(minutes: number): string {
  if (minutes < 0) minutes = 0;
  const hours = Math.floor(minutes / 60);
  const mins = Math.round(minutes % 60);

  if (hours === 0) return `${mins}m`;
  if (mins === 0) return `${hours}h`;
  return `${hours}h ${mins}m`;
}

/**
 * Format minutes to a compact display.
 */
export function formatDurationCompact(minutes: number): string {
  if (minutes < 0) minutes = 0;
  const hours = Math.floor(minutes / 60);
  const mins = Math.round(minutes % 60);
  return `${hours}h${mins.toString().padStart(2, "0")}m`;
}

/**
 * Format a date to a readable string in the business timezone.
 */
export function formatDate(date: Date | string | null | undefined): string {
  if (!date) return "—";
  const d = typeof date === "string" ? new Date(date) : date;
  return d.toLocaleString("en-IN", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

/**
 * Format a date to a short date string.
 */
export function formatDateOnly(date: Date | string | null | undefined): string {
  if (!date) return "—";
  const d = typeof date === "string" ? new Date(date) : date;
  return d.toLocaleDateString("en-IN", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/**
 * Get a color class for a priority badge.
 */
export function priorityColor(priority: string): string {
  switch (priority) {
    case "P1":
      return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
    case "P2":
      return "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200";
    case "P3":
      return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
    case "P4":
      return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

/**
 * Get a color class for SLA status badge.
 */
export function slaStatusColor(slaStatus: string): string {
  switch (slaStatus) {
    case "ON_TRACK":
      return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
    case "AT_RISK":
      return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
    case "BREACHED":
      return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
    case "PAUSED":
      return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
    case "RESOLVED":
      return "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

/**
 * Get a color class for ticket status badge.
 */
export function statusColor(status: string): string {
  switch (status) {
    case "OPEN":
      return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
    case "IN_PROGRESS":
      return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200";
    case "ON_HOLD":
      return "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200";
    case "RESOLVED":
      return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
    default:
      return "bg-gray-100 text-gray-800";
  }
}