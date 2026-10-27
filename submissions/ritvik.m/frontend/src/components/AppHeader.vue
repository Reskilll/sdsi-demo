<script setup lang="ts">
import { initials } from '../utils/display';
import type { TabId } from '../types/ui';

defineProps<{
  username: string;
  modelValue: TabId;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: TabId];
  logout: [];
}>();

const tabs: ReadonlyArray<{ id: TabId; label: string }> = [
  { id: 'day', label: 'Day view' },
  { id: 'find', label: 'Find a slot' },
  { id: 'recurring', label: 'Recurring' },
];

function select(id: TabId): void {
  emit('update:modelValue', id);
}
</script>

<template>
  <header class="app-header">
    <div class="app-header__inner">
      <div class="brand">
        <span class="brand__mark" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <rect x="3.5" y="5" width="17" height="15.5" rx="3" />
            <path d="M3.5 9.5h17M8 3v4M16 3v4" />
            <path d="M7.5 13h3v3h-3z" class="brand__mark-fill" />
          </svg>
        </span>
        <span class="brand__text">
          <strong>Roomline</strong>
          <small>Meeting rooms, simplified</small>
        </span>
      </div>

      <nav class="tabs" aria-label="Sections">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          type="button"
          class="tabs__button"
          :class="{ 'tabs__button--active': modelValue === tab.id }"
          :aria-current="modelValue === tab.id ? 'page' : undefined"
          @click="select(tab.id)"
        >
          {{ tab.label }}
        </button>
      </nav>

      <div class="user-menu">
        <span class="avatar" aria-hidden="true">{{ initials(username) }}</span>
        <span class="user-menu__name" :title="username">{{ username }}</span>
        <button type="button" class="btn btn--ghost btn--sm" @click="emit('logout')">
          Log out
        </button>
      </div>
    </div>
  </header>
</template>
