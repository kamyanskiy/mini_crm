# Анализ поведения бизнес-сущностей Mini CRM

## Оглавление
1. [Обзор системы](#обзор-системы)
2. [Ключевые бизнес-сущности](#ключевые-бизнес-сущности)
3. [Жизненные циклы сущностей](#жизненные-циклы-сущностей)
4. [Бизнес-правила и ограничения](#бизнес-правила-и-ограничения)
5. [Модель прав доступа](#модель-прав-доступа)
6. [Взаимодействие между сущностями](#взаимодействие-между-сущностями)
7. [Аналитика и метрики](#аналитика-и-метрики)
8. [Автоматизация процессов](#автоматизация-процессов)

---

## Обзор системы

Mini CRM представляет собой систему управления взаимоотношениями с клиентами (CRM) с мультитенантной архитектурой. Система организована вокруг концепции **Organizations** (организаций), где каждая организация имеет изолированное пространство для своих данных.

### Архитектурная модель данных

```
┌──────────────────────────────────────────────────────────┐
│                    МУЛЬТИТЕНАНТНОСТЬ                      │
└──────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
       User(1)     Organization(2)     User(N)
            │               │               │
            └───────┬───────┴───────┬───────┘
                    ▼               ▼
            OrganizationMember (роли)
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
    Contact      Deal       Activity
                   │
                   └──→ Task
```

---

## Ключевые бизнес-сущности

### 1. User (Пользователь)

**Назначение**: Представляет физического пользователя системы. Один пользователь может состоять в нескольких организациях с разными ролями.

#### Атрибуты
```python
{
    "id": int,                    # Уникальный идентификатор
    "email": str,                 # Уникальный email (логин)
    "hashed_password": str,       # Хэшированный пароль (bcrypt)
    "name": str,                  # Имя пользователя
    "is_active": bool,            # Активен ли аккаунт
    "created_at": datetime        # Дата регистрации
}
```

#### Связи
- **1:N** с `OrganizationMember` - может быть участником многих организаций
- **1:N** с `Contact` (owner) - владеет контактами
- **1:N** с `Deal` (owner) - владеет сделками
- **1:N** с `Activity` (author) - создает активности

#### Состояния
- **Active** (`is_active=True`) - нормальное состояние, может пользоваться системой
- **Inactive** (`is_active=False`) - деактивирован, вход запрещен

#### Поведение
- После регистрации пользователь активен по умолчанию
- Пользователь не может быть удален напрямую (только деактивирован)
- При аутентификации проверяется статус активности
- Пароль всегда хранится в хэшированном виде (bcrypt с salt)

---

### 2. Organization (Организация)

**Назначение**: Корневая сущность мультитенантности. Изолирует данные различных компаний/команд.

#### Атрибуты
```python
{
    "id": int,                    # Уникальный идентификатор
    "name": str,                  # Название организации
    "created_at": datetime        # Дата создания
}
```

#### Связи
- **1:N** с `OrganizationMember` - члены организации
- **1:N** с `Contact` - контакты организации
- **1:N** с `Deal` - сделки организации

#### Поведение
- При создании организации создатель автоматически получает роль `OWNER`
- Организация не может существовать без хотя бы одного владельца
- Удаление организации каскадно удаляет все связанные данные (contacts, deals, members)
- Изоляция данных: пользователь видит только данные своих организаций

---

### 3. OrganizationMember (Членство в организации)

**Назначение**: Связующая сущность между пользователями и организациями. Определяет роль пользователя в контексте конкретной организации.

#### Атрибуты
```python
{
    "id": int,
    "organization_id": int,       # FK на организацию
    "user_id": int,               # FK на пользователя
    "role": MemberRole            # Роль в организации
}
```

#### Роли (MemberRole Enum)
```python
class MemberRole(str, enum.Enum):
    OWNER = "owner"        # Владелец - все права
    ADMIN = "admin"        # Администратор - управление + редактирование
    MANAGER = "manager"    # Менеджер - создание/редактирование ресурсов
    MEMBER = "member"      # Участник - ограниченные права
```

#### Ограничения
- **Уникальность**: пара (organization_id, user_id) уникальна
- Нельзя добавить пользователя дважды в одну организацию
- Пользователь не может изменить свою собственную роль
- Пользователь не может удалить сам себя из организации

---

### 4. Contact (Контакт)

**Назначение**: Представляет клиента или потенциального клиента организации.

#### Атрибуты
```python
{
    "id": int,
    "organization_id": int,       # FK на организацию (изоляция)
    "owner_id": int,              # FK на владельца контакта
    "name": str,                  # ФИО контакта
    "email": str | None,          # Email (опционально)
    "phone": str | None,          # Телефон (опционально)
    "created_at": datetime
}
```

#### Связи
- **N:1** с `Organization` - принадлежит организации
- **N:1** с `User` (owner) - имеет владельца
- **1:N** с `Deal` - может быть связан с несколькими сделками

#### Жизненный цикл
```
CREATE → ACTIVE → UPDATE* → DELETE
                     ↓
            [Has Deals?] → NO → DELETE OK
                     ↓
                    YES → DELETE BLOCKED
```

#### Бизнес-правила
1. **Защита от удаления**: контакт с активными сделками не может быть удален
   - Требуется сначала переназначить или удалить связанные сделки
2. **Изоляция**: контакт привязан к организации, пользователи других организаций не видят его
3. **Владение**: каждый контакт имеет владельца (owner)
4. **Фильтрация**:
   - Members видят только свои контакты
   - Manager/Admin/Owner видят все контакты организации

---

### 5. Deal (Сделка)

**Назначение**: Ключевая бизнес-сущность - представляет потенциальную или завершенную продажу.

#### Атрибуты
```python
{
    "id": int,
    "organization_id": int,       # FK на организацию
    "contact_id": int | None,     # FK на контакт (опционально)
    "owner_id": int,              # FK на владельца сделки
    "title": str,                 # Название сделки
    "amount": Decimal,            # Сумма сделки
    "currency": str,              # Валюта (по умолчанию USD)
    "status": DealStatus,         # Текущий статус
    "stage": DealStage,           # Этап воронки продаж
    "created_at": datetime,
    "updated_at": datetime        # Автообновление
}
```

#### Связи
- **N:1** с `Organization` - принадлежит организации
- **N:1** с `Contact` - связана с контактом (опционально)
- **N:1** с `User` (owner) - имеет владельца
- **1:N** с `Task` - имеет задачи
- **1:N** с `Activity` - имеет историю активностей

#### Статусы (DealStatus Enum)
```python
class DealStatus(str, enum.Enum):
    NEW = "new"                # Новая сделка
    IN_PROGRESS = "in_progress" # В работе
    WON = "won"                # Выиграна
    LOST = "lost"              # Проиграна
```

#### Этапы воронки (DealStage Enum)
```python
class DealStage(str, enum.Enum):
    QUALIFICATION = "qualification"  # Квалификация (1)
    PROPOSAL = "proposal"            # Предложение (2)
    NEGOTIATION = "negotiation"      # Переговоры (3)
    CLOSED = "closed"                # Закрыта (4)
```

#### Жизненный цикл сделки

```
┌────────────────────────────────────────────────────────┐
│                    СОЗДАНИЕ СДЕЛКИ                      │
│  Status: NEW, Stage: QUALIFICATION                     │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│              ДВИЖЕНИЕ ПО ВОРОНКЕ                        │
│                                                         │
│  QUALIFICATION (1) → PROPOSAL (2) → NEGOTIATION (3)    │
│                                                         │
│  Прямое движение: любой пользователь                   │
│  Откат назад: только OWNER/ADMIN                       │
└────────────────────┬───────────────────────────────────┘
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │   WON   │ │  LOST   │ │ CLOSED  │
    │ Stage:  │ │ Stage:  │ │ (stage) │
    │ CLOSED  │ │ CLOSED  │ └─────────┘
    └─────────┘ └─────────┘
         │
         └──→ Автоматическое создание Activity
```

#### Бизнес-правила

##### 1. Валидация amount при закрытии
```python
if status == "won" and amount <= 0:
    raise BusinessRuleViolation(
        "Cannot close deal as won with amount <= 0"
    )
```
- Выигранная сделка должна иметь положительную сумму

##### 2. Контроль движения по этапам
```python
# Порядок этапов
STAGE_ORDER = {
    DealStage.QUALIFICATION: 1,
    DealStage.PROPOSAL: 2,
    DealStage.NEGOTIATION: 3,
    DealStage.CLOSED: 4,
}

# Правило отката
if new_stage_order < old_stage_order:
    # Откат назад - только для admin/owner
    if not auth_context.is_owner_or_admin():
        raise PermissionDenied(
            "Only admins and owners can rollback deal stages"
        )
```
- Движение вперед по этапам: доступно всем
- Откат назад: только OWNER или ADMIN

##### 3. Связь с контактом
```python
if contact_id and contact.organization_id != deal.organization_id:
    raise BusinessRuleViolation(
        "Contact does not belong to this organization"
    )
```
- Контакт должен принадлежать той же организации

##### 4. Автоматическое логирование
При изменении статуса или этапа автоматически создается Activity:
```python
# Пример для изменения статуса
Activity.create(
    type=ActivityType.STATUS_CHANGED,
    payload={
        "old_status": "in_progress",
        "new_status": "won"
    }
)
```

---

### 6. Task (Задача)

**Назначение**: Представляет действие или работу, которую нужно выполнить в рамках сделки.

#### Атрибуты
```python
{
    "id": int,
    "deal_id": int,               # FK на сделку
    "title": str,                 # Название задачи
    "description": str | None,    # Описание (опционально)
    "due_date": datetime | None,  # Срок выполнения
    "is_done": bool,              # Выполнена ли (по умолчанию False)
    "created_at": datetime
}
```

#### Связи
- **N:1** с `Deal` - принадлежит сделке
- Транзитивно связана с `Organization` через Deal

#### Жизненный цикл
```
CREATE → OPEN (is_done=False) → DONE (is_done=True)
  ↓                                      ↓
  └──────────────────┬───────────────────┘
                     │
                UPDATE/DELETE
```

#### Бизнес-правила

##### 1. Права доступа на основе владения сделкой
```python
# Members могут создавать/редактировать только задачи для своих сделок
if auth_context.is_member() and deal.owner_id != auth_context.user_id:
    raise PermissionDenied(
        "Members can only create tasks for their own deals"
    )
```

##### 2. Фильтрация по владельцу
```python
# Members видят только свои задачи
owner_id = auth_context.user_id if auth_context.is_member() else None
tasks = await repo.list_with_filters(
    organization_id=org_id,
    owner_id=owner_id,
    only_open=only_open,
    due_before=due_before,
    due_after=due_after
)
```

##### 3. Каскадное удаление
- При удалении сделки все связанные задачи удаляются автоматически

---

### 7. Activity (Активность)

**Назначение**: Аудит-лог всех важных событий, происходящих со сделкой. Иммутабельная сущность.

#### Атрибуты
```python
{
    "id": int,
    "deal_id": int,               # FK на сделку
    "author_id": int | None,      # FK на автора (null для системных)
    "type": ActivityType,         # Тип активности
    "payload": dict,              # JSONB - детали события
    "created_at": datetime        # Метка времени
}
```

#### Типы активностей (ActivityType Enum)
```python
class ActivityType(str, enum.Enum):
    COMMENT = "comment"           # Комментарий пользователя
    STATUS_CHANGED = "status_changed"    # Изменение статуса
    STAGE_CHANGED = "stage_changed"      # Изменение этапа
    TASK_CREATED = "task_created"        # Создание задачи
    SYSTEM = "system"                    # Системное событие
```

#### Payload структуры

##### STATUS_CHANGED
```json
{
  "old_status": "in_progress",
  "new_status": "won"
}
```

##### STAGE_CHANGED
```json
{
  "old_stage": "qualification",
  "new_stage": "proposal"
}
```

##### COMMENT
```json
{
  "text": "Called the client, they are interested"
}
```

##### TASK_CREATED
```json
{
  "task_id": 123,
  "task_title": "Follow up call"
}
```

#### Характеристики
- **Иммутабельность**: активности не могут быть изменены или удалены
- **Автоматическое создание**: при изменении статуса/этапа сделки
- **Пользовательские**: комментарии от пользователей
- **Системные**: `author_id = null` для автоматических событий
- **Хронология**: упорядочены по `created_at`

---

## Жизненные циклы сущностей

### Цикл работы со сделкой (полный пример)

```
День 1: СОЗДАНИЕ
─────────────────────────────────────
User: Manager создает сделку
→ Deal(status=NEW, stage=QUALIFICATION, amount=50000)
→ Activity(type=SYSTEM, payload={action: "created"})

День 3: КВАЛИФИКАЦИЯ
─────────────────────────────────────
User: Manager добавляет комментарий
→ Activity(type=COMMENT, payload={text: "Клиент заинтересован"})

User: Manager создает задачу
→ Task(title="Подготовить КП", due_date=2024-01-10)
→ Activity(type=TASK_CREATED)

День 5: ДВИЖЕНИЕ ПО ВОРОНКЕ
─────────────────────────────────────
User: Manager переводит в PROPOSAL
→ Deal.stage = PROPOSAL
→ Activity(type=STAGE_CHANGED, payload={
    old_stage: "qualification",
    new_stage: "proposal"
})

День 7: ПЕРЕГОВОРЫ
─────────────────────────────────────
User: Manager переводит в NEGOTIATION
→ Deal.stage = NEGOTIATION
→ Activity(type=STAGE_CHANGED)

День 10: ОТКАТ (особый случай)
─────────────────────────────────────
User: Member пытается вернуть в PROPOSAL
→ PERMISSION DENIED (откат только для Admin/Owner)

User: Admin возвращает в PROPOSAL
→ Deal.stage = PROPOSAL ✓
→ Activity(type=STAGE_CHANGED)

День 15: УСПЕШНОЕ ЗАКРЫТИЕ
─────────────────────────────────────
User: Manager закрывает как WON
→ Validate: amount > 0 ✓
→ Deal.status = WON
→ Deal.stage = CLOSED
→ Activity(type=STATUS_CHANGED, payload={
    old_status: "in_progress",
    new_status: "won"
})

АНАЛИТИКА:
→ Deals Summary обновляется (кэш инвалидируется)
→ Funnel Analytics пересчитываются
```

---

## Бизнес-правила и ограничения

### Матрица бизнес-правил

| Правило | Сущности | Условие | Действие |
|---------|----------|---------|----------|
| **Уникальность email** | User | При регистрации | Reject если email существует |
| **Активность аккаунта** | User | При логине | Reject если `is_active=False` |
| **Автоматический OWNER** | OrganizationMember | При создании Organization | Создатель → OWNER |
| **Уникальность членства** | OrganizationMember | При добавлении member | Reject если уже существует |
| **Самоизменение роли** | OrganizationMember | При смене роли | Reject если меняет свою роль |
| **Самоудаление** | OrganizationMember | При удалении member | Reject если удаляет себя |
| **Защита контакта** | Contact | При удалении | Reject если есть связанные Deal |
| **Amount > 0 для WON** | Deal | При status=WON | Reject если amount ≤ 0 |
| **Откат этапа** | Deal | При stage rollback | Allow только для Owner/Admin |
| **Контакт из той же org** | Deal | При связывании Contact | Reject если разные organizations |
| **Автологирование** | Activity | При изменении Deal.status/stage | Auto-create Activity |
| **Member видит свое** | Task | При списке задач | Filter по owner_id |
| **Task только для своих Deal** | Task | CRUD операции Member | Reject если не владелец Deal |

---

## Модель прав доступа

### Иерархия ролей

```
OWNER > ADMIN > MANAGER > MEMBER
```

### Матрица прав доступа

#### Организация (Organization)

| Действие | OWNER | ADMIN | MANAGER | MEMBER |
|----------|-------|-------|---------|--------|
| Просмотр | ✅ | ✅ | ✅ | ✅ |
| Создание | ✅ (автоматически становится Owner) | ✅ | ✅ | ✅ |
| Редактирование | ✅ | ✅ | ❌ | ❌ |
| Удаление | ✅ | ❌ | ❌ | ❌ |
| Добавление членов | ✅ | ✅ | ❌ | ❌ |
| Изменение ролей | ✅ | ✅ | ❌ | ❌ |
| Удаление членов | ✅ | ✅ | ❌ | ❌ |

#### Контакты (Contact)

| Действие | OWNER | ADMIN | MANAGER | MEMBER |
|----------|-------|-------|---------|--------|
| Просмотр всех | ✅ | ✅ | ✅ | ❌ |
| Просмотр своих | ✅ | ✅ | ✅ | ✅ |
| Создание | ✅ | ✅ | ✅ | ✅ |
| Редактирование всех | ✅ | ✅ | ✅ | ❌ |
| Редактирование своих | ✅ | ✅ | ✅ | ✅ |
| Удаление всех | ✅ | ✅ | ✅ | ❌ |
| Удаление своих | ✅ | ✅ | ✅ | ✅ |

#### Сделки (Deal)

| Действие | OWNER | ADMIN | MANAGER | MEMBER |
|----------|-------|-------|---------|--------|
| Просмотр всех | ✅ | ✅ | ✅ | ❌ |
| Просмотр своих | ✅ | ✅ | ✅ | ✅ |
| Создание | ✅ | ✅ | ✅ | ✅ |
| Редактирование всех | ✅ | ✅ | ✅ | ❌ |
| Редактирование своих | ✅ | ✅ | ✅ | ✅ |
| Продвижение по этапам | ✅ | ✅ | ✅ | ✅ |
| **Откат этапов** | ✅ | ✅ | ❌ | ❌ |
| Изменение статуса | ✅ | ✅ | ✅ | ✅ (свои) |
| Удаление | ✅ | ✅ | ✅ | ✅ (свои) |

#### Задачи (Task)

| Действие | OWNER | ADMIN | MANAGER | MEMBER |
|----------|-------|-------|---------|--------|
| Просмотр всех | ✅ | ✅ | ✅ | ❌ |
| Просмотр своих | ✅ | ✅ | ✅ | ✅ |
| Создание для всех Deal | ✅ | ✅ | ✅ | ❌ |
| Создание для своих Deal | ✅ | ✅ | ✅ | ✅ |
| Редактирование всех | ✅ | ✅ | ✅ | ❌ |
| Редактирование своих | ✅ | ✅ | ✅ | ✅ |
| Удаление | аналогично редактированию | | | |

#### Активности (Activity)

| Действие | OWNER | ADMIN | MANAGER | MEMBER |
|----------|-------|-------|---------|--------|
| Просмотр | ✅ | ✅ | ✅ | ✅ (для доступных Deal) |
| Создание (комментарии) | ✅ | ✅ | ✅ | ✅ |
| Редактирование | ❌ | ❌ | ❌ | ❌ |
| Удаление | ❌ | ❌ | ❌ | ❌ |

#### Аналитика

| Действие | OWNER | ADMIN | MANAGER | MEMBER |
|----------|-------|-------|---------|--------|
| Deals Summary | ✅ | ✅ | ✅ | ✅ (свои данные) |
| Deals Funnel | ✅ | ✅ | ✅ | ✅ (свои данные) |

### Реализация проверки прав

#### 1. Базовый AuthContext
```python
@dataclass
class AuthContext:
    user_id: int
    organization_id: int
    role: MemberRole

    def can_access_resource(self, resource_owner_id: int) -> bool:
        """
        Managers и выше: доступ ко всем ресурсам
        Members: только свои ресурсы
        """
        if self.is_manager_or_above():
            return True
        return self.user_id == resource_owner_id
```

#### 2. Декораторы/функции проверки
```python
def require_owner_or_admin(org_context: OrgContext) -> None:
    if not org_context.is_owner_or_admin():
        raise PermissionDenied(
            "Only owners and admins can perform this action"
        )

def check_resource_ownership(org_context: OrgContext,
                            resource_owner_id: int) -> None:
    if org_context.is_manager_or_above():
        return  # Доступ разрешен

    if org_context.user_id != resource_owner_id:
        raise PermissionDenied(
            "You can only access your own resources"
        )
```

#### 3. Автоматическая фильтрация
```python
# В сервисах и репозиториях
async def list_deals(
    self,
    organization_id: int,
    auth_context: AuthContext,
    ...
) -> list[Deal]:
    # Members видят только свои сделки
    owner_id = (
        auth_context.user_id
        if auth_context.is_member()
        else None
    )

    return await self.repo.list_with_filters(
        organization_id=organization_id,
        owner_id=owner_id,
        ...
    )
```

---

## Взаимодействие между сущностями

### Диаграмма зависимостей

```
┌───────────────────────────────────────────────────────┐
│                   ИЗОЛЯЦИЯ ДАННЫХ                      │
│              (по Organization ID)                      │
└───────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
    Contact          Deal           Activity
        │               │               │
        │               ├──────────────►│
        │               │               │
        └──────────────►│               │
                        │               │
                        ▼               │
                     Task ──────────────┘
```

### Сценарии взаимодействия

#### Сценарий 1: Создание новой продажи

```
Шаг 1: СОЗДАНИЕ КОНТАКТА
─────────────────────────────────────
POST /api/v1/contacts
{
  "name": "Иван Иванов",
  "email": "ivan@example.com",
  "phone": "+7 999 123-45-67"
}

Результат:
→ Contact #101 (owner_id = current_user.id)
→ organization_id = current_org.id

Шаг 2: СОЗДАНИЕ СДЕЛКИ
─────────────────────────────────────
POST /api/v1/deals
{
  "title": "Поставка оборудования",
  "contact_id": 101,
  "amount": 500000,
  "currency": "RUB"
}

Валидация:
→ Проверка: contact #101 принадлежит той же организации ✓
→ Статус по умолчанию: NEW
→ Этап по умолчанию: QUALIFICATION

Результат:
→ Deal #201 (owner_id = current_user.id)
→ Activity #1 (type=SYSTEM, "deal created")

Шаг 3: ПЛАНИРОВАНИЕ РАБОТЫ
─────────────────────────────────────
POST /api/v1/deals/201/tasks
{
  "title": "Подготовить коммерческое предложение",
  "due_date": "2024-01-15T10:00:00Z"
}

Результат:
→ Task #301 (deal_id = 201)
→ Activity #2 (type=TASK_CREATED)

Шаг 4: РАБОТА СО СДЕЛКОЙ
─────────────────────────────────────
POST /api/v1/deals/201/activities
{
  "type": "comment",
  "payload": {
    "text": "Провел встречу с ЛПР, готовы к переговорам"
  }
}

Результат:
→ Activity #3 (type=COMMENT, author_id=current_user.id)

Шаг 5: ПРОДВИЖЕНИЕ ПО ВОРОНКЕ
─────────────────────────────────────
PATCH /api/v1/deals/201
{
  "stage": "proposal"
}

Результат:
→ Deal.stage = PROPOSAL
→ Deal.updated_at = NOW()
→ Activity #4 (type=STAGE_CHANGED)

...продолжение работы...

Шаг N: ЗАКРЫТИЕ СДЕЛКИ
─────────────────────────────────────
PATCH /api/v1/deals/201
{
  "status": "won"
}

Валидация:
→ Проверка: amount > 0 ✓ (500000)

Результат:
→ Deal.status = WON
→ Deal.stage = CLOSED
→ Activity #N (type=STATUS_CHANGED)
→ Обновление аналитики (кэш инвалидируется)
```

#### Сценарий 2: Попытка удаления контакта

```
Попытка: DELETE /api/v1/contacts/101

Шаг 1: Загрузка контакта
→ Contact #101 найден
→ Проверка прав: current_user может удалить ✓

Шаг 2: Проверка бизнес-правил
→ Запрос: есть ли связанные сделки?
  SELECT COUNT(*) FROM deals WHERE contact_id = 101
  Результат: 1 (Deal #201)

→ REJECT: BusinessRuleViolation
  "Cannot delete contact with existing deals.
   Remove or reassign deals first."

HTTP 409 Conflict
```

#### Сценарий 3: Member пытается откатить этап сделки

```
Текущее состояние:
→ Deal #201: stage = NEGOTIATION (order=3)
→ User: role = MEMBER

Попытка: PATCH /api/v1/deals/201
{
  "stage": "proposal"  // order=2, откат назад
}

Шаг 1: Загрузка сделки
→ Deal #201 найден
→ Проверка прав: member владеет сделкой ✓

Шаг 2: Валидация изменения этапа
→ old_stage = NEGOTIATION (order=3)
→ new_stage = PROPOSAL (order=2)
→ Определение: откат назад (2 < 3)

Шаг 3: Проверка прав на откат
→ auth_context.is_owner_or_admin() = False
→ REJECT: PermissionDenied
  "Only admins and owners can rollback deal stages"

HTTP 403 Forbidden
```

---

## Аналитика и метрики

### 1. Deals Summary (Сводка по сделкам)

**Назначение**: Агрегированная статистика по сделкам организации.

#### Метрики
```python
{
  "by_status": [
    {
      "status": "new",
      "count": 15,
      "total_amount": 1250000.00
    },
    {
      "status": "in_progress",
      "count": 23,
      "total_amount": 3400000.00
    },
    {
      "status": "won",
      "count": 12,
      "total_amount": 2100000.00
    },
    {
      "status": "lost",
      "count": 8,
      "total_amount": 950000.00
    }
  ],
  "avg_won_amount": 175000.00,  # Средний чек выигранных сделок
  "new_deals_last_n_days": 7,   # Новых сделок за последние N дней
  "days": 30                     # Период для новых сделок
}
```

#### Оптимизация
```sql
-- Единственный оптимизированный запрос с условной агрегацией
SELECT
    status,
    COUNT(id) as count,
    COALESCE(SUM(amount), 0) as total_amount,
    AVG(CASE WHEN status = 'won' THEN amount END) as avg_won_amount,
    SUM(CASE WHEN created_at >= :cutoff_date THEN 1 ELSE 0 END)
        as new_deals_count
FROM deals
WHERE organization_id = :org_id
GROUP BY status;
```

#### Кэширование
- **Ключ**: `deals_summary:{organization_id}:{days}`
- **TTL**: 300 секунд (5 минут)
- **Инвалидация**: при создании/обновлении сделки

### 2. Deals Funnel (Воронка продаж)

**Назначение**: Визуализация движения сделок по этапам и конверсий.

#### Метрики
```python
{
  "stages": [
    {
      "stage": "qualification",
      "stage_order": 1,
      "total_count": 50,
      "status_breakdown": {
        "new": 30,
        "in_progress": 15,
        "won": 3,
        "lost": 2
      },
      "conversion_from_previous": null  # Первый этап
    },
    {
      "stage": "proposal",
      "stage_order": 2,
      "total_count": 35,
      "status_breakdown": {
        "in_progress": 25,
        "won": 6,
        "lost": 4
      },
      "conversion_from_previous": 70.0  # 35/50 * 100
    },
    {
      "stage": "negotiation",
      "stage_order": 3,
      "total_count": 20,
      "status_breakdown": {
        "in_progress": 15,
        "won": 3,
        "lost": 2
      },
      "conversion_from_previous": 57.14  # 20/35 * 100
    },
    {
      "stage": "closed",
      "stage_order": 4,
      "total_count": 15,
      "status_breakdown": {
        "won": 12,
        "lost": 3
      },
      "conversion_from_previous": 75.0  # 15/20 * 100
    }
  ]
}
```

#### Расчет конверсии
```python
# Конверсия показывает, какой % сделок дошел до текущего этапа
conversion = (current_stage_count / previous_stage_count) * 100

# Пример:
# QUALIFICATION: 50 сделок → базовый этап
# PROPOSAL: 35 сделок → 70% конверсия (35/50)
# NEGOTIATION: 20 сделок → 57% конверсия (20/35)
# CLOSED: 15 сделок → 75% конверсия (15/20)

# Итоговая конверсия: 15/50 = 30% (от начала до закрытия)
```

#### Оптимизация
```sql
-- Группировка по этапу и статусу
SELECT
    stage,
    status,
    COUNT(id) as count
FROM deals
WHERE organization_id = :org_id
GROUP BY stage, status;
```

#### Кэширование
- **Ключ**: `deals_funnel:{organization_id}`
- **TTL**: 300 секунд (5 минут)
- **Инвалидация**: при изменении stage/status сделки

### 3. Производительность аналитики

#### Индексы для оптимизации
```sql
-- Основной индекс для фильтрации
CREATE INDEX idx_deals_org_status
ON deals(organization_id, status);

-- Индекс для временных фильтров
CREATE INDEX idx_deals_org_created
ON deals(organization_id, created_at DESC);

-- Составной индекс для воронки
CREATE INDEX idx_deals_org_stage_status
ON deals(organization_id, stage, status);
```

#### Стратегия кэширования
```python
# Паттерн использования кэша
async def get_deals_summary(org_id: int, days: int = 30):
    cache_key = f"deals_summary:{org_id}:{days}"

    # Попытка получить из кэша
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # Вычисление (тяжелый запрос)
    result = await compute_summary(org_id, days)

    # Сохранение в кэш
    await redis.setex(
        cache_key,
        300,  # TTL 5 минут
        json.dumps(result)
    )

    return result
```

#### Инвалидация кэша
```python
# При изменении сделки - инвалидировать все связанные кэши
async def invalidate_analytics_cache(organization_id: int):
    patterns = [
        f"deals_summary:{organization_id}:*",
        f"deals_funnel:{organization_id}"
    ]

    for pattern in patterns:
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
```

---

## Автоматизация процессов

### 1. Автоматическое логирование активностей

Система автоматически создает Activity записи для важных событий:

#### Триггеры автоматического логирования

##### a) Изменение статуса сделки
```python
# В DealService.update_deal()
if "status" in update_data:
    await activity_repo.create(
        deal_id=deal.id,
        author_id=auth_context.user_id,
        type=ActivityType.STATUS_CHANGED,
        payload={
            "old_status": deal.status.value,
            "new_status": update_data["status"].value
        }
    )
```

**Payload пример**:
```json
{
  "old_status": "in_progress",
  "new_status": "won"
}
```

##### b) Изменение этапа воронки
```python
# В DealService.update_deal()
if "stage" in update_data:
    await activity_repo.create(
        deal_id=deal.id,
        author_id=auth_context.user_id,
        type=ActivityType.STAGE_CHANGED,
        payload={
            "old_stage": deal.stage.value,
            "new_stage": update_data["stage"].value
        }
    )
```

**Payload пример**:
```json
{
  "old_stage": "qualification",
  "new_stage": "proposal"
}
```

##### c) Создание задачи (опционально)
Можно расширить для автологирования создания задач:
```python
# В TaskService.create_task()
# Опционально: автоматически логировать создание задачи
await activity_repo.create(
    deal_id=task.deal_id,
    author_id=None,  # Системное событие
    type=ActivityType.TASK_CREATED,
    payload={
        "task_id": task.id,
        "task_title": task.title,
        "due_date": task.due_date.isoformat() if task.due_date else None
    }
)
```

### 2. Каскадное удаление

#### Определение в моделях
```python
# Organization → Contacts
contacts: Mapped[list["Contact"]] = relationship(
    back_populates="organization",
    cascade="all, delete-orphan"
)

# Organization → Deals
deals: Mapped[list["Deal"]] = relationship(
    back_populates="organization",
    cascade="all, delete-orphan"
)

# Deal → Tasks
tasks: Mapped[list["Task"]] = relationship(
    back_populates="deal",
    cascade="all, delete-orphan"
)

# Deal → Activities
activities: Mapped[list["Activity"]] = relationship(
    back_populates="deal",
    cascade="all, delete-orphan"
)
```

#### Эффект каскадного удаления
```
DELETE Organization #1
    ↓
    ├─→ DELETE all OrganizationMember (org_id=1)
    ├─→ DELETE all Contact (organization_id=1)
    ├─→ DELETE all Deal (organization_id=1)
    │       ↓
    │       ├─→ DELETE all Task (deal_id in ...)
    │       └─→ DELETE all Activity (deal_id in ...)
    └─→ Cascade complete
```

### 3. Автоматические обновления временных меток

#### updated_at в Deal
```python
# Модель Deal
updated_at: Mapped[datetime] = mapped_column(
    server_default=func.now(),
    onupdate=func.now()  # Автообновление
)
```

**Поведение**:
- При любом `UPDATE deals SET ...` → `updated_at` обновляется автоматически
- Не требует явного указания в коде

### 4. Значения по умолчанию

#### В моделях
```python
# User
is_active: Mapped[bool] = mapped_column(default=True)

# Deal
status: Mapped[DealStatus] = mapped_column(default=DealStatus.NEW)
stage: Mapped[DealStage] = mapped_column(default=DealStage.QUALIFICATION)
currency: Mapped[str] = mapped_column(default="USD")
amount: Mapped[Decimal] = mapped_column(
    Numeric(12, 2),
    default=Decimal("0.00")
)

# Task
is_done: Mapped[bool] = mapped_column(default=False)
```

#### В создании организации
```python
# OrganizationService.create_organization()
async def create_organization(
    self,
    data: OrganizationCreate,
    owner_id: int
) -> Organization:
    # Автоматически создает организацию И добавляет создателя как OWNER
    return await self.repo.create_organization(data.name, owner_id)
```

**В репозитории**:
```python
async def create_organization(
    self,
    name: str,
    owner_id: int
) -> Organization:
    org = Organization(name=name)
    self.db.add(org)
    await self.db.flush()  # Получить org.id

    # Автоматическое создание Owner membership
    member = OrganizationMember(
        organization_id=org.id,
        user_id=owner_id,
        role=MemberRole.OWNER  # Создатель всегда OWNER
    )
    self.db.add(member)
    await self.db.commit()

    return org
```

### 5. Автоматическая фильтрация по правам

#### В сервисах
```python
# ContactService.list_contacts()
async def list_contacts(
    self,
    organization_id: int,
    owner_id: int | None = None,  # Явно передается
    ...
) -> list[Contact]:
    # Members автоматически видят только свои контакты
    # Manager+ видят все
    contacts = await self.repo.list_with_filters(
        organization_id=organization_id,
        owner_id=owner_id,  # None для manager+
        ...
    )
    return contacts
```

#### В API endpoints
```python
@router.get("/contacts", response_model=list[ContactResponse])
async def list_contacts(
    org_context: OrgContext = Depends(require_organization),
    ...
):
    # Автоматическое определение owner_id на основе роли
    owner_id = (
        org_context.user_id
        if org_context.is_member()
        else None
    )

    contacts = await contact_service.list_contacts(
        organization_id=org_context.organization_id,
        owner_id=owner_id,
        ...
    )
    return contacts
```

---

## Расширенные сценарии использования

### Сценарий 4: Работа с командой (Multi-user)

```
Этап 1: OWNER создает организацию
─────────────────────────────────────
User: Alice (OWNER)
POST /api/v1/organizations
→ Organization #1 "Sales Corp"
→ OrganizationMember(user=Alice, role=OWNER)

Этап 2: OWNER приглашает команду
─────────────────────────────────────
User: Alice
POST /api/v1/organizations/1/members
{
  "user_id": 2,  # Bob
  "role": "manager"
}
→ OrganizationMember(user=Bob, role=MANAGER)

POST /api/v1/organizations/1/members
{
  "user_id": 3,  # Charlie
  "role": "member"
}
→ OrganizationMember(user=Charlie, role=MEMBER)

Этап 3: MANAGER создает сделку
─────────────────────────────────────
User: Bob (MANAGER)
POST /api/v1/deals
{
  "title": "Enterprise contract",
  "amount": 1000000
}
→ Deal #100 (owner_id=2, Bob)

Этап 4: MEMBER видит только свои сделки
─────────────────────────────────────
User: Charlie (MEMBER)
GET /api/v1/deals
→ Автофильтр: owner_id=3
→ Результат: [] (у Charlie нет своих сделок)

User: Bob (MANAGER)
GET /api/v1/deals
→ Автофильтр: owner_id=None (видит все)
→ Результат: [Deal #100, ...]

Этап 5: MEMBER пытается редактировать чужую сделку
─────────────────────────────────────
User: Charlie (MEMBER)
PATCH /api/v1/deals/100
{
  "stage": "proposal"
}
→ Проверка прав: check_resource_ownership()
→ Deal #100 принадлежит Bob (user_id=2)
→ Charlie (user_id=3) не владелец
→ Charlie is MEMBER → нет доступа ко всем ресурсам
→ REJECT: PermissionDenied

Этап 6: MANAGER редактирует чужую сделку
─────────────────────────────────────
User: Bob (MANAGER)
→ Manager может редактировать все сделки организации ✓

Этап 7: OWNER меняет роль
─────────────────────────────────────
User: Alice (OWNER)
PATCH /api/v1/organizations/1/members/3
{
  "role": "manager"
}
→ Charlie повышен до MANAGER
→ Теперь Charlie видит все сделки
```

### Сценарий 5: Аналитика для разных ролей

```
Организация: Sales Corp (id=1)
Сделки:
  - Deal #1: owner=Alice, amount=100k, status=won
  - Deal #2: owner=Bob, amount=200k, status=in_progress
  - Deal #3: owner=Charlie, amount=50k, status=new

Запрос аналитики от OWNER/ADMIN/MANAGER:
─────────────────────────────────────
User: Alice (OWNER)
GET /api/v1/analytics/deals/summary

Результат (все сделки организации):
{
  "by_status": [
    {"status": "won", "count": 1, "total_amount": 100000},
    {"status": "in_progress", "count": 1, "total_amount": 200000},
    {"status": "new", "count": 1, "total_amount": 50000}
  ],
  "avg_won_amount": 100000,
  "new_deals_last_n_days": 3
}

Запрос аналитики от MEMBER:
─────────────────────────────────────
User: Charlie (MEMBER)
GET /api/v1/analytics/deals/summary

Результат (только сделки Charlie):
{
  "by_status": [
    {"status": "new", "count": 1, "total_amount": 50000}
  ],
  "avg_won_amount": null,  # У Charlie нет выигранных сделок
  "new_deals_last_n_days": 1
}
```

---

## Ограничения и известные компромиссы

### 1. Мягкое удаление не реализовано

**Текущее поведение**: Hard delete из базы данных

**Последствия**:
- Невозможно восстановить удаленные данные
- История активностей теряется при удалении сделки

**Возможное улучшение**:
```python
# Добавить поля в модели
deleted_at: Mapped[datetime | None] = mapped_column(default=None)
is_deleted: Mapped[bool] = mapped_column(default=False)

# Изменить запросы
query = select(Deal).where(
    Deal.organization_id == org_id,
    Deal.is_deleted == False  # Фильтр везде
)
```

### 2. Activity иммутабельность не полная

**Текущее поведение**: Нет `UPDATE` эндпоинтов, но физически можно изменить в БД

**Возможное улучшение**:
```sql
-- PostgreSQL trigger для защиты
CREATE TRIGGER prevent_activity_update
BEFORE UPDATE ON activities
FOR EACH ROW
EXECUTE FUNCTION raise_exception('Activities are immutable');
```

### 3. Нет лимитов на размер payload в Activity

**Риск**: Большие JSON могут замедлить запросы

**Возможное улучшение**:
```python
# Валидация в схеме
class ActivityCreate(BaseModel):
    payload: dict

    @validator('payload')
    def validate_payload_size(cls, v):
        json_size = len(json.dumps(v))
        if json_size > 10_000:  # 10KB limit
            raise ValueError("Payload too large")
        return v
```

### 4. Конверсия в воронке упрощенная

**Текущая логика**: Последовательная конверсия (stage N+1 / stage N)

**Ограничение**: Не учитывает:
- Временные рамки (сделки могут быть созданы в разное время)
- Реальное движение (сделка может перескочить этапы)

**Правильная метрика требует**:
```sql
-- Cohort analysis
-- Отслеживать, сколько из сделок, созданных в определенный период,
-- дошли до каждого этапа
```

### 5. Один контакт на сделку

**Текущее**: `contact_id` - single FK

**Реальность**: В сделке могут участвовать несколько лиц принимающих решения

**Возможное улучшение**:
```python
# Промежуточная таблица many-to-many
class DealContact(Base):
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id"))
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"))
    role: Mapped[str]  # "decision_maker", "influencer", etc.
```

### 6. Нет версионирования сделок

**Текущее**: `updated_at` метка, но нет истории изменений

**Проблема**: Невозможно посмотреть, каким был amount неделю назад

**Возможное улучшение**:
- Event sourcing паттерн
- Версионирование через отдельную таблицу `deal_history`

---

## Рекомендации по развитию

### Краткосрочные улучшения (1-2 месяца)

1. **Мягкое удаление**
   - Добавить `deleted_at` / `is_deleted` поля
   - Обновить все запросы с фильтром `is_deleted=False`
   - API endpoint для восстановления

2. **Улучшенная аналитика**
   - Конверсия с учетом когорт
   - Средняя длительность на каждом этапе
   - Win rate по владельцам

3. **Bulk операции**
   - Массовое назначение сделок
   - Массовое изменение этапа
   - Импорт контактов из CSV

4. **Уведомления**
   - Email при назначении сделки
   - Напоминания о просроченных задачах
   - Webhook для интеграций

### Среднесрочные улучшения (3-6 месяцев)

1. **Кастомные поля**
   - Гибкая схема для дополнительных полей
   - Разные типы: текст, число, дата, выбор

2. **Продвинутая воронка**
   - Кастомные этапы (не фиксированные 4)
   - Вероятность закрытия на каждом этапе
   - Прогнозирование выручки

3. **Автоматизация**
   - Правила: "Если сделка в PROPOSAL > 14 дней → уведомить менеджера"
   - Автоприсвоение задач
   - Шаблоны сделок

4. **Расширенные права**
   - Детальные permissions (например, "can_delete_won_deals")
   - Ограничение по суммам
   - Approval workflow для больших сделок

### Долгосрочные улучшения (6+ месяцев)

1. **ML/AI интеграция**
   - Предсказание вероятности закрытия
   - Рекомендация следующего действия
   - Автоматическое распределение лидов

2. **Интеграции**
   - Email (Gmail, Outlook)
   - Календари
   - Телефония
   - Платежные системы

3. **Мобильное приложение**
   - iOS/Android нативные приложения
   - Офлайн режим
   - Push уведомления

4. **Масштабирование**
   - Sharding по organization_id
   - Read replicas
   - Событийная архитектура (event sourcing)

---

## Заключение

Mini CRM представляет собой хорошо структурированную систему с четкой бизнес-логикой и продуманной моделью прав доступа. Ключевые сильные стороны:

### ✅ Сильные стороны

1. **Мультитенантность**: Четкая изоляция данных по организациям
2. **Роли и права**: Гибкая система с 4 уровнями доступа
3. **Аудит**: Иммутабельный лог всех важных событий (Activity)
4. **Бизнес-правила**: Явная валидация на уровне сервисов
5. **Производительность**: Оптимизированные запросы и кэширование
6. **Архитектура**: Чистое разделение слоев (API → Service → Repository → Model)

### 🎯 Ключевые бизнес-процессы

1. **Продажи**: Полный цикл от лида до закрытия с контролем на каждом этапе
2. **Коллаборация**: Команды работают вместе с разными уровнями доступа
3. **Аналитика**: Real-time метрики для принятия решений
4. **Автоматизация**: Автологирование событий снижает ручную работу

Система готова к продакшену и может эффективно обслуживать малый и средний бизнес с командами до 50-100 человек на организацию.
