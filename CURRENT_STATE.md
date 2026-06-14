# Текущее состояние проекта

## 📋 Восстановление истории: что делали предыдущие агенты

### Git-история и основные этапы
Предыдущие агенты работали над следующими этапами:

1. **Агент 1 (Основная разработка)**:
   - Создание полного MVP с использованием FastAPI и Next.js.
   - Архитектура: Clean Architecture (domain, application, infrastructure, api).
   - Реализация SQLAlchemy моделей, Alembic миграций, pgvector для векторных поисков.
   - JWT-аутентификация с поддержкой refresh токенов и `pbkdf2_sha256`.
   - Все API-роутеры: auth, groups, games, reviews, recommendations, dashboard, Steam.
   - Разработка `RecommendationService` с генерацией кандидатов на основе Steam API и локальной базы.
   - Docker Compose для развертывания API, веб-приложения и PostgreSQL.
   - Seed-скрипты, smoke тесты, e2e тесты.
   - Документация (architecture.md, schema.sql, API-запросы).
   - **Статус**: ✅ Полностью завершен.

2. **Агент 2 (Тесты)**:
   - Разработка и запуск тестов для API-роутеров (`test_api_routers.py`).
   - Тесты для Steam-интеграции (`test_steam_integration.py`).
   - Тесты для Steam-утилит (`test_steam_utils.py`).
   - Обновление теста для `recommendation_service.py` (+23 строки).
   - **Статус**: ✅ Завершено, смержено в main.

3. **Агент 3 (Фронтенд)**:
   - Авто-refresh токенов в `ApiClient` (`api.ts`).
   - Кнопка «Generate & Persist» в `RecommendationsPanel.tsx`.
   - Добавление `release_date` в тип данных `Game` в `api.ts`.
   - **Статус**: ✅ Завершено, смержено в main.

4. **Агент 4 (Docker/Infra + RecommendationService rewrite)**:
   - Полная переработка `recommendation_service.py`:
     - Улучшение `_is_coop_game()` с проверкой `description` и строгих ключевых слов для co-op.
     - Переписан `generate_candidates_for_group()` для локальных и Steam-обогащенных кандидатов.
   - Добавление сервиса Ollama и настройки окружения в `docker-compose.yml`.
   - Обновление `Dockerfile` и `pyproject.toml`.
   - Обновление тестов под новый интерфейс `_is_coop_game`.
   - **Статус**: ✅ Завершено, смержено в main.

---

## 🚀 Главный блокер

### Основная проблема: `release_date` в `GameModel` отсутствует

Предыдущий агент добавил три фильтра (`_is_coop_game`, `_is_new_game`, `_parse_steam_release_date`) и интегрировал их в логику генерации рекомендаций, но **не внедрил `release_date` в базу данных, модели и схемы**. В результате:

- Все игры имеют `release_date = None`, и фильтр `_is_new_game(None)` всегда возвращает `False`.
- Рекомендации возвращаются пустыми списками, без ошибок.
- Тесты с `_DummyGame` также проваливаются, так как не учитывают `release_date` и `co-op` ключевые слова.

### Список ключевых задач для устранения блокера:

1. **Добавить `release_date` в `GameModel`**:
   - `apps/api/app/infrastructure/db/models.py` (добавление `release_date: Mapped[datetime | None]`).
   - `infra/schema.sql` (добавление столбца `release_date timestamptz`).

2. **Создать Alembic миграцию**:
   - `apps/api/alembic/versions/0002_add_release_date.py` с добавлением столбца.

3. **Обновить `GameRepository.create()`**:
   - `apps/api/app/infrastructure/repositories/games.py` (добавление параметра `release_date: Optional[datetime] = None`).

4. **Обновить Pydantic схемы**:
   - `apps/api/app/schemas/game.py` (добавление `release_date` в `GameCreate` и `GameRead`).

5. **Исправить логику Steam импорта**:
   - `apps/api/app/api/v1/routers/external.py` (парсинг и передача `release_date` из Steam API).

6. **Обновить тесты**:
   - `test_recommendation_service.py` и `test_recommendation_service_extra.py` (добавление `release_date`, `genres`, `tags` в `_DummyGame`).

---

## ✅ Исправления, уже выполненные

- **Слияние веток** завершено успешно.
- **Проверка Steam дубликатов** реализована (метод `find_by_external_id()` в `GameRepository`).
- **Исправление `EMBEDDING_DIM`** корректно интегрировано с Alembic миграциями.
- **Логирование fallback** в `OllamaProvider` добавлено для предупреждений о неудачных вызовах.
- **Проверка зависимостей** подтвердила корректность `pyproject.toml`.

---

## 📊 Оставшиеся задачи (приоритетные)

### Приоритет 1: Основные блокировки
1. **Steam import дубликаты** — тестирование логики повторного импорта.
2. **Rate limiting для Steam API** — защита от перегрузки API.

### Приоритет 2: Тесты и улучшения
3. **Интеграционные тесты с реальной БД** — проверка полного API-флоу.
4. **Тест Steam импорта дубликатов** — проверка обработки повторных импортов.

### Приоритет 3: Фронтенд и пользовательский опыт
5. **CTA при пустом списке игр** — отображение кнопки для добавления игр.
6. **Очистка localStorage при logout** — удаление временных данных.

### Приоритет 4: Архитектурные улучшения
7. **DI рефакторинг в recommendation_service** — улучшение инъекции зависимостей.
8. **Структурированное логирование (JSON)** — переход на JSON-логи для продакшена.

---

## 💡 Рекомендации по дальнейшему развитию

1. **Реструктуризация логики Steam API**: Извлеките дублированный код в отдельный сервис для Steam API.
2. **Использование абстракции для AI-провайдера**: Убедитесь, что `OllamaProvider` и `LocalAIProvider` корректно обрабатывают ошибки.
3. **Улучшение тестов**: Добавьте интеграционные тесты для проверки взаимодействия с реальной БД и Steam API.
4. **Отслеживание ошибок**: Настройте Sentry или аналогичный инструмент для мониторинга ошибок в продакшене.