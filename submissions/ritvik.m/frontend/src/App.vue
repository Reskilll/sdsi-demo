<script setup lang="ts">
import { ref, watch } from 'vue';
import { ApiError, errorMessage } from './api/client';
import { roomsApi } from './api/rooms';
import type { Room } from './api/types';
import { useAuth } from './composables/auth';
import { useToasts } from './composables/toasts';
import type { TabId } from './types/ui';
import AppHeader from './components/AppHeader.vue';
import LoginScreen from './components/LoginScreen.vue';
import ToastHost from './components/ToastHost.vue';
import DayView from './views/DayView.vue';
import FindSlotView from './views/FindSlotView.vue';
import RecurringView from './views/RecurringView.vue';

const { isAuthenticated, username, logout } = useAuth();
const { notify } = useToasts();

const activeTab = ref<TabId>('day');
const rooms = ref<Room[]>([]);
const roomsLoading = ref(false);
const roomsError = ref('');

let roomsSequence = 0;

async function loadRooms(): Promise<void> {
  const sequence = ++roomsSequence;
  roomsLoading.value = true;
  roomsError.value = '';
  try {
    const result = await roomsApi.list();
    if (sequence !== roomsSequence) return;
    rooms.value = result;
  } catch (error: unknown) {
    if (sequence !== roomsSequence) return;
    if (error instanceof ApiError && error.status === 401) return;
    roomsError.value = errorMessage(error);
    notify(roomsError.value, 'error');
  } finally {
    if (sequence === roomsSequence) roomsLoading.value = false;
  }
}

watch(
  isAuthenticated,
  (authenticated) => {
    if (authenticated) {
      void loadRooms();
    } else {
      rooms.value = [];
      roomsError.value = '';
      activeTab.value = 'day';
    }
  },
  { immediate: true },
);

function handleLogout(): void {
  logout();
  notify('You have been signed out.', 'info');
}
</script>

<template>
  <div class="app-shell">
    <template v-if="isAuthenticated">
      <AppHeader v-model="activeTab" :username="username" @logout="handleLogout" />

      <main id="main-content" class="app-main">
        <div v-if="roomsLoading && rooms.length === 0" class="card app-loading" aria-busy="true">
          <span class="spinner" aria-hidden="true" />
          <div>
            <h1>Loading rooms</h1>
            <p class="muted">Getting the room catalogue ready…</p>
          </div>
        </div>

        <div v-else-if="roomsError" class="card app-loading app-loading--error" role="alert">
          <div>
            <h1>Rooms could not be loaded</h1>
            <p class="muted">{{ roomsError }}</p>
            <button type="button" class="btn btn--secondary" @click="loadRooms">Try again</button>
          </div>
        </div>

        <template v-else>
          <DayView v-if="activeTab === 'day'" :rooms="rooms" />
          <FindSlotView v-else-if="activeTab === 'find'" :rooms="rooms" :username="username" />
          <RecurringView v-else :rooms="rooms" :username="username" />
        </template>
      </main>

      <footer class="app-footer">
        <span>Roomline</span>
        <span class="muted">Office hours 09:00–18:00 · Times shown in office-local wall clock</span>
      </footer>
    </template>

    <LoginScreen v-else />

    <ToastHost />
  </div>
</template>
