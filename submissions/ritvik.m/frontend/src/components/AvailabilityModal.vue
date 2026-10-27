<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { roomsApi } from '../api/rooms';
import { ApiError, errorMessage } from '../api/client';
import type { FreeInterval, Room, RoomAvailability } from '../api/types';
import { amenityLabel, roomCapacityLabel, roomLocation } from '../utils/display';
import {
  CLOSE_MINUTES,
  formatDate,
  formatDuration,
  formatTime,
  formatTimeRange,
  minutesOfDay,
  minutesToTime,
} from '../utils/time';
import ModalDialog from './ModalDialog.vue';

const props = defineProps<{
  room: Room;
  date: string;
}>();

const emit = defineEmits<{
  close: [];
  book: [payload: { roomId: string; date: string; startTime: string; endTime: string }];
}>();

const availability = ref<RoomAvailability | null>(null);
const loading = ref(false);
const error = ref('');

const freeWindows = computed(() => availability.value?.free ?? []);
const busyWindows = computed(() => availability.value?.busy ?? []);

async function load(): Promise<void> {
  loading.value = true;
  error.value = '';
  try {
    availability.value = await roomsApi.availability(props.room.id, props.date);
  } catch (caught: unknown) {
    if (caught instanceof ApiError && caught.status === 401) return;
    error.value = errorMessage(caught);
  } finally {
    loading.value = false;
  }
}

function bookWindow(window: FreeInterval): void {
  const start = minutesOfDay(window.start) ?? 9 * 60;
  const end = Math.min(start + 60, minutesOfDay(window.end) ?? CLOSE_MINUTES);
  emit('book', {
    roomId: props.room.id,
    date: props.date,
    startTime: minutesToTime(start),
    endTime: minutesToTime(Math.max(end, start + 15)),
  });
}

onMounted(load);
</script>

<template>
  <ModalDialog
    title="Room availability"
    :subtitle="`${props.room.name} · ${formatDate(props.date, 'long')}`"
    size="md"
    @close="emit('close')"
  >
    <div class="availability">
      <div class="availability__room">
        <div>
          <strong>{{ props.room.name }}</strong>
          <p class="muted">{{ roomLocation(props.room) }} · {{ roomCapacityLabel(props.room) }}</p>
        </div>
        <div class="chip-list">
          <span v-for="amenity in props.room.amenities" :key="amenity" class="chip chip--soft">
            {{ amenityLabel(amenity) }}
          </span>
        </div>
      </div>

      <div v-if="loading" class="loading-block" aria-busy="true">
        <span class="spinner" aria-hidden="true" /> Loading availability…
      </div>
      <div v-else-if="error" class="alert alert--error" role="alert">
        {{ error }}
        <button type="button" class="btn btn--ghost btn--sm" @click="load">Retry</button>
      </div>

      <template v-else>
        <section class="availability__section">
          <div class="section-heading">
            <h3>Free windows</h3>
            <span class="muted">{{ freeWindows.length }} available</span>
          </div>
          <div v-if="freeWindows.length" class="slot-list">
            <div v-for="window in freeWindows" :key="window.start" class="slot-row">
              <div>
                <strong>{{ formatTimeRange(window.start, window.end) }}</strong>
                <span class="muted">{{ formatDuration(window.minutes) }} free</span>
              </div>
              <button type="button" class="btn btn--secondary btn--sm" @click="bookWindow(window)">
                Book
              </button>
            </div>
          </div>
          <p v-else class="empty-state empty-state--inline">No free windows remain on this day.</p>
        </section>

        <section class="availability__section">
          <div class="section-heading">
            <h3>Confirmed bookings</h3>
            <span class="muted">{{ busyWindows.length }}</span>
          </div>
          <div v-if="busyWindows.length" class="slot-list">
            <div v-for="window in busyWindows" :key="window.bookingId" class="slot-row slot-row--busy">
              <div>
                <strong>{{ window.title }}</strong>
                <span class="muted">
                  {{ formatTime(window.start) }}–{{ formatTime(window.end) }} · {{ window.organiser }}
                </span>
              </div>
            </div>
          </div>
          <p v-else class="empty-state empty-state--inline">The room is completely free today.</p>
        </section>
      </template>
    </div>

    <template #footer>
      <button type="button" class="btn btn--ghost" @click="emit('close')">Close</button>
      <button type="button" class="btn btn--primary" @click="emit('book', { roomId: props.room.id, date: props.date, startTime: '10:00', endTime: '11:00' })">
        New booking
      </button>
    </template>
  </ModalDialog>
</template>
