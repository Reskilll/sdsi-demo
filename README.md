# Employee Management System (EMS)

Full-stack Employee Management System with **Angular 17** frontend, **Spring Boot 3.2** backend, and **PostgreSQL** database.

## Architecture

```
├── backend/                    # Spring Boot 3.2 + Java 17
│   ├── src/main/java/com/ems/
│   │   ├── config/             # SecurityConfig, DataSeeder
│   │   ├── controller/         # REST controllers (Auth, Employee)
│   │   ├── dto/                # Request/Response DTOs
│   │   ├── entity/             # JPA entities (Employee, User)
│   │   ├── repository/         # Spring Data repositories
│   │   ├── security/           # JWT utils, auth filter, UserDetails
│   │   └── service/            # Business logic (Auth, Employee)
│   └── pom.xml
│
└── frontend/                   # Angular 17 standalone components
    └── src/app/
        ├── components/
        │   ├── login/          # Login/Register page
        │   ├── employee-list/  # Table, search, pagination, stats
        │   └── employee-form/  # Create/Edit modal form
        ├── guards/             # Auth guard (canActivate)
        ├── interceptors/       # Auth token + error handling
        ├── models/             # TypeScript interfaces
        └── services/           # Auth + Employee HTTP services
```

## Features

### 1. Login / Authentication
- JWT-based authentication (stateless)
- Login and Register endpoints
- Role-based access (USER / ADMIN)
- Auth guard on Angular routes
- HTTP interceptors attach Bearer token automatically
- 401 handling logs user out gracefully

### 2. Employee CRUD
- **List** — paginated table with search and department filter
- **Create** — modal form with validation
- **Update** — inline editing via modal
- **Delete** — soft-delete (set `isActive=false`)
- **Reactivate** — re-enable deactivated employees
- Stats row: total, active, departments, showing count

### 3. Security
- BCrypt password hashing
- JWT token generation & validation
- Method-level Spring Security (`@PreAuthorize`)
- CORS configured for Angular dev server (`localhost:4200`)
- Stateless sessions — no server-side session state

## API Endpoints

| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | `/api/auth/login` | Public | Authenticate user |
| POST | `/api/auth/register` | Public | Register new user |
| GET | `/api/employees` | USER+ | List employees (supports `?search=` and `?department=`) |
| GET | `/api/employees/{id}` | USER+ | Get single employee |
| POST | `/api/employees` | ADMIN | Create employee |
| PUT | `/api/employees/{id}` | ADMIN | Update employee |
| DELETE | `/api/employees/{id}` | ADMIN | Soft-delete employee |
| PATCH | `/api/employees/{id}/reactivate` | ADMIN | Reactivate employee |

## Getting Started

### Prerequisites
- Java 17+
- Node.js 18+
- PostgreSQL 15+
- Maven 3.9+

### 1. Database Setup

```sql
CREATE DATABASE ems_db;
```

### 2. Backend Setup

```bash
cd backend

# Set required environment variables (see backend/.env.example for the list)
# The app needs: DB_USERNAME, DB_PASSWORD, JWT_SECRET
# Optional for seeding: EMS_ADMIN_PASSWORD, EMS_USER_PASSWORD
#
# On first run with EMS_*_PASSWORD set, default admin and user accounts are created.

# Build & run
mvn spring-boot:run
```

Backend starts on `http://localhost:8080`.

### 3. Frontend Setup

```bash
cd frontend
npm install
npm start   # → http://localhost:4200
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Angular 17 (standalone components), Bootstrap 5, Reactive Forms |
| Backend | Spring Boot 3.2, Spring Security, Spring Data JPA |
| Database | PostgreSQL |
| Auth | JWT (jjwt 0.12.3), BCrypt |
| Build | Maven (backend), Angular CLI (frontend) |

## Changelog

### v1.1.0 — vishal.02
- CSV export endpoint (`GET /api/export/employees/csv`)
- Dashboard stats API (`GET /api/dashboard/stats`) — total, active, inactive, top department
- Departments list API (`GET /api/dashboard/departments`)
- Export button on frontend with one-click CSV download
- API-driven stats cards replacing client-side aggregation

### v1.0.0 — vishal.01
- Initial release: Login/Register with JWT auth
- Employee CRUD (create, read, update, delete)
- Role-based access control (ADMIN/USER)
- Spring Boot 3.2 backend with PostgreSQL
- Angular 17 frontend with standalone components
- Paginated table, search, department filter, stats cards