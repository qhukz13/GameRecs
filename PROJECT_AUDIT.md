# Project Audit Report: Co-op Game Recommendations MVP

## 1. Цель проекта

**Co-op Game Recommendations MVP** — веб-платформа для рекомендации кооперативных игр группе друзей.

**Основная логика:**
- Пользователи пишут отзывы на игры
- AI-сервис извлекает `liked_features`, `disliked_features`, `sentiment` и эмбеддинг отзыва
- Профиль пользователя = среднее эмбеддингов его отзывов
- Профиль группы = среднее профилей её участников
- Кандидаты ранжируются по косинусной близости между эмбеддингом группы и эмбеддингом игры
- Результат сохраняется как рекомендация с AI-объяснением

**Стек:**
- **Backend:** FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, pgvector
- **Frontend:** Next.js 15, TypeScript, TailwindCSS, shadcn/ui-style
- **Database:** PostgreSQL + pgvector (dim=8)
- **Auth:** JWT access + refresh tokens (pbkdf2_sha256)
- **AI:** Детерминированный встроенный провайдер (AIService) с опциональной заменой на Ollama
- **Инфраструктура:** Docker Compose

---

## 2. Что уже реализовано

### Backend (`apps/api`)

**API роутеры (`/api/v1`):**

| Роутер | Методы | Статус |
|---|---|---|
| `/auth` | `POST /register`, `POST /login`, `POST /refresh`, `GET /me` | ✅ Реализовано |
| `/groups` | `POST /`, `GET /`, `GET /{id}`, `POST /{id}/invite`, `DELETE /{id}` | ✅ Реализовано |
| `/games` | `POST /`, `GET /`, `GET /{id}`, `GET /{id}/reviews`, `DELETE /{id}` | ✅ Реализовано |
| `/reviews` | `POST /`, `GET /me`, `GET /games/{id}`, `DELETE /{id}` | ✅ Реализовано |
| `/dashboard` | `GET /` | ✅ Реализовано |
| `/external` | `GET /steam/search`, `POST /steam/import` | ✅ Реализовано |
| `/groups/{id}/recommendations` | `POST /generate`, `GET /`, `DELETE /` | ✅ Реализовано |

**Сервисы:**
- `AuthService` — регистрация, логин, refresh токенов
- `AIService` — детерминированный AI: эмбеддинги по частоте слов в словаре, анализ отзывов, объяснение рекомендаций
- `OllamaProvider` — обёртка для вызова Ollama API с fallback на `AIService`
- `ProfileService` — обновление профиля пользователя и группы (усреднение эмбеддингов)
- `RecommendationService` — генерация рекомендаций: поиск похожих игр в локальной БД + интеграция со Steam

**Инфраструктура:**
- SQLAlchemy модели: `UserModel`, `RefreshTokenModel`, `GroupModel`, `GroupMemberModel`, `GameModel`, `ReviewModel`, `RecommendationModel`
- Репозитории: `UserRepository`, `RefreshTokenRepository`, `GroupRepository`, `GameRepository`, `ReviewRepository`, `RecommendationRepository`
- pgvector: `cosine_distance` для similarity search, `ivfflat` индекс
- Alembic миграции (2 версии: базовая + `release_date`)
- Seed script (`scripts/seed.py`)

**Безопасность:**
- JWT access tokens (30 мин) + refresh tokens (30 дней)
- Хеширование паролей через pbkdf2_sha256
- Хеширование refresh токенов в БД

### Frontend (`apps/web`)

- `app/layout.tsx` — корневой layout с ToastProvider
- `app/page.tsx` — рендерит DashboardShell
- `features/dashboard/DashboardShell.tsx` — главная страница с секциями:
  - AuthPanel (логин/регистрация)
  - GroupsPanel (список групп)
  - GamesPanel (список игр)
  - ReviewPanel (отзывы)
  - RecommendationsPanel (рекомендации с генерацией)
- `lib/api.ts` — ApiClient для HTTP запросов
- `components/ui/` — базовые UI компоненты (Button, Card, Badge, Toast, ConfirmDialog)

### Инфраструктура

