<script setup lang="ts">
import type { OccurrenceView } from '../api/types';
import { formatDate, formatTimeRange } from '../utils/time';

withDefaults(
  defineProps<{
    occurrences: OccurrenceView[];
    caption?: string;
  }>(),
  { caption: 'Recurring occurrences and conflicts' },
);
</script>

<template>
  <div class="table-wrap">
    <table class="data-table occurrence-table">
      <caption class="sr-only">{{ caption }}</caption>
      <thead>
        <tr>
          <th scope="col">Date</th>
          <th scope="col">Time</th>
          <th scope="col">Status</th>
          <th scope="col">Clashes with</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="occurrence in occurrences"
          :key="`${occurrence.start}-${occurrence.status}`"
          :class="{ 'row--conflict': occurrence.status === 'CONFLICT' }"
        >
          <td data-label="Date">{{ formatDate(occurrence.start) }}</td>
          <td data-label="Time">{{ formatTimeRange(occurrence.start, occurrence.end) }}</td>
          <td data-label="Status">
            <span
              class="badge"
              :class="occurrence.status === 'CONFLICT' ? 'badge--danger' : 'badge--success'"
            >
              {{ occurrence.status === 'CONFLICT' ? 'Conflict' : 'Free' }}
            </span>
          </td>
          <td data-label="Clashes with">
            <ul v-if="occurrence.conflicts.length" class="conflict-list">
              <li v-for="conflict in occurrence.conflicts" :key="conflict.bookingId || conflict.start">
                <strong>{{ conflict.title }}</strong>
                <span class="muted">
                  {{ formatTimeRange(conflict.start, conflict.end) }} · {{ conflict.organiser }}
                </span>
              </li>
            </ul>
            <span v-else class="muted">No clash</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
