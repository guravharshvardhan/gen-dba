# GenStore — Realistic E-commerce Demo for Gen-DBA

GenStore is a polished, Amazon-inspired **but independently designed** e-commerce demo that runs on the same PostgreSQL `gendba` database as Gen-DBA.

The purpose is not only to look like a real storefront, but to generate realistic database workload that Gen-DBA can observe.

## Architecture

```text
GenStore React UI (5174)
        ↓
GenStore FastAPI (8010)
        ↓
PostgreSQL / gendba
        ↓
query_logs
        ↓
Gen-DBA (8000)
```

Every important GenStore SQL request is logged into `query_logs` so Gen-DBA can analyze the workload.

## One-time database setup

Open pgAdmin → `gendba` → Query Tool and run:

```sql
-- contents of database/gen_store_upgrade.sql
```

The script only adds catalog columns, inserts missing demo products and creates a normal category index. It does not delete your existing data.

## Backend setup

From `gen-store/backend`:

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` from `.env.example` and use the **same DB values** as your existing Gen-DBA `backend/.env`.

Start:

```powershell
..\backend\venv\Scripts\uvicorn.exe main:app --reload --port 8010
```

Or, when the prompt is already inside `gen-store/backend`:

```powershell
.\venv\Scripts\uvicorn.exe main:app --reload --port 8010
```

Health check:

`http://127.0.0.1:8010/api/health`

## Frontend setup

From `gen-store/frontend`:

```powershell
npm install
npm run dev
```

Open:

`http://localhost:5174/`

## Important Gen-DBA demo query

The Customer Search screen intentionally uses this realistic workload pattern:

```sql
SELECT user_id, name, email, city, created_at
FROM users
WHERE LOWER(city) = LOWER(%s)
ORDER BY user_id DESC
LIMIT 25;
```

Your existing `users(city)` index can make this a useful Gen-DBA optimization candidate because the `LOWER()` wrapper changes how the normal index can be used.

Use **Customer search → Pune** to generate the workload. Then run the Gen-DBA automation engine and review the recommendation.

## Demo flow

```text
Open GenStore
    ↓
Browse products
    ↓
Search customers by city
    ↓
Real SQL hits PostgreSQL
    ↓
GenStore writes workload to query_logs
    ↓
Gen-DBA detects the query
    ↓
Gemini recommendation
    ↓
DBA approval
    ↓
Optimization / benchmark / rollback workflow
```

## Design note

The UI is intentionally enterprise-grade and marketplace-like, while not copying any specific site's branding or exact layout.
