# Mini CRM

Минималистичная CRM система на FastAPI с SQLAlchemy 2.0 и PostgreSQL для управления контактами, сделками и задачами в организации.

## Возможности

- 🔐 **Аутентификация** - JWT токены (access + refresh), регистрация пользователей
- 🏢 **Организации** - мультитенантность с ролями (owner/admin/member)
- 👥 **Контакты** - управление клиентской базой
- 💼 **Сделки** - воронка продаж (lead → qualification → proposal → negotiation)
- ✅ **Задачи** - отслеживание работы по сделкам
- 📝 **Активности** - лог событий по сущностям
- 📊 **Аналитика** - сводки и воронка продаж с кешированием

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                         Client                              │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Nginx (Reverse Proxy)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Application                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  API Layer (v1)                                      │   │
│  │  ├─ auth         - аутентификация                    │   │
│  │  ├─ organizations - управление организациями         │   │
│  │  ├─ contacts     - работа с контактами               │   │
│  │  ├─ deals        - управление сделками               │   │
│  │  ├─ tasks        - задачи                            │   │
│  │  ├─ activities   - лог событий                       │   │
│  │  └─ analytics    - аналитика и отчеты                │   │
│  └────────────┬─────────────────────────────────────────┘   │
│               │                                              │
│  ┌────────────▼─────────────────────────────────────────┐   │
│  │  Service Layer                                       │   │
│  │  - Бизнес-логика                                     │   │
│  │  - Валидация данных                                  │   │
│  │  - Агрегация из нескольких источников                │   │
│  └────────────┬─────────────────────────────────────────┘   │
│               │                                              │
│  ┌────────────▼─────────────────────────────────────────┐   │
│  │  Repository Layer                                    │   │
│  │  - CRUD операции                                     │   │
│  │  - Запросы к БД                                      │   │
│  │  - Фильтрация и пагинация                            │   │
│  └────────────┬─────────────────────────────────────────┘   │
│               │                                              │
│  ┌────────────▼─────────────────────────────────────────┐   │
│  │  SQLAlchemy Models                                   │   │
│  │  - ORM модели                                        │   │
│  │  - Связи между сущностями                            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────┬─────────────────────────┬────────────────────┘
              │                         │
              ▼                         ▼
    ┌──────────────────┐      ┌──────────────────┐
    │   PostgreSQL     │      │      Redis       │
    │   - Данные       │      │   - Кеширование  │
    │   - Индексы      │      │   - Аналитика    │
    └──────────────────┘      └──────────────────┘
```

### Слои архитектуры

1. **API Layer** (`src/api/v1/`)
   - REST endpoints
   - Валидация входных данных (Pydantic)
   - Документация OpenAPI
   - Dependency injection

2. **Service Layer** (`src/services/`)
   - Бизнес-логика приложения
   - Работа с несколькими репозиториями
   - Управление транзакциями
   - Логирование событий

3. **Repository Layer** (`src/repositories/`)
   - Абстракция над БД
   - Базовые CRUD операции
   - Специфичные запросы
   - Фильтрация и пагинация

4. **Model Layer** (`src/models/`)
   - SQLAlchemy ORM модели
   - Связи между таблицами
   - Индексы и constraints

## Технологический стек

- **FastAPI** 0.123+ - асинхронный веб-фреймворк
- **SQLAlchemy 2.0** - ORM с async поддержкой
- **PostgreSQL 17** - основная БД
- **Redis 7** - кеширование аналитики
- **Alembic** - миграции БД
- **Pydantic v2** - валидация и сериализация
- **uvicorn + gunicorn** - ASGI сервер
- **Docker + docker-compose** - контейнеризация
- **Nginx** - reverse proxy

### Dev инструменты

- **pytest** - тестирование
- **ruff** - линтинг и форматирование
- **mypy** - проверка типов
- **uv** - управление зависимостями

## Структура проекта

```
mini_crm/
├── src/
│   ├── api/
│   │   ├── dependencies/    # DI: auth, org context, pagination
│   │   └── v1/              # API endpoints v1
│   ├── core/                # Конфиги, БД, кеш, security
│   ├── models/              # SQLAlchemy модели
│   ├── repositories/        # Data access layer
│   ├── schemas/             # Pydantic схемы
│   └── services/            # Бизнес-логика
├── alembic/                 # Миграции БД
├── tests/                   # Тесты
├── nginx/                   # Nginx конфиг
├── docker-compose.yaml      # Оркестрация сервисов
└── pyproject.toml           # Зависимости и настройки
```

## Быстрый старт с Docker Compose

### Предварительные требования

- Docker 20.10+
- Docker Compose v2+

### Запуск приложения

```bash
# 1. Клонируйте репозиторий
git clone <repository-url>
cd mini_crm

