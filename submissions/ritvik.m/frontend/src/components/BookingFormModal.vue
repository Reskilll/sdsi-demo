<script setup lang="ts">
import { computed, nextTick, reactive, ref, useId, watch } from 'vue';
import { ApiError, errorMessage } from '../api/client';
import { bookingsApi } from '../api/bookings';
import type {
  Booking,
  BookingCreatePayload,
  ConflictView,
  Room,
} from '../api/types';
import { useAuth } from '../composables/auth';
import { parseAttendeeNames, roomLocation } from '../utils/display';
import {
  combineDateTime,
  dateOf,
  formatDate,
  formatTimeRange,
  parseDateParts,
  timeOf,
  todayISO,
  validateWindow,
} from '../utils/time';
import type { BookingFormMode, BookingInitial } from '../types/ui';
import FormField from './FormField.vue';
import ModalDialog from './ModalDialog.vue';

const props = defineProps<{
  rooms: Room[];
  mode: BookingFormMode;
  initial?: BookingInitial | null;
  booking?: Booking | null;
}>();

const emit = defineEmits<{
  close: [];
  saved: [booking: Booking];
}>();

const auth = useAuth();
const formId = useId();

const initial = props.initial ?? null;
const booking = props.booking ?? null;

interface FormState {
  roomId: string;
  title: string;
  organiser: string;
  organiserEmail: string;
  description: string;
  date: string;
  startTime: string;
  endTime: string;
  attendeeCount: number;
  attendeeNames: string;
}

const form = reactive<FormState>({
  roomId: booking?.room.id ?? initial?.roomId ?? props.rooms[0]?.id ?? '',
  title: booking?.title ?? initial?.title ?? '',
  organiser: booking?.organiser ?? initial?.organiser ?? auth.username.value,
  organiserEmail: booking?.organiserEmail ?? initial?.organiserEmail ?? '',
  description: booking?.description ?? initial?.description ?? '',
  date: booking ? dateOf(booking.start) : (initial?.date ?? todayISO()),
  startTime: booking ? timeOf(booking.start) : (initial?.startTime ?? '10:00'),
  endTime: booking ? timeOf(booking.end) : (initial?.endTime ?? '11:00'),
  attendeeCount: booking?.attendeeCount ?? initial?.attendeeCount ?? 1,
  attendeeNames: (booking?.attendees ?? initial?.attendees ?? []).join(', '),
});

type FieldKey =
  | 'roomId'
  | 'title'
  | 'organiser'
  | 'organiserEmail'
  | 'description'
  | 'date'
  | 'startTime'
  | 'endTime'
  | 'attendeeCount'
  | 'attendees';

type LocalErrors = Partial<Record<FieldKey, string>>;

const localErrors = ref<LocalErrors>({});
const serverErrors = ref<Record<string, string>>({});
const globalError = ref('');
const conflicts = ref<ConflictView[]>([]);
const saving = ref(false);

const selectedRoom = computed(() =>
  props.rooms.find((room) => room.id === form.roomId) ?? null,
);

const submitLabel = computed(() =>
  props.mode === 'edit' ? 'Save changes' : 'Create booking',
);

const subtitle = computed(() => {
  const room = selectedRoom.value;
  const date = form.date ? formatDate(form.date, 'long') : 'Choose a date';
  return room ? `${date} · ${room.name}` : date;
});

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

watch(
  form,
  () => {
    if (saving.value) return;
    localErrors.value = {};
    if (globalError.value || conflicts.value.length > 0) {
      globalError.value = '';
      conflicts.value = [];
      serverErrors.value = {};
    }
  },
  { deep: true },
);

function errorFor(...keys: string[]): string | undefined {
  for (const key of keys) {
    const server = serverErrors.value[key];
    if (server) return server;
    const local = localErrors.value[key as FieldKey];
    if (local) return local;
  }
  return undefined;
}

