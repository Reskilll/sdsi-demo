<script setup lang="ts">
import { useToasts } from '../composables/toasts';

const { toasts, dismiss } = useToasts();
</script>

<template>
  <div class="toast-host" aria-live="polite" aria-atomic="false">
    <TransitionGroup name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="toast"
        :class="`toast--${toast.kind}`"
        :role="toast.kind === 'error' ? 'alert' : 'status'"
      >
        <span class="toast__dot" aria-hidden="true" />
        <p class="toast__message">{{ toast.message }}</p>
        <button
          type="button"
          class="toast__close"
          aria-label="Dismiss notification"
          @click="dismiss(toast.id)"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>
