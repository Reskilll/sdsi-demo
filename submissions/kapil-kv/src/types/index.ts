export type Priority = "P1" | "P2" | "P3" | "P4";

export type TicketStatus = "OPEN" | "IN_PROGRESS" | "ON_HOLD" | "RESOLVED";

export type SlaStatus =
  | "ON_TRACK"
  | "AT_RISK"
  | "BREACHED"
  | "PAUSED"
  | "RESOLVED";

export interface StatusEvent {
  status: TicketStatus;
  timestamp: Date;
  reason?: string;
}

export interface SlaResult {
  elapsedBusinessMinutes: number;
  slaTargetMinutes: number;
  dueBy: Date | null;
  isBreached: boolean;
  breachMinutes: number;
  remainingBusinessMinutes: number;
  slaStatus: SlaStatus;
  /** True when the due date is provisional (ticket currently on hold). */
  isProvisional: boolean;
}

export interface BusinessCalendarConfig {
  timezone: string;
  businessStartHour: number;
  businessEndHour: number;
  /** Active holiday dates (as UTC Date objects normalized to the business timezone's date). */
  holidays: Date[];
}

export interface Policy {
  _id: string;
  priority: Priority;
  targetBusinessHours: number;
  isActive: boolean;
}

export interface Ticket {
  _id: string;
  ticketNumber: string;
  title: string;
  description: string;
  priority: Priority;
  status: TicketStatus;
  assigneeGroup?: string | null;
  createdAt: Date;
  resolvedAt?: Date | null;
  statusHistory: StatusEvent[];
  createdBy?: string | null;
  updatedAt: Date;
}

export interface AdminUser {
  _id: string;
  email: string;
  role: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface AssigneeGroup {
  _id: string;
  name: string;
  description?: string;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface Holiday {
  _id: string;
  date: Date;
  name: string;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}
