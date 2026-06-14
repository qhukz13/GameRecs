# Game Recommendations API — Codebase Overview

## Summary
This is a FastAPI-based backend for a co-op game recommendation system. It takes group profiles (aggregated from member reviews), finds similar games via vector embeddings (pgvector cosine similarity), and optionally augments results with live Steam store data. The system is designed to recommend games that a group hasn't played yet, with a co-op and 2020+ release date filter that was partially implemented by a previous agent.

## Architecture

- **Pattern**: Layered — API router → Service → Repository → Database
- **Language**: Python 3.12+
- **Framework**: FastAPI with SQLAlchemy 2.0 ORM + PostgreSQL + pgvector
- **Vector dimension**: 8 (configured in `app.core.config.Settings.embedding_dim`)
- **AI Provider**: Two implementations — `local` (in-process text model) and `ollama` (remote API). Switchable via `AI_PROVIDER` env var.
- **Embedded AI**: Dual-purpose — `embed_text()` for vector creation and `analyze_review()` for extracting liked/disliked features + sentiment

### Execution flow
1. FastAPI receives request at `/api/v1/groups/{id}/recommendations/generate`
2. Router (`recommendations.py`) creates `RecommendationService` with all dependencies injected
3. Service calls `profiles.update_group_profile()` → averages member review embeddings into a group embedding
4. Service calls `games.search_similar()` → pgvector cosine distance search excluding played games
5. (Optionally) Service fetches Steam API data to discover new games not yet in the local DB
6. Results are filtered for co-op and post-2020 release date
7. Recommendations are either persisted to DB (full flow) or returned as transient dicts (`persist=False`)

## Directory Structure

```
apps/api/
├── app/
│   ├── main.py                               — FastAPI app factory, CORS, router mount
│   ├── api/
│   │   ├── deps.py                           — get_db, get_current_user dependency injection
│   │   └── v1/
│   │       ├── router.py                     — master router aggregating all sub-routers
│   │       └── routers/
│   │           ├── recommendations.py        — /groups/{id}/recommendations/* (generate, list, delete)
│   │           ├── external.py               — /steam/search, /steam/import
│   │           ├── auth.py                   — /auth/register, /auth/login, /auth/refresh
│   │           ├── games.py                  — CRUD for games
│   │           ├── groups.py                 — CRUD for groups + membership
│   │           ├── reviews.py                — CRUD for reviews
│   │           └── dashboard.py              — dashboard stats endpoint
│   ├── application/
│   │   └── services/
│   │       ├── recommendation_service.py     — Core: candidate discovery + filtering + explanation
│   │       ├── profile_service.py            — User/group embedding aggregation
│   │       ├── ai_service.py                 — AI abstraction (compat, wraps AIServiceBase)
│   │       ├── llm_provider.py               — Factory: returns LocalAIProvider or OllamaProvider
│   │       ├── auth_service.py               — Registration, login, token rotation
│   │       └── vector_math.py                — normalize() utility
│   ├── core/
│   │   ├── config.py                         — Pydantic Settings (DB URL, JWT, AI provider, etc.)
│   │   └── security.py                       — JWT encode/decode + password hashing
│   ├── domain/
│   │   └── entities.py                       — ReviewAnalysis, SimilarGame dataclasses
│   ├── infrastructure/
│   │   ├── db/
│   │   │   ├── base.py                       — SQLAlchemy declarative Base
│   │   │   ├── models.py                     — All ORM models (User, Group, Game, Review, etc.)
│   │   │   └── session.py                    — SessionLocal + get_db generator
│   │   └── repositories/
│   │       ├── games.py                      — GameRepository (create, get, list, delete, search_similar)
│   │       ├── reviews.py                    — ReviewRepository
│   │       ├── recommendations.py            — RecommendationRepository
│   │       ├── groups.py                     — GroupRepository
│   │       ├── users.py                      — UserRepository
│   │       └── tokens.py                     — RefreshTokenRepository
│   ├── schemas/                              — Pydantic request/response models
│   └── tests/                                — Pytest test files
├── alembic/
│   └── versions/
│       └── 0001_initial.py                   — initial schema (no release_date on games)
├── scripts/
│   └── seed.py                               — Creates test users, games, reviews, and seed recommendations
infra/
└── schema.sql                                — raw SQL schema (no release_date on games)
```

## Key Abstractions

### RecommendationService
- **File**: `apps/api/app/application/services/recommendation_service.py`
- **Responsibility**: Orchestrates the recommendation pipeline — profile aggregation → candidate discovery (local DB + Steam) → filtering → explanation → persistence
- **Methods**:
  - `generate_for_group(group_id, limit)` — Full flow: discovers candidates, filters (co-op + new), persists games (via Steam import) and recommendations, returns saved models
  - `generate_candidates_for_group(group_id, limit)` — Transient flow: returns raw candidate dicts without persisting anything; used when `persist=False` query param is set
- **Key implementation details**:
  - Contains inner functions `_is_coop_game()`, `_is_new_game()`, `_parse_steam_release_date()` defined at module level
  - Steam integration is inline (direct `requests.get` calls) — not abstracted into a service
  - Filters are applied AFTER the Steam fetch/DB search in BOTH methods (co-op AND new-game AND)

