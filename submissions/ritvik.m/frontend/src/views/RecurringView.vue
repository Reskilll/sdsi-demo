<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue';
import { ApiError, errorMessage } from '../api/client';
import { recurringApi, seriesApi } from '../api/series';
import type {
  DayOfWeek,
  OccurrenceView,
  RecurringBookingPayload,
  RecurringCreateResponse,
  RecurringPreviewResponse,
  Room,
  SeriesDetail,
  SeriesSummary,
} from '../api/types';
import { useToasts } from '../composables/toasts';
import {
  parseAttendeeNames,
  pluralize,
  roomLocation,
  scheduleSummary,
  sortedWeekdays,
} from '../utils/display';
import {
  WEEKDAY_LABELS,
  WEEKDAY_ORDER,
  formatDate,
  formatTimeRange,
  isoLocalNow,
  parseDateParts,
  todayISO,
  validateWindow,
  weekdayOf,
} from '../utils/time';
import FormField from '../components/FormField.vue';
import OccurrenceTable from '../components/OccurrenceTable.vue';

const props = defineProps<{
  rooms: Room[];
  username: string;
}>();

const { notify } = useToasts();

const initialWeekday = weekdayOf(todayISO()) ?? 'MONDAY';

const form = reactive({
  roomId: props.rooms[0]?.id ?? '',
  title: '',
  organiser: props.username,
  organiserEmail: '',
  description: '',
  startsOn: todayISO(),
  startTime: '10:00',
  endTime: '11:00',
  daysOfWeek: [initialWeekday] as DayOfWeek[],
  weeks: 4,
  attendeeCount: 4,
  attendeeNames: '',
  skipConflicts: false,
});

const daysTouched = ref(false);
const localErrors = ref<LocalErrors>({});
const serverErrors = ref<Record<string, string>>({});
const globalError = ref('');
const previewing = ref(false);
const creating = ref(false);
const preview = ref<RecurringPreviewResponse | null>(null);
const conflictError = ref<ApiError | null>(null);
const createResult = ref<RecurringCreateResponse | null>(null);

type FieldKey =
  | 'roomId'
  | 'title'
  | 'organiser'
  | 'organiserEmail'
  | 'description'
  | 'startsOn'
  | 'startTime'
  | 'endTime'
  | 'weekdays'
  | 'weeks'
  | 'attendeeCount'
  | 'attendees';

type LocalErrors = Partial<Record<FieldKey, string>>;

const selectedRoom = computed(() =>
  props.rooms.find((room) => room.id === form.roomId) ?? null,
);

const hasConflicts = computed(() => {
  if (conflictError.value) return true;
  return (preview.value?.conflictCount ?? 0) > 0;
});

const displayedOccurrences = computed<OccurrenceView[]>(() => {
  if (conflictError.value && conflictError.value.occurrences.length > 0) {
    return conflictError.value.occurrences;
  }
  return preview.value?.occurrences ?? [];
});

const displayedConflictCount = computed(() => {
  if (conflictError.value) {
    return (
      conflictError.value.conflictCount ??
      conflictError.value.occurrences.filter((occurrence) => occurrence.status === 'CONFLICT').length
    );
  }
  return preview.value?.conflictCount ?? 0;
});

const displayedTotal = computed(() => {
  if (conflictError.value) {
    return (
      conflictError.value.totalOccurrences ??
      conflictError.value.occurrences.length
    );
  }
  return preview.value?.occurrenceCount ?? 0;
});

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

watch(
  () => form.startsOn,
  (value) => {
    if (daysTouched.value) return;
    const day = weekdayOf(value);
    form.daysOfWeek = day ? [day] : [];
  },
);

/**
 * Reset stale feedback when the request changes. skipConflicts is deliberately
 * excluded: ticking "skip conflicts" after a 409 must keep the conflict report
 * (and the checkbox itself) visible.
 */
const formSignature = computed(() =>
  [
    form.roomId,
    form.title,
    form.organiser,
    form.organiserEmail,
    form.description,
    form.startsOn,
    form.startTime,
    form.endTime,
    form.daysOfWeek.join(','),
    form.weeks,
    form.attendeeCount,
    form.attendeeNames,
  ].join('|'),
);

