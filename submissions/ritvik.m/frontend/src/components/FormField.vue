<script setup lang="ts">
import { useId } from 'vue';

defineProps<{
  label: string;
  hint?: string;
  error?: string;
  required?: boolean;
}>();

const id = useId();
</script>

<template>
  <div class="field" :class="{ 'field--invalid': Boolean(error) }">
    <label class="field__label" :for="id">
      {{ label }}
      <span v-if="required" class="field__req" aria-hidden="true">*</span>
    </label>
    <slot :id="id" />
    <p v-if="error" class="field__error">{{ error }}</p>
    <p v-else-if="hint" class="field__hint">{{ hint }}</p>
  </div>
</template>