### GameRepository
- **File**: `apps/api/app/infrastructure/repositories/games.py`
- **Responsibility**: Persistence for GameModel, including pgvector similarity search
- **Methods**: `create()`, `get()`, `list()`, `delete()`, `search_similar()`
- **Bug**: `create()` does NOT accept `release_date` parameter. The `recommendation_service.py` passes `release_date=release_date` in one code path, but it's silently dropped. The model also has no `release_date` column.

### GameModel / games table
- **File**: `apps/api/app/infrastructure/db/models.py` (line 94-110), schema in `infra/schema.sql`
- **Columns**: `id` (UUID PK), `external_id` (varchar 120, unique), `title`, `description`, `genres` (JSONB), `tags` (JSONB), `players_min`, `players_max`, `embedding` (vector(8)), `created_at`
- **Missing column**: No `release_date` column. The co-op filter logic references `game.release_date` which will be `None` for all existing records, causing `_is_new_game()` to return `False` and filtering everything out.

### GameRead / GameCreate (schemas)
- **File**: `apps/api/app/schemas/game.py`
- **Missing field**: No `release_date` field in either schema.

### _is_coop_game() / _is_new_game() / _parse_steam_release_date()
- **File**: `apps/api/app/application/services/recommendation_service.py` (module-level functions, lines 18-79)
- `_is_coop_game(genres, tags)` — Returns True if any genre or tag (lowercased) contains any of 15 co-op keywords ("co-op", "cooperative", "split screen", etc.)
- `_is_new_game(release_date)` — Returns True if date is not None and `year >= 2020`
- `_parse_steam_release_date(release_data: dict)` — Parses Steam's `{"date": "Oct 21, 2022", "coming_soon": false}` using 5 date format attempts. Returns `None` for coming-soon or unparseable dates.
- **These functions are complete and correct** — the issue is that the data they operate on (the DB model, schemas, repository) doesn't support `release_date`.

## Data Flow

### Full recommendation generation (persist=True):
1. Client POSTs `POST /api/v1/groups/{group_id}/recommendations/generate?persist=true`
2. `recommendations.py:generate_recommendations()` — validates group membership, instantiates all dependencies
3. Calls `service.generate_for_group(group_id, limit=None)`
4. `ProfileService.update_group_profile(group_id)` — Averages review embeddings of group members → group embedding
5. `GameRepository.search_similar(embedding, exclude_game_ids=[played], limit=15)` — pgvector cosine distance query, returns `[(GameModel, score)]`
6. **Steam augmentation loop** (in `generate_for_group`): Collects genres/tags from local candidates → queries `steampowered.com/api/storesearch` for each → fetches `appdetails` for matching IDs → filters out non-games (DLC, soundtrack, tool, software), filters for game-like keywords, parses `release_date`, creates embeddings, calls `repo.create()` — **but `release_date` is silently dropped because `repo.create()` doesn't accept it**
7. `GameRepository.search_similar()` runs again on the now-enriched local DB
8. Filter step: iterate candidates, keep only those where `_is_coop_game(game.genres, game.tags) AND _is_new_game(game.release_date)` — **but `game.release_date` is always None, so all games are filtered out**
9. For surviving candidates: `ai.explain_recommendation(game, score)` generates explanation text
10. `RecommendationRepository.upsert(group_id, game_id, score, explanation)` persists each
11. Router converts ORM models to dicts and returns JSON

### Transient candidates (persist=False):
1. Same entry point with `?persist=false`
2. Calls `service.generate_candidates_for_group(group_id)`
3. Similar flow but never saves games or recommendations to DB
4. Returns list of dicts with `"transient": True` flag
5. Filtering is applied in the same way

## Non-Obvious Behaviors & Design Decisions

### Critical: `release_date` column does NOT exist anywhere in the database, model, or repository

The previous agent added the **filtering logic** (`_is_coop_game`, `_is_new_game`, `_parse_steam_release_date`) and wired them into the recommendation pipeline, but **never added the `release_date` column** to:
- `GameModel` (SQLAlchemy ORM model)
- `games` table schema (`infra/schema.sql`)
- Alembic migration (only one exists, `0001_initial.py`)
- `GameRepository.create()` method signature
- `GameRead` / `GameCreate` Pydantic schemas

**Consequence**: ALL recommendations that go through the filter are discarded because `game.release_date` is `None` for every game in the database. The system returns empty recommendation lists.

### Tests are broken

The existing unit tests (`test_recommendation_service.py` and `test_recommendation_service_extra.py`) use `_DummyGame` stubs that:
- Don't set `release_date` → `_is_new_game()` returns `False` → game filtered out
- Don't set `genres` or `tags` to co-op keywords → `_is_coop_game()` returns `False` → game filtered out

The first test expects 2 recommendations but will get 0. The second test expects 1 recommendation but will get 0. **These tests must be updated to include `release_date=datetime(2021, 1, 1)` and `genres=["co-op"]` on the stub games.**

### Steam integration is inlined with request.Response calls

