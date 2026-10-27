# Roomline frontend

Vue 3 + TypeScript + Vite SPA for the meeting-room booking backend.

## Run

Start the backend first (from the submission root):

```bash
cd ../backend
mvn spring-boot:run
```

Then, in this directory:

```bash
npm install
npm run dev
```

Open the URL printed by Vite (normally <http://localhost:5173>) and sign in with
`admin` / `admin123`.

`/api` requests are proxied to `http://localhost:8080` by `vite.config.ts`, so no CORS
configuration is needed in development.

## Checks and build

```bash
npm test          # Vitest unit tests
npm run build     # vue-tsc type-check + production build into dist/
npm run preview   # serve the production build locally
```

For a single deployable jar, build the backend with its `frontend` profile:

```bash
cd ../backend
mvn -Pfrontend package
java -jar target/room-booking-1.0.0.jar
```

The UI is then served at <http://localhost:8080>.

## Structure

```
src/api/          typed fetch client and contract types
src/components/   dialogs, timeline, tables, shared form fields
src/views/        Day view, find-slot, recurring series
src/composables/  auth and toast state
src/utils/        wall-clock time/date helpers (+ tests)
```

Times are office-local wall-clock values (`YYYY-MM-DDTHH:mm:ss`, no timezone offset);
the UI never converts them with `Date` timezone logic.

The full HTTP contract (payloads, error codes, status codes) is in
[`../API.md`](../API.md).
