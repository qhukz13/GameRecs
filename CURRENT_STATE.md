# Текущее состояние проекта

## ✅ Фаза 1: Очистка технического долга (ЗАВЕРШЕНА)

### Что сделано:
1. **Мёртвый код удалён** — блок `try/except` с `if False else None` в `recommendation_service.py`
2. **Создан `steam_utils.py`** — общие функции `has_blacklist_categories()`, `is_game_like()`, `log_skipped_steam_item()` и константы
3. **`__import__("requests")` исправлен** на `import requests` в `external.py` (2 места)
4. **Дублирующийся импорт удалён** — `RepoGameRepository` заменён на `GameRepository`
5. **Зависимости почищены** — `email-validator` и `passlib[bcrypt]` убраны из `pyproject.toml`
6. **Документация обновлена** — добавлены `release_date` в ERD/SQL schema и Steam endpoints в OpenAPI

---

## ✅ Фаза 2: Улучшение тестов (ЗАВЕРШЕНА)

### Что сделано:
7. **Тесты API роутеров** (`test_api_routers.py`): 6 тестов
8. **Тесты Steam integration** (`test_steam_integration.py`): 5 тестов (моки requests)
9. **Тест `release_date=None`** — игры без даты фильтруются
10. **Тесты `steam_utils.py`** — 6 тестов на утилиты

---

## ✅ Исправление бага "No recommendations were generated"

Метод `generate_candidates_for_group` переписан: сначала возвращает локальные кандидаты (всегда), затем обогащает Steam-данными (best-effort). Steam-ошибки не блокируют показ результатов.

---

## ✅ Фаза 3: Фронтенд (ЗАВЕРШЕНА)

### Что сделано:
11. **Steam search/import UI** — уже был реализован в `GamesPanel.tsx`
12. **Кнопка "Generate & Persist"** — добавлена в `RecommendationsPanel.tsx` рядом с кнопкой "Generate"
13. **Auto-refresh токенов** — `ApiClient` в `api.ts` теперь:
    - При 401 ошибке автоматически вызывает `POST /auth/refresh`
    - Обновляет `accessToken` в localStorage
    - Повторяет запрос с новым токеном
    - Если refresh не удался — очищает auth state и бросает ошибку
14. **`release_date`** — добавлен в тип `Game` в `api.ts`

---

## ✅ Фаза 4: Жёсткий co-op фильтр (ЗАВЕРШЕНА)

### Проблема:
Фильтр `_is_coop_game` был слишком мягким: проверял только `genres` и `tags`, и мог пропускать игры без явного указания "co-op" (например, PvP-only игры с тэгом "multiplayer").

### Изменения:

**`_is_coop_game()`** — полная переработка:
- **Проверка description** — теперь проверяет не только genres/tags, но и описание игры
- **Строгие ключевые слова** — только точные совпадения с "co-op", "cooperative", "local co-op", "online co-op", "pve co-op", "co-op campaign" и т.д.
- **Убраны ложные срабатывания** — "split screen", "shared screen", "team-based" (эти термины могут быть у PvP игр) заменены на более точные
- **Heuristic fallback** — если есть тэг "multiplayer" и в описании есть "co-op" — всё ещё валидно

**Вызовы `_is_coop_game()`** — везде передаётся `description`:
- `generate_for_group()` — `_is_coop_game(game.genres, game.tags, game.description)`
- `generate_candidates_for_group()` Phase 1 — `_is_coop_game(game.genres, game.tags, game.description)`
- `generate_candidates_for_group()` Phase 2 (Steam) — `_is_coop_game(genres, tags_list, desc)`

**Тесты обновлены:**
- `_DummyGame` во всех 3 тестовых файлах теперь содержит `description`