# EBC: External Business Center

Full-stack business development platform for managing external opportunities pipeline.

## Stack
- **Backend**: Java 25 + Spring Boot 3.4 + PostgreSQL + JPA
- **Frontend**: Vue 3 + Vite + Axios
- **Database**: PostgreSQL with JPA auto-DDL

## Prerequisites
- Java 25, Maven, PostgreSQL, Node.js 18+

## Quick Start

### 1. Database
```bash
psql -U postgres -f database/schema.sql
```

### 2. Backend
```bash
cd backend
mvn clean package
java -jar target/ebc-1.0.0.jar
```
Runs on http://localhost:8085

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```
Runs on http://localhost:5173

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/dashboard | KPI dashboard stats |
| GET | /api/opportunities | All opportunities |
| GET | /api/opportunities/open | Open opportunities |
| POST | /api/opportunities | Create opportunity |
| POST | /api/opportunities/{id}/advance | Advance stage |
| POST | /api/opportunities/{id}/close | Close with review |
| POST | /api/bid-check | Run bid probability check |
| GET | /api/pipeline | Pipeline grouped by stage |
| GET | /api/stats/sources | Source performance stats |
| GET | /health | Health check |

## Screens
1. **Dashboard** - KPIs, source performance, quick actions
2. **Pipeline** - Kanban board (Lead to RFP to Go/No-Go to Proposal)
3. **Bid Check** - Probability gauge, margin, capacity analysis
4. **Learnings** - Search closed-bid reviews by outcome

## Database
- PostgreSQL tables for opportunities, leaders, clients, divisions, resources, audit trail
- JPA auto-creates tables on startup
- Seed data in database/schema.sql