function validate(): LocalErrors {
  const errors: LocalErrors = {};
  const room = selectedRoom.value;

  if (!form.roomId || !room) errors.roomId = 'Choose a room.';

  const title = form.title.trim();
  if (!title) errors.title = 'Give the booking a title.';
  else if (title.length > 160) errors.title = 'Keep the title under 160 characters.';

  const organiser = form.organiser.trim();
  if (!organiser) errors.organiser = 'Who is organising this meeting?';
  else if (organiser.length > 120) errors.organiser = 'Keep the organiser under 120 characters.';

  const email = form.organiserEmail.trim();
  if (email && !emailPattern.test(email)) {
    errors.organiserEmail = 'Enter a valid email address.';
  } else if (email.length > 160) {
    errors.organiserEmail = 'Keep the email under 160 characters.';
  }

  if (form.description.trim().length > 1000) {
    errors.description = 'Keep the description under 1000 characters.';
  }

  if (!parseDateParts(form.date)) errors.date = 'Choose a valid date.';

  const windowError = validateWindow(form.startTime, form.endTime);
  if (windowError) errors.endTime = windowError;

  const count = Number(form.attendeeCount);
  if (!Number.isInteger(count) || count < 1) {
    errors.attendeeCount = 'At least one attendee is required.';
  } else if (room && count > room.capacity) {
    errors.attendeeCount = `${room.name} seats ${room.capacity}; reduce the group size.`;
  }

  const names = parseAttendeeNames(form.attendeeNames);
  if (names.length > 50) {
    errors.attendees = 'Add at most 50 named attendees.';
  } else if (names.length > 0 && names.length !== count) {
    errors.attendees = `You listed ${names.length} ${names.length === 1 ? 'name' : 'names'} but the count is ${count}.`;
  }

  return errors;
}

function focusFirstInvalid(): void {
  void nextTick(() => {
    const target = document.querySelector<HTMLElement>(
      '.modal .field--invalid input:not([type="hidden"]):not([disabled]), .modal .field--invalid select:not([disabled]), .modal .field--invalid textarea:not([disabled])',
    );
    target?.focus();
  });
}

function buildPayload(): BookingCreatePayload {
  const payload: BookingCreatePayload = {
    roomId: form.roomId,
    organiser: form.organiser.trim(),
    title: form.title.trim(),
    start: combineDateTime(form.date, form.startTime),
    end: combineDateTime(form.date, form.endTime),
    attendeeCount: Number(form.attendeeCount),
  };

  const email = form.organiserEmail.trim();
  if (email) payload.organiserEmail = email;
  const description = form.description.trim();
  if (description) payload.description = description;
  const names = parseAttendeeNames(form.attendeeNames);
  if (names.length > 0) payload.attendees = names;
  return payload;
}

async function submit(): Promise<void> {
  if (saving.value) return;

  globalError.value = '';
  serverErrors.value = {};
  conflicts.value = [];
  const errors = validate();
  localErrors.value = errors;
  if (Object.keys(errors).length > 0) {
    focusFirstInvalid();
    return;
  }

  saving.value = true;
  try {
    const payload = buildPayload();
    let saved: Booking;
    if (props.mode === 'edit' && props.booking) {
      saved = await bookingsApi.update(props.booking.id, {
        ...payload,
        version: props.booking.version,
      });
    } else {
      saved = await bookingsApi.create(payload);
    }
    emit('saved', saved);
  } catch (error: unknown) {
    if (error instanceof ApiError) {
      if (error.status === 401) return;
      serverErrors.value = Object.fromEntries(
        error.fieldErrors.map((entry) => [entry.field, entry.message]),
      );
      conflicts.value = error.conflicts;
      globalError.value =
        error.code === 'STALE_VERSION'
          ? 'This booking changed while you were editing it. Close this form, reopen the booking and try again.'
          : error.detail;
    } else {
      globalError.value = errorMessage(error);
    }
  } finally {
    saving.value = false;
  }
}

function requestClose(): void {
  if (!saving.value) emit('close');
}
</script>

