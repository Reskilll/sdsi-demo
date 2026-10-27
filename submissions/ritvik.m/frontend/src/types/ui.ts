import type { Booking } from '../api/types';

export type TabId = 'day' | 'find' | 'recurring';

export interface BookingInitial {
  roomId?: string;
  title?: string;
  organiser?: string;
  organiserEmail?: string;
  description?: string;
  date?: string;
  startTime?: string;
  endTime?: string;
  attendeeCount?: number;
  attendees?: string[];
}

export type BookingFormMode = 'create' | 'edit';

export interface BookingFormState {
  mode: BookingFormMode;
  initial: BookingInitial | null;
  booking: Booking | null;
}

export type ToastKind = 'success' | 'error' | 'info';

export interface ToastMessage {
  id: number;
  kind: ToastKind;
  message: string;
}
