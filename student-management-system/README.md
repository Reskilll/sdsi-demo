# 🎓 Student Management System

A full, end-to-end **Student Management System** with complete CRUD operations and a
security-first design. Node.js + Express REST API, SQLite storage, JWT authentication,
role-based access control, and a clean single-page web UI.

## Features

### CRUD
- **Create / Read / Update / Delete** students
- Fields: first name, last name, email (unique), age, grade, enrollment status
- Server-side **search** (name/email) and **pagination**

### Security
| Area | Implementation |
|------|----------------|
| Password storage | **bcrypt** hashing (12 rounds) — plaintext never stored |
| Authentication | **JWT** in an **httpOnly, SameSite=strict** cookie (also accepts `Bearer` tokens) |
| Authorization | **Role-based access control** — `admin` can write, `user` is read-only |
| SQL injection | **Parameterized / prepared statements** everywhere |
| Input validation | **express-validator** with strong rules + sanitization |
| Brute force | **Rate limiting** (strict on auth, global on API) |
| HTTP headers | **Helmet** incl. a strict **Content-Security-Policy** |
| XSS | CSP + DOM rendered via `textContent` (no `innerHTML` of user data) |
| CSRF | SameSite=strict cookies |
| DoS | JSON body size cap (100kb) |
| Secrets | Loaded from `.env`; refuses to start in prod with an insecure secret |

## Quick start

```bash
npm install            # installs dependencies
cp .env.example .env   # (already created for local dev)
npm start              # starts on http://localhost:4000
```

Open **http://localhost:4000** and log in with the seeded admin:

```
Email:    admin@school.edu
Password: Admin@12345
```

Register a new account from the UI to get a **read-only** user and see RBAC in action.

## Scripts
- `npm start` — run the server
- `npm run dev` — run with auto-reload (`node --watch`)
- `npm run seed` — (re)seed the admin + sample students
- `npm test` — run the end-to-end API test suite

## API

Base URL: `/api`

### Auth
| Method | Path | Body | Notes |
|--------|------|------|-------|
| POST | `/auth/register` | `{ email, password }` | Creates a read-only user |
| POST | `/auth/login` | `{ email, password }` | Sets auth cookie, returns token |
| POST | `/auth/logout` | — | Clears cookie |
| GET | `/auth/me` | — | Current user (requires auth) |

### Students (requires auth)
| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/students?q=&page=&limit=` | user/admin | List + search + paginate |
| GET | `/students/:id` | user/admin | Get one |
| POST | `/students` | admin | Create |
| PUT | `/students/:id` | admin | Update |
| DELETE | `/students/:id` | admin | Delete |

### Example (curl)
```bash
# Login and capture the token
TOKEN=$(curl -s -X POST http://localhost:4000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@school.edu","password":"Admin@12345"}' | node -pe 'JSON.parse(require("fs").readFileSync(0)).token')

# Create a student
curl -s -X POST http://localhost:4000/api/students \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"first_name":"Ada","last_name":"Byron","email":"ada.b@school.edu","age":17,"grade":"Grade 11"}'
```

## Project structure
```
student-management-system/
├── server.js                 # App entry: security middleware, routes, static UI
├── src/
│   ├── config.js             # Env-driven config
│   ├── db.js                 # SQLite connection + schema
│   ├── seed.js               # Default admin + sample data
│   ├── middleware/
│   │   ├── auth.js           # JWT authenticate + RBAC authorize
│   │   ├── validate.js       # express-validator rule sets
│   │   └── errorHandler.js   # 404 + central error handler
│   ├── controllers/
│   │   ├── authController.js # register/login/logout/me
│   │   └── studentController.js # CRUD
│   └── routes/
│       ├── auth.js
│       └── students.js
├── public/                   # Frontend SPA (HTML/CSS/vanilla JS)
└── test/api.test.js          # End-to-end API tests
```

## Notes for production
- Set a strong `JWT_SECRET` and `NODE_ENV=production` (server refuses insecure secrets in prod).
- Serve over HTTPS (the auth cookie becomes `Secure` automatically).
- Put behind a reverse proxy; `trust proxy` is enabled in production.
- Change the default admin password immediately.
