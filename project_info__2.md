# Game Recommendations API — Codebase Overview

## Summary
This is a FastAPI-based backend for a co-op game recommendation system. It takes group profiles (aggregated from member reviews), finds similar games via vector embeddings (pgvector cosine similarity), and optionally augments results with live Steam store data. The system is designed to recommend games that a group hasn't played yet, with a co-op and 2020+ release date filter that was **partially implemented by a previous agent and never completed**.

---

## Critical Finding: The filter implementation is incomplete — it will silently return **empty results**

The previous agent added three filter functions (`_is_coop_game`, `_is_new_game`, `_parse_steam_release_date`) and wired them into both generation methods. However, they **never added the `release_date` column to the database, model, repository, or schemas**. This means:

- Every `GameModel.release_date` attribute is `None` for all games in the DB
- `_is_new_game(None)` returns `False` → **ALL games are filtered out**
- The system returns empty recommendation lists silently (no error, just `[]`)

Additionally, the existing unit tests use `_DummyGame` stubs that don't set `release_date` or co-op keywords, so they also return 0 results and **fail**.

---

## What was done correctly (already in the code)

The three module-level filter functions in `recommendation_service.py` are complete and correct:

- **`_is_coop_game(genres, tags)`** — Checks if any genre/tag contains co-op keywords ("co-op", "cooperative", "split screen", "local co-op", etc.)
- **`_is_new_game(release_date)`** — Returns `True` if `release_date.year >= 2020`
- **`_parse_steam_release_date(release_data)`** — Parses Steam's `{"date": "Oct 21, 2022", "coming_soon": false}` into a `datetime` using 5 format attempts

Both `generate_for_group()` and `generate_candidates_for_group()` already have the filter step applied at the end:
```python
if _is_coop_game(game.genres, game.tags) and _is_new_game(game.release_date):
    filtered_candidates.append((game, score))
```

The `generate_for_group()` path even tries to pass `release_date=release_date` when creating games via Steam import — but `GameRepository.create()` doesn't accept the parameter.

---

## Complete checklist of what must be done

Here is every file and every change needed, in dependency order:

### 1. Add `release_date` column to `GameModel` (ORM)
**File:** `apps/api/app/infrastructure/db/models.py`
- Add `release_date: Mapped[datetime | None]` after `embedding` column (or anywhere in the model)

### 2. Add column to SQL schema
**File:** `infra/schema.sql`
- Add `release_date timestamptz` to `games` table

### 3. Create a new Alembic migration
**Directory:** `apps/api/alembic/versions/`
- Create `0002_add_release_date.py` with:
  ```python
  op.add_column("games", sa.Column("release_date", sa.DateTime(timezone=True), nullable=True))
  ```

### 4. Update `GameRepository.create()` to accept `release_date`
**File:** `apps/api/app/infrastructure/repositories/games.py`
- Add `release_date: Optional[datetime] = None` parameter
- Pass it to `GameModel(release_date=release_date)`

### 5. Add `release_date` to Pydantic schemas
**File:** `apps/api/app/schemas/game.py`
- `GameCreate`: Add `release_date: datetime | None = None`
- `GameRead`: Add `release_date: datetime | None`

### 6. Fix `external.py:steam_import` to parse and pass `release_date`
**File:** `apps/api/app/api/v1/routers/external.py`
- Import `_parse_steam_release_date` from `recommendation_service.py`
- Parse `release_date = _parse_steam_release_date(d.get("release_date", {}))`
- Pass to `repo.create(release_date=release_date)`

### 7. Fix unit tests
**Files:** `apps/api/app/tests/test_recommendation_service.py` and `test_recommendation_service_extra.py`
- Update `_DummyGame` to accept `genres`, `tags`, and `release_date`
- Instantiate with `tags=["co-op"]` and `release_date=datetime(2021, 6, 15, tzinfo=timezone.utc)` for games expected to pass the filter

### 8. Update `generate_for_group()` import for `_parse_steam_release_date`
**File:** `apps/api/app/application/services/recommendation_service.py`
- The function is already at module level — no change needed. But ensure the `repo.create()` call properly passes `release_date` after step 4 is done.

---

## Additional non-obvious findings

- **Duplicated Steam fetching logic**: The same ~50 lines of Steam API fetch + blacklist filtering + keyword heuristics + embedding logic are copy-pasted in both `generate_for_group()` and `generate_candidates_for_group()`. Huge maintenance liability.
- **Steam integration has no abstraction**: No client class, no retry, no rate limiting. Direct `requests.get()` calls in service methods.
- **Game-like heuristics are fragile**: Two hardcoded keyword lists (`BLACKLIST_CATS` and `GAME_KEYWORDS`) determine what's "a real game." A legitimate game with niche genre tags (e.g., "educational", "simulation" without matching keywords) gets silently skipped.
- **No DI framework**: All dependencies are manually constructed in the router — every new service means a change in `recommendations.py`.
- **Test coverage is minimal**: Only two unit tests exist, both with stubs that don't reflect the actual model shape. No integration tests for Steam API calls.

The report has been saved to `project_info__1.md` in the project root with all the details, including a suggested reading order. Switch to **Act Mode** to implement the 8 changes listed above.