- `docker-compose.yml` — API + Web + PostgreSQL (с pgvector)
- `Dockerfile` для api и web
- `.env.example`
- `infra/schema.sql` — standalone SQL схема
- `scripts/e2e_api_check.py`, `scripts/smoke_test.py` — скрипты проверки

---

## 3. Незавершённые части

### Backend

| Компонент | Проблема |
|---|---|
| `recommendation_service.py` | Метод `generate_for_group` содержит мёртвый код (строки 94-96: `if False else None`). |
| `recommendation_service.py` | Дублирование функций `_has_blacklist`, `_is_game_like`, констант `BLACKLIST_CATS`, `GAME_KEYWORDS` в `generate_for_group` и `generate_candidates_for_group`. |
| `recommendation_service.py` | Логика Steam-импорта в `generate_for_group` запутанная: создаёт игры в БД, но затем просто делает `search_similar` по локальной БД (перезаписывая `candidates`). |
| `llm_provider.py` | Паттерн fallback (Ollama → AIService) молча скрывает ошибки сети/конфигурации. |
| `external.py` | Steam import не проверяет дубликаты (`external_id` unique constraint может выбросить исключение). |
| Архитектура | В `recommendation_service.py` импортируется `requests` и `get_llm_provider` напрямую, а не через DI — смешение уровней. |
| Архитектура | `GameRepository` в `recommendation_service.py` импортируется дважды: как `GameRepository` и как `RepoGameRepository`. |

### Frontend

| Компонент | Проблема |
|---|---|
| `DashboardShell.tsx` | Нет выбора игры при загрузке, если список игр пуст — `selectedGameId` остаётся `null`. |
| `RecommendationsPanel.tsx` | Нет кнопки "Generate & Persist" (с `persist=true`), хотя API поддерживает. |
| Steam UI | Нет UI для `/external/steam/search` и `/external/steam/import` — только API-эндпоинты. |
| Токены | Refresh token хранится в localStorage, но никогда не используется для автоматического обновления — по истечении access token пользователь должен перелогиниться. |
| Типы | `Game` в `api.ts` не содержит `release_date`. |

### Документация

| Файл | Проблема |
|---|---|
| `docs/architecture.md` | SQL-схема в документации не включает колонку `release_date` для таблицы `games` (хотя реальная schema.sql и модель БД содержат). |
| `docs/architecture.md` | Не описаны эндпоинты `/external/steam/search`, `/external/steam/import`. |

### Тесты

| Файл | Статус |
|---|---|
| `test_recommendation_service.py` | ✅ Есть (3 теста) — использует стабы, тестирует базовую генерацию |
| `test_recommendation_service_extra.py` | ✅ Есть (2 теста) — пустой профиль, исключение сыгранных игр |
| `test_ai_service.py` | ✅ Есть |
| `test_llm_provider.py` | ✅ Есть |
| `test_llm_provider_parse.py` | ✅ Есть |
| `test_vector_math.py` | ✅ Есть |
| Интеграционные тесты (БД, роутеры) | ❌ Отсутствуют |
| Тесты репозиториев | ❌ Отсутствуют |
| Тесты фронтенда | ❌ Отсутствуют |

---

## 4. TODO и заглушки

### Код
1. **Мёртвый код** в `recommendation_service.py` (строки 94-96):
   ```python
   recent_reviews = self.reviews.db.scalars(...) if False else None
   ```
   Блок с `if False else None` никогда не выполняется.

2. **Неиспользуемые импорты** в `recommendation_service.py`:
   ```python
   from app.application.services.recommendation_service import _parse_steam_release_date  # в external.py
   ```
   Используется, но импорт выглядит как cross-module import.

3. **`passlib[bcrypt]`** в зависимостях не используется — код использует `pbkdf2_sha256`.

4. **`email-validator`** в зависимостях — не видно использования в коде.

5. **`# mark these as transient so callers can detect non-persisted candidates`** — transient кандидаты без персистенции.

6. **`logging.getLogger(__name__).info("Skipping steam:%s due to blacklist categories...")`** — логирование есть только для skip, нет для успешного импорта.

