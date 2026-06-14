# Co-op Game Recommendations MVP

MVP web-platform for recommending cooperative games to a group of friends.

## Stack

- Frontend: Next.js 15, TypeScript, TailwindCSS, shadcn/ui-style components, App Router
- Backend: FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2
- Database: PostgreSQL with pgvector
- Auth: JWT access tokens and persisted refresh tokens

## Run Locally

```bash
cp .env.example .env
docker compose up --build
```

Seed demo data:

```bash
docker compose exec api python scripts/seed.py
```

Open:

- Web: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

Demo login after seed:

```text
alex@example.com / password123
```

## Development

Backend:

```bash
cd apps/api
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
pytest
```

Frontend:

```bash
cd apps/web
npm install
npm run dev
npm run typecheck
```

## Documentation

- Architecture, catalog structure, ERD, endpoints, SQL schema: `docs/architecture.md`
- Standalone SQL schema: `infra/schema.sql`
- Example API requests: `examples/api.http`