# 2. Создайте .env файл (опционально, есть значения по умолчанию)
cat > .env << EOF
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=mini_crm
POSTGRES_HOST=db
POSTGRES_PORT=5432
REDIS_HOST=redis
REDIS_PORT=6379
SECRET_KEY=your-secret-key-here-change-in-production
EOF

# 3. Запустите все сервисы
docker-compose up -d

# 4. Проверьте статус
docker-compose ps
```

**Приложение доступно:**
- API: http://localhost:80
- Swagger UI: http://localhost:80/docs
- ReDoc: http://localhost:80/redoc
- Health check: http://localhost:80/health

### Инициализация администратора

При первом запуске создайте администратора:

```bash
# Способ 1: Автоматически при старте (добавьте в .env)
CREATE_ADMIN_ON_STARTUP=true
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=SecurePass123
ADMIN_NAME=System Administrator
ADMIN_ORGANIZATION=My Company

# После добавления в .env, перезапустите
docker-compose restart crm

# Способ 2: Через CLI команду
docker-compose exec crm uv run crm-admin create-admin \
  -e admin@example.com \
  -p SecurePass123 \
  -n "Admin User" \
  -o "My Company"
```

**📖 Подробная документация:** [ADMIN_CLI.md](ADMIN_CLI.md)

### Проверка работы

```bash
# Логи всех сервисов
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f crm
docker-compose logs -f nginx
docker-compose logs -f db
docker-compose logs -f redis

# Проверка health endpoint
curl http://localhost:80/health
```

### Остановка

```bash
# Остановить сервисы (данные сохранятся)
docker-compose down

# Остановить и удалить данные
docker-compose down -v
```

## Локальная разработка

### Установка зависимостей

Проект использует [uv](https://github.com/astral-sh/uv) для управления зависимостями:

```bash
# Установка uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Установка зависимостей проекта
uv sync
```

### Настройка окружения

```bash
# Создайте .env файл для локальной разработки
cat > .env << EOF
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=mini_crm
POSTGRES_HOST=localhost  # для локальной разработки
POSTGRES_PORT=5432
REDIS_HOST=localhost    # для локальной разработки
REDIS_PORT=6379
SECRET_KEY=dev-secret-key-change-in-production

# Автоматическое создание администратора
CREATE_ADMIN_ON_STARTUP=true
ADMIN_EMAIL=admin@localhost
ADMIN_PASSWORD=dev123456
ADMIN_NAME=Dev Admin
ADMIN_ORGANIZATION=Dev Organization
EOF
```

### Запуск сервисов для разработки

```bash
# Запустите только БД и Redis в Docker
docker-compose up -d db redis

# Дождитесь готовности PostgreSQL
docker-compose logs db | grep "ready to accept connections"

# Примените миграции
uv run alembic upgrade head

# Запустите приложение в режиме разработки
cd src
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Приложение доступно:**
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Hot reload

При изменении файлов в `src/` uvicorn автоматически перезагрузит приложение.

### Запуск тестов

```bash
# Запуск всех тестов
uv run pytest

# С покрытием кода
uv run pytest --cov=src --cov-report=html

# Конкретный тест
uv run pytest tests/test_auth.py::TestAuthEndpoints::test_register

# В режиме verbose
uv run pytest -v
```

### Линтинг и форматирование

