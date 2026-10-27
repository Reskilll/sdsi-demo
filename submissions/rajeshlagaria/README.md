# Expense Splitter

A web application to split group expenses with equal, exact, and percentage
splits. Shows each member's net balance and simplifies debts into minimal
"A pays B ₹X" settlements.

## Tech Stack
- **Frontend:** React + Vite + Tailwind CSS
- **Backend:** Node.js + Express
- **Database:** PostgreSQL

## Quick Start

### Prerequisites
- Node.js 18+
- PostgreSQL 15+

### 1. Database setup
```bash
createdb expense_splitter
psql -d expense_splitter -f database/init.sql
psql -d expense_splitter -f database/seed.sql   # optional sample data
```

### 2. Server
```bash
cd server
npm install
cp .env.example .env   # edit DB credentials if needed
npm run dev             # → http://localhost:3001
```

### 3. Client
```bash
cd client
npm install
npm run dev             # → http://localhost:5173
```

## Features

| Feature | Description |
|---|---|
| **M1** Split types | Equal, exact amounts, percentage |
| **M2** Net balances | Computed per member from all expenses |
| **M3** Settlements | Minimal "A pays B ₹X" using greedy min-cash-flow |
| **M4** Batch upload | Single transaction import from JSON |
| **M5** Validation | % sum to 100, exact amounts sum to total, payer is member |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/groups` | Create group |
| GET | `/api/groups` | List groups |
| GET | `/api/groups/:id` | Get group detail |
| PATCH | `/api/groups/:id` | Update group |
| DELETE | `/api/groups/:id` | Delete group |
| POST | `/api/groups/:id/members` | Add member |
| GET | `/api/groups/:id/members` | List members |
| DELETE | `/api/groups/:id/members/:mid` | Remove member |
| POST | `/api/groups/:id/expenses` | Add expense |
| POST | `/api/groups/:id/expenses/batch` | Batch import |
| GET | `/api/groups/:id/expenses` | List expenses |
| GET | `/api/groups/:id/balances` | Net balances (M2) |
| GET | `/api/groups/:id/settlements` | Simplified settlements (M3) |