`recommendation_service.py` makes direct HTTP calls to Steam API via `requests.get()` inside the service methods. There is no abstraction (no SteamClient class, no retry logic, no rate limiting). If Steam is slow or returns errors, the entire recommendation generation can fail. The exception handlers fall back to local-only search.

### Duplicated Steam fetching logic

The Steam fetch + filtering + embedding logic is copy-pasted in two places:
1. `generate_for_group()` lines 79-128 (the "create game in DB" path)
2. `generate_candidates_for_group()` lines 158-233 (the "transient" path)

Both have nearly identical code for fetching from Steam, parsing responses, filtering blacklist/game-like keywords, parsing release dates, and embedding. This is a maintenance liability.

### Game-like heuristics are fragile

The code uses two hardcoded keyword lists to determine if a Steam entry is a "real game":
- `BLACKLIST_CATS` — DLC, soundtrack, tool, software, utility, demo
- `GAME_KEYWORDS` — action, adventure, RPG, strategy, etc.

A legitimate game that doesn't match ANY `GAME_KEYWORDS` (e.g., an "educational" or "simulation" game tagged only in a niche genre) would be silently skipped.

### AI provider has two modes but is treated uniformly

`get_llm_provider()` returns either `LocalAIProvider` or `OllamaProvider`. Both implement `embed_text()` and `analyze_review()`. The `RecommendationService` uses `self.ai` for both embedding and explanation. The `generate_for_group` path also calls `ai.embed_text()` inline within the Steam augmentation loop.

### Dependencies are injected manually (no DI framework)

`RecommendationService.__init__` takes 5 keyword-annotated positional args. The router constructs them by instantiating each repository/service manually. There's no dependency injection container — every new dependency means a change in the router.

## Complete list of changes needed to finish the filter implementation

The previous agent got to the filtering logic but left the implementation incomplete. Here is what must change:

### 1. Database schema — Add `release_date` column to `games` table

**Files to modify:**
- `apps/api/app/infrastructure/db/models.py` — Add `release_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)` to `GameModel`
- `infra/schema.sql` — Add `release_date timestamptz` column to `games` table
- Create a new Alembic migration (e.g., `0002_add_release_date.py`) with `op.add_column("games", sa.Column("release_date", sa.DateTime(timezone=True), nullable=True))`

### 2. Repository — Accept `release_date` in `GameRepository.create()`

**File:** `apps/api/app/infrastructure/repositories/games.py`
- Add `release_date: Optional[datetime] = None` parameter to `create()`
- Pass it to `GameModel(release_date=release_date)`

### 3. Schemas — Add `release_date` to `GameCreate` and `GameRead`

**File:** `apps/api/app/schemas/game.py`
- `GameCreate`: Add `release_date: datetime | None = None`
- `GameRead`: Add `release_date: datetime | None`

### 4. Fix tests — Update `_DummyGame` stubs with `release_date`, `genres`, `tags`

**Files:** `test_recommendation_service.py` and `test_recommendation_service_extra.py`
- Add `release_date: datetime` attribute to `_DummyGame` — set to e.g. `datetime(2021, 6, 15, tzinfo=timezone.utc)` for games that should pass the filter
- Add `genres=["co-op"]` or `tags=["co-op"]` to ensure `_is_coop_game` returns True

Example fix:
```python
_DummyGame(uuid4(), "Alpha Co-op", tags=["co-op", "combat"], release_date=datetime(2021, 6, 15, tzinfo=timezone.utc))
```

### 5. Fix `external.py:steam_import` — Parse and pass `release_date`

**File:** `apps/api/app/api/v1/routers/external.py`
- Parse `release_date` from Steam API response using `_parse_steam_release_date(d.get("release_date", {}))`
- Pass it to `GameRepository.create(release_date=release_date)`

### 6. (Optional) Fix the `generate_for_group` path bug

In `recommendation_service.py` `generate_for_group()` line where it calls `repo.create(..., release_date=release_date)` — this will only work if step 2 is done. Currently the kwarg is silently ignored.

## Suggested Reading Order

1. **`apps/api/app/infrastructure/db/models.py`** — Start here to understand the data model. Note what `GameModel` has vs what it needs (release_date).
2. **`apps/api/app/application/services/recommendation_service.py`** — The heart of the change. Read the filter functions, then the two generation methods, note the duplicated Steam logic and where `release_date` is passed but dropped.
3. **`apps/api/app/infrastructure/repositories/games.py`** — See the `create()` signature that's missing `release_date`.
4. **`apps/api/app/schemas/game.py`** — See `GameRead` and `GameCreate` that don't have `release_date`.
5. **`apps/api/app/api/v1/routers/recommendations.py`** — The router that wires everything together. Note the `persist` query parameter.
6. **`apps/api/app/api/v1/routers/external.py`** — The `/steam/import` endpoint that also creates games without `release_date`.
7. **Test files** — `test_recommendation_service.py` and `test_recommendation_service_extra.py` — Update after the model changes.
8. **`infra/schema.sql`** and **`apps/api/alembic/versions/0001_initial.py`** — Reference for the migration you need to create.
