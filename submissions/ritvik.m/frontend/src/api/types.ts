/** Contract types mirrored from the Spring Boot API. */

export type DayOfWeek =
  | 'MONDAY'
  | 'TUESDAY'
  | 'WEDNESDAY'
  | 'THURSDAY'
  | 'FRIDAY'
  | 'SATURDAY'
  | 'SUNDAY';

export type BookingStatus = 'CONFIRMED' | 'CANCELLED';

export interface Room {
  id: string;
  name: string;
  capacity: number;
  floor?: number | null;
  location?: string | null;
  amenities: string[];
}

export interface Booking {
  id: string;
  room: Room;
  organiser: string;
  organiserEmail?: string | null;
  title: string;
  description?: string | null;
  /** Wall-clock ISO local date-time, e.g. 2026-11-02T10:00:00. */
  start: string;
  /** Wall-clock ISO local date-time, e.g. 2026-11-02T11:00:00. */
  end: string;
  attendeeCount: number;
  attendees?: string[] | null;
  status: BookingStatus;
  seriesId?: string | null;
  occurrenceIndex?: number | null;
  createdAt?: string;
  updatedAt?: string;
  version: number;
}

export interface PageResponse<T> {
  content: T[];
  page: number;
  size: number;
  totalElements: number;
  totalPages: number;
  first: boolean;
  last: boolean;
}

export interface BusyInterval {
  start: string;
  end: string;
  bookingId: string;
  title: string;
  organiser: string;
}

export interface FreeInterval {
  start: string;
  end: string;
  minutes: number;
}

export interface RoomAvailability {
  room: Room;
  /** YYYY-MM-DD */
  date: string;
  busy: BusyInterval[];
  free: FreeInterval[];
}

export interface SlotView {
  start: string;
  end: string;
  room: Room;
}

export interface SlotSearchResponse {
  date: string;
  durationMinutes: number;
  attendees: number;
  slot?: SlotView | null;
  alternatives: SlotView[];
  message?: string | null;
}

export interface ConflictView {
  bookingId: string;
  title: string;
  organiser: string;
  start: string;
  end: string;
}

export type OccurrenceStatus = 'FREE' | 'CONFLICT';

export interface OccurrenceView {
  start: string;
  end: string;
  status: OccurrenceStatus;
  conflicts: ConflictView[];
}

export interface RecurringPreviewResponse {
  startsOn: string;
  weeks: number;
  daysOfWeek: DayOfWeek[];
  occurrenceCount: number;
  conflictCount: number;
  occurrences: OccurrenceView[];
}

export interface SeriesSummary {
  id: string;
  room: Room;
  organiser: string;
  organiserEmail?: string | null;
  title: string;
  description?: string | null;
  /** HH:mm:ss */
  startTime: string;
  /** HH:mm:ss */
  endTime: string;
  /** YYYY-MM-DD */
  startsOn: string;
  weeks: number;
  daysOfWeek: DayOfWeek[];
  attendeeCount: number;
  attendees?: string[] | null;
  createdAt?: string;
}

export interface SeriesDetail extends SeriesSummary {
  occurrences: Booking[];
}

export interface RecurringCreateResponse {
  seriesId: string;
  series: SeriesSummary;
  created: Booking[];
  skipped: OccurrenceView[];
  message?: string | null;
}

export interface CancelSeriesResponse {
  seriesId: string;
  cancelledCount: number;
}

export interface FieldError {
  field: string;
  message: string;
}

export interface BookingBasePayload {
  roomId: string;
  organiser: string;
  organiserEmail?: string;
  title: string;
  description?: string;
  start: string;
  end: string;
  attendeeCount?: number;
  attendees?: string[];
}

export type BookingCreatePayload = BookingBasePayload;

export interface BookingUpdatePayload extends BookingBasePayload {
  version?: number;
}

export interface RecurringBookingPayload {
  roomId: string;
  organiser: string;
  organiserEmail?: string;
  title: string;
  description?: string;
  startsOn: string;
  startTime: string;
  endTime: string;
  daysOfWeek?: DayOfWeek[];
  weeks: number;
  attendeeCount: number;
  attendees?: string[];
  skipConflicts: boolean;
}

export interface BookingListParams {
  roomId?: string;
  organiser?: string;
  status?: BookingStatus;
  date?: string;
  from?: string;
  to?: string;
  page?: number;
  size?: number;
}

export interface SlotSearchParams {
  date: string;
  durationMinutes: number;
  attendees: number;
  amenities?: string[];
  roomId?: string;
}
