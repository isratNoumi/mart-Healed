# Build Mart

Regional home-improvement ecommerce application built with FastAPI, SQLAlchemy, SQLite, and a React frontend.

## Backend setup

Install dependencies and create the local virtual environment:

```powershell
uv sync
```



```powershell
Copy-Item .env.example .env
```

Initialize or reset the SQLite database from `schema.sql`:

```powershell
uv run python -m app.init_db
```

Run the API:

```powershell
uv run python -m app.main
```

The health endpoint is available at `http://127.0.0.1:8000/health`.



## Project layout

```text
backend/app/       FastAPI application and database utilities
schema.sql         SQLite schema and seed data
ecommerce.db       Local development database generated from schema.sql
frontend/          React application (next implementation phase)
docs/              Feature documentation
.env.example       Template for the gitignored .env settings file
pyproject.toml     uv/Python project configuration
```