import { apiRequest } from './client';
import type {
  CancelSeriesResponse,
  PageResponse,
  RecurringBookingPayload,
  RecurringCreateResponse,
  RecurringPreviewResponse,
  SeriesDetail,
  SeriesSummary,
} from './types';

export const recurringApi = {
  preview(payload: RecurringBookingPayload): Promise<RecurringPreviewResponse> {
    return apiRequest<RecurringPreviewResponse>('/bookings/recurring/preview', {
      method: 'POST',
      body: payload,
    });
  },

  create(payload: RecurringBookingPayload): Promise<RecurringCreateResponse> {
    return apiRequest<RecurringCreateResponse>('/bookings/recurring', {
      method: 'POST',
      body: payload,
    });
  },
};

export const seriesApi = {
  list(page = 0, size = 20): Promise<PageResponse<SeriesSummary>> {
    return apiRequest<PageResponse<SeriesSummary>>('/series', {
      query: { page, size },
    });
  },

  get(id: string): Promise<SeriesDetail> {
    return apiRequest<SeriesDetail>(`/series/${encodeURIComponent(id)}`);
  },

  cancelFuture(id: string, from: string): Promise<CancelSeriesResponse> {
    return apiRequest<CancelSeriesResponse>(`/series/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      query: { from },
    });
  },
};
