# 🎮 GameRecs: Co-op Game Recommendations

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

GameRecs is a modern, AI-powered web platform designed to solve the age-old problem: *"What should we play next?"* 

It provides highly personalized, cooperative game recommendations for groups of friends based on their individual gaming histories, preferences, and playtime data.

---

## ✨ Features

- **Group-Based AI Recommendations**: Uses state-of-the-art vector embeddings (`pgvector`) to analyze the collective preferences of all group members and suggest games everyone will enjoy.
- **Steam Integration**: Automatically fetches game metadata, genres, tags, and reviews directly from the Steam Store API.
- **Strict Co-op Filtering**: Ensures recommendations are strictly cooperative multiplayer experiences, prioritizing recent and highly-rated titles.
- **Dynamic Group Profiles**: Creates dynamic mathematical profiles (embeddings) for groups that update automatically as members join or leave.
- **Modern User Interface**: A sleek, dark-themed UI built with Next.js 15 and Tailwind CSS for a premium user experience.
- **Robust Security**: Uses secure JWT access tokens and persisted refresh tokens for user authentication.

## 🏗️ Architecture & Tech Stack

### Frontend (`apps/web`)
- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS with custom `shadcn/ui`-inspired components
- **State/Fetching**: React Query, Axios

### Backend (`apps/api`)
- **Framework**: FastAPI
- **Language**: Python 3.11+
- **Database ORM**: SQLAlchemy 2.0 with Alembic for migrations
- **Validation**: Pydantic v2
- **Vector Search**: pgvector (via SQLAlchemy)
- **AI Models**: Local/Ollama embeddings for game and group profiles

### Database
- **PostgreSQL 15+** with the `pgvector` extension.

## 🚀 Getting Started (Local Development)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- Node.js 18+ (if running frontend locally outside Docker)
- Python 3.11+ (if running backend locally outside Docker)

### 1. Environment Setup

Clone the repository and copy the example environment file:

```bash
git clone https://github.com/your-org/GameRecs.git
cd GameRecs
cp .env.example .env
```

### 2. Run with Docker Compose

The easiest way to get the entire stack (Database, Backend API, Frontend) running is via Docker Compose:

```bash
docker compose up --build
```

### 3. Seed Demo Data

To quickly test the application, you can populate the database with demo users, groups, and games:

```bash
docker compose exec api python scripts/seed.py
```

### 4. Access the Application

- **Web App**: [http://localhost:3000](http://localhost:3000)
- **API Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

*(If you ran the seed script, you can log in with `alex@example.com` / `password123`)*

## 🛠️ Manual Development Setup

If you prefer to run services outside of Docker for easier debugging:

### Backend API

```bash
cd apps/api
python -m venv venv
source venv/bin/activate  # Or `venv\Scripts\activate` on Windows
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start the dev server
uvicorn app.main:app --reload --port 8000
```

### Frontend Web

```bash
cd apps/web
npm install

# Start the dev server
npm run dev

# Run typechecking
npm run typecheck
```

## 📚 Documentation

For deep dives into the project's design and schemas, check the `docs/` and `infra/` directories:

- **Architecture & ERD**: [`docs/architecture.md`](docs/architecture.md)
- **Database Schema**: [`infra/schema.sql`](infra/schema.sql)
- **API Request Examples**: [`examples/api.http`](examples/api.http)

## 🚢 Deployment

The application is designed to be easily deployable to modern cloud providers:

- **Frontend**: Optimized for [Netlify](https://www.netlify.com/) or [Vercel](https://vercel.com/).
- **Backend**: Can be containerized and deployed to [Render](https://render.com/), Fly.io, or AWS ECS.
- **Database**: Requires a PostgreSQL provider that supports `pgvector` (e.g., [Neon.tech](https://neon.tech/), AWS RDS, Supabase).

*Note: Ensure you update the `DATABASE_URL` and `VITE_API_URL` environment variables appropriately in your production environments.*

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
