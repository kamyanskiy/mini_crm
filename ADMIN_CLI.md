# CRM Admin CLI - Руководство

CLI инструмент для управления администраторами и пользователями CRM системы.

## Установка

```bash
# Установите зависимости
uv sync

# Проверьте доступность команды
uv run crm-admin --help
```

---

## Команды

### 1. Автоматическая инициализация администратора

Создает администратора из переменных окружения (используется в Docker entrypoint):

```bash
uv run crm-admin init
```

**Переменные окружения:**

```env
CREATE_ADMIN_ON_STARTUP=true
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=SecurePass123
ADMIN_NAME=System Administrator
ADMIN_ORGANIZATION=Default Organization
```

**Примечание:** Эта команда автоматически запускается при старте Docker контейнера через `entrypoint.sh`.

---

### 2. Создать администратора вручную

Создает пользователя с ролью OWNER в новой организации:

```bash
uv run crm-admin create-admin \
  --email admin@example.com \
  --password "SecurePass123" \
  --name "Admin User" \
  --org "My Company"
```

**Короткий синтаксис:**

```bash
uv run crm-admin create-admin -e admin@example.com -p SecurePass123 -n "Admin User" -o "My Company"
```

**Параметры:**
- `-e, --email` - Email администратора (обязательно)
- `-p, --password` - Пароль (минимум 8 символов, обязательно)
- `-n, --name` - Полное имя (обязательно)
- `-o, --org` - Название организации (по умолчанию: "Admin Organization")

**Пример вывода:**

```
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ Field        ┃ Value              ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ User ID      │ 1                  │
│ Email        │ admin@example.com  │
│ Name         │ Admin User         │
│ Organization │ My Company         │
│ Role         │ OWNER              │
└──────────────┴────────────────────┘
```

---

### 3. Список пользователей

```bash
uv run crm-admin list-users
```

**Вывод:**

```
┏━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━┓
┃ ID ┃ Email              ┃ Name       ┃ Active ┃
┡━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━┩
│ 1  │ admin@example.com  │ Admin User │ ✅     │
│ 2  │ user@example.com   │ John Doe   │ ✅     │
└────┴────────────────────┴────────────┴────────┘
```

---

### 4. Список организаций

```bash
uv run crm-admin list-orgs
```

**Вывод:**

```
┏━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ ID ┃ Name       ┃ Created At       ┃
┡━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ 1  │ My Company │ 2024-12-02 10:30 │
└────┴────────────┴──────────────────┘
```

---

### 5. Помощь

```bash
# Список команд
uv run crm-admin --help

# Помощь по команде
uv run crm-admin create-admin --help
uv run crm-admin init --help
```

---

## Автоматическое создание администратора при старте

### Настройка через .env

Создайте `.env` файл или добавьте переменные:

```env
# Initial Admin Setup
CREATE_ADMIN_ON_STARTUP=true
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=changeme123
ADMIN_NAME=System Administrator
ADMIN_ORGANIZATION=Default Organization
```

### Как это работает

1. **Docker контейнер** запускается через `entrypoint.sh`
2. Применяются миграции: `alembic upgrade head`
3. Запускается команда: `crm-admin init`
4. Команда проверяет `CREATE_ADMIN_ON_STARTUP=true`
5. Если пользователь не существует, создается администратор
6. Запускается gunicorn

### Логи при создании

```
Running database migrations...
Migrations completed successfully
Checking admin initialization...
✓ Admin user created: admin@example.com (ID: 1)
✓ Organization created: Default Organization (ID: 1)
✓ Admin user 'admin@example.com' assigned as OWNER of 'Default Organization'
============================================================
ADMIN CREDENTIALS:
  Email: admin@example.com
  Password: changeme123
  ⚠️  CHANGE PASSWORD IMMEDIATELY IN PRODUCTION!
============================================================
Admin initialization check completed
```

---

## Использование в разных окружениях

### Development (локальная разработка)

```bash
# .env
CREATE_ADMIN_ON_STARTUP=true
ADMIN_EMAIL=dev@localhost
ADMIN_PASSWORD=dev123456
ADMIN_NAME=Dev Admin
ADMIN_ORGANIZATION=Dev Organization

# Запустить инициализацию
uv run crm-admin init
```

### Docker Compose

```bash
# Добавьте в .env
CREATE_ADMIN_ON_STARTUP=true
ADMIN_EMAIL=admin@company.com
ADMIN_PASSWORD=SecurePass123
ADMIN_NAME=System Admin

# Запустите/перезапустите
docker-compose up -d
docker-compose restart crm
```

### Docker Run

```bash
docker run -d \
  -e CREATE_ADMIN_ON_STARTUP=true \
  -e ADMIN_EMAIL=admin@example.com \
  -e ADMIN_PASSWORD=SecurePass123 \
  -e ADMIN_NAME="Admin User" \
  mini-crm
```