```bash
# Проверка кода
uv run ruff check src/

# Автоматическое форматирование
uv run ruff format src/

# Проверка типов
uv run mypy src/

# Запуск всех проверок
uv run ruff check src/ && uv run ruff format src/ && uv run mypy src/
```

## Работа с миграциями

### Автоматическое применение в Docker

При использовании docker-compose миграции применяются автоматически при старте CRM сервиса через `entrypoint.sh`:

```bash
# Миграции применяются автоматически
docker-compose up -d

# Просмотр логов миграций
docker-compose logs crm | grep "Running database migrations"

# Ручное применение (если контейнер уже запущен)
docker-compose exec crm uv run alembic upgrade head

# Проверка текущей версии БД
docker-compose exec crm uv run alembic current
```

### Создание новой миграции

```bash
# 1. Измените модели в src/models/
# 2. Создайте автоматическую миграцию
uv run alembic revision --autogenerate -m "Add user avatar field"

# 3. Проверьте созданный файл в alembic/versions/
# 4. Примените миграцию локально
uv run alembic upgrade head
```

### Управление миграциями

```bash
# Применить все миграции
uv run alembic upgrade head

# Применить следующую миграцию
uv run alembic upgrade +1

# Откатить последнюю миграцию
uv run alembic downgrade -1

# Откатить к конкретной версии
uv run alembic downgrade <revision_id>

# Просмотр истории
uv run alembic history

# Текущая версия БД
uv run alembic current
```

### ⚠️ Важные моменты

1. **Проверяйте сгенерированные миграции** - `--autogenerate` не всегда точен
2. **БД должна быть запущена** - миграции требуют подключения к PostgreSQL
3. **Бэкап на проде** - всегда делайте резервные копии перед миграциями
4. **Fail-fast** - если миграция падает, приложение не стартует

## Модели данных

### Основные сущности

```
User                 Organization
  ↓                       ↓
  └──→ OrganizationMember ←──┘
            ↓
            ├──→ Contact
            ├──→ Deal ──→ Task
            └──→ Activity
```

| Модель | Описание | Ключевые поля |
|--------|----------|---------------|
| **User** | Пользователи системы | email, hashed_password, full_name |
| **Organization** | Организации (мультитенантность) | name, created_by |
| **OrganizationMember** | Роли пользователей в организациях | user_id, organization_id, role |
| **Contact** | Контакты/клиенты | full_name, email, phone, organization_id |
| **Deal** | Сделки с воронкой | title, amount, stage, status |
| **Task** | Задачи по сделкам | title, description, due_date, status |
| **Activity** | Лог событий | entity_type, entity_id, action, details |

### Роли в организации

- **owner** - владелец организации (все права)
- **admin** - администратор (управление + редактирование)
- **member** - участник (только чтение)

### Статусы сделок

- **new** - новая сделка
- **in_progress** - в работе
- **won** - успешно закрыта
- **lost** - проиграна

### Этапы воронки продаж

- **lead** - лид (первичный контакт)
- **qualification** - квалификация
- **proposal** - предложение
- **negotiation** - переговоры

## API Endpoints

### Документация

После запуска доступна интерактивная документация:

- **Swagger UI**: http://localhost/docs
- **ReDoc**: http://localhost/redoc
- **OpenAPI JSON**: http://localhost/openapi.json

### Список endpoints

#### 🔐 Аутентификация `/api/v1/auth`

```
POST   /register        - Регистрация пользователя
POST   /login           - Вход (получение токенов)
POST   /refresh         - Обновление access токена
GET    /me              - Информация о текущем пользователе
```

#### 🏢 Организации `/api/v1/organizations`

```
POST   /                      - Создать организацию
GET    /                      - Список моих организаций
GET    /{id}                  - Детали организации
PUT    /{id}                  - Обновить организацию
DELETE /{id}                  - Удалить организацию
POST   /{id}/members          - Добавить участника
GET    /{id}/members          - Список участников
DELETE /{id}/members/{user_id} - Удалить участника
```

#### 👥 Контакты `/api/v1/contacts`

