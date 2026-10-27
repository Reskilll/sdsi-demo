import { apiRequest } from './client';
import type { Room, RoomAvailability } from './types';

function roomPath(id: string): string {
  return `/rooms/${encodeURIComponent(id)}`;
}

export const roomsApi = {
  /** Passing a token validates credentials without touching the session. */
  list(token?: string): Promise<Room[]> {
    return apiRequest<Room[]>('/rooms', {
      token,
      skipUnauthorizedHandler: token !== undefined,
    });
  },

  get(id: string): Promise<Room> {
    return apiRequest<Room>(roomPath(id));
  },

  availability(id: string, date: string): Promise<RoomAvailability> {
    return apiRequest<RoomAvailability>(`${roomPath(id)}/availability`, {
      query: { date },
    });
  },
};
