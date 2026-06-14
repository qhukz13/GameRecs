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

## Фаза 2: Улучшение тестов

### Очередь задач:
7. [ ] Добавить тесты для API роутеров через `fastapi.TestClient`
8. [ ] Добавить тесты для Steam integration (моки `requests`)
9. [ ] Добавить тест на `release_date=None` в `RecommendationService`
10. [ ] Добавить тесты для `steam_utils.py`