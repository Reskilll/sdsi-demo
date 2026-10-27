import { apiRequest } from './client';
import type { SlotSearchParams, SlotSearchResponse } from './types';

export const slotsApi = {
  find(params: SlotSearchParams): Promise<SlotSearchResponse> {
    return apiRequest<SlotSearchResponse>('/find-slot', {
      query: {
        date: params.date,
        durationMinutes: params.durationMinutes,
        attendees: params.attendees,
        amenities: params.amenities,
        roomId: params.roomId,
      },
    });
  },
};
