<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { bookingsApi } from '../api/bookings';
import { ApiError, errorMessage } from '../api/client';
import type { Booking, Room } from '../api/types';
import { useToasts } from '../composables/toasts';
import {
  addDays,
  defaultStartTime,
  durationMinutes,
  formatDate,
  formatDuration,
  formatTimeRange,
  minutesOfDay,
  minutesToTime,
  todayISO,
} from '../utils/time';
import type { BookingFormState, BookingInitial } from '../types/ui';
import AvailabilityModal from '../components/AvailabilityModal.vue';
import BookingDetailModal from '../components/BookingDetailModal.vue';
import BookingFormModal from '../components/BookingFormModal.vue';
import DayTimeline from '../components/DayTimeline.vue';

const props = defineProps<{ rooms: Room[] }>();

const { notify } = useToasts();

const selectedDate = ref(todayISO());
const roomFilter = ref('all');
const bookings = ref<Booking[]>([]);
const totalElements = ref(0);
const loading = ref(false);
const loadError = ref('');
const detailBooking = ref<Booking | null>(null);
const formState = ref<BookingFormState | null>(null);
const availabilityTarget = ref<{ room: Room; date: string } | null>(null);

let loadSequence = 0;

const visibleRooms = computed(() =>
  roomFilter.value === 'all'
    ? props.rooms
    : props.rooms.filter((room) => room.id === roomFilter.value),
);

const sortedBookings = computed(() =>
  [...bookings.value].sort((left, right) => left.start.localeCompare(right.start)),
);

const confirmedCount = computed(
  () => bookings.value.filter((booking) => booking.status === 'CONFIRMED').length,
);

const cancelledBookings = computed(() =>
  bookings.value.filter((booking) => booking.status === 'CANCELLED'),
);

const bookedMinutes = computed(() =>
  bookings.value
    .filter((booking) => booking.status === 'CONFIRMED')
    .reduce((total, booking) => total + durationMinutes(booking.start, booking.end), 0),
);

const isToday = computed(() => selectedDate.value === todayISO());
const selectedDateLabel = computed(() => formatDate(selectedDate.value, 'long'));

async function loadBookings(): Promise<void> {
  const sequence = ++loadSequence;
  loading.value = true;
  loadError.value = '';
  try {
    const response = await bookingsApi.list({
      date: selectedDate.value,
      roomId: roomFilter.value === 'all' ? undefined : roomFilter.value,
      page: 0,
      size: 100,
    });
    if (sequence !== loadSequence) return;
    bookings.value = response.content;
    totalElements.value = response.totalElements;
  } catch (caught: unknown) {
    if (sequence !== loadSequence) return;
    if (caught instanceof ApiError && caught.status === 401) return;
    loadError.value = errorMessage(caught);
  } finally {
    if (sequence === loadSequence) loading.value = false;
  }
}

watch([selectedDate, roomFilter], () => {
  void loadBookings();
}, { immediate: true });

function stepDate(days: number): void {
  selectedDate.value = addDays(selectedDate.value, days);
}

function goToday(): void {
  selectedDate.value = todayISO();
}

function defaultEndTime(startTime: string): string {
  const start = minutesOfDay(startTime) ?? 9 * 60;
  return minutesToTime(Math.min(start + 60, 18 * 60));
}

function openCreate(payload?: { roomId?: string; startTime?: string; endTime?: string }): void {
  const roomId = payload?.roomId ?? visibleRooms.value[0]?.id ?? props.rooms[0]?.id ?? '';
  const startTime = payload?.startTime ?? defaultStartTime(selectedDate.value);
  const initial: BookingInitial = {
    roomId,
    date: selectedDate.value,
    startTime,
    endTime: payload?.endTime ?? defaultEndTime(startTime),
  };
  formState.value = { mode: 'create', initial, booking: null };
  detailBooking.value = null;
}

function openEdit(booking: Booking): void {
  formState.value = { mode: 'edit', initial: null, booking };
  detailBooking.value = null;
}

function onSaved(booking: Booking): void {
  const mode = formState.value?.mode ?? 'create';
  formState.value = null;
  notify(`“${booking.title}” ${mode === 'edit' ? 'updated' : 'created'}.`, 'success');
  void loadBookings();
}

function onUpdated(booking: Booking): void {
  detailBooking.value = booking;
  void loadBookings();
}

function onDeleted(): void {
  detailBooking.value = null;
  void loadBookings();
}

function onAvailabilityBook(payload: {
  roomId: string;
  date: string;
  startTime: string;
  endTime: string;
}): void {
  availabilityTarget.value = null;
  openCreate(payload);
}
</script>

