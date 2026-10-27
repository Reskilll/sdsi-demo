<script setup lang="ts">
import { computed, ref } from 'vue';
import { useAuth } from '../composables/auth';

const { login, busy, notice } = useAuth();

const username = ref('');
const password = ref('');
const error = ref('');
const showPassword = ref(false);
const successHint = computed(() => notice.value);

async function submit(): Promise<void> {
  error.value = '';
  const result = await login(username.value, password.value);
  if (!result.ok) {
    error.value = result.message ?? 'Sign in failed.';
    password.value = '';
  }
}
</script>

<template>
  <main class="login-shell">
    <section class="login-card" aria-labelledby="login-title">
      <aside class="login-brand">
        <div class="brand brand--on-dark">
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

        <div class="login-brand__copy">
          <h1>Find the right room,<br />at the right time.</h1>
          <p>One place for room availability, conflict-free scheduling and recurring meetings.</p>
        </div>

        <ul class="login-brand__features">
          <li><span aria-hidden="true">✓</span> Live day timeline across every room</li>
          <li><span aria-hidden="true">✓</span> Smart slot finder for any group size</li>
          <li><span aria-hidden="true">✓</span> Recurring series with conflict previews</li>
        </ul>
      </aside>

      <div class="login-panel">
        <div class="login-panel__head">
          <p class="eyebrow">Welcome back</p>
          <h2 id="login-title">Sign in to book</h2>
          <p class="muted">
            Use the credentials configured for your booking service. This session stays private to
            this browser tab.
          </p>
        </div>

        <p v-if="successHint && !error" class="alert alert--info" role="status">
          {{ successHint }}
        </p>
        <p v-if="error" class="alert alert--error" role="alert">{{ error }}</p>

        <form class="form" novalidate @submit.prevent="submit">
          <div class="field">
            <label class="field__label" for="login-username">Username</label>
            <input
              id="login-username"
              v-model="username"
              name="username"
              type="text"
              autocomplete="username"
              autocapitalize="none"
              spellcheck="false"
              placeholder="admin"
              required
              data-autofocus
            />
          </div>

          <div class="field">
            <label class="field__label" for="login-password">Password</label>
            <div class="input-with-action">
              <input
                id="login-password"
                v-model="password"
                name="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                required
              />
              <button
                type="button"
                class="input-action"
                :aria-label="showPassword ? 'Hide password' : 'Show password'"
                :aria-pressed="showPassword"
                @click="showPassword = !showPassword"
              >
                {{ showPassword ? 'Hide' : 'Show' }}
              </button>
            </div>
          </div>

          <button type="submit" class="btn btn--primary btn--block btn--lg" :disabled="busy">
            <span v-if="busy" class="spinner spinner--light" aria-hidden="true" />
            {{ busy ? 'Signing in…' : 'Sign in' }}
          </button>
        </form>

        <p class="login-panel__foot">
          Authentication is HTTP Basic. Credentials are kept in sessionStorage and cleared when the
          tab closes or the session expires.
        </p>
      </div>
    </section>
  </main>
</template>
