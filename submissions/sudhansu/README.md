# Employee Management System

A minimal, production-shaped employee management CRUD app built with **FastAPI +
SQLite + Jinja2**. Full server-rendered UI plus a clean REST API, search, filters,
pagination, and dashboard stats.

## Quick start

```bash
cd submissions/sid-grey
pip install -r requirements.txt
python main.py
# → http://127.0.0.1:8000
```

The database (`ems.db`) is auto-created and pre-seeded with 15 sample employees.

## Features

- **Dashboard** — total employees, departments, avg team size, recent hires
- **Employee list** — search (name/email/position), department filter, pagination
- **Full CRUD** — add, edit, delete employees (form + REST API)
- **REST API** — JSON endpoints with validation and proper status codes
- **Responsive UI** — dark/light mode, works on mobile

## API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/employees` | List all (supports `?search=` & `?dept=`) |
| `GET`  | `/api/employees/{id}` | Get one employee |
| `POST` | `/api/employees` | Create employee |
| `PUT`  | `/api/employees/{id}` | Update employee |
| `DELETE` | `/api/employees/{id}` | Delete employee |
| `GET`  | `/api/stats` | Aggregate stats |

## Tech stack

- **FastAPI** — modern async web framework, auto OpenAPI docs at `/docs`
- **SQLite** via SQLAlchemy 2.0 — zero-config persistence
- **Jinja2** — server-side templating
- **Pydantic v2** — request validation & response serialization

## Project structure

```
main.py            # app, models, routes, API
requirements.txt   # pinned dependencies
templates/         # Jinja2 HTML templates
  base.html        # layout, styles, JS
  dashboard.html   # landing stats
  employees.html   # list/search/filter
  form.html        # add/edit form
ems.db             # SQLite database (auto-generated)
```
