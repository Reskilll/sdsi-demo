import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    // better-sqlite3 is a native addon; worker threads can be flaky on Windows.
    pool: 'forks',
    reporters: ['default'],
    clearMocks: true,
    restoreMocks: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      include: ['src/**/*.ts'],
      exclude: ['src/index.ts', 'src/types/**'],
      thresholds: {
        lines: 80,
        statements: 80,
        functions: 75,
        branches: 70,
      },
    },
  },
});