watch(formSignature, () => {
  if (previewing.value || creating.value) return;
  localErrors.value = {};
  preview.value = null;
  createResult.value = null;
  conflictError.value = null;
  serverErrors.value = {};
  globalError.value = '';
});

function toggleDay(day: DayOfWeek): void {
  daysTouched.value = true;
  const index = form.daysOfWeek.indexOf(day);
  if (index >= 0) form.daysOfWeek.splice(index, 1);
  else form.daysOfWeek.push(day);
  form.daysOfWeek = sortedWeekdays(form.daysOfWeek);
}

function isDaySelected(day: DayOfWeek): boolean {
  return form.daysOfWeek.includes(day);
}

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
  if (!title) errors.title = 'Give the series a title.';
  else if (title.length > 160) errors.title = 'Keep the title under 160 characters.';

  const organiser = form.organiser.trim();
  if (!organiser) errors.organiser = 'Who is organising this series?';
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

  if (!parseDateParts(form.startsOn)) errors.startsOn = 'Choose a valid start date.';

  const windowError = validateWindow(form.startTime, form.endTime);
  if (windowError) errors.endTime = windowError;

  const weeks = Number(form.weeks);
  if (!Number.isInteger(weeks) || weeks < 1 || weeks > 52) {
    errors.weeks = 'Weeks must be a whole number between 1 and 52.';
  }

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

  // An empty selection is allowed: the backend falls back to startsOn's weekday.
  return errors;
}

function focusFirstInvalid(): void {
  void nextTick(() => {
    const target = document.querySelector<HTMLElement>(
      '.recurring-form .field--invalid input:not([type="hidden"]):not([disabled]), .recurring-form .field--invalid select:not([disabled]), .recurring-form .field--invalid textarea:not([disabled])',
    );
    target?.focus();
  });
}

function buildPayload(): RecurringBookingPayload | null {
  const errors = validate();
  localErrors.value = errors;
  if (Object.keys(errors).length > 0) {
    focusFirstInvalid();
    return null;
  }

  const payload: RecurringBookingPayload = {
    roomId: form.roomId,
    organiser: form.organiser.trim(),
    title: form.title.trim(),
    startsOn: form.startsOn,
    startTime: form.startTime,
    endTime: form.endTime,
    weeks: Number(form.weeks),
    attendeeCount: Number(form.attendeeCount),
    skipConflicts: form.skipConflicts,
  };

  const email = form.organiserEmail.trim();
  if (email) payload.organiserEmail = email;
  const description = form.description.trim();
  if (description) payload.description = description;
  const names = parseAttendeeNames(form.attendeeNames);
  if (names.length > 0) payload.attendees = names;
  if (form.daysOfWeek.length > 0) payload.daysOfWeek = sortedWeekdays(form.daysOfWeek);
  return payload;
}

function resetFeedback(): void {
  globalError.value = '';
  serverErrors.value = {};
  conflictError.value = null;
}

async function previewSeries(): Promise<void> {
  if (previewing.value || creating.value) return;
  const payload = buildPayload();
  if (!payload) return;
  resetFeedback();
  preview.value = null;
  createResult.value = null;
  previewing.value = true;
  try {
    preview.value = await recurringApi.preview(payload);
  } catch (error: unknown) {
    if (error instanceof ApiError) {
      if (error.status === 401) return;
      serverErrors.value = Object.fromEntries(
        error.fieldErrors.map((entry) => [entry.field, entry.message]),
      );
      globalError.value = error.detail;
    } else {
      globalError.value = errorMessage(error);
    }
  } finally {
    previewing.value = false;
  }
}

async function createSeries(): Promise<void> {
  if (previewing.value || creating.value) return;
  const payload = buildPayload();
  if (!payload) return;
  resetFeedback();
  creating.value = true;
  try {
    const result = await recurringApi.create(payload);
    createResult.value = result;
    preview.value = null;
    notify(result.message ?? 'Recurring series created.', 'success', 7000);
    await loadSeries(0);
  } catch (error: unknown) {
    if (error instanceof ApiError) {
      if (error.status === 401) return;
      serverErrors.value = Object.fromEntries(
        error.fieldErrors.map((entry) => [entry.field, entry.message]),
      );
      if (error.occurrences.length > 0) {
        conflictError.value = error;
      } else {
        globalError.value = error.detail;
      }
    } else {
      globalError.value = errorMessage(error);
    }
  } finally {
    creating.value = false;
  }
}