```
POST   /         - Создать контакт
GET    /         - Список контактов (с фильтрацией)
GET    /{id}     - Детали контакта
PUT    /{id}     - Обновить контакт
DELETE /{id}     - Удалить контакт
```

#### 💼 Сделки `/api/v1/deals`

```
POST   /              - Создать сделку
GET    /              - Список сделок (с фильтрацией по stage/status)
GET    /{id}          - Детали сделки
PUT    /{id}          - Обновить сделку
DELETE /{id}          - Удалить сделку
PATCH  /{id}/stage    - Изменить этап воронки
PATCH  /{id}/status   - Изменить статус
```

#### ✅ Задачи `/api/v1/tasks`

```
POST   /         - Создать задачу
GET    /         - Список задач (с фильтрацией)
GET    /{id}     - Детали задачи
PUT    /{id}     - Обновить задачу
DELETE /{id}     - Удалить задачу
```

#### 📝 Активности `/api/v1/activities`

```
GET    /         - Список событий (с фильтрацией)
GET    /{id}     - Детали события
```

#### 📊 Аналитика `/api/v1/analytics`

```
GET    /deals/summary   - Сводка по сделкам (с кешированием)
GET    /deals/funnel    - Воронка продаж (с кешированием)
```

### Аутентификация

Все защищенные endpoints требуют JWT токен в заголовке:

```bash
Authorization: Bearer <access_token>
```

Также требуется указать организацию в заголовке:

```bash
X-Organization-ID: <organization_id>
```

### Пример использования

```bash
# 1. Регистрация
curl -X POST http://localhost/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123", "full_name": "John Doe"}'

# 2. Вход
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# 3. Создание организации
curl -X POST http://localhost/api/v1/organizations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Company"}'

# 4. Создание контакта
curl -X POST http://localhost/api/v1/contacts \
  -H "Authorization: Bearer <token>" \
  -H "X-Organization-ID: <org_id>" \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Jane Smith", "email": "jane@example.com"}'
```

## Дополнительно

### Кеширование

Приложение использует Redis для кеширования:

- **Аналитика** - результаты запросов кешируются на 5 минут
- **Сводки** - агрегированные данные по сделкам
- **Воронка** - статистика по этапам продаж

Настройки кеша в `.env`:

```env
REDIS_HOST=redis
REDIS_PORT=6379
UNIT_CACHE_EXPIRE_IN_SECONDS=300  # 5 минут
```

### Логирование

Приложение логирует в stdout в формате JSON:

```json
{
  "timestamp": "2024-01-01T12:00:00",
  "level": "INFO",
  "message": "User registered",
  "user_id": 123
}
```

Просмотр логов:

```bash
# Все логи
docker-compose logs -f crm

# Только ошибки
docker-compose logs crm | grep ERROR

# Последние 100 строк
docker-compose logs --tail=100 crm
```

### Мониторинг

Health check endpoint для мониторинга:

```bash
curl http://localhost/health
```

Ответ:

```json
{
  "status": "ok",
  "service": "Mini CRM",
  "cache": "ok"
}
```

## Production Deploy

### Чеклист безопасности (ввиду сжатости по времени и ресурсам, я решил что пока эти пункты опустим)

- [ ] Используйте HTTPS/TLS для всех подключений
- [ ] Установите сложные пароли для PostgreSQL
- [ ] Настройте firewall (только порты 80/443)
- [ ] Включите CORS только для нужных доменов
- [ ] Настройте rate limiting на Nginx
- [ ] Настройте SSL + пароль для Redis

### Переменные окружения для prod

```env
# Security
SECRET_KEY=<strong-random-secret-key-64-chars>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database (managed service)
POSTGRES_HOST=<rds-endpoint>
POSTGRES_PORT=5432
POSTGRES_DB=mini_crm_prod
POSTGRES_USER=<db-user>
POSTGRES_PASSWORD=<strong-password>

# Redis (managed service or ElastiCache)
REDIS_HOST=<redis-endpoint>
REDIS_PORT=6379

# App
PROJECT_NAME="Mini CRM"
UNIT_CACHE_EXPIRE_IN_SECONDS=300
```

