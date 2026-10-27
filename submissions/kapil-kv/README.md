# IT Service-Desk SLA Tracker

A production-quality IT Service-Desk SLA Tracking application built with Next.js, TypeScript, MongoDB, and Tailwind CSS. Tracks ticket SLAs with accurate business-time calculations, excluding weekends, holidays, and ON_HOLD periods.

## Features

- **Secure Admin Authentication** — JWT-based session authentication with rate limiting
- **Ticket Management** — Create, view, edit, and manage tickets with full status lifecycle
- **SLA Calculation Engine** — Business-time SLA calculations excluding weekends, holidays, and ON_HOLD periods
- **SLA Policy Management** — Configure SLA targets per priority (P1–P4)
- **Holiday Management** — Add, edit, and deactivate holidays excluded from SLA calculations
- **Assignee Group Management** — Organize tickets by support groups
- **Dashboard** — Real-time metrics: total tickets, breached, SLA compliance, status distribution
- **Reports** — Breach analysis by priority and assignee group with CSV export
- **Responsive UI** — Desktop, tablet, and mobile layouts with light/dark mode support

## Technology Stack

| Layer      | Technology                                  |
| ---------- | ------------------------------------------- |
| Frontend   | Next.js 15 (App Router), React 18, TypeScript, Tailwind CSS |
| Backend    | Next.js Route Handlers                      |
| Database   | MongoDB (Mongoose ODM)                      |
| Auth       | jose (JWT), bcryptjs                        |
| Validation | Joi                                         |
| Forms      | React Hook Form                             |
| Charts     | Custom CSS progress bars                    |
| Testing    | Vitest (unit/integration), Playwright (e2e) |
| Code Quality | ESLint, Prettier, strict TypeScript       |

## Prerequisites

- **Node.js** 18+ (v20+ recommended)
- **npm** 9+
- **MongoDB** 7.0+ (local installation or MongoDB Atlas)

## Installation

### 1. Clone and install dependencies

```bash
git clone <repo-url> sla-tracker
cd sla-tracker
npm install
```

### 2. Configure environment variables

Copy the example file and edit values:

```bash
cp .env.example .env.local
```

Key variables to configure:

| Variable              | Description                          |
| --------------------- | ------------------------------------ |
| `MONGODB_URI`         | MongoDB connection string            |
| `ADMIN_EMAIL`         | Initial admin email                  |
| `ADMIN_PASSWORD`      | Initial admin password (min 8 chars) |
| `SESSION_SECRET`      | Long random string (min 32 chars)    |
| `APP_TIMEZONE`        | Business timezone (e.g., Asia/Kolkata) |
| `BUSINESS_START_HOUR` | Business day start hour (0–23)       |
| `BUSINESS_END_HOUR`   | Business day end hour (0–23)         |

### 3. MongoDB Setup

**Local MongoDB:**

```bash
# Start MongoDB (if not running)
mongod --dbpath /path/to/data

# The default connection string in .env.example:
# mongodb://127.0.0.1:27017/sla_tracker
```

**MongoDB Atlas:**