### Kubernetes

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: crm-admin-secret
stringData:
  admin-email: admin@example.com
  admin-password: SecurePass123
---
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: crm
        env:
        - name: CREATE_ADMIN_ON_STARTUP
          value: "true"
        - name: ADMIN_EMAIL
          valueFrom:
            secretKeyRef:
              name: crm-admin-secret
              key: admin-email
        - name: ADMIN_PASSWORD
          valueFrom:
            secretKeyRef:
              name: crm-admin-secret
              key: admin-password
```

---

## Роли и права администратора

Созданный администратор получает роль **OWNER** и может:

- ✅ Управлять пользователями (создание, редактирование, удаление)
- ✅ Назначать роли: OWNER, ADMIN, MANAGER, MEMBER
- ✅ Управлять всеми сущностями (контакты, сделки, задачи)
- ✅ Просматривать и экспортировать аналитику
- ✅ Управлять настройками организации
- ✅ Полный доступ ко всем API endpoints

**Иерархия ролей:**
```
OWNER     - полный доступ ко всему
  ↓
ADMIN     - управление + редактирование
  ↓
MANAGER   - редактирование всех ресурсов
  ↓
MEMBER    - только свои ресурсы
```

---

## Безопасность

### ⚠️ Для Production

**1. Используйте сильные пароли:**

```env
ADMIN_PASSWORD=YourVerySecurePassword123!@#$%
```

**2. Измените JWT secret:**

```env
JWT_SECRET_KEY=your-very-long-and-random-secret-key-64-chars-minimum
```

**3. Отключите после первого запуска (опционально):**

```env
CREATE_ADMIN_ON_STARTUP=false
```

**4. Защитите .env файл:**

```bash
chmod 600 .env
```

**5. Используйте секретные хранилища:**
- AWS Secrets Manager
- HashiCorp Vault
- Kubernetes Secrets
- Azure Key Vault

### Требования к паролю

- ✅ Минимум 8 символов
- ✅ Рекомендуется: буквы, цифры, спецсимволы
- ❌ Не используйте простые пароли: `password`, `123456`, `admin`

---

## Примеры использования

### Быстрый старт - первый администратор

```bash
# Способ 1: Через CLI (рекомендуется для локальной разработки)
uv run crm-admin create-admin \
  -e admin@company.com \
  -p "MySecurePassword123" \
  -n "System Administrator"

# Способ 2: Через переменные окружения (для Docker)
# Настройте .env и запустите
docker-compose up -d
```

### Создание администратора для новой компании

```bash
uv run crm-admin create-admin \
  -e ceo@startup.com \
  -p "StartupPass2024" \
  -n "CEO Name" \
  -o "Startup Inc"
```

### Проверка созданных пользователей

```bash
uv run crm-admin list-users
uv run crm-admin list-orgs
```

---

## Troubleshooting

### "User already exists"

**Проблема:** Пользователь с таким email уже зарегистрирован.

**Решение:**
- Используйте другой email
- Или войдите с существующими credentials
- Используйте `list-users` для просмотра существующих пользователей

### "Password must be at least 8 characters"

**Проблема:** Пароль слишком короткий.

**Решение:** Используйте пароль минимум 8 символов.

### Database connection failed

**Проблема:** Ошибка подключения к БД.

**Решение:**
1. Проверьте, что PostgreSQL запущен
2. Проверьте параметры в `.env`:
   ```env
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=crm_database
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   ```
3. Примените миграции:
   ```bash
   uv run alembic upgrade head
   ```

### Admin не создается автоматически

**Проблема:** Администратор не создается при запуске Docker.

**Решение:**
1. Проверьте `.env`: `CREATE_ADMIN_ON_STARTUP=true`
2. Проверьте логи:
   ```bash
   docker-compose logs crm | grep "Admin"
   ```
3. Попробуйте вручную:
   ```bash
   docker-compose exec crm uv run crm-admin init
   ```

### Импорт typer/rich не найден

**Проблема:** При запуске CLI ошибки импорта.

**Решение:**
```bash
# Установите зависимости
uv sync

# Или вручную
uv pip install typer rich
```

---

## Интеграция с API

После создания администратора можно авторизоваться через API:

```bash
# 1. Войти
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "changeme123"
  }'

# Ответ:
# {
#   "access_token": "eyJ...",
#   "refresh_token": "eyJ...",
#   "token_type": "bearer"
# }

# 2. Использовать токен
curl http://localhost/api/v1/auth/me \
  -H "Authorization: Bearer eyJ..."
```

---

## См. также

- [README.md](README.md) - Общая документация проекта
- [ENV_VARIABLES.md](ENV_VARIABLES.md) - Все переменные окружения
- `.env.example` - Пример конфигурации