<template>
  <ModalDialog
    :title="props.mode === 'edit' ? 'Edit booking' : 'New booking'"
    :subtitle="subtitle"
    size="lg"
    @close="requestClose"
  >
    <form :id="formId" class="form" novalidate @submit.prevent="submit">
      <p v-if="globalError" class="alert alert--error" role="alert">{{ globalError }}</p>

      <div v-if="conflicts.length" class="alert alert--warning" role="alert">
        <strong>That room is already booked at this time.</strong>
        <ul class="conflict-list">
          <li v-for="conflict in conflicts" :key="conflict.bookingId || conflict.start">
            <strong>{{ conflict.title }}</strong>
            <span class="muted">
              {{ formatTimeRange(conflict.start, conflict.end) }} · {{ conflict.organiser }}
            </span>
          </li>
        </ul>
        <p class="alert__hint">Choose another time or room, then try again.</p>
      </div>

      <div class="form-grid">
        <FormField
          class="span-2"
          v-slot="{ id }"
          label="Title"
          required
          :error="errorFor('title')"
        >
          <input
            :id="id"
            v-model="form.title"
            type="text"
            maxlength="160"
            placeholder="e.g. Weekly design review"
            data-autofocus
          />
        </FormField>

        <FormField
          v-slot="{ id }"
          label="Room"
          required
          :error="errorFor('roomId')"
          :hint="selectedRoom ? `${roomLocation(selectedRoom)} · ${selectedRoom.capacity} seats` : undefined"
        >
          <select :id="id" v-model="form.roomId">
            <option v-for="room in props.rooms" :key="room.id" :value="room.id">
              {{ room.name }} · {{ room.capacity }} seats
            </option>
          </select>
        </FormField>

        <FormField v-slot="{ id }" label="Date" required :error="errorFor('date')">
          <input :id="id" v-model="form.date" type="date" />
        </FormField>

        <FormField v-slot="{ id }" label="Start time" required :error="errorFor('startTime', 'start')">
          <input :id="id" v-model="form.startTime" type="time" step="900" min="09:00" max="18:00" />
        </FormField>

        <FormField
          v-slot="{ id }"
          label="End time"
          required
          :error="errorFor('endTime', 'end')"
          hint="Office hours: 09:00–18:00"
        >
          <input :id="id" v-model="form.endTime" type="time" step="900" min="09:00" max="18:00" />
        </FormField>

        <FormField v-slot="{ id }" label="Organiser" required :error="errorFor('organiser')">
          <input :id="id" v-model="form.organiser" type="text" maxlength="120" autocomplete="name" />
        </FormField>

        <FormField
          v-slot="{ id }"
          label="Organiser email"
          :error="errorFor('organiserEmail')"
          hint="Optional — used in calendar invites."
        >
          <input :id="id" v-model="form.organiserEmail" type="email" maxlength="160" autocomplete="email" />
        </FormField>

        <FormField
          v-slot="{ id }"
          label="Attendees"
          required
          :error="errorFor('attendeeCount')"
          :hint="selectedRoom ? `Capacity ${selectedRoom.capacity}` : undefined"
        >
          <input :id="id" v-model.number="form.attendeeCount" type="number" min="1" max="1000" />
        </FormField>

        <FormField
          v-slot="{ id }"
          label="Named attendees"
          :error="errorFor('attendees')"
          hint="Optional, comma separated. Must match the count."
        >
          <input
            :id="id"
            v-model="form.attendeeNames"
            type="text"
            placeholder="Ada, Grace, Alan"
          />
        </FormField>

        <FormField
          class="span-2"
          v-slot="{ id }"
          label="Description"
          :error="errorFor('description')"
        >
          <textarea
            :id="id"
            v-model="form.description"
            rows="3"
            maxlength="1000"
            placeholder="Agenda, dial-in details, anything useful…"
          />
        </FormField>
      </div>
    </form>

    <template #footer>
      <button type="button" class="btn btn--ghost" :disabled="saving" @click="requestClose">
        Cancel
      </button>
      <button type="submit" class="btn btn--primary" :form="formId" :disabled="saving">
        <span v-if="saving" class="spinner spinner--light" aria-hidden="true" />
        {{ saving ? 'Saving…' : submitLabel }}
      </button>
    </template>
  </ModalDialog>
</template>
