<script setup lang="ts">
import { computed } from 'vue';
import type { CSSProperties } from 'vue';
import type { Booking, Room } from '../api/types';
import { amenityLabel } from '../utils/display';
import {
  CLOSE_MINUTES,
  OPEN_MINUTES,
  defaultStartTime,
  formatTimeRange,
  minutesOfDay,
  minutesToTime,
  roundToStep,
} from '../utils/time';

const props = defineProps<{
  rooms: Room[];
  bookings: Booking[];
  date: string;
}>();

const emit = defineEmits<{
  create: [payload: { roomId: string; startTime: string; endTime: string }];
  select: [booking: Booking];
  availability: [payload: { room: Room; date: string }];
}>();

/** Must stay in sync with the --hour-height custom property below. */
const HOUR_HEIGHT = 76;
const TOTAL_HEIGHT = ((CLOSE_MINUTES - OPEN_MINUTES) / 60) * HOUR_HEIGHT;

const hourMarks = Array.from({ length: 10 }, (_, index) => {
  const minutes = OPEN_MINUTES + index * 60;
  return { minutes, label: minutesToTime(minutes) };
});

const bookingsByRoom = computed(() => {
  const map = new Map<string, Booking[]>();
  for (const booking of props.bookings) {
    if (booking.status !== 'CONFIRMED') continue;
    const list = map.get(booking.room.id);
    if (list) list.push(booking);
    else map.set(booking.room.id, [booking]);
  }
  return map;
});

function bookingsFor(roomId: string): Booking[] {
  return bookingsByRoom.value.get(roomId) ?? [];
}

function paletteIndex(roomId: string): number {
  const index = props.rooms.findIndex((room) => room.id === roomId);
  return index < 0 ? 0 : index % 6;
}

interface BlockStyle extends CSSProperties {
  top: string;
  height: string;
}

function blockStyle(booking: Booking): BlockStyle {
  const rawStart = minutesOfDay(booking.start);
  const rawEnd = minutesOfDay(booking.end);
  if (rawStart === null || rawEnd === null) return { top: '0px', height: '0px' };
  const start = Math.min(Math.max(rawStart, OPEN_MINUTES), CLOSE_MINUTES);
  const end = Math.min(Math.max(rawEnd, start + 15), CLOSE_MINUTES);
  const top = ((start - OPEN_MINUTES) / 60) * HOUR_HEIGHT;
  const height = Math.max(24, ((end - start) / 60) * HOUR_HEIGHT - 4);
  return { top: `${top}px`, height: `${height}px` };
}

function isCompact(booking: Booking): boolean {
  const style = blockStyle(booking);
  return Number.parseFloat(style.height) < 58;
}

function onColumnClick(event: MouseEvent, room: Room): void {
  const column = event.currentTarget;
  if (!(column instanceof HTMLElement)) return;
  const rect = column.getBoundingClientRect();
  if (rect.height <= 0) return;
  const ratio = (event.clientY - rect.top) / rect.height;
  const rawMinutes = OPEN_MINUTES + ratio * (CLOSE_MINUTES - OPEN_MINUTES);
  const latestStart = CLOSE_MINUTES - 60;
  const rounded = Math.min(
    Math.max(roundToStep(rawMinutes, 15), OPEN_MINUTES),
    latestStart,
  );
  emit('create', {
    roomId: room.id,
    startTime: minutesToTime(rounded),
    endTime: minutesToTime(Math.min(rounded + 60, CLOSE_MINUTES)),
  });
}

function addBooking(room: Room): void {
  const start = defaultStartTime(props.date);
  const startMinutes = minutesOfDay(start) ?? OPEN_MINUTES;
  const endMinutes = Math.min(startMinutes + 60, CLOSE_MINUTES);
  emit('create', {
    roomId: room.id,
    startTime: minutesToTime(startMinutes),
    endTime: minutesToTime(endMinutes),
  });
}

function openAvailability(room: Room): void {
  emit('availability', { room, date: props.date });
}
</script>

<template>
  <div class="timeline-card">
    <div class="timeline-scroll">
      <div
        class="timeline"
        :style="{
          '--hour-height': `${HOUR_HEIGHT}px`,
          '--room-count': rooms.length,
          minWidth: `${64 + rooms.length * 190}px`,
        }"
      >
        <div class="timeline__head" :style="{ gridTemplateColumns: `64px repeat(${rooms.length}, minmax(190px, 1fr))` }">
          <div class="timeline__gutter" aria-hidden="true"></div>
          <div v-for="room in rooms" :key="room.id" class="room-head">
            <div class="room-head__top">
              <strong class="room-head__name">{{ room.name }}</strong>
              <span class="room-head__capacity">{{ room.capacity }} seats</span>
            </div>
            <p class="room-head__meta">
              <template v-if="room.floor !== null && room.floor !== undefined">Floor {{ room.floor }} · </template>{{ room.location || 'Office' }}
            </p>
            <p class="room-head__amenities" :title="room.amenities.map(amenityLabel).join(', ')">
              {{ room.amenities.map(amenityLabel).join(' · ') }}
            </p>
            <div class="room-head__actions">
              <button type="button" class="room-action" @click="openAvailability(room)">
                Availability
              </button>
              <button type="button" class="room-action room-action--primary" @click="addBooking(room)">
                + Add
              </button>
            </div>
          </div>
        </div>

        <div
          class="timeline__body"
          :style="{
            gridTemplateColumns: `64px repeat(${rooms.length}, minmax(190px, 1fr))`,
            height: `${TOTAL_HEIGHT}px`,
          }"
        >
          <div class="time-axis" aria-hidden="true">
            <span
              v-for="mark in hourMarks"
              :key="mark.minutes"
              class="time-axis__label"
              :style="{ top: `${((mark.minutes - OPEN_MINUTES) / 60) * HOUR_HEIGHT}px` }"
            >
              {{ mark.label }}
            </span>
          </div>

          <div
            v-for="room in rooms"
            :key="room.id"
            class="timeline__column"
            :aria-label="`${room.name} bookings. Click empty space to add a booking.`"
            @click="onColumnClick($event, room)"
          >
            <div
              v-for="booking in bookingsFor(room.id)"
              :key="booking.id"
              class="booking-block"
              :class="[
                `booking-block--${paletteIndex(room.id)}`,
                { 'booking-block--compact': isCompact(booking) },
              ]"
              :style="blockStyle(booking)"
              role="button"
              tabindex="0"
              :aria-label="`${booking.title}, ${room.name}, ${formatTimeRange(booking.start, booking.end)}`"
              @click.stop="emit('select', booking)"
              @keydown.enter.prevent="emit('select', booking)"
              @keydown.space.prevent="emit('select', booking)"
            >
              <span class="booking-block__title">{{ booking.title }}</span>
              <span class="booking-block__meta">
                {{ formatTimeRange(booking.start, booking.end) }} · {{ booking.organiser }}
              </span>
              <span class="booking-block__meta">
                {{ booking.attendeeCount }} {{ booking.attendeeCount === 1 ? 'person' : 'people' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
