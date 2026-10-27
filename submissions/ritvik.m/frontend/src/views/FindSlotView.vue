<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import { ApiError, errorMessage } from '../api/client';
import { slotsApi } from '../api/slots';
import type { Booking, Room, SlotSearchResponse, SlotView } from '../api/types';
import { useToasts } from '../composables/toasts';
import { amenityLabel, roomCapacityLabel, roomLocation } from '../utils/display';
import {
  dateOf,
  formatDate,
  formatDuration,
  formatTimeRange,
  timeOf,
  todayISO,
} from '../utils/time';
import type { BookingInitial } from '../types/ui';
import BookingFormModal from '../components/BookingFormModal.vue';
import FormField from '../components/FormField.vue';

const props = defineProps<{
  rooms: Room[];
  username: string;
}>();

const { notify } = useToasts();

const form = reactive({
  date: todayISO(),
  durationMinutes: 60,
  attendees: 4,
  roomId: 'all',
  amenities: [] as string[],
});

const loading = ref(false);
const searched = ref(false);
const error = ref('');
const validationError = ref('');
const result = ref<SlotSearchResponse | null>(null);
const bookingInitial = ref<BookingInitial | null>(null);

const availableAmenities = computed(() =>
  [...new Set(props.rooms.flatMap((room) => room.amenities))].sort((left, right) =>
    left.localeCompare(right),
  ),
);

const bestSlot = computed(() => result.value?.slot ?? null);
const alternatives = computed(() => result.value?.alternatives ?? []);

const emptyMessage = computed(
  () =>
    result.value?.message ??
    'No free slot fits those requirements. Try a shorter meeting, fewer attendees or another day.',
);

async function search(): Promise<void> {
  error.value = '';
  validationError.value = '';
  const duration = Number(form.durationMinutes);
  const attendees = Number(form.attendees);

  if (!Number.isInteger(duration) || duration < 15 || duration > 540) {
    validationError.value = 'Duration must be between 15 and 540 minutes.';
    return;
  }
  if (!Number.isInteger(attendees) || attendees < 1) {
    validationError.value = 'Enter at least one attendee.';
    return;
  }

  loading.value = true;
  try {
    result.value = await slotsApi.find({
      date: form.date,
      durationMinutes: duration,
      attendees,
      amenities: form.amenities.length > 0 ? form.amenities : undefined,
      roomId: form.roomId === 'all' ? undefined : form.roomId,
    });
    searched.value = true;
  } catch (caught: unknown) {
    if (caught instanceof ApiError && caught.status === 401) return;
    result.value = null;
    searched.value = true;
    error.value = errorMessage(caught);
  } finally {
    loading.value = false;
  }
}

function bookSlot(slot: SlotView): void {
  bookingInitial.value = {
    roomId: slot.room.id,
    date: dateOf(slot.start),
    startTime: timeOf(slot.start),
    endTime: timeOf(slot.end),
    attendeeCount: Number(form.attendees),
    organiser: props.username,
  };
}

function onBooked(booking: Booking): void {
  bookingInitial.value = null;
  notify(`“${booking.title}” booked in ${booking.room.name}.`, 'success');
  void search();
}
</script>

