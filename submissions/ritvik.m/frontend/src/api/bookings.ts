import { apiRequest } from './client';
import type {
  Booking,
  BookingCreatePayload,
  BookingListParams,
  BookingUpdatePayload,
  PageResponse,
} from './types';

function bookingPath(id: string): string {
  return `/bookings/${encodeURIComponent(id)}`;
}

export const bookingsApi = {
  list(params: BookingListParams = {}): Promise<PageResponse<Booking>> {
    return apiRequest<PageResponse<Booking>>('/bookings', {
      query: {
        roomId: params.roomId,
        organiser: params.organiser,
        status: params.status,
        date: params.date,
        from: params.from,
        to: params.to,
        page: params.page ?? 0,
        size: params.size ?? 50,
      },
    });
  },

  get(id: string): Promise<Booking> {
    return apiRequest<Booking>(bookingPath(id));
  },

  create(payload: BookingCreatePayload): Promise<Booking> {
    return apiRequest<Booking>('/bookings', { method: 'POST', body: payload });
  },

  update(id: string, payload: BookingUpdatePayload): Promise<Booking> {
    return apiRequest<Booking>(bookingPath(id), { method: 'PUT', body: payload });
  },

  cancel(id: string): Promise<Booking> {
    return apiRequest<Booking>(`${bookingPath(id)}/cancel`, { method: 'PATCH' });
  },

  remove(id: string): Promise<void> {
    return apiRequest<void>(bookingPath(id), {
      method: 'DELETE',
      responseType: 'void',
    });
  },

  downloadIcs(id: string): Promise<Blob> {
    return apiRequest<Blob>(`${bookingPath(id)}/ics`, {
      responseType: 'blob',
      query: undefined,
    });
  },
};