### Docker для production

```bash
# Build production image
docker build -t mini-crm:latest .

# Run with production config
docker-compose -f docker-compose.prod.yaml up -d
```

### Миграции в production

Миграции применяются автоматически через `entrypoint.sh`:

```bash
# Логика в entrypoint.sh:
# 1. Ждем доступности БД
# 2. Применяем миграции (alembic upgrade head)
# 3. Если миграции fail - контейнер упадет
# 4. Запускаем gunicorn только после успешных миграций
```

Для критичных миграций с даунтаймом:

```bash
# 1. Остановите приложение
docker-compose stop crm

# 2. Примените миграции вручную
docker-compose run --rm crm uv run alembic upgrade head

# 3. Запустите приложение
docker-compose start crm
```

### CI/CD Pipeline

```yaml
# Пример GitHub Actions
name: Deploy Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          uv sync
          uv run pytest

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Build and push Docker image
        run: docker build -t mini-crm:${{ github.sha }} .
      - name: Deploy to production
        run: |
          # Деплой в Kubernetes/ECS/etc
```

### Мониторинг и алерты

Рекомендуемые инструменты:

- **Логи**: ELK Stack, CloudWatch, DataDog
- **Метрики**: Prometheus + Grafana
- **APM**: Sentry, New Relic
- **Uptime**: UptimeRobot, Pingdom

### Бэкапы

PostgreSQL:

```bash
# Автоматический бэкап (cron)
0 2 * * * pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +\%Y\%m\%d).sql

# Восстановление
psql -h $POSTGRES_HOST -U $POSTGRES_USER $POSTGRES_DB < backup_20240101.sql
```

Используйте managed БД для автоматических бэкапов.

### Масштабирование

**Горизонтальное:**
- Запускайте несколько инстансов FastAPI за load balancer
- Stateless архитектура позволяет легко масштабироваться
- Nginx upstream для балансировки

**Вертикальное:**
- Увеличьте workers в gunicorn (CPU cores * 2 + 1)
- Настройте connection pool для PostgreSQL
- Увеличьте memory для Redis

**База данных:**
- Настройте read replicas для PostgreSQL
- Используйте connection pooling (PgBouncer)

## Troubleshooting

### Проблемы с подключением к БД

```bash
# Проверьте статус PostgreSQL
docker-compose ps db

# Проверьте логи
docker-compose logs db

# Проверьте подключение вручную
docker-compose exec db psql -U postgres -d mini_crm
```

### Проблемы с Redis

```bash
# Проверьте статус Redis
docker-compose ps redis

# Проверьте подключение
docker-compose exec redis redis-cli ping
# Должно вернуть: PONG
```

### Миграции не применяются

```bash
# Проверьте логи миграций
docker-compose logs crm | grep -A10 "Running database migrations"

# Примените вручную
docker-compose exec crm uv run alembic upgrade head

# Проверьте текущую версию
docker-compose exec crm uv run alembic current
```

### Порты заняты

```bash
# Найти процесс на порту 80
lsof -i :80

# Найти процесс на порту 8000
lsof -i :8000

# Остановить процесс
kill -9 <PID>
```

## Производительность

### Мониторинг медленных запросов

```sql
-- Включить логирование медленных запросов
ALTER SYSTEM SET log_min_duration_statement = 1000; -- 1 секунда
SELECT pg_reload_conf();

-- Просмотр медленных запросов
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

## Roadmap

- [ ] Webhooks для интеграций
- [ ] Email уведомления
- [ ] Импорт/экспорт данных (CSV, Excel)
- [ ] Кастомные поля для сущностей
- [ ] Отчеты и дашборды

## Contributing

1. Fork проект
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

### Стандарты кода

- Следуйте PEP 8
- Используйте type hints
- Пишите docstrings для функций
- Покрытие тестами > 80%
- Проверяйте код: `ruff check src/`
- Форматируйте: `ruff format src/`

---

**Сделано с ❤️ на FastAPI**