/* ------------------------------- series list ------------------------------ */

const seriesItems = ref<SeriesSummary[]>([]);
const seriesLoading = ref(false);
const seriesError = ref('');
const seriesPage = ref(0);
const seriesTotalPages = ref(0);
const seriesTotalElements = ref(0);
const expandedId = ref<string | null>(null);
const detailById = ref<Record<string, SeriesDetail>>({});
const detailLoadingId = ref<string | null>(null);
const detailError = ref('');
const confirmCancelId = ref<string | null>(null);
const cancellingId = ref<string | null>(null);

let seriesSequence = 0;

const expandedDetail = computed(() =>
  expandedId.value ? (detailById.value[expandedId.value] ?? null) : null,
);

async function loadSeries(page = 0): Promise<void> {
  const sequence = ++seriesSequence;
  seriesLoading.value = true;
  seriesError.value = '';
  try {
    const response = await seriesApi.list(page, 10);
    if (sequence !== seriesSequence) return;
    seriesItems.value = response.content;
    seriesPage.value = response.page;
    seriesTotalPages.value = response.totalPages;
    seriesTotalElements.value = response.totalElements;
  } catch (error: unknown) {
    if (sequence !== seriesSequence) return;
    if (error instanceof ApiError && error.status === 401) return;
    seriesError.value = errorMessage(error);
  } finally {
    if (sequence === seriesSequence) seriesLoading.value = false;
  }
}

async function loadDetail(id: string): Promise<void> {
  detailLoadingId.value = id;
  detailError.value = '';
  try {
    const detail = await seriesApi.get(id);
    detailById.value = { ...detailById.value, [id]: detail };
  } catch (error: unknown) {
    if (error instanceof ApiError && error.status === 401) return;
    detailError.value = errorMessage(error);
  } finally {
    if (detailLoadingId.value === id) detailLoadingId.value = null;
  }
}

function toggleDetails(series: SeriesSummary): void {
  if (expandedId.value === series.id) {
    expandedId.value = null;
    return;
  }
  expandedId.value = series.id;
  detailError.value = '';
  if (!detailById.value[series.id]) void loadDetail(series.id);
}

function requestCancel(series: SeriesSummary): void {
  confirmCancelId.value = series.id;
}

async function cancelFuture(series: SeriesSummary): Promise<void> {
  if (cancellingId.value) return;
  cancellingId.value = series.id;
  try {
    const result = await seriesApi.cancelFuture(series.id, isoLocalNow());
    notify(
      `${result.cancelledCount} future ${pluralize(result.cancelledCount, 'occurrence')} cancelled.`,
      'success',
    );
    confirmCancelId.value = null;
    const nextDetails = { ...detailById.value };
    delete nextDetails[series.id];
    detailById.value = nextDetails;
    if (expandedId.value === series.id) void loadDetail(series.id);
    await loadSeries(seriesPage.value);
  } catch (error: unknown) {
    if (error instanceof ApiError && error.status === 401) return;
    notify(errorMessage(error), 'error');
  } finally {
    cancellingId.value = null;
  }
}

void loadSeries(0);
</script>

