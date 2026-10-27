<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { bookingsApi } from '../api/bookings';
import { ApiError, errorMessage, triggerBlobDownload } from '../api/client';
import type { Booking } from '../api/types';
import { useToasts } from '../composables/toasts';
import { amenityLabel, roomCapacityLabel, roomLocation, slugify } from '../utils/display';
import { formatDate, formatTimeRange } from '../utils/time';
import ModalDialog from './ModalDialog.vue';

const props = defineProps<{ booking: Booking }>();

const emit = defineEmits<{
  close: [];
  edit: [booking: Booking];
  updated: [booking: Booking];
  deleted: [];
}>();

const { notify } = useToasts();
const current = ref<Booking>(props.booking);
const actionBusy = ref<'cancel' | 'delete' | 'ics' | null>(null);
const confirmAction = ref<'cancel' | 'delete' | null>(null);
const actionError = ref('');

const canModify = computed(() => current.value.status === 'CONFIRMED');
const attendeeNames = computed(() => current.value.attendees ?? []);

onMounted(async () => {
  try {
    current.value = await bookingsApi.get(props.booking.id);
  } catch (error: unknown) {
    if (error instanceof ApiError && error.status === 401) return;
    // Keep showing the list snapshot if a refresh is unavailable.
  }
});

async function cancelBooking(): Promise<void> {
  if (actionBusy.value) return;
  actionBusy.value = 'cancel';
  actionError.value = '';
  try {
    const updated = await bookingsApi.cancel(current.value.id);
    current.value = updated;
    confirmAction.value = null;
    emit('updated', updated);
    notify('Booking cancelled.', 'success');
  } catch (error: unknown) {
    if (error instanceof ApiError && error.status === 401) return;
    actionError.value = errorMessage(error);
  } finally {
    actionBusy.value = null;
  }
}

async function deleteBooking(): Promise<void> {
  if (actionBusy.value) return;
  actionBusy.value = 'delete';
  actionError.value = '';
  try {
    await bookingsApi.remove(current.value.id);
    notify('Booking deleted.', 'success');
    emit('deleted');
  } catch (error: unknown) {
    if (error instanceof ApiError && error.status === 401) return;
    actionError.value = errorMessage(error);
    actionBusy.value = null;
  }
}

async function downloadIcs(): Promise<void> {
  if (actionBusy.value) return;
  actionBusy.value = 'ics';
  actionError.value = '';
  try {
    const blob = await bookingsApi.downloadIcs(current.value.id);
    triggerBlobDownload(blob, `${slugify(current.value.title)}.ics`);
    notify('Calendar file downloaded.', 'success');
  } catch (error: unknown) {
    if (error instanceof ApiError && error.status === 401) return;
    actionError.value = errorMessage(error);
  } finally {
    actionBusy.value = null;
  }
}

function requestClose(): void {
  if (!actionBusy.value) emit('close');
}
</script>

