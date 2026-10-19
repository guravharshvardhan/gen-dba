
# Gen-DBA + GenStore
### AI-Assisted Database Performance Analysis and E-commerce Workload Simulation

Gen-DBA is an AI-assisted database performance analysis system designed to identify potential SQL query bottlenecks, analyze query execution plans, assess performance risks, and provide optimization recommendations.

GenStore is a companion e-commerce demonstration application that generates realistic database workloads using PostgreSQL. It allows Gen-DBA to observe application queries and demonstrate how database performance analysis can be integrated into a real-world application workflow.

The two applications are designed to work with the same PostgreSQL database, `gendba`.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Objectives](#objectives)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Database Configuration](#database-configuration)
- [Database Setup](#database-setup)
- [Installation and Execution](#installation-and-execution)
- [GenStore Workload Demonstration](#genstore-workload-demonstration)
- [Key Features](#key-features)
- [Troubleshooting](#troubleshooting)
- [Security and Limitations](#security-and-limitations)
- [Future Scope](#future-scope)

---

## Project Overview

### Gen-DBA

Gen-DBA focuses on database query analysis and performance optimization. It provides a structured workflow for examining query performance, identifying potential inefficiencies, and reviewing optimization recommendations.

The backend contains modules for query analysis, scoring, recommendations, workload monitoring, automation, query comparison, authentication, execution, and optimization-related workflows.

### GenStore

GenStore is a modern e-commerce demo built with React and FastAPI. It provides a marketplace-style interface for browsing products, viewing categories, and searching customers.

Unlike a static UI demonstration, GenStore is designed to execute database queries against PostgreSQL. Its workload can be recorded in `query_logs`, allowing Gen-DBA to analyze relevant database activity.

---

## Objectives

- Analyze SQL queries and identify potential performance bottlenecks.
- Examine query execution plans and database workload information.
- Calculate risk or impact scores using the available analysis modules.
- Generate AI-assisted database optimization recommendations.
- Demonstrate database workload generation through an e-commerce application.
- Connect GenStore and Gen-DBA through a shared PostgreSQL database.
- Provide a workflow for reviewing recommendations before considering database changes.

---

## System Architecture

```text
                 GenStore React Frontend
                         |
                         v
                  GenStore FastAPI
                         |
                         v
                 PostgreSQL Database
                     (gendba)
                         |
                         v
                     query_logs
                         |
                         v
                   Gen-DBA Backend
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
        Query Plan    Risk and     AI-Assisted
         Analysis   Impact Scoring Recommendations
             |           |           |
             +-----------+-----------+
                         |
                         v
                  Gen-DBA Frontend
                         |
                         v
               Review and Analysis
```

### Default Local Ports

| Component | Port | Purpose |
|---|---:|---|
| Gen-DBA Frontend | 5173 | Database analysis dashboard |
| Gen-DBA Backend | 8000 | Gen-DBA REST API |
| GenStore Frontend | 5174 | E-commerce interface |
| GenStore Backend | 8010 | GenStore REST API |
| PostgreSQL | 5432 | Shared database service |

**Note:** Vite may select another frontend port if the default port is already in use. Always use the actual URL printed in the terminal and configure CORS accordingly.

---

## Technology Stack

### Frontend
- React
- JavaScript and JSX
- Vite
- HTML and CSS

### Backend
- Python
- FastAPI
- Uvicorn
- psycopg2

### Database
- PostgreSQL
- SQL
- Query logging and workload analysis

### AI Integration
- Gemini integration for AI-assisted recommendations, subject to API configuration and availability

### Development Tools
- Visual Studio Code
- Git and GitHub
- pgAdmin
- FastAPI Swagger UI

---

## Project Structure

```text
Gen-DBA-RECOVERY/
|
|-- backend/
|   |-- analyzer.py
|   |-- approval.py
|   |-- auth.py
|   |-- automation.py
|   |-- comparison.py
|   |-- dashboard.py
|   |-- execution.py
|   |-- gemini_service.py
|   |-- main.py
|   |-- optimization.py
|   |-- query_security.py
|   |-- recommendation.py
|   |-- scheduler.py
|   |-- scoring.py
|   |-- workload.py
|   |-- .env
|   |-- venv/
|
|-- frontend/
|   |-- public/
|   |-- src/
|   |   |-- assets/
|   |   |-- App.jsx
|   |   |-- App.css
|   |   |-- AutomationCenter.jsx
|   |   |-- index.css
|   |   |-- main.jsx
|   |-- package.json
|   |-- package-lock.json
|   |-- vite.config.js
|
|-- gen-store/
|   |-- backend/
|   |   |-- main.py
|   |   |-- requirements.txt
|   |   |-- .env
|   |
|   |-- database/
|   |   |-- gen_store_upgrade.sql
|   |
|   |-- frontend/
|       |-- src/
|       |-- index.html
|       |-- package.json
|       |-- package-lock.json
|       |-- vite.config.js
|
|-- README.md
```

Local environment folders such as `venv`, `node_modules`, and `__pycache__` are omitted from the logical project structure above where not needed for explanation.

---

## Prerequisites

Install the following before running the project:

- Python compatible with the backend dependencies
- Node.js and npm
- PostgreSQL
- pgAdmin or another PostgreSQL client
- Visual Studio Code
- Git (recommended)

A Gemini API key is required only when using the configured AI functionality that depends on it.

---

## Database Configuration

Both applications must connect to the intended PostgreSQL database if GenStore workload is to be visible to Gen-DBA.

The target database is:

```text
Database: gendba
Default PostgreSQL Port: 5432
```

Configure the database connection variables expected by each backend in its own `.env` file.

Example configuration:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=gendba
DB_USER=your_postgres_user
DB_PASSWORD=your_postgres_password
```

Replace the example values with the correct local database credentials. Check the actual variable names used in each backend before configuring the files.

**Important:** Never commit real passwords, API keys, or other secrets to GitHub.

---

## Database Setup

1. Start the PostgreSQL service.
2. Open pgAdmin and connect to your PostgreSQL server.
3. Select the `gendba` database.
4. Open the Query Tool.
5. Review the SQL script at:

   `gen-store/database/gen_store_upgrade.sql`

6. Execute the script against the intended development database after reviewing its contents.
7. Verify that the tables and sample data required by the application are present.

The GenStore backend uses database objects for product browsing, customer searches, order-related operations, and workload logging. Verify the actual schema and required columns against the current code and SQL script.

Back up important data before making schema changes.

---

## Installation and Execution

Run the two applications in four separate terminals. Keep all four terminals open while using the applications.

### Terminal 1: Start Gen-DBA Backend

Open a PowerShell terminal and run:

```powershell
cd D:\Gen-DBA-RECOVERY
backend\venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Backend API documentation:

http://127.0.0.1:8000/docs

### Terminal 2: Start Gen-DBA Frontend

```powershell
cd D:\Gen-DBA-RECOVERY\frontend
npm install
npm run dev -- --port 5173
```

Open the Local URL printed by Vite.

Default URL:

http://localhost:5173/

### Terminal 3: Start GenStore Backend

```powershell
cd D:\Gen-DBA-RECOVERY\gen-store\backend
.\venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --port 8010
```

If the virtual environment or dependencies are missing, create the environment and install the requirements:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

GenStore API documentation:

http://127.0.0.1:8010/docs

Health endpoint:

http://127.0.0.1:8010/api/health

### Terminal 4: Start GenStore Frontend

```powershell
cd D:\Gen-DBA-RECOVERY\gen-store\frontend
npm install
npm run dev -- --port 5174
```

Open the Local URL printed by Vite.

Default URL:

http://localhost:5174/

If port 5174 is occupied, use the actual port selected by Vite and add that exact frontend origin to the GenStore backend CORS configuration.

---

## GenStore Workload Demonstration

GenStore provides a practical way to generate database activity for the Gen-DBA demonstration.

### Demo Steps

1. Start PostgreSQL.
2. Start both backend services.
3. Start both frontend applications.
4. Open GenStore in the browser.
5. Browse product categories or search for products.
6. Open the Customer Search feature.
7. Search for `Pune`.
8. Verify that the backend receives the request and executes the database query.
9. Confirm that workload logging succeeds in `query_logs`.
10. Open Gen-DBA and inspect the available workload and query analysis views.
11. Review the resulting recommendations.

### Example Optimization Candidate

The customer-search workload uses a query pattern similar to:

```sql
SELECT user_id, name, email, city, created_at
FROM users
WHERE LOWER(city) = LOWER(%s)
ORDER BY user_id DESC
LIMIT 25;
```

Applying a function such as `LOWER()` to a column can prevent a conventional index on that column from being used for the predicate as expected.

This provides an example for investigating expression indexes, query plans, and alternative query designs. Any proposed optimization should be validated using the actual schema and execution plan.

### Integration Flow

```text
Customer searches for Pune
           |
           v
GenStore sends API request
           |
           v
FastAPI executes SQL
           |
           v
PostgreSQL processes query
           |
           v
Workload is recorded in query_logs
           |
           v
Gen-DBA inspects the workload
           |
           v
Optimization recommendations are reviewed
```

Successful integration requires both applications to use the same database and compatible schema. Confirm workload logging and analysis in the running application rather than assuming that a successful server startup proves the complete flow works.

---

## Key Features

### Gen-DBA
- SQL query analysis
- Query execution-plan inspection where supported
- Potential bottleneck identification
- Risk and impact scoring modules
- AI-assisted recommendation integration
- Workload and automation modules
- Query comparison functionality
- Authentication-related functionality
- Optimization workflow modules

### GenStore
- E-commerce-style interface
- Product and category browsing
- Product search
- Customer search
- Order and payment-related API routes
- PostgreSQL-backed operations
- Workload logging intended for Gen-DBA analysis

The availability and completeness of individual features depend on the current implementation and configuration.

---

## Troubleshooting

### Database Offline

If GenStore displays `Database Offline`:

1. Open `http://127.0.0.1:8010/api/health`.
2. Check the GenStore backend terminal for database errors.
3. Verify that PostgreSQL is running.
4. Check the database credentials in `gen-store/backend/.env`.
5. Confirm the target database is `gendba`.
6. Verify that the required tables and columns exist.

### CORS Error

If the browser reports a CORS policy error:

1. Check the exact frontend origin in the address bar, including its port.
2. Add that origin to the relevant backend's `CORSMiddleware` `allow_origins` list.
3. Save the file and confirm that Uvicorn reloads.
4. Refresh the frontend using `Ctrl + Shift + R`.
5. If the problem continues, inspect backend logs and the network request response.

For example, if GenStore runs on port 5177, the backend allowlist must include:

```python
"http://localhost:5177",
"http://127.0.0.1:5177",
```

### Port Already in Use

If Vite reports that a port is in use, it may select another available port automatically.

Use the exact Local URL printed in the terminal. Ensure that the corresponding backend CORS configuration includes the new origin.

### Workload Not Visible in Gen-DBA

Check the following:

- GenStore and Gen-DBA connect to the same PostgreSQL database.
- The GenStore request reaches the backend.
- The SQL query executes successfully.
- The insert into `query_logs` succeeds.
- Gen-DBA reads the expected workload table and schema.

### Backend Does Not Start

- Verify that the terminal is in the correct directory.
- Activate the intended virtual environment.
- Install missing dependencies.
- Check the first traceback in the terminal.
- Confirm that the selected port is available.

---

## Security and Limitations

- This project is an academic/demo prototype and is not a production-certified database administration platform.
- AI-generated recommendations are advisory and must be reviewed before use.
- The current Gen-DBA interface has displayed a message that approval is disabled for safety. Do not assume that approval or automated execution is enabled merely because related modules exist.
- Never commit `.env` files containing secrets.
- Use a development database and maintain backups before schema changes or optimization experiments.
- Validate SQL changes using execution plans and representative workloads.
- Confirm authorization, audit logging, transaction handling, and rollback behavior before considering production deployment.

---

## Future Scope

Possible future enhancements include:

- More comprehensive workload analytics
- Additional query-plan analysis rules
- Improved benchmarking and before/after comparisons
- Safer, explicitly authorized optimization execution
- Better workload dashboards and historical trends
- Automated regression tests for API and database integration
- Containerized deployment for easier setup
- Stronger authentication and audit controls
- Monitoring and alerting for database performance

These are potential enhancements, not claims that all are currently implemented.

---

## Development Cost Note

Any project cost figures included in academic documentation should distinguish actual expenditure from estimated development value. Label estimates clearly and do not report them as actual money spent unless supported by invoices or receipts.

---