### Фронтенд
7. **Refresh token не ротируется** — в `DashboardShell.tsx` нет логики вызова `/auth/refresh`.

8. **Транзиентные результаты** сохраняются в localStorage под ключом `transient_recs:{groupId}`, но никогда не очищаются при logout.

---

## 5. Ошибки сборки и тестов

### Потенциальные проблемы при сборке
| Проблема | Описание |
|---|---|
| `passlib[bcrypt]` vs `pbkdf2_sha256` | В зависимостях указан `passlib[bcrypt]`, но код использует `pbkdf2_sha256`. Если bcrypt не установится — ничего не сломается, но лишняя зависимость. |
| `email-validator` | Включён в зависимости, но не используется в коде. |
| Отсутствие `release_date` в GameRead | Может вызвать ошибки сериализации, если фронтенд ожидает поле. |
| `http.client` import | `external.py` использует `__import__("requests")` вместо прямого импорта — нестандартный подход. |

### Тесты
- Все тесты используют стабы/mocks и не тестируют реальную БД или интеграцию.
- Нет тестов для API роутеров (fastapi TestClient).
- Нет тестов для Steam integration (нет моков для requests).
- Тесты `test_recommendation_service.py` могут не покрывать случай с `release_date=None` (игра без даты).

---

## 6. Следующий логичный шаг разработки

Предлагаемый порядок работ:

### Приоритет 1: Очистка кода (технический долг)
1. Удалить мёртвый код в `recommendation_service.py` (строки 94-96)
2. Вынести дублирующиеся функции (`_has_blacklist`, `_is_game_like`, константы) из `recommendation_service.py` в общие утилиты
3. Исправить импорты: `__import__("requests")` → `import requests`
4. Удалить неиспользуемые зависимости из `pyproject.toml` (или добавить `email-validator` в валидацию)
5. Обновить `docs/architecture.md`: добавить `release_date`, описать Steam endpoints

### Приоритет 2: Улучшение тестов
6. Добавить тесты для API роутеров с `TestClient`
7. Добавить тесты для Steam integration (моки requests)
8. Добавить тесты для репозиториев (с тестовой БД)
9. Добавить тест на `release_date=None` в recommendation service

### Приоритет 3: Фронтенд
10. Добавить UI для Steam search/import (поле поиска, список результатов, кнопка импорта)
11. Добавить кнопку "Generate & Persist" в RecommendationsPanel
12. Реализовать автоматический refresh токена при 401 ошибке в ApiClient

### Приоритет 4: Функциональность
13. Исправить Steam import: проверять дубликаты по `external_id` до создания
14. Улучшить обработку ошибок Steam API (rate limiting, таймауты)
15. Рассмотреть увеличение `embedding_dim` с 8 до большего значения для продакшена

---

## Структура проекта (сводка)

```
├── apps/
│   ├── api/                        # FastAPI backend
│   │   ├── alembic/                # Миграции БД
│   │   ├── app/
│   │   │   ├── api/v1/routers/     # Роутеры (auth, games, groups, reviews, recommendations, dashboard, external)
│   │   │   ├── application/services/ # Бизнес-логика (AI, auth, profile, recommendation, vector_math, llm_provider)
│   │   │   ├── core/               # Конфиг, security (JWT, password)
│   │   │   ├── domain/             # Entity (dataclass: ReviewAnalysis, SimilarGame)
│   │   │   ├── infrastructure/     # DB models, repositories, session
│   │   │   ├── schemas/            # Pydantic схемы
│   │   │   └── tests/              # Unit тесты (6 файлов)
│   │   └── scripts/seed.py
│   └── web/                        # Next.js frontend
│       ├── app/                    # Layout, pages
│       ├── components/ui/          # UI primitives
│       ├── features/               # Auth, Dashboard, Games, Groups, Recommendations, Reviews
│       └── lib/api.ts              # API клиент
├── docs/architecture.md            # Документация
├── infra/schema.sql                # SQL схема
├── docker-compose.yml
└── scripts/                        # Smoke/e2e тесты
```

**Всего файлов исходного кода (без node_modules):** ~60 файлов с кодом, ~6 тестовых файлов.