<template>
  <ModalDialog
    title="Booking details"
    :subtitle="`${formatDate(current.start, 'long')} · ${formatTimeRange(current.start, current.end)}`"
    size="md"
    @close="requestClose"
  >
    <div class="booking-detail">
      <div class="booking-detail__top">
        <div>
          <span
            class="badge"
            :class="current.status === 'CONFIRMED' ? 'badge--success' : 'badge--muted'"
          >
            {{ current.status === 'CONFIRMED' ? 'Confirmed' : 'Cancelled' }}
          </span>
          <span v-if="current.seriesId" class="badge badge--series">Recurring</span>
        </div>
        <span class="booking-detail__duration">
          {{ formatTimeRange(current.start, current.end) }}
        </span>
      </div>

      <h3 class="booking-detail__title">{{ current.title }}</h3>

      <dl class="detail-grid">
        <div>
          <dt>Room</dt>
          <dd>
            <strong>{{ current.room.name }}</strong>
            <span class="muted">
              {{ roomLocation(current.room) }} · {{ roomCapacityLabel(current.room) }}
            </span>
          </dd>
        </div>
        <div>
          <dt>Organiser</dt>
          <dd>
            <strong>{{ current.organiser }}</strong>
            <span v-if="current.organiserEmail" class="muted">{{ current.organiserEmail }}</span>
          </dd>
        </div>
        <div>
          <dt>Attendees</dt>
          <dd>
            <strong>{{ current.attendeeCount }} {{ current.attendeeCount === 1 ? 'person' : 'people' }}</strong>
            <span v-if="current.seriesId" class="muted">
              Occurrence {{ current.occurrenceIndex ?? '—' }} of this series
            </span>
          </dd>
        </div>
        <div>
          <dt>Booking ID</dt>
          <dd class="mono">{{ current.id }}</dd>
        </div>
      </dl>

      <div v-if="current.description" class="booking-detail__section">
        <h4>Description</h4>
        <p class="pre-line">{{ current.description }}</p>
      </div>

      <div class="booking-detail__section">
        <h4>Named attendees</h4>
        <div v-if="attendeeNames.length" class="chip-list">
          <span v-for="name in attendeeNames" :key="name" class="chip">{{ name }}</span>
        </div>
        <p v-else class="muted">No names supplied for this booking.</p>
      </div>

      <div class="booking-detail__section">
        <h4>Room amenities</h4>
        <div class="chip-list">
          <span v-for="amenity in current.room.amenities" :key="amenity" class="chip chip--soft">
            {{ amenityLabel(amenity) }}
          </span>
        </div>
      </div>

      <p v-if="!canModify" class="alert alert--info">
        This booking is cancelled. It remains visible for the record but can no longer be edited.
      </p>

      <p v-if="actionError" class="alert alert--error" role="alert">{{ actionError }}</p>

      <div v-if="confirmAction === 'cancel'" class="confirm-box" role="alertdialog" aria-label="Confirm cancellation">
        <p>
          Cancel this booking? The slot will become available to others, but the booking stays in
          the record as cancelled.
        </p>
        <div class="confirm-box__actions">
          <button type="button" class="btn btn--ghost btn--sm" @click="confirmAction = null">
            Keep booking
          </button>
          <button
            type="button"
            class="btn btn--danger btn--sm"
            :disabled="actionBusy === 'cancel'"
            @click="cancelBooking"
          >
            <span v-if="actionBusy === 'cancel'" class="spinner spinner--light" aria-hidden="true" />
            Yes, cancel it
          </button>
        </div>
      </div>

      <div v-if="confirmAction === 'delete'" class="confirm-box confirm-box--danger" role="alertdialog" aria-label="Confirm deletion">
        <p>Permanently delete this booking? This cannot be undone.</p>
        <div class="confirm-box__actions">
          <button type="button" class="btn btn--ghost btn--sm" @click="confirmAction = null">
            Keep booking
          </button>
          <button
            type="button"
            class="btn btn--danger btn--sm"
            :disabled="actionBusy === 'delete'"
            @click="deleteBooking"
          >
            <span v-if="actionBusy === 'delete'" class="spinner spinner--light" aria-hidden="true" />
            Delete permanently
          </button>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="footer-actions">
        <button
          type="button"
          class="btn btn--ghost"
          :disabled="actionBusy !== null"
          @click="downloadIcs"
        >
          {{ actionBusy === 'ics' ? 'Preparing…' : 'Download .ics' }}
        </button>
        <div class="footer-actions__right">
          <button
            v-if="canModify"
            type="button"
            class="btn btn--secondary"
            :disabled="actionBusy !== null"
            @click="emit('edit', current)"
          >
            Edit
          </button>
          <button
            v-if="canModify"
            type="button"
            class="btn btn--ghost btn--danger-text"
            :disabled="actionBusy !== null"
            @click="confirmAction = 'cancel'"
          >
            Cancel booking
          </button>
          <button
            type="button"
            class="btn btn--ghost btn--danger-text"
            :disabled="actionBusy !== null"
            @click="confirmAction = 'delete'"
          >
            Delete
          </button>
        </div>
      </div>
    </template>
  </ModalDialog>
</template>