<template>
  <section class="view">
    <header class="view-head">
      <div class="view-head__copy">
        <p class="eyebrow">Find a slot</p>
        <h1>A room that fits, automatically</h1>
        <p class="muted">
          Tell us the day, group size and kit you need. We’ll find the earliest room that works.
        </p>
      </div>
    </header>

    <div class="split-layout">
      <form class="card search-card" novalidate @submit.prevent="search">
        <div class="section-heading">
          <h2>Your requirements</h2>
          <span class="badge badge--soft">15-minute grid</span>
        </div>

        <div class="form-grid">
          <FormField v-slot="{ id }" label="Date" required>
            <input :id="id" v-model="form.date" type="date" />
          </FormField>

          <FormField v-slot="{ id }" label="Duration (minutes)" required hint="15–540 minutes">
            <input
              :id="id"
              v-model.number="form.durationMinutes"
              type="number"
              min="15"
              max="540"
              step="15"
            />
          </FormField>

          <FormField v-slot="{ id }" label="Attendees" required>
            <input :id="id" v-model.number="form.attendees" type="number" min="1" max="1000" />
          </FormField>

          <FormField v-slot="{ id }" label="Room">
            <select :id="id" v-model="form.roomId">
              <option value="all">Any suitable room</option>
              <option v-for="room in props.rooms" :key="room.id" :value="room.id">
                {{ room.name }} · {{ room.capacity }} seats
              </option>
            </select>
          </FormField>
        </div>

        <fieldset class="field checkbox-fieldset">
          <legend class="field__label">Amenities</legend>
          <p class="field__hint">Optional. Every selected item must be available.</p>
          <div v-if="availableAmenities.length" class="checkbox-grid">
            <label v-for="amenity in availableAmenities" :key="amenity" class="checkbox">
              <input v-model="form.amenities" type="checkbox" :value="amenity" />
              <span>{{ amenityLabel(amenity) }}</span>
            </label>
          </div>
          <p v-else class="muted">Room amenities have not loaded yet.</p>
        </fieldset>

        <p v-if="validationError" class="alert alert--error" role="alert">{{ validationError }}</p>

        <button type="submit" class="btn btn--primary btn--block" :disabled="loading">
          <span v-if="loading" class="spinner spinner--light" aria-hidden="true" />
          {{ loading ? 'Searching…' : 'Find a slot' }}
        </button>

        <p class="search-card__foot">
          The search only considers confirmed bookings inside office hours.
        </p>
      </form>

      <div class="results-panel" aria-live="polite">
        <div v-if="loading" class="card loading-block" aria-busy="true">
          <span class="spinner" aria-hidden="true" /> Searching every room…
        </div>

        <div v-else-if="error" class="card empty-state">
          <h2>Search failed</h2>
          <p>{{ error }}</p>
          <button type="button" class="btn btn--secondary" @click="search">Try again</button>
        </div>

        <template v-else-if="searched && result">
          <article v-if="bestSlot" class="best-slot">
            <p class="best-slot__eyebrow">Best available</p>
            <p class="best-slot__time">{{ formatTimeRange(bestSlot.start, bestSlot.end) }}</p>
            <p class="best-slot__date">{{ formatDate(bestSlot.start, 'long') }}</p>
            <div class="best-slot__room">
              <h2>{{ bestSlot.room.name }}</h2>
              <p class="best-slot__meta">
                {{ roomLocation(bestSlot.room) }} · {{ roomCapacityLabel(bestSlot.room) }}
              </p>
              <div class="chip-list">
                <span
                  v-for="amenity in bestSlot.room.amenities"
                  :key="amenity"
                  class="chip chip--on-dark"
                >
                  {{ amenityLabel(amenity) }}
                </span>
              </div>
            </div>
            <div class="best-slot__footer">
              <p>
                {{ result.attendees }} {{ result.attendees === 1 ? 'attendee' : 'attendees' }} ·
                {{ formatDuration(result.durationMinutes) }}
              </p>
              <button type="button" class="btn btn--light" @click="bookSlot(bestSlot)">
                Book this slot
              </button>
            </div>
          </article>

          <article v-else class="card empty-state">
            <h2>No slot available</h2>
            <p>{{ emptyMessage }}</p>
            <p class="muted">
              {{ form.attendees }} attendees · {{ formatDuration(Number(form.durationMinutes)) }} ·
              {{ formatDate(form.date, 'long') }}
            </p>
          </article>

          <section v-if="alternatives.length" class="card alternatives-card">
            <div class="section-heading">
              <h2>Other options</h2>
              <span class="muted">{{ alternatives.length }} found</span>
            </div>
            <div class="slot-list">
              <div v-for="slot in alternatives" :key="`${slot.room.id}-${slot.start}`" class="slot-row">
                <div>
                  <strong>{{ slot.room.name }}</strong>
                  <span class="muted">
                    {{ formatTimeRange(slot.start, slot.end) }} · {{ roomCapacityLabel(slot.room) }} ·
                    {{ roomLocation(slot.room) }}
                  </span>
                </div>
                <button type="button" class="btn btn--secondary btn--sm" @click="bookSlot(slot)">
                  Book
                </button>
              </div>
            </div>
          </section>

          <p v-if="bestSlot" class="muted results-panel__note">
            Times are office-local and never shift with the browser timezone.
          </p>
        </template>

        <div v-else class="card empty-state empty-state--illustrated">
          <div class="empty-state__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <circle cx="10.5" cy="10.5" r="6.5" />
              <path d="M15.5 15.5L21 21" />
            </svg>
          </div>
          <h2>Find the earliest fit</h2>
          <p>Set the essentials and we’ll rank the best room and time for your meeting.</p>
        </div>
      </div>
    </div>

    <BookingFormModal
      v-if="bookingInitial"
      :rooms="props.rooms"
      mode="create"
      :initial="bookingInitial"
      @close="bookingInitial = null"
      @saved="onBooked"
    />
  </section>
</template>
