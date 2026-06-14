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

## 2. Что реализовано (фазы 1–4 завершены)

### Фаза 1: Очистка технического долга ✅
1. Удалён мёртвый код (`if False else None`) в `recommendation_service.py`
2. Создан `steam_utils.py` — общие функции и константы
3. `__import__("requests")` заменён на `import requests`
4. Дублирующийся импорт `RepoGameRepository` убран
5. Неиспользуемые зависимости (`email-validator`, `passlib[bcrypt]`) удалены из `pyproject.toml`
6. Документация обновлена (`release_date` в ERD, Steam endpoints в OpenAPI)

### Фаза 2: Улучшение тестов ✅
7. Тесты API роутеров (`test_api_routers.py`): 6 тестов
8. Тесты Steam integration (`test_steam_integration.py`): 5 тестов с моками
9. Тест `release_date=None` — игры без даты фильтруются
10. Тесты `steam_utils.py`: 6 тестов

### Исправление бага "No recommendations were generated" ✅
- `generate_candidates_for_group` переписан: сначала локальные кандидаты, затем best-effort Steam-обогащение

### Фаза 3: Фронтенд ✅
11. Steam search/import UI в `GamesPanel.tsx`
12. Кнопка "Generate & Persist" в `RecommendationsPanel.tsx`
13. Auto-refresh токенов в `ApiClient` (401 → refresh → retry)
14. `release_date` добавлен в тип `Game`

### Фаза 4: Жёсткий co-op фильтр ✅
15. `_is_coop_game()` переработан: проверка description, строгие ключевые слова, убраны ложные срабатывания

---

## 3. Оставшиеся проблемы

### Backend

| # | Компонент | Проблема | Приоритет |
|---|-----------|----------|-----------|
| B1 | `llm_provider.py` | Паттерн fallback (Ollama → AIService) молча скрывает ошибки сети/конфигурации — нет логирования ошибок при fallback | Средний |
| B2 | `external.py` | Steam import не проверяет дубликаты по `external_id` до INSERT — unique constraint может выбросить необработанное исключение | Высокий |
| B3 | `recommendation_service.py` | Прямые импорты `requests` и `get_llm_provider` смешивают уровни архитектуры (нарушение DI) | Низкий |
| B4 | `external.py` | Нет rate limiting / таймаутов для вызовов Steam API | Средний |
| B5 | Steam import | Нет логирования успешного импорта (только логирование skip) | Низкий |

### Frontend

| # | Компонент | Проблема | Приоритет |
|---|-----------|----------|-----------|
| F1 | `DashboardShell.tsx` | Если список игр пуст — `selectedGameId` остаётся `null`, нет UX-подсказки | Средний |
| F2 | `DashboardShell.tsx` | Транзиентные результаты в localStorage (`transient_recs:{groupId}`) не очищаются при logout | Низкий |
| F3 | UX | Нет индикации загрузки/пустого состояния для recommendations | Низкий |

### Тесты

| # | Тип | Что отсутствует | Приоритет |
|---|-----|-----------------|-----------|
| T1 | Интеграционные | Нет тестов репозиториев (с реальной/тестовой БД) | Средний |
| T2 | Интеграционные | Нет интеграционных тестов API через TestClient с БД | Средний |
| T3 | Unit | Нет тестов фронтенда (нет ни одного .test.ts/.spec.ts) | Низкий |
| T4 | Unit | Нет теста на Steam import дубликаты (когда `external_id` уже существует) | Средний |

### Архитектура / Инфраструктура

| # | Область | Проблема | Приоритет |
|---|---------|----------|-----------|
| A1 | DI | `recommendation_service.py` создаёт/импортирует зависимости напрямую вместо получения через FastAPI Depends | Низкий |
| A2 | Embedding | `EMBEDDING_DIM=8` — слишком мало для продакшена, нужен миграционный путь | Низкий |
| A3 | Логирование | Нет структурированного логирования (JSON logs) | Низкий |

---

## 4. План действий (следующие шаги)

### Приоритет 1: Backend Hardening (b1 — b2)
> Срок: ~1–2 дня

- [ ] **B2: Проверка дубликатов Steam import** — перед `INSERT` в `external.py` проверять существование `external_id`, возвращать 409 Conflict если уже есть. Добавить тест `test_steam_import_duplicate`.
- [ ] **B1: Логирование fallback в llm_provider** — добавить `logger.warning()` при fallback с Ollama на AIService, чтобы ошибки не терялись молча.

### Приоритет 2: Тесты покрытия (t1 — t4)
> Срок: ~2–3 дня

- [ ] **T4: Тест Steam import дубликат** — проверить что повторный импорт одного и того же `external_id` корректно обрабатывается.
- [ ] **T2: Интеграционные тесты API** — создать `test_api_integration.py` с TestClient + test DB: полный флоу register → create group → add game → create review → generate recommendations.
- [ ] **T1: Тесты репозиториев** — тесты CRUD для `GameRepository`, `ReviewRepository`, `RecommendationRepository` через test DB.

### Приоритет 3: Frontend Polish (f1 — f3)
> Срок: ~1 день

- [ ] **F1: Пустой список игр** — показать CTA "Добавьте игру (через Steam или вручную)" когда `games.length === 0`, вместо пустого состояния.
- [ ] **F2: Очистка localStorage при logout** — удалить `transient_recs:*` ключи при logout.
- [ ] **F3: Индикация состояний** — skeleton/spinner при загрузке рекомендаций, пустое состояние если рекомендаций нет.

### Приоритет 4: Architecture & Polish (a1 — a3, b3 — b5)
> Срок: ~2–3 дня (можно отложить)

- [ ] **B4: Rate limiting для Steam API** — добавить simple in-memory rate limiter или использовать `aiolimiter` для Steam API вызовов.
- [ ] **B3: DI в recommendation_service** — рефакторинг: передавать зависимости через конструктор/`Depends` вместо прямых импортов.
- [ ] **B5: Логирование Steam import** — добавить `logger.info()` при успешном импорте.
- [ ] **A3: Структурированное логирование** — настроить JSON-формат логов для продакшена.
- [ ] **A2: Путь к production embedding_dim** — спроектировать миграцию `vector(8)` → `vector(384)` с переимпортом данных.

### Приоритет 5: Production Readiness (отдалённая перспектива)

- [ ] Rate limiting на API endpoints (nginx/cloudflare или fastapi-limiter)
- [ ] Prometheus метрики / health check расширение
- [ ] CI/CD pipeline (GitHub Actions: lint → test → build → deploy)
- [ ] HTTPS / домен для продакшена
- [ ] Мониторинг ошибок (Sentry или аналог)

---

## 5. Структура проекта

```
├── apps/
│   ├── api/                        # FastAPI backend
│   │   ├── alembic/                # Миграции БД
│   │   ├── app/
│   │   │   ├── api/v1/routers/     # Роутеры (auth, games, groups, reviews, recommendations, dashboard, external)
│   │   │   ├── application/services/ # Бизнес-логика (AI, auth, profile, recommendation, vector_math, llm_provider, steam_utils)
│   │   │   ├── core/               # Конфиг, security (JWT, password)
│   │   │   ├── domain/             # Entity (dataclass: ReviewAnalysis, SimilarGame)
│   │   │   ├── infrastructure/     # DB models, repositories, session
│   │   │   ├── schemas/            # Pydantic схемы
│   │   │   └── tests/              # Unit тесты
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