1. Create a cluster at [https://cloud.mongodb.com](https://cloud.mongodb.com)
2. Add your IP to the network access list
3. Create a database user with password
4. Get the connection string and set `MONGODB_URI` in `.env.local`

### 4. Seed the database

```bash
# Create the admin account
npm run seed:admin

# (Optional) Import sample data
npm run seed:sample
```

### 5. Start the development server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Default Admin Credentials

| Field    | Value               |
| -------- | ------------------- |
| Email    | admin@example.com   |
| Password | ChangeMe123!        |

⚠️ **Change the default password after first login.** See the Settings page for instructions.

## Development Commands

| Command              | Description                               |
| -------------------- | ----------------------------------------- |
| `npm run dev`        | Start development server on port 3000     |
| `npm run build`      | Production build                          |
| `npm run start`      | Start production server                   |
| `npm run lint`       | Run ESLint                                |
| `npm run format`     | Check formatting with Prettier            |
| `npm run format:fix` | Auto-fix formatting                       |
| `npm run test`       | Run unit and integration tests            |
| `npm run test:watch` | Run tests in watch mode                   |
| `npm run test:e2e`   | Run Playwright end-to-end tests           |
| `npm run typecheck`  | TypeScript type checking                  |
| `npm run seed:admin` | Create/verify admin account               |
| `npm run seed:sample`| Import sample data                        |

## Project Structure

```
sla-tracker/
├── src/
│   ├── app/                      # Next.js App Router pages and API routes
│   │   ├── (auth)/login/         # Login page
│   │   ├── (dashboard)/          # Dashboard layout + pages
│   │   │   ├── dashboard/        # Main dashboard
│   │   │   ├── tickets/          # Ticket listing, create, detail
│   │   │   ├── reports/          # SLA reports
│   │   │   ├── sla-policies/     # SLA policy management
│   │   │   ├── holidays/         # Holiday management
│   │   │   ├── assignee-groups/  # Group management
│   │   │   └── settings/         # Settings page
│   │   └── api/                  # Backend API routes
│   │       ├── auth/             # Authentication endpoints
│   │       ├── tickets/          # Ticket CRUD + status
│   │       ├── sla-policies/     # Policy management
│   │       ├── holidays/         # Holiday management
│   │       ├── assignee-groups/  # Group management
│   │       ├── dashboard/        # Dashboard summary
│   │       └── reports/          # SLA reports + CSV export
│   ├── components/               # Reusable UI components
│   │   ├── layout/               # Sidebar, Header, MobileNav
│   │   └── ui/                   # Badge, Button, Input, Select, Modal, StatCard
│   ├── lib/                      # Core libraries
│   │   ├── db.ts                 # MongoDB connection
│   │   ├── auth.ts               # JWT session management
│   │   ├── env.ts                # Environment validation
│   │   ├── api-response.ts       # Standardized API responses
│   │   ├── api-auth.ts           # API authentication middleware
│   │   └── logger.ts             # Structured logging
│   ├── models/                   # Mongoose models
│   │   ├── Admin.ts
│   │   ├── Ticket.ts
│   │   ├── SLAPolicy.ts
│   │   ├── Holiday.ts
│   │   └── AssigneeGroup.ts
│   ├── services/                 # Business logic
│   │   ├── business-calendar.ts  # Business day/hour calculations
│   │   └── sla-calculator.ts     # Core SLA engine
│   ├── validators/               # Joi schemas
│   ├── types/                    # TypeScript type definitions
│   └── utils/                    # Formatters, utilities
├── scripts/                      # Seed scripts
├── tests/                        # Test files
│   ├── unit/                     # Unit tests (SLA engine)
│   ├── integration/              # API integration tests
│   └── e2e/                      # Playwright e2e tests
├── sample-data/                  # Sample JSON import files
└── .env.example                  # Environment template
```

## API Endpoints

### Authentication

| Method | Endpoint              | Description              |
| ------ | --------------------- | ------------------------ |
| POST   | `/api/auth/login`     | Admin login              |
| POST   | `/api/auth/logout`    | Admin logout             |
| GET    | `/api/auth/session`   | Get current session      |

### Tickets

| Method | Endpoint                     | Description              |
| ------ | ---------------------------- | ------------------------ |
| GET    | `/api/tickets`               | List tickets (paginated) |
| POST   | `/api/tickets`               | Create ticket            |
| GET    | `/api/tickets/[id]`          | Get ticket detail        |
| PATCH  | `/api/tickets/[id]`          | Update ticket fields     |
| POST   | `/api/tickets/[id]/status`   | Change ticket status     |

### SLA Policies

| Method | Endpoint                    | Description              |
| ------ | --------------------------- | ------------------------ |
| GET    | `/api/sla-policies`         | List all policies        |
| PATCH  | `/api/sla-policies/[id]`    | Update a policy          |

### Holidays

| Method | Endpoint                 | Description              |
| ------ | ------------------------ | ------------------------ |
| GET    | `/api/holidays`          | List holidays            |
| POST   | `/api/holidays`          | Create holiday           |
| PATCH  | `/api/holidays/[id]`     | Update holiday           |
| DELETE | `/api/holidays/[id]`     | Delete holiday           |

### Assignee Groups

| Method | Endpoint                      | Description              |
| ------ | ----------------------------- | ------------------------ |
| GET    | `/api/assignee-groups`        | List groups              |
| POST   | `/api/assignee-groups`        | Create group             |
| PATCH  | `/api/assignee-groups/[id]`   | Update group             |
| DELETE | `/api/assignee-groups/[id]`   | Delete group (if unused) |

### Dashboard & Reports

| Method | Endpoint                     | Description              |
| ------ | ---------------------------- | ------------------------ |
| GET    | `/api/dashboard/summary`     | Dashboard metrics        |
| GET    | `/api/reports/sla`           | SLA breach report        |
| GET    | `/api/reports/sla/export`    | Export report as CSV     |

## SLA Business Rules

### M1: SLA Targets

| Priority | Target (Business Hours) | Target (Minutes) |
| -------- | ----------------------- | ---------------- |
| P1       | 4 hours                 | 240              |
| P2       | 8 hours                 | 480              |
| P3       | 24 hours                | 1440             |
| P4       | 72 hours                | 4320             |

### M2: Business Calendar

- **Working days**: Monday–Friday
- **Working hours**: 09:00–18:00 (configurable in `.env.local`)
- **Excluded**: Saturdays, Sundays, and all active holidays
- Tickets created outside business hours start at the next business opening

### M3: ON_HOLD Pause

- SLA clock pauses when ticket enters `ON_HOLD` status
- SLA clock resumes when ticket leaves `ON_HOLD` status
- Multiple hold/resume cycles are supported
- The `dueBy` deadline is extended by the total real-time hold duration

### M4: SLA Statuses

| Status    | Condition                                          |
| --------- | -------------------------------------------------- |
| `ON_TRACK`  | > 25% of SLA target remaining                    |
| `AT_RISK`   | ≤ 25% of SLA target remaining                   |
| `BREACHED`  | Elapsed business time > SLA target               |
| `PAUSED`    | Ticket currently `ON_HOLD`                        |
| `RESOLVED`  | Ticket resolved                                   |

- BreachStatus is evaluated at the current time for unresolved tickets
- A ticket resolved exactly at its deadline is **not** breached
- Breach minutes are reported in business minutes, not clock minutes

## Status Transition Rules

| From         | Allowed Transitions              |
| ------------ | -------------------------------- |
| `OPEN`       | `IN_PROGRESS`, `ON_HOLD`, `RESOLVED` |
| `IN_PROGRESS`| `ON_HOLD`, `RESOLVED`, `OPEN`    |
| `ON_HOLD`    | `IN_PROGRESS`, `RESOLVED`, `OPEN` |
| `RESOLVED`   | (none — final state)             |

## Reporting Formulas

- **SLA Compliance**: `(Resolved Non-Breached Tickets / Resolved Tickets) × 100`
- **Breach Percentage**: `(Breached Tickets / Total Eligible Tickets) × 100`
- **Average Resolution Time**: Mean business minutes of resolved tickets
- **Average Breach Duration**: Mean breach minutes of breached tickets

Unresolved tickets are included in breach counts based on current elapsed time vs target.

## Troubleshooting

**MongoDB connection errors:**
- Ensure MongoDB is running (`mongosh` to test)
- Check `MONGODB_URI` in `.env.local`
- For Atlas: verify IP whitelist and database user credentials

**Login failures:**
- Re-run `npm run seed:admin` to ensure the admin account exists
- Check `ADMIN_EMAIL` and `ADMIN_PASSWORD` match `.env.local`

**SLA calculations seem wrong:**
- Verify `APP_TIMEZONE`, `BUSINESS_START_HOUR`, `BUSINESS_END_HOUR` in `.env.local`
- Check that holidays with active status exist for the relevant dates
- Review the ticket's `statusHistory` for correct ON_HOLD entries

**Type errors:**
- Run `npm run typecheck` to see all type errors
- Ensure `npm install` completed successfully

## Security Notes

- All API routes require authentication (except login)
- Passwords are hashed with bcrypt (12 salt rounds)
- Sessions use HTTP-only cookies with JWT
- Rate limiting on login endpoint (5 attempts per 15 min)
- Environment variables are server-only (no `NEXT_PUBLIC_*` for secrets)
- Input validation on all API endpoints via Joi
- MongoDB injection protection via Mongoose
- Generic error messages on authentication failures

## Known Limitations

- No multi-admin support (single admin with configurable credentials)
- Password change requires re-running seed script or direct DB access
- No email notifications for SLA breaches
- No real-time WebSocket updates
- No SSO/OAuth authentication
- Reports are live calculations, not snapshots (policy changes affect historical views)
- Large ticket volumes may require pagination tuning

## License

This project is created as part of the SDSI Reskill PS6 assignment.

## Contributors

Built with [Claude Code](https://claude.com/claude-code)