<template>
  <section class="view">
    <header class="view-head">
      <div class="view-head__copy">
        <p class="eyebrow">Day view</p>
        <h1>{{ selectedDateLabel }}</h1>
        <p class="muted">
          {{ confirmedCount }} confirmed · {{ formatDuration(bookedMinutes) }} booked
          <span v-if="cancelledBookings.length"> · {{ cancelledBookings.length }} cancelled</span>
        </p>
      </div>

      <div class="view-head__actions">
        <div class="date-nav" role="group" aria-label="Change selected date">
          <button type="button" class="icon-btn" aria-label="Previous day" @click="stepDate(-1)">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7" /></svg>
          </button>
          <input v-model="selectedDate" type="date" class="date-nav__input" aria-label="Selected date" />
          <button type="button" class="icon-btn" aria-label="Next day" @click="stepDate(1)">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7" /></svg>
          </button>
          <button type="button" class="btn btn--ghost btn--sm" :disabled="isToday" @click="goToday">
            Today
          </button>
        </div>
        <button type="button" class="btn btn--primary" @click="openCreate()">
          <span aria-hidden="true">+</span> New booking
        </button>
      </div>
    </header>

    <div class="toolbar">
      <div class="toolbar__group">
        <label class="toolbar__label" for="room-filter">Room</label>
        <select id="room-filter" v-model="roomFilter" class="select--compact">
          <option value="all">All rooms</option>
          <option v-for="room in props.rooms" :key="room.id" :value="room.id">
            {{ room.name }}
          </option>
        </select>
      </div>

      <div class="toolbar__group toolbar__group--end">
        <span v-if="loading" class="loading-inline" role="status">
          <span class="spinner" aria-hidden="true" /> Updating
        </span>
        <button
          type="button"
          class="btn btn--ghost btn--sm"
          :disabled="loading"
          @click="loadBookings"
        >
          Refresh
        </button>
      </div>
    </div>

    <p v-if="loadError" class="alert alert--error" role="alert">
      {{ loadError }}
      <button type="button" class="btn btn--ghost btn--sm" @click="loadBookings">Retry</button>
    </p>

    <div class="legend">
      <span class="legend__item"><span class="legend__swatch legend__swatch--confirmed" /> Confirmed</span>
      <span class="legend__item"><span class="legend__swatch legend__swatch--cancelled" /> Cancelled (list only)</span>
      <span class="legend__hint">Click empty space in a room column to book a 60-minute slot.</span>
    </div>

    <div v-if="visibleRooms.length === 0" class="card empty-state">
      <h2>No rooms to show</h2>
      <p>The room catalogue is empty or the selected filter no longer matches a room.</p>
    </div>
    <div v-else class="timeline-wrap" :class="{ 'is-loading': loading }" :aria-busy="loading">
      <DayTimeline
        :rooms="visibleRooms"
        :bookings="bookings"
        :date="selectedDate"
        @create="openCreate"
        @select="detailBooking = $event"
        @availability="availabilityTarget = $event"
      />
    </div>

    <section class="card day-list" aria-labelledby="day-list-title">
      <div class="section-heading">
        <h2 id="day-list-title">All bookings</h2>
        <span class="muted">{{ sortedBookings.length }} on this day</span>
      </div>

      <div v-if="sortedBookings.length" class="booking-list">
        <button
          v-for="booking in sortedBookings"
          :key="booking.id"
          type="button"
          class="booking-row"
          @click="detailBooking = booking"
        >
          <span class="booking-row__time">{{ formatTimeRange(booking.start, booking.end) }}</span>
          <span class="booking-row__main">
            <strong>{{ booking.title }}</strong>
            <span class="muted">
              {{ booking.room.name }} · {{ booking.organiser }} ·
              {{ booking.attendeeCount }} {{ booking.attendeeCount === 1 ? 'person' : 'people' }}
            </span>
          </span>
          <span v-if="booking.seriesId" class="badge badge--series">Series</span>
          <span
            class="badge"
            :class="booking.status === 'CONFIRMED' ? 'badge--success' : 'badge--muted'"
          >
            {{ booking.status === 'CONFIRMED' ? 'Confirmed' : 'Cancelled' }}
          </span>
          <svg class="booking-row__chevron" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>
      <p v-else class="empty-state empty-state--inline">
        Nothing booked on this day yet. Use the timeline or “New booking” to get started.
      </p>

      <p v-if="totalElements > sortedBookings.length" class="muted day-list__more">
        Showing {{ sortedBookings.length }} of {{ totalElements }} bookings for this day.
      </p>
    </section>

    <BookingDetailModal
      v-if="detailBooking"
      :key="detailBooking.id"
      :booking="detailBooking"
      @close="detailBooking = null"
      @edit="openEdit"
      @updated="onUpdated"
      @deleted="onDeleted"
    />

    <BookingFormModal
      v-if="formState"
      :rooms="props.rooms"
      :mode="formState.mode"
      :initial="formState.initial"
      :booking="formState.booking"
      @close="formState = null"
      @saved="onSaved"
    />

    <AvailabilityModal
      v-if="availabilityTarget"
      :room="availabilityTarget.room"
      :date="availabilityTarget.date"
      @close="availabilityTarget = null"
      @book="onAvailabilityBook"
    />
  </section>
</template>
