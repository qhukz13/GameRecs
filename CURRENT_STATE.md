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
7. **Тесты API роутеров** (`test_api_routers.py`):
   - `test_health` — проверка /health
   - `test_auth_register_requires_email_and_password` — валидация полей
   - `test_create_review_validates_game_exists` — 404 для несуществующей игры
   - `test_external_steam_search_requires_query` — пустой результат для пустого запроса
   - `test_list_groups_returns_list` — список групп
   - `test_dashboard_returns_structure` — структура дашборда

8. **Тесты Steam integration** (`test_steam_integration.py`):
   - `test_generate_falls_back_to_local_when_steam_fails` — fallback при ошибке Steam
   - `test_generate_skips_non_game_steam_entries` — пропуск non-game записей
   - `test_generate_skips_blacklisted_steam_categories` — пропуск DLC/саундтреков
   - `test_parse_steam_release_date` — парсинг дат
   - `test_is_new_game` — проверка фильтра `_is_new_game`

9. **Тест `release_date=None`** (`test_recommendation_service.py`):
   - `test_generate_filters_out_games_without_release_date` — игры без даты и старые фильтруются

10. **Тесты `steam_utils.py`** (`test_steam_utils.py`):
    - `test_has_blacklist_categories_true`/`_false`
    - `test_is_game_like_true`/`_false`
    - `test_constants_are_non_empty`

---

## Фаза 3: Фронтенд

### Очередь задач:
11. [ ] Добавить UI для Steam search/import
12. [ ] Добавить кнопку "Generate & Persist" в RecommendationsPanel
13. [ ] Реализовать auto-refresh токенов в ApiClient