<template>
  <section class="view">
    <header class="view-head">
      <div class="view-head__copy">
        <p class="eyebrow">Recurring</p>
        <h1>Repeat meetings, without surprises</h1>
        <p class="muted">
          Preview every occurrence before you commit, then skip only the slots that clash.
        </p>
      </div>
    </header>

    <div class="recurring-layout">
      <form class="card recurring-form" novalidate @submit.prevent="createSeries">
        <div class="section-heading">
          <h2>New recurring series</h2>
          <span class="badge badge--soft">Weekly pattern</span>
        </div>

        <p v-if="globalError" class="alert alert--error" role="alert">{{ globalError }}</p>

        <div class="form-grid">
          <FormField
            class="span-2"
            v-slot="{ id }"
            label="Title"
            required
            :error="errorFor('title')"
          >
            <input :id="id" v-model="form.title" type="text" maxlength="160" placeholder="e.g. Sprint planning" />
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

          <FormField v-slot="{ id }" label="Organiser" required :error="errorFor('organiser')">
            <input :id="id" v-model="form.organiser" type="text" maxlength="120" autocomplete="name" />
          </FormField>

          <FormField v-slot="{ id }" label="Organiser email" :error="errorFor('organiserEmail')">
            <input :id="id" v-model="form.organiserEmail" type="email" maxlength="160" autocomplete="email" />
          </FormField>

          <FormField
            v-slot="{ id }"
            label="Weeks"
            required
            :error="errorFor('weeks')"
            hint="1–52 weeks"
          >
            <input :id="id" v-model.number="form.weeks" type="number" min="1" max="52" />
          </FormField>

          <FormField
            v-slot="{ id }"
            label="First date"
            required
            :error="errorFor('startsOn')"
            hint="Occurrences start on or after this date."
          >
            <input :id="id" v-model="form.startsOn" type="date" />
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

          <FormField
            class="span-2"
            v-slot="{ id }"
            label="Named attendees"
            :error="errorFor('attendees')"
            hint="Optional, comma separated. Must match the count."
          >
            <input :id="id" v-model="form.attendeeNames" type="text" placeholder="Ada, Grace, Alan" />
          </FormField>

          <fieldset
            class="field span-2 weekday-field"
            :class="{ 'field--invalid': Boolean(errorFor('weekdays', 'daysOfWeek')) }"
          >
            <legend class="field__label">Weekdays</legend>
            <div class="weekday-picker">
              <button
                v-for="day in WEEKDAY_ORDER"
                :key="day"
                type="button"
                class="weekday-toggle"
                :class="{ 'weekday-toggle--active': isDaySelected(day) }"
                :aria-pressed="isDaySelected(day)"
                @click="toggleDay(day)"
              >
                {{ WEEKDAY_LABELS[day].short }}
              </button>
            </div>
            <p v-if="errorFor('weekdays', 'daysOfWeek')" class="field__error">
              {{ errorFor('weekdays', 'daysOfWeek') }}
            </p>
            <p v-else class="field__hint">
              Leave all clear to repeat on the first date’s weekday. Selected days are ordered
              Monday–Sunday.
            </p>
          </fieldset>

          <FormField
            class="span-2"
            v-slot="{ id }"
            label="Description"
            :error="errorFor('description')"
          >
            <textarea
              :id="id"
              v-model="form.description"
              rows="2"
              maxlength="1000"
              placeholder="Agenda, dial-in details, anything useful…"
            />
          </FormField>
        </div>

        <label v-if="hasConflicts" class="checkbox checkbox--emphasis">
          <input v-model="form.skipConflicts" type="checkbox" />
          <span>
            Skip conflicting occurrences and create the rest
            <small>
              {{ displayedConflictCount }} of {{ displayedTotal }} occurrences clash. Leave this
              unchecked to let the backend reject the whole series.
            </small>
          </span>
        </label>

        <div class="form-actions">
          <button
            type="button"
            class="btn btn--secondary"
            :disabled="previewing || creating"
            @click="previewSeries"
          >
            <span v-if="previewing" class="spinner" aria-hidden="true" />
            {{ previewing ? 'Checking…' : 'Preview conflicts' }}
          </button>
          <button type="submit" class="btn btn--primary" :disabled="previewing || creating">
            <span v-if="creating" class="spinner spinner--light" aria-hidden="true" />
            {{ creating ? 'Creating…' : 'Create series' }}
          </button>
        </div>
      </form>

      <div class="preview-stack">
        <section v-if="createResult" class="card create-summary" aria-live="polite">
          <div class="section-heading">
            <h2>Series created</h2>
            <span class="badge badge--success">Done</span>
          </div>
          <p class="create-summary__message">
            {{ createResult.message ?? 'The recurring series was created.' }}
          </p>
          <div class="stat-grid">
            <div class="stat">
              <span class="stat__value">{{ createResult.created.length }}</span>
              <span class="stat__label">created</span>
            </div>
            <div class="stat" :class="{ 'stat--danger': createResult.skipped.length > 0 }">
              <span class="stat__value">{{ createResult.skipped.length }}</span>
              <span class="stat__label">skipped</span>
            </div>
            <div class="stat">
              <span class="stat__value">{{ createResult.series.weeks }}</span>
              <span class="stat__label">weeks</span>
            </div>
          </div>
          <details v-if="createResult.skipped.length" class="details-block">
            <summary>Skipped occurrences ({{ createResult.skipped.length }})</summary>
            <OccurrenceTable :occurrences="createResult.skipped" caption="Skipped occurrences" />
          </details>
          <p class="muted">The new series is listed under “Existing series” below.</p>
        </section>

        <section class="card preview-card" aria-live="polite">
          <div class="section-heading">
            <h2>Conflict preview</h2>
            <span v-if="preview" class="badge badge--soft">{{ preview.occurrenceCount }} occurrences</span>
          </div>

          <div v-if="previewing" class="loading-block" aria-busy="true">
            <span class="spinner" aria-hidden="true" /> Checking every occurrence…
          </div>

          <template v-else-if="conflictError">
            <p class="alert alert--error" role="alert">
              <strong>No series was created.</strong>
              {{ conflictError.detail }}
            </p>
            <div class="stat-grid">
              <div class="stat stat--danger">
                <span class="stat__value">{{ displayedConflictCount }}</span>
                <span class="stat__label">conflicts</span>
              </div>
              <div class="stat">
                <span class="stat__value">{{ displayedTotal }}</span>
                <span class="stat__label">occurrences</span>
              </div>
            </div>
            <OccurrenceTable
              :occurrences="displayedOccurrences"
              caption="Conflicting occurrences returned by the server"
            />
            <p class="alert alert--warning">
              {{ displayedConflictCount }} of {{ displayedTotal }} occurrences clash. Tick
              “Skip conflicting occurrences” in the form and create again to keep the free slots.
            </p>
          </template>

          <template v-else-if="preview">
            <div class="stat-grid">
              <div class="stat">
                <span class="stat__value">{{ preview.occurrenceCount }}</span>
                <span class="stat__label">occurrences</span>
              </div>
              <div class="stat" :class="{ 'stat--danger': preview.conflictCount > 0 }">
                <span class="stat__value">{{ preview.conflictCount }}</span>
                <span class="stat__label">conflicts</span>
              </div>
              <div class="stat">
                <span class="stat__value">{{ preview.daysOfWeek.length }}</span>
                <span class="stat__label">weekdays</span>
              </div>
            </div>

            <p v-if="preview.conflictCount === 0" class="alert alert--success">
              All {{ preview.occurrenceCount }} occurrences are free.
            </p>
            <p v-else class="alert alert--warning">
              {{ preview.conflictCount }} of {{ preview.occurrenceCount }} occurrences clash with
              existing bookings. Tick the skip option in the form to create only the free ones.
            </p>

            <OccurrenceTable
              :occurrences="preview.occurrences"
              caption="Preview of recurring occurrences"
            />
          </template>

          <div v-else class="empty-state empty-state--inline">
            <h3>Not previewed yet</h3>
            <p>Run “Preview conflicts” to see each occurrence, its status and any clashing bookings.</p>
          </div>
        </section>
      </div>
    </div>

    <section class="card series-section" aria-labelledby="series-title">
      <div class="section-heading">
        <div>
          <h2 id="series-title">Existing series</h2>
          <p class="muted">Cancel future occurrences without disturbing the past.</p>
        </div>
        <div class="section-heading__actions">
          <span class="muted">{{ seriesTotalElements }} total</span>
          <button
            type="button"
            class="btn btn--ghost btn--sm"
            :disabled="seriesLoading"
            @click="loadSeries(seriesPage)"
          >
            Refresh
          </button>
        </div>
      </div>

      <p v-if="seriesError" class="alert alert--error" role="alert">
        {{ seriesError }}
        <button type="button" class="btn btn--ghost btn--sm" @click="loadSeries(seriesPage)">
          Retry
        </button>
      </p>

      <div v-if="seriesLoading && seriesItems.length === 0" class="loading-block" aria-busy="true">
        <span class="spinner" aria-hidden="true" /> Loading series…
      </div>

      <div v-else-if="seriesItems.length === 0" class="empty-state empty-state--inline">
        <h3>No recurring series yet</h3>
        <p>Create one above and it will appear here with its full occurrence history.</p>
      </div>

      <div v-else class="series-list" :class="{ 'is-loading': seriesLoading }">
        <article v-for="series in seriesItems" :key="series.id" class="series-card">
          <div class="series-card__head">
            <div class="series-card__copy">
              <div class="series-card__title-row">
                <h3>{{ series.title }}</h3>
                <span class="badge badge--soft">{{ series.weeks }} {{ pluralize(series.weeks, 'week') }}</span>
              </div>
              <p class="muted">
                {{ series.room.name }} · {{ roomLocation(series.room) }} · {{ series.attendeeCount }}
                {{ series.attendeeCount === 1 ? 'person' : 'people' }}
              </p>
            </div>
            <div class="series-card__actions">
              <button type="button" class="btn btn--ghost btn--sm" @click="toggleDetails(series)">
                {{ expandedId === series.id ? 'Hide details' : 'Details' }}
              </button>
              <button
                type="button"
                class="btn btn--ghost btn--sm btn--danger-text"
                @click="requestCancel(series)"
              >
                Cancel future
              </button>
            </div>
          </div>

          <div class="series-card__schedule">
            <span class="chip chip--soft">
              {{ scheduleSummary(series.daysOfWeek, series.startTime, series.endTime) }}
            </span>
            <span class="muted">Starts {{ formatDate(series.startsOn) }}</span>
            <span class="muted">Organised by {{ series.organiser }}</span>
          </div>

          <div v-if="confirmCancelId === series.id" class="confirm-box confirm-box--danger">
            <p>
              Cancel all confirmed occurrences from now onwards? Past occurrences stay in the
              record.
            </p>
            <div class="confirm-box__actions">
              <button type="button" class="btn btn--ghost btn--sm" @click="confirmCancelId = null">
                Keep series
              </button>
              <button
                type="button"
                class="btn btn--danger btn--sm"
                :disabled="cancellingId === series.id"
                @click="cancelFuture(series)"
              >
                <span v-if="cancellingId === series.id" class="spinner spinner--light" aria-hidden="true" />
                Yes, cancel future
              </button>
            </div>
          </div>

          <div v-if="expandedId === series.id" class="series-details">
            <div v-if="detailLoadingId === series.id" class="loading-block" aria-busy="true">
              <span class="spinner" aria-hidden="true" /> Loading occurrences…
            </div>
            <p v-else-if="detailError" class="alert alert--error" role="alert">{{ detailError }}</p>
            <template v-else-if="expandedDetail">
              <p v-if="expandedDetail.description" class="pre-line">{{ expandedDetail.description }}</p>
              <div v-if="expandedDetail.attendees?.length" class="chip-list">
                <span v-for="name in expandedDetail.attendees" :key="name" class="chip">
                  {{ name }}
                </span>
              </div>
              <ul class="series-occurrences">
                <li v-for="occurrence in expandedDetail.occurrences" :key="occurrence.id">
                  <span class="series-occurrences__time">
                    {{ formatDate(occurrence.start) }} · {{ formatTimeRange(occurrence.start, occurrence.end) }}
                  </span>
                  <span class="muted">#{{ occurrence.occurrenceIndex ?? '—' }}</span>
                  <span
                    class="badge"
                    :class="occurrence.status === 'CONFIRMED' ? 'badge--success' : 'badge--muted'"
                  >
                    {{ occurrence.status === 'CONFIRMED' ? 'Confirmed' : 'Cancelled' }}
                  </span>
                </li>
              </ul>
              <p v-if="expandedDetail.occurrences.length === 0" class="muted">
                This series has no stored occurrences.
              </p>
            </template>
          </div>
        </article>
      </div>

      <div v-if="seriesTotalPages > 1" class="pager">
        <button
          type="button"
          class="btn btn--ghost btn--sm"
          :disabled="seriesPage <= 0 || seriesLoading"
          @click="loadSeries(seriesPage - 1)"
        >
          Previous
        </button>
        <span class="muted">Page {{ seriesPage + 1 }} of {{ seriesTotalPages }}</span>
        <button
          type="button"
          class="btn btn--ghost btn--sm"
          :disabled="seriesPage >= seriesTotalPages - 1 || seriesLoading"
          @click="loadSeries(seriesPage + 1)"
        >
          Next
        </button>
      </div>
    </section>
  </section>
</template>
