# Тесты CRM системы

## Структура тестов

### Unit-тесты бизнес-логики
- `test_business_logic_permissions.py` - проверка ролей и прав доступа
- `test_business_logic_deals.py` - бизнес-правила для сделок
- `test_business_logic_contacts.py` - бизнес-правила для контактов
- `test_business_logic_tasks.py` - бизнес-правила для задач

### Интеграционные тесты API
- `test_integration_api.py` - полные сценарии работы через API

## Запуск тестов

### Требования
1. Запущенный PostgreSQL (параметры из `.env`)
2. Установленные зависимости: `uv sync --extra dev`

### Команды

```bash
# Все тесты
uv run pytest tests/ -v

# Только unit-тесты (без БД)
uv run pytest tests/test_business_logic_permissions.py -v

# Конкретный тест
uv run pytest tests/test_business_logic_deals.py::TestDealCreationRules -v

# С покрытием кода
uv run pytest tests/ -v --cov=src --cov-report=html
```

## Покрытие бизнес-правил

### Multi-tenant и роли
- ✅ Owner/admin доступ ко всем ресурсам
- ✅ Manager доступ ко всем ресурсам
- ✅ Member только к своим ресурсам

### Правила по сделкам
- ✅ Нельзя закрыть сделку как won с amount <= 0
- ✅ Нельзя откатить стадию назад (кроме admin/owner)
- ✅ Автосоздание Activity при смене статуса/стадии
- ✅ Контакт должен быть из той же организации

### Правила по контактам
- ✅ Нельзя удалить контакт с существующими сделками

### Правила по задачам
- ✅ Member не может создать задачу для чужой сделки
- ✅ Нельзя установить due_date в прошлом

### Интеграционные сценарии
- ✅ Полный workflow: регистрация → организация → участники → контакты → сделки → задачи → аналитика
- ✅ Multi-tenant изоляция
- ✅ Role-based access control

## Тестовая БД

Тесты автоматически создают отдельную БД с суффиксом `_test`:
- Основная БД: `crm_database` (из .env)
- Тестовая БД: `crm_database_test`

БД создаётся перед тестами и удаляется после.
