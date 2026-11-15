# DopaDrop — полное техническое задание для Codex

> **Статус:** утверждённая спецификация MVP.  
> **Язык интерфейса:** русский.  
> **Тип:** юмористический FakeShop для прокрастинаторов, без реальных покупок и платежей.  
> **Архитектура:** модульный монолит на Python/Flask.  
> **Главный принцип:** один развёртываемый Flask-проект, одна SQLite-база, один статический JSON-каталог, никаких фоновых работников и микросервисов.

## 0. Инструкция исполнителю (Codex): как использовать документ

Ты — инженер, реализующий **полностью запускаемый проект**, а не демонстрационный набор фрагментов. Считай все требования ниже обязательными, кроме явно помеченных «можно позже» или «не входит в MVP». Не упрощай самостоятельно ключевые сценарии, тесты или безопасность. Если мелкий аспект не определён, выбирай минимальное решение, соответствующее архитектуре, и фиксируй его в `README.md`.

### Определение готовности

Проект готов, только когда одновременно выполняются условия:

1. `python -m flask --app run.py run --debug` запускает сайт после настройки окружения и создания БД.
2. Пользователь видит каталог **ровно из 15** фиктивных товаров, может искать/фильтровать их, складывать в корзину, перезагружать страницу без потери корзины.
3. Нельзя создать заказ с несуществующими `product_id`, некорректным количеством, пустой корзиной или суммами, подменёнными клиентом.
4. После оформления заказ фиксируется в SQLite, показывается шуточный чек, ссылка и QR-код, ведущие на страницу отслеживания.
5. Отслеживание **меняется автоматически по времени** без Celery, cron, APScheduler и без ручного обновления БД. Обновление страницы и открытие той же ссылки на другом устройстве показывают один и тот же статус в зависимости от сохранённого времени создания заказа.
6. Данные другого заказа нельзя получить угадыванием последовательного ID; публичный доступ разрешён только по случайному криптостойкому токену.
7. Все основные маршруты, модели, сервисы и проверки покрыты тестами; `pytest` проходит.
8. Есть корректный `README.md`: установка, запуск, тесты, устройство проекта, демонстрация автоматического трекинга, особенности фиктивного магазина.

### Порядок приоритетов

**P0 (обязательно):** старт приложения, каталог, корзина, оформление, сохранение, автоматический трекинг, чек, QR, обработка ошибок, тесты.  
**P1 (обязательно в конце):** адаптивный дизайн, доступность, понятные пустые состояния, качественный юмористический контент и README.  
**Не входит в MVP:** авторизация, личный кабинет, админка, платежи, доставка, email/SMS, реальные остатки, внешние API, WebSocket, Celery, Redis, Docker, React/Vue, сложная DI-система.

---

## 1. Идея, продукт и UX

### 1.1. Концепция

DopaDrop — сатирический интернет-магазин для прокрастинаторов. Посетитель выбирает абсурдные товары, например «невидимые носки», складывает их в корзину, откладывает оформление, а затем «оформляет» полностью ненастоящую покупку. Итог — шутливый чек, QR-код и трекер заказа с мемными стадиями вроде «заказ застрял в мультивселенной».

**Никаких реальных расходов или обязательств пользователя.** На всех точках оформления должна быть ясная пометка: «Это шуточный магазин. Деньги не списываются, товары не доставляются». Валюта и цены — игровые, например `₽` для сатирического оформления; надпись о фиктивности обязательна возле кнопки подтверждения. Не собирать банковские данные, реальный адрес доставки, паспорт, телефон или email.

### 1.2. Аудитория и характер

- Посетители, которым близка тема прокрастинации, интернет-мемов и шуточных маркетплейсов.
- Тон текста — ироничный, доброжелательный, без унижения пользователей.
- Интерфейс должен действительно работать как маленький магазин; юмор встроен в описания, состояние корзины и трекинг, а не заменяет функциональность.

### 1.3. Главный пользовательский сценарий

1. Открыть главную страницу и увидеть приветствие и 15 товаров.
2. Выбрать категорию или поискать по названию/описанию.
3. Добавить несколько товаров в корзину; изменить количество/удалить.
4. Обновить страницу: корзина восстановится из `localStorage`.
5. Перейти к оформлению, увидеть итог, принять условие о фиктивности.
6. Отправить заказ без платежа и персональных данных.
7. Получить страницу подтверждения с номером, позициями, чековой суммой, QR и ссылкой «Отследить приключение».
8. Перейти по ссылке или QR, увидеть шкалу статусов; статус сам меняется с течением времени.
9. Открыть ссылку позже, в инкогнито или с другого устройства — получить тот же заказ и актуальное состояние.

### 1.4. UX-рамки

- Mobile-first, ширина от 320 px, без горизонтальной прокрутки.
- Визуальный стиль: игровой маркетплейс, аккуратные карточки, спокойная читабельная типографика, заметные CTA; реализовать собственными CSS без тяжёлого UI-фреймворка.
- Использовать небольшие локальные иллюстрации/эмодзи/SVG, не скачивать случайные изображения с авторскими правами. Должен работать офлайн после локальной установки без CDN.
- Кнопки и ссылки управляются клавиатурой; изображения имеют `alt`; сообщения об ошибках понятны.
- Семантические HTML-теги и явный фокус (`:focus-visible`).
- Наличие JS нужно для корзины и таймлайна; серверные HTML-страницы по-прежнему должны отображать основные данные заказа.

---

## 2. Неизменяемые архитектурные решения

### 2.1. Стек

- **Python:** поддерживаемая стабильная версия Python 3.12+; указать протестированную версию в README.
- **Backend:** Flask 3.x, серверные Jinja2-шаблоны, Flask Blueprints.
- **ORM и SQL:** Flask-SQLAlchemy 3.x (SQLAlchemy 2.x) и SQLite; запросы только через ORM/repository, без raw SQL в routes и сервисах.
- **Конфигурация:** стандартный `os.environ`; `python-dotenv` для локального `.env` при необходимости.
- **QR:** `qrcode[pil]` (SVG/PNG в памяти; в MVP PNG через Pillow).
- **Тесты:** `pytest`, Flask test client, временная SQLite-база.
- **Frontend:** HTML5 + CSS + современный vanilla JS (без bundler, npm, React).
- **Данные каталога:** `app/data/catalog.json`; каталог read-only во время работы.
- **Локальная разработка:** виртуальное окружение `venv` и `pip install -r requirements.txt`.

Версии зависимостей выбирать **взаимно совместимые и актуальные на момент реализации**. Записать зафиксированные версии в `requirements.txt`; не использовать несуществующие версии.

### 2.2. Почему именно монолит

- Одно Flask-приложение отдаёт страницы, API, CSS, JS, QR и загружает каталог.
- Все business services — **обычные Python-классы в одном процессе**, не сетевые службы.
- Нет фронтенд-приложения с отдельным сервером. Нет отдельного каталожного сервиса.
- SQLite — единственное постоянное хранилище заказов. `catalog.json` — ресурс с исходными товарами.
- Сервисы не должны знать о `request`, `session`, `render_template` или `jsonify`; это ответственность HTTP-слоя.

### 2.3. Слои и направление зависимостей

```text
Browser: Jinja HTML + CSS + JS + localStorage
             |
             | HTTP: HTML routes + JSON API
             v
Flask app factory -> Blueprints / route handlers
             |
             v
Business services: Catalog, Cart, Order, Tracking, Receipt, QR
             |
             v
OrderRepository -> SQLAlchemy models -> SQLite(shop.db)

CatalogService ----------------------------> app/data/catalog.json
```

Правила:

1. Routes получают и валидируют HTTP-вход, вызывают сервисы, возвращают response.
2. `OrderService` оркестрирует оформление, но не строит HTML.
3. `CartService` проверяет и нормализует строки корзины, используя `CatalogService`.
4. `TrackingService` вычисляет стадию из **UTC `created_at`**, текущего UTC-времени и неизменяемого сценария. Не обновляет БД на каждом запросе.
5. `ReceiptService` строит структурированное представление на основе **снимка** заказа; не берёт текущие цены из JSON.
6. `QRCodeService` принимает публичный URL, возвращает PNG-байты. Это может быть простой класс ради тестируемости; не создавать универсальный QR-фреймворк.
7. `OrderRepository` — единственная абстракция доступа к заказам. `CatalogService` читает JSON напрямую, без repository.
8. Никаких циклических импортов: использовать `extensions.py` для экземпляра `db`, `create_app` для сборки зависимостей.

---

## 3. Полное дерево каталогов

Реализовать минимум следующую структуру (мелкие вспомогательные файлы разрешены, но не плодить слои):

```text
dopadrop/
├── README.md
├── CODEX_SPEC_DOPADROP.md
├── .gitignore
├── .env.example
├── requirements.txt
├── run.py
├── instance/                      # автоматически создаётся; shop.db не коммитить
├── app/
│   ├── __init__.py                # create_app(config_overrides=None)
│   ├── config.py                  # Config, TestingConfig (по необходимости)
│   ├── extensions.py              # db = SQLAlchemy()
│   ├── errors.py                  # доменные ошибки и HTTP-маппинг
│   ├── models/
│   │   ├── __init__.py
│   │   ├── order.py               # Order, OrderItem
│   │   └── dto.py                 # dataclass: Product, CartLine, TrackingStage ...
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── order_repository.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── catalog_service.py
│   │   ├── cart_service.py
│   │   ├── order_service.py
│   │   ├── tracking_service.py
│   │   ├── receipt_service.py
│   │   └── qr_code_service.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── pages.py
│   │   ├── orders_api.py
│   │   └── qr.py
│   ├── data/
│   │   ├── catalog.json
│   │   └── tracking_scenarios.json
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── cart.html
│   │   ├── checkout.html
│   │   ├── order_success.html
│   │   ├── tracking.html
│   │   ├── 404.html
│   │   ├── 500.html
│   │   └── components/
│   │       ├── product_card.html
│   │       ├── header.html
│   │       └── footer.html
│   └── static/
│       ├── css/style.css
│       ├── js/api.js
│       ├── js/cart.js
│       ├── js/catalog.js
│       ├── js/checkout.js
│       ├── js/tracking.js
│       └── img/                   # необязательные локальные SVG
└── tests/
    ├── conftest.py
    ├── test_catalog.py
    ├── test_cart.py
    ├── test_order_service.py
    ├── test_orders_api.py
    ├── test_tracking.py
    ├── test_receipt_qr.py
    └── test_pages.py
```

**Важно:** `instance/shop.db` и `.env` в `.gitignore`. Не создавать миграции без необходимости: для MVP допустимо `db.create_all()` в явной CLI-команде `flask init-db`, но не пересоздавать БД на каждом запросе. Если Codex добавит Alembic/Flask-Migrate, это допустимо только при сохранении простого setup и README.

---

## 4. Данные каталога: строгий контракт

### 4.1. `catalog.json`

Формат — корневой объект:

```json
{
  "schema_version": 1,
  "categories": [
    {"id": "procrastination", "name": "Прокрастинация"},
    {"id": "invisible", "name": "Невидимые вещи"},
    {"id": "motivation", "name": "Мотивация"},
    {"id": "chaos", "name": "Хаос и мультивселенная"},
    {"id": "office", "name": "Рабочие ритуалы"}
  ],
  "products": [
    {
      "id": "invisible-socks",
      "name": "Невидимые носки",
      "category_id": "invisible",
      "price_kopeks": 49900,
      "description": "На случай, когда выходить из дома совершенно незачем.",
      "meme": "Если их не видно, значит, они уже в стирке.",
      "emoji": "🧦",
      "featured": true
    }
  ]
}
```

**Нормы:**

- В финальном каталоге **ровно 15 товаров**, ровно **5 категорий**, по **3 товара** в каждой (выбор количества категорий — проектное решение для MVP).
- Все `id` уникальны, ASCII kebab-case; `category_id` должен существовать.
- `price_kopeks` — целое число от 0 до 10_000_000 (условные копейки), не float. Цены отображаются в рублях/двух знаках после запятой, но не отправляются браузером как источник истины.
- `name`, `description`, `meme`, `emoji` заполнены; текст на русском, шуточный и без оскорблений.
- `featured` — boolean; на главной рекомендованные карточки можно визуально выделять.
- Элемент каталога **не является** записью БД: нет CRUD-интерфейса для товаров.
- Проверять схему JSON при старте приложения; если каталог повреждён, прерывать запуск с понятным исключением (fail fast).

### 4.2. Зафиксированный набор 15 товаров

Codex должен создать контент примерно в таком ключе с **указанными ID** и категориями; названия и юмористические описания допускается стилистически улучшать без изменения назначения товара. Цены в условных копейках; можно использовать указанные значения как финальные:

| ID | Название | Категория | Цена, ₽ |
|---|---|---|---:|
| `invisible-socks` | Невидимые носки | invisible | 499 |
| `empty-box` | Коробка с обещаниями | invisible | 299 |
| `transparent-umbrella` | Зонт от несуществующего дождя | invisible | 799 |
| `tomorrow-planner` | Планер «Начну завтра» | procrastination | 899 |
| `five-more-minutes` | Сертификат «Ещё пять минут» | procrastination | 199 |
| `deadline-extender` | Продлитель дедлайна | procrastination | 1499 |
| `motivation-battery` | Батарейка мотивации 1% | motivation | 599 |
| `success-sticker` | Наклейка «Почти сделал» | motivation | 149 |
| `inspiration-air` | Банка вдохновляющего воздуха | motivation | 699 |
| `multiverse-map` | Карта потерянных вселенных | chaos | 1099 |
| `quantum-excuse` | Квантовая отговорка | chaos | 1299 |
| `chaos-organizer` | Органайзер организованного хаоса | chaos | 999 |
| `meeting-escape` | Пропуск с совещания | office | 399 |
| `coffee-placeholder` | Заглушка для кофе | office | 249 |
| `focus-switch` | Переключатель концентрации (муляж) | office | 1199 |

### 4.3. `Product` DTO

Не ORM-модель. Предлагаемая реализация — неизменяемый `@dataclass(frozen=True)`:

```python
@dataclass(frozen=True)
class Product:
    id: str
    name: str
    category_id: str
    price_kopeks: int
    description: str
    meme: str
    emoji: str
    featured: bool
```

Категорию можно представить отдельным `Category` dataclass `{id, name}`. Не создавать отдельный `ProductRepository`: каталог статичен.

### 4.4. `CatalogService`

**Зависимости:** путь к JSON-файлу (`pathlib.Path`), стандартный `json`. Не зависит от SQLite, Flask и других сервисов.

Интерфейс:

```python
class CatalogService:
    def __init__(self, catalog_path: Path): ...
    def list_products(self, *, category_id: str | None = None,
                      query: str | None = None) -> list[Product]: ...
    def get_product(self, product_id: str) -> Product | None: ...
    def list_categories(self) -> list[Category]: ...
```

Поведение:

- Загрузка/валидация каталога **один раз при создании сервиса**, хранение в памяти; на каждом запросе JSON заново не читать.
- Поиск без учёта регистра (`casefold`) по `name` и `description`; обрезать пробелы; если запрос пустой — без фильтра.
- Неизвестная категория: пустой список на странице фильтра, без 500.
- Сортировка исходным порядком файла; не менять порядок неожиданно.
- `get_product` выдаёт `None` для неизвестного ID; при оформлении заказов `CartService` превращает это в `ValidationError`.
- Не мутировать исходные DTO.

---

## 5. SQLite: сущности, поля, индексы, ограничения

### 5.1. `Order` (`orders`)

| Поле | Тип | Требования |
|---|---|---|
| `id` | INTEGER PK | внутренний автоинкремент, **не выдавать как идентификатор доступа** |
| `public_token` | VARCHAR(64) | NOT NULL, UNIQUE, INDEX; `secrets.token_urlsafe(24)` или эквивалент |
| `order_number` | VARCHAR(32) | NOT NULL, UNIQUE; человекочитаемый `DD-YYYYMMDD-XXXXXX` с криптостойким суффиксом |
| `created_at` | UTC datetime | NOT NULL; timezone-aware на уровне Python; для SQLite документировать конвертацию UTC |
| `total_kopeks` | INTEGER | NOT NULL, >= 0; вычисляется сервером |
| `item_count` | INTEGER | NOT NULL, >= 1; сумма количеств |
| `tracking_scenario_id` | VARCHAR(64) | NOT NULL; `default-v1` |
| `tracking_version` | INTEGER | NOT NULL, default 1 |

Опционально `idempotency_key` (UNIQUE) для защиты от повторной отправки; **для MVP реализовать обязательно**, см. API ниже. Если хранить в `Order`, строка UUIDv4 из клиента, нормализованная/валидированная на сервере. Ключ должен быть уникальным глобально; привязывать его к **отпечатку нормализованной корзины**, чтобы повторное использование с другим содержимым отклонялось, см. ниже. Отпечаток `request_fingerprint` — VARCHAR(64), SHA-256 нормализованных позиций. Уникальный индекс по `idempotency_key`.

### 5.2. `OrderItem` (`order_items`)

| Поле | Тип | Требования |
|---|---|---|
| `id` | INTEGER PK | внутренний |
| `order_id` | INTEGER FK | NOT NULL -> `orders.id`, ON DELETE CASCADE |
| `product_id` | VARCHAR(64) | NOT NULL, снимок идентификатора |
| `product_name` | VARCHAR(160) | NOT NULL, снимок названия |
| `unit_price_kopeks` | INTEGER | NOT NULL, >= 0, снимок цены |
| `quantity` | INTEGER | NOT NULL, 1..10 |
| `line_total_kopeks` | INTEGER | NOT NULL, = unit_price_kopeks × quantity |

- На уровне ORM: `Order.items`, relationship, `cascade="all, delete-orphan"`.
- На уровне SQLite: активировать `PRAGMA foreign_keys=ON` для соединений.
- Ограничения SQL (`CHECK`) для количества и неотрицательных денежных полей, где возможно.
- Индекс `order_items(order_id)`; уникальный индекс `(order_id, product_id)` — повторяющиеся ID объединяются на этапе нормализации; в БД максимум одна строка для товара.
- В заказе минимум 1 и максимум 15 разных товаров; общее количество единиц максимум 50 (но каждая позиция не более 10).
- **Никогда не пересчитывать старый заказ по `catalog.json`.** Сохранённые `OrderItem` — источник истины для истории/чека.

### 5.3. Сохранение и транзакции

- Создание `Order` со всеми `OrderItem` — **одна атомарная транзакция**.
- При ошибке делать rollback, не оставляя пустой заказ.
- `OrderRepository` возвращает ORM-сущность с заранее загруженными `items` (например, `selectinload`), избегает доступа к закрытой сессии.
- SQLite для локального запуска; включить корректный `busy_timeout` / разумный timeout, не делать ручные блокировки.
- Не пытаться сделать SQLite высоконагруженной многосерверной системой; для MVP достаточно.

### 5.4. Даты

- Устанавливать `created_at` только на сервере, в UTC.
- SQLite обычно хранит datetime без tzinfo: строго определить слой сериализации, трактовать значение как UTC и **никогда не принимать локальную дату браузера для расчёта этапов**.
- Все API timestamp — ISO 8601 со смещением `Z`, например `2026-11-15T12:30:00Z`.
- Текущая стадия вычисляется при каждом запросе через внедряемый UTC-clock, не через JS-локальное время как источник истины.

---

## 6. Бизнес-классы: точные контракты и зависимости

### 6.1. `CartLine` / `ValidatedCart`

```python
@dataclass(frozen=True)
class CartLine:
    product_id: str
    product_name: str
    unit_price_kopeks: int
    quantity: int
    line_total_kopeks: int

@dataclass(frozen=True)
class ValidatedCart:
    lines: tuple[CartLine, ...]
    item_count: int
    total_kopeks: int
```

DTO живут в `models/dto.py`, не зависят от ORM.

### 6.2. `CartService`

**Зависимость:** `CatalogService`.

```python
class CartService:
    def __init__(self, catalog: CatalogService): ...
    def validate(self, raw_items: object) -> ValidatedCart: ...
```

Алгоритм `validate`:

1. Проверить, что `raw_items` — `list`, длина 1..15. Пример элемента: `{"product_id":"invisible-socks","quantity":2}`.
2. Запретить `bool`, float, строки вместо `quantity`; принимать только `type(quantity) is int` и 1..10.
3. `product_id` — строка допустимой длины и известный товар каталога.
4. Запретить повторяющиеся `product_id` в запросе (ошибка 422), чтобы не возникало двойного подсчёта; frontend заранее обеспечивает уникальность.
5. Проверить сумму `quantity` <= 50.
6. Использовать цену **только из `CatalogService`**, игнорировать присланные поля цены/суммы (рекомендуется отклонить лишние поля согласно API-контракту).
7. Построить `CartLine`, `item_count`, `total_kopeks` с целочисленной арифметикой.
8. Порядок линий — порядок входного массива; при расчёте идемпотентного fingerprint отсортировать по `product_id`.
9. Для любой ошибки бросить `ValidationError(code, message, details)` с дружелюбным русским сообщением, не `KeyError`/500.

**Уточнение:** browser localStorage — лишь локальное состояние UI; сервер никогда не считает его доверенным.

### 6.3. `OrderRepository`

**Зависимость:** `db.session`/SQLAlchemy models. Сервис не обязан создавать отдельную сессию; использовать единый request-scoped SQLAlchemy session.

```python
class OrderRepository:
    def __init__(self, session): ...
    def get_by_public_token(self, token: str) -> Order | None: ...
    def get_by_idempotency_key(self, key: str) -> Order | None: ...
    def save(self, order: Order) -> Order: ...
```

`save` добавляет объект в сессию и выполняет `flush()` для получения ID; **commit/rollback контролирует `OrderService`**. Не предоставлять наружу произвольные SQL-конструкции. Не создавать метод поиска публичных заказов по `id`.

### 6.4. `OrderService`

**Зависимости:** `CartService`, `OrderRepository`, UTC clock (`Callable[[], datetime]`), генератор токена (`Callable[[], str]`) для тестов.

```python
class OrderService:
    def create_order(self, raw_items: object, idempotency_key: str) -> Order: ...
    def get_order(self, public_token: str) -> Order: ...
```

`create_order`:

1. Провалидировать `idempotency_key`: UUIDv4 (36 символов, стандартный формат), обязательный.
2. Перед записью валидировать корзину через `CartService` и построить `request_fingerprint`: `sha256(json.dumps(sorted([{"product_id":...,"quantity":...}]), separators=(',', ':'), ensure_ascii=True).encode())`.
3. Найти существующий заказ с таким ключом. Если найден и fingerprint совпадает, **вернуть тот же заказ**. Если не совпадает — `ConflictError` (409).
4. Иначе создать токен, номер заказа, UTC-дату, снимки строк, суммы и `tracking_scenario_id='default-v1'`, `tracking_version=1`.
5. Сохранить атомарно и выполнить commit. Если столкновение уникального токена/номера — ограниченно повторить генерацию; если столкновение ключа при параллельном POST — после rollback перечитать заказ и сравнить fingerprint.
6. Не отправлять уведомления и не запускать таймеры/фоновые процессы.
7. `get_order`: валидировать токен в допустимом формате и вернуть заказ; неизвестный токен -> `NotFoundError`, не раскрывать детали.

Не включать в `OrderService` QR/HTML/receipt: они формируются по уже созданному заказу в соответствующих слоях.

### 6.5. `TrackingStage` / `TrackingState`

```python
@dataclass(frozen=True)
class TrackingStage:
    id: str
    title: str
    description: str
    start_after_seconds: int
    emoji: str

@dataclass(frozen=True)
class TrackingState:
    current_stage_index: int
    current_stage: TrackingStage
    stages: tuple[TrackingStage, ...]
    elapsed_seconds: int
    next_stage_at: datetime | None
    is_final: bool
```

`elapsed_seconds` всегда `max(0, floor((now_utc - created_at_utc).total_seconds()))`.

### 6.6. `TrackingService` — ключевая логика проекта

**Зависимости:** загрузчик неизменяемого `tracking_scenarios.json` (или загруженная схема), UTC clock. **Не зависит от Flask, браузера, SQLAlchemy, потоков или scheduler.** На вход получает `Order` или минимальные значения `created_at`, `tracking_scenario_id`, `tracking_version`.

```python
class TrackingService:
    def __init__(self, scenarios_path: Path, clock: Callable[[], datetime]): ...
    def get_state(self, order: Order) -> TrackingState: ...
```

**Строго заданный сценарий `default-v1`:**

| Индекс | `id` | С какого времени после заказа | Заголовок |
|---:|---|---:|---|
| 0 | `accepted` | 0 сек | «Заказ принят. Мы морально готовимся.» |
| 1 | `packing` | 30 сек | «Упаковываем в воображаемую коробку.» |
| 2 | `courier` | 90 сек | «Курьер вышел. Кажется, не туда.» |
| 3 | `multiverse` | 180 сек | «Заказ застрял в мультивселенной.» |
| 4 | `delivered` | 300 сек | «Доставлено прямо в ваше воображение.» |

Это **демонстрационно короткая** шкала: весь путь занимает 5 минут, чтобы трекинг можно было реально проверить на презентации. Значения живут в JSON и могут настраиваться, но для MVP используем указанные.

Пример `tracking_scenarios.json`:

```json
{
  "schema_version": 1,
  "scenarios": [
    {
      "id": "default-v1",
      "version": 1,
      "stages": [
        {"id":"accepted","title":"Заказ принят. Мы морально готовимся.","description":"Система делает вид, что очень занята.","emoji":"✅","start_after_seconds":0},
        {"id":"packing","title":"Упаковываем в воображаемую коробку.","description":"Главное — не забыть положить туда ничего.","emoji":"📦","start_after_seconds":30},
        {"id":"courier","title":"Курьер вышел. Кажется, не туда.","description":"Он отвлёкся на ещё одно очень важное видео.","emoji":"🚴","start_after_seconds":90},
        {"id":"multiverse","title":"Заказ застрял в мультивселенной.","description":"Там сейчас особенно напряжённая логистика.","emoji":"🌀","start_after_seconds":180},
        {"id":"delivered","title":"Доставлено прямо в ваше воображение.","description":"Проверьте карман фантазии, пожалуйста.","emoji":"🎉","start_after_seconds":300}
      ]
    }
  ]
}
```

**Алгоритм без фоновых задач:**

```python
elapsed = max(0, int((clock_utc() - order.created_at_utc).total_seconds()))
current_index = max(i for i, s in enumerate(stages)
                    if s.start_after_seconds <= elapsed)
next_stage_at = (
    order.created_at_utc + timedelta(seconds=stages[current_index + 1].start_after_seconds)
    if current_index + 1 < len(stages) else None
)
```

Правила:

- На точных границах (30/90/180/300 секунд) **уже** показывать следующий статус.
- Если системные часы меньше времени заказа — стадия 0.
- Финальная стадия остаётся навсегда, не циклируется.
- Два обращения с одинаковыми `created_at`/`now` возвращают одинаковое состояние.
- Нет случайности, различий по пользователям/устройствам и записи текущего статуса в БД.
- `tracking_scenarios.json` загружается и валидируется при создании приложения: уникальные ID, возрастающие смещения, первый старт=0, минимум 2 стадии; для `default-v1` строго пять стадий.
- Сценарии должны быть **версионированы**. После появления заказов нельзя менять значения времени или текст `default-v1`: добавлять `default-v2` и назначать его новым заказам. Для MVP используется только `default-v1`.
- API возвращает серверное `server_time`, `next_stage_at`, текущий статус и весь таймлайн.
- Frontend делает `GET` статуса каждые **5 секунд**, только пока документ видим; при возвращении на вкладку — немедленно обновляет. Рекомендуется также запланировать однократный refresh на границе `next_stage_at`, но опрос раз в 5 секунд достаточен. Прекращать polling после финала.
- Вывод countdown до следующего этапа — необязательная, но желательная функция, вычисляемая относительно `server_time`, чтобы уменьшить расхождение часов на клиенте.
- Предусмотреть `Cache-Control: no-store` для endpoint статуса и страниц, где требуется свежий статус.

### 6.7. `ReceiptService`

**Зависимости:** только снимок `Order` и `Order.items`. Вернуть `ReceiptDTO` или обычный сериализуемый словарь:

```python
class ReceiptService:
    def build(self, order: Order) -> ReceiptDTO: ...
```

Поля: `order_number`, `created_at`, `lines`, `item_count`, `total_kopeks`, `disclaimer` = «Это шуточная покупка. Деньги не списаны. Доставки не будет». Отображение денежных значений — отдельный Jinja filter `format_rub`, принимающий целое число копеек; в JS тот же формат делать через `Intl.NumberFormat('ru-RU', {style:'currency', currency:'RUB'})` после деления на 100 **только для отображения**.

Не генерировать PDF (не требуется), не хранить чеки отдельной таблицей. HTML-чек в `order_success.html` достаточен; возможна печать страницы через `window.print()` и CSS `@media print`.

### 6.8. `QRCodeService`

```python
class QRCodeService:
    def make_png(self, absolute_url: str) -> bytes: ...
```

- Содержимое QR: абсолютный URL `/track/<public_token>`.
- Генерировать в памяти через `BytesIO`, `qrcode` и Pillow, возвращать `image/png`.
- **Не принимать произвольный URL из query params.** Endpoint сам составляет URL из проверенного заказа через `url_for(..., _external=True)`.
- В production учитывать `PUBLIC_BASE_URL` как канонический корень URL, чтобы QR не зависел от недоверенного Host header. В dev использовать `http://localhost:5000` (или настроенный `PUBLIC_BASE_URL`). Убирать завершающий `/`, путь соединять безопасно.
- Ошибка/неизвестный заказ -> 404; не выдавать QR для несуществующего токена.
- Не записывать PNG на диск без нужды.

### 6.9. `Clock` и зависимости для тестирования

Не требуется отдельный класс clock: использовать инъекцию `Callable[[], datetime]` c default-функцией `datetime.now(timezone.utc)`. В тестах подставлять фиксированное UTC-время. Аналогично генератор токенов. **Никаких `sleep()` в тестах трекинга.**

### 6.10. Ошибки домена

```python
class DomainError(Exception):
    code: str
    message: str
    status_code: int

class ValidationError(DomainError): ...   # 422
class NotFoundError(DomainError): ...     # 404
class ConflictError(DomainError): ...     # 409
```

Соблюдать единый JSON-формат ответа об ошибке в API; HTML-маршруты рендерят `404.html` / `500.html`.

---

## 7. Приложение Flask, конфигурация, создание зависимостей

### 7.1. App factory

`app/__init__.py`:

```python
def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)
    # create instance dir
    # db.init_app(app)
    # validate and load catalog / tracking scenarios
    # construct services and repository provider
    # register blueprints, error handlers, filters, CLI init-db
    return app
```

Важная деталь: не создавать `OrderRepository(db.session)` и не сохранять ORM session как глобальный singleton вне Flask application/request context. Реализовать `repository_factory()` в слое сборки/маршрута, принимающий актуальный `db.session`. Остальные статические сервисы (`CatalogService`, `TrackingService`, `QRCodeService`) можно сохранить в `app.extensions['dopadrop']` или небольшой `Services` dataclass; избегать новых контейнеров DI.

### 7.2. Настройки (`Config`)

- `SECRET_KEY` — из окружения, для production обязателен; dev fallback допустим с предупреждением и **не использовать** как источник публичных токенов.
- `SQLALCHEMY_DATABASE_URI` — по умолчанию `sqlite:///shop.db` в instance-пути; проверить корректность расположения фактического файла.
- `SQLALCHEMY_TRACK_MODIFICATIONS = False`.
- `CATALOG_PATH`, `TRACKING_SCENARIOS_PATH` — по умолчанию абсолютные пути от `app/`; тесты переопределяют.
- `PUBLIC_BASE_URL` — default `http://localhost:5000` для локальной разработки; в production указывается реальный HTTPS-домен.
- `MAX_CONTENT_LENGTH = 16 * 1024` (16 KiB на JSON-запрос заказа).
- `JSON_AS_ASCII = False` при необходимости; явно возвращать UTF-8.
- `TESTING`, `WTF_CSRF_ENABLED` не добавлять, если Flask-WTF не используется.

`.env.example`:

```dotenv
FLASK_APP=run.py
FLASK_DEBUG=1
SECRET_KEY=change-me-in-production
PUBLIC_BASE_URL=http://localhost:5000
# DATABASE_URL=sqlite:///shop.db
```

Если поддерживается `DATABASE_URL`, конфиг должен использовать его аккуратно; README объясняет относительный путь SQLite.

### 7.3. Создание таблиц

Добавить команду `flask init-db`, которая вызывает `db.create_all()` в app context. Допустимо при первом старте для удобства разработчика создать базу явно через CLI, **но не делать auto-drop и не удалять пользовательские заказы**. Для тестов создавать/удалять таблицы в fixtures.

### 7.4. Безопасные HTTP-заголовки

- `X-Content-Type-Options: nosniff`.
- `Referrer-Policy: strict-origin-when-cross-origin` или `no-referrer` для страниц, где URL содержит токен (предпочтительно `no-referrer`).
- `Cache-Control: no-store` для ответов заказа/трекинга/чека/QR.
- Не включать `DEBUG=True` в production.
- Не логировать токены заказа целиком в прикладных логах.
- Не вставлять HTML от пользователя через `|safe`; Jinja autoescape включён.
- Не открывать CORS для всех сайтов: frontend и backend работают на одном origin.

---

## 8. HTTP-маршруты и точный API-контракт

### 8.1. HTML-страницы (`pages` Blueprint)

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/` | Каталог 15 товаров, фильтр/поиск (`?category=...&q=...`) |
| GET | `/cart` | Корзина, отрисовывается JS из localStorage |
| GET | `/checkout` | Подтверждение фиктивного оформления; при пустой корзине пояснение и ссылка в каталог |
| GET | `/orders/<public_token>/success` | Чек, детали заказа, QR и ссылка на трекинг |
| GET | `/track/<public_token>` | Страница автоматического отслеживания |

Допускается `/about`, если возникнет потребность, но не обязательно.

Страница заказа и трекинг используют серверный поиск по токену. Никаких страниц `/orders/1` по числовому ID.

### 8.2. JSON API (`orders_api` Blueprint, prefix `/api`)

#### `POST /api/orders`

**Request headers:** `Content-Type: application/json`.

**Body (строго):**

```json
{
  "idempotency_key": "d35833cb-9d5d-4c18-8b90-399837ed57a2",
  "items": [
    {"product_id": "invisible-socks", "quantity": 2},
    {"product_id": "tomorrow-planner", "quantity": 1}
  ]
}
```

- Разрешены только ключи верхнего уровня `idempotency_key`, `items`; в элементах — только `product_id`, `quantity`.
- Все поля обязательны. UUIDv4 на клиенте создавать `crypto.randomUUID()` (для localhost работает как secure context; описать fallback при необходимости).
- Суммы и пользовательская информация **не принимаются**.
- Перед повтором запроса после сетевой ошибки frontend обязан использовать **тот же** `idempotency_key` и ту же нормализованную корзину; новый ключ создавать только при новом оформлении.

**201 Created (новый заказ):**

```json
{
  "order": {
    "order_number": "DD-20261115-A7D9F2",
    "public_token": "<случайный_непредсказуемый_токен>",
    "created_at": "2026-11-15T12:30:00Z",
    "total_kopeks": 189700,
    "item_count": 3,
    "items": [
      {"product_id":"invisible-socks","product_name":"Невидимые носки","quantity":2,"unit_price_kopeks":49900,"line_total_kopeks":99800},
      {"product_id":"tomorrow-planner","product_name":"Планер «Начну завтра»","quantity":1,"unit_price_kopeks":89900,"line_total_kopeks":89900}
    ]
  },
  "links": {
    "success": "/orders/<token>/success",
    "tracking": "/track/<token>",
    "qr": "/orders/<token>/qr.png"
  }
}
```

В примере суммы: 99800 + 89900 = **189700 коп.** `public_token` у реального ответа будет криптостойким, не строкой-плейсхолдером.

**200 OK (повторный идентичный запрос с тем же ключом):** тот же формат и тот же заказ. Никаких дубликатов в БД.

Ошибки:

- `400 Bad Request` — некорректный JSON / неверный Content-Type (допустим `415` для Content-Type).
- `413 Payload Too Large` — превышен лимит размера.
- `422 Unprocessable Entity` — неизвестный товар, пустой список, неправильное количество, дублирующиеся товары, неверный UUIDv4.
- `409 Conflict` — idempotency key повторно использован для другой корзины.
- `500` — непредвиденная серверная ошибка, без утечки tracebacks клиенту.

Ошибочный ответ:

```json
{
  "error": {
    "code": "invalid_quantity",
    "message": "Количество товара должно быть целым числом от 1 до 10.",
    "details": {"index": 0}
  }
}
```

#### `GET /api/orders/<public_token>/tracking`

**200 OK:**

```json
{
  "order_number": "DD-20261115-A7D9F2",
  "server_time": "2026-11-15T12:31:40Z",
  "created_at": "2026-11-15T12:30:00Z",
  "tracking": {
    "current_stage_index": 2,
    "current_stage_id": "courier",
    "elapsed_seconds": 100,
    "is_final": false,
    "next_stage_at": "2026-11-15T12:33:00Z",
    "stages": [
      {"id":"accepted","title":"Заказ принят. Мы морально готовимся.","description":"Система делает вид, что очень занята.","emoji":"✅","start_after_seconds":0,"state":"complete"},
      {"id":"packing","title":"Упаковываем в воображаемую коробку.","description":"Главное — не забыть положить туда ничего.","emoji":"📦","start_after_seconds":30,"state":"complete"},
      {"id":"courier","title":"Курьер вышел. Кажется, не туда.","description":"Он отвлёкся на ещё одно очень важное видео.","emoji":"🚴","start_after_seconds":90,"state":"current"},
      {"id":"multiverse","title":"Заказ застрял в мультивселенной.","description":"Там сейчас особенно напряжённая логистика.","emoji":"🌀","start_after_seconds":180,"state":"pending"},
      {"id":"delivered","title":"Доставлено прямо в ваше воображение.","description":"Проверьте карман фантазии, пожалуйста.","emoji":"🎉","start_after_seconds":300,"state":"pending"}
    ]
  }
}
```

- `state`: предыдущие `complete`, текущий `current`, будущие `pending`; на финальном этапе только последний `current`, все предыдущие `complete`.
- `next_stage_at = null` для последней стадии.
- Текущий статус вычисляется при запросе; не хранить его в БД.
- `404` для неизвестного токена, `Cache-Control: no-store`.

### 8.3. QR endpoint (`qr` Blueprint)

`GET /orders/<public_token>/qr.png` -> PNG с QR-кодом, который открывает `PUBLIC_BASE_URL + /track/<token>`; MIME `image/png`, `Cache-Control: no-store`. Неизвестный токен -> 404. QR должен быть реально сканируемым: обеспечить поля/контраст/разумный размер.

### 8.4. Обработка запросов и возврата ссылок

- Не составлять URL из небезопасных параметров `next`, `redirect_url`.
- Для формируемых клиенту относительных URL использовать Flask `url_for`, а не ручное склеивание token/path, кроме канонического абсолютного URL QR.
- Для HTML ошибок рендерить шаблон и выставлять корректный HTTP status.
- Код HTTP JSON API не должен выдавать ORM-объект напрямую; сериализовать DTO/словарём.

---

## 9. Frontend и состояние корзины

### 9.1. `localStorage`

Ключ: `dopadrop.cart.v1`. Значение:

```json
{
  "version": 1,
  "items": [
    {"product_id":"invisible-socks","quantity":2},
    {"product_id":"tomorrow-planner","quantity":1}
  ]
}
```

Не хранить в localStorage в качестве истины название, цену, сумму или итог. Если хранить кэш для рендера — только как неавторитетные данные, пересчитывать из каталога на странице, а на backend всегда валидировать снова. Для MVP проще встраивать минимальный каталог в HTML при рендеринге главной/корзины/checkout через Jinja `tojson`, либо предоставить JSON endpoint `GET /api/catalog` (см. ниже).

**Предпочтительное решение:** добавить `GET /api/catalog` с безопасным публичным read-only списком товаров и категорий, а клиентские страницы используют его для актуального UI. Никакой отдельной инфраструктуры API не возникает.

`GET /api/catalog` -> `{"categories":[...],"products":[...]}` со всеми полями Product, статус 200; браузер может кэшировать кратко (например 60 секунд), но корзина при заказе обязательно проверяется сервером. HTML `GET /` всё равно отображает карточки на сервере Jinja для доступности.

### 9.2. `cart.js`

Реализовать небольшой модуль без глобального хаоса. Обязательные операции:

```javascript
readCart()                 // returns normalized {version:1, items:[...]}
writeCart(cart)            // persist; dispatch custom 'cart:changed'
addItem(productId, qty=1)
setQuantity(productId, qty)
removeItem(productId)
clearCart()
getItemCount()
```

Нормализация при чтении:

- `try/catch` для некорректного JSON; при повреждении — пустая корзина и дружелюбное сообщение (без падения JS).
- Миграций версий не требуется: неизвестная версия -> очистить с сообщением.
- Дубли убрать/объединить безопасно; количество ограничить 1..10 для каждого продукта.
- Максимум 15 разных товаров и 50 единиц; если лимит нарушен, не допускать добавления, показать уведомление.
- Неизвестные товары из старой корзины отфильтровывать после получения актуального каталога, показать уведомление.
- Обрабатывать `storage` event для синхронизации между вкладками.
- Пытаться записать в localStorage в `try/catch` (возможно запрещено браузером); при отказе хранить сессию в памяти и сообщить, что корзина не переживёт перезагрузку.

### 9.3. `api.js`

Функции `getCatalog()`, `createOrder(payload)`, `getTracking(token)` используют `fetch`, проверяют `response.ok`, парсят JSON и формируют удобную ошибку с `error.message`. При сетевом сбое отображают retry UI. Не использовать axios/jQuery.

### 9.4. `catalog.js`

- Кнопка «В корзину» работает на каждой карточке.
- Показ счётчика товаров в header обновляется при изменении корзины.
- Фильтрация категорий и поиск: серверные GET-параметры `category`, `q`; UI предоставляет форму, ссылку «Сбросить фильтры».
- После нажатия показывать краткое подтверждение, не навязчивый alert.
- Предусмотреть пустой результат поиска.

### 9.5. `cart.html`

- Страница показывает строки корзины с названием, ценой за единицу, количеством (+/-/input), суммой строки, общим итогом и удалением.
- Отображение строится из localStorage плюс актуальный `GET /api/catalog`. После изменения количества сразу пересчитывать UI.
- Пустая корзина: «Ваша корзина пока откладывает принятие решений» и ссылка назад.
- Кнопка «Оформить понарошку» ведёт на `/checkout`; disabled для пустой корзины.

### 9.6. `checkout.html` + `checkout.js`

- Показать резюме корзины, итог и **заметный дисклеймер** о ненастоящей покупке.
- Checkbox «Понимаю, что заказ шуточный и деньги не списываются» — обязательное UI-подтверждение до отправки. Не нужно хранить его в БД (нет реальной юридической операции).
- Не собирать email, телефон, адрес и реквизиты карты.
- Кнопка «Оформить заказ без оплаты»: disabled во время запроса; прогресс и ошибки доступны screen reader.
- Создать `idempotency_key` один раз на попытку оформления и сохранять в `sessionStorage` вместе с **fingerprint/снимком корзины** до успешного ответа. После сетевой ошибки повторять тот же запрос с тем же ключом/тем же payload; при изменении корзины — новая попытка/ключ. После успеха очистить checkout attempt и корзину, перейти на `links.success`.
- Для недоверенных/битых данных сервер вернёт ошибку; показать `message` рядом с кнопкой, не уводить на 500.
- При двойном клике заказ создаётся один раз.
- Если переход на success URL не удался после успешного POST, показать ссылку из ответа; не оставлять пользователя без доступа к созданному заказу.

### 9.7. `order_success.html`

- Номер заказа, время, перечень, шуточная сумма, дисклеймер.
- QR как `<img src=".../qr.png" alt="QR-код для отслеживания заказа">`.
- Ссылка на `/track/<token>`, кнопка «Скопировать ссылку» через Clipboard API с fallback (если доступ запрещён — показать текстовую ссылку для ручного копирования).
- Кнопка «Распечатать шуточный чек» -> `window.print()` (опционально).
- Не показывать внутренний `order.id`.

### 9.8. `tracking.html` + `tracking.js`

- Сервер при первом рендеринге уже отдаёт фактическое состояние трекинга (для пользователя без JS тоже есть статус).
- JS запускает периодический `fetch GET /api/orders/<token>/tracking` каждые 5 секунд; использовать `document.visibilityState` и останавливать interval на скрытой вкладке. При `visibilitychange` на visible обновлять сразу.
- После достижения финального статуса очистить таймер.
- Визуальный таймлайн из 5 пунктов; `aria-current="step"` у актуального. Поле текущего статуса в `aria-live="polite"`, но не озвучивать весь экран каждые 5 секунд (обновлять только при реальной смене стадии).
- Временное отсутствие интернета не ломает страницу: последний известный статус остаётся на месте, появляется ненавязчивая надпись «Не удалось обновить. Попробуем ещё раз».
- **Никаких локальных `setTimeout` как единственного источника статуса.** Статус — серверный.
- Стадии `pending/complete/current` визуально различаются и текстом/иконками, а не только цветом.

---

## 10. HTML-дизайн и контент

### 10.1. Общая структура

`base.html`: `<html lang="ru">`, `<meta charset="utf-8">`, responsive viewport, metadata title/description, header (логотип DopaDrop + «Каталог» + «Корзина (N)»), `<main>`, footer с дисклеймером, локальный CSS/JS. Все пути через `url_for`.

### 10.2. Главная страница

- Hero: заголовок «DopaDrop — магазин вещей, которые можно купить потом»; подзаголовок об абсурдной торговле без списаний.
- Подсказка «15 совершенно необязательных товаров».
- Поиск, фильтр по 5 категориям, каталог карточек: emoji/иконка, название, описание, шуточный мем, цена, кнопка.
- Улыбчивые микротексты: «Отложить на потом» как дополнительная декоративная метка, но основная кнопка должна оставаться понятной «В корзину».

### 10.3. Цвета и CSS

Выбрать 3-4 согласованных цвета с доступным контрастом, CSS custom properties, аккуратные тени, `border-radius`, адаптивная сетка 1/2/3 карточки по ширине. Не тянуть шрифты с Google Fonts; использовать system fonts.

### 10.4. Состояния

Обязательно: загрузка, пустая корзина, отсутствие результатов поиска, неизвестный токен/404, сбой API, успешное оформление, финальный трекинг. У всех форм есть явные labels и доступные сообщения.

---

## 11. Точная матрица зависимостей и жизненный цикл

| Компонент | От чего зависит | Кто вызывает | Что НЕ делает |
|---|---|---|---|
| `Product`, `Category` | только stdlib dataclasses | CatalogService, templates | ORM/HTTP |
| `CatalogService` | `catalog.json` | CartService, pages, catalog API | SQL, заказ |
| `CartService` | CatalogService | OrderService | localStorage |
| `Order`, `OrderItem` | SQLAlchemy | OrderRepository | бизнес-правила HTTP |
| `OrderRepository` | `db.session`, ORM models | OrderService, маршруты чтения | цены/трекинг |
| `OrderService` | CartService, OrderRepository, clock, tokens | POST orders, pages read facade | HTML/QR |
| `TrackingService` | сценарии, clock | tracking page/API | scheduler/DB writes |
| `ReceiptService` | Order snapshot | success page | catalog repricing |
| `QRCodeService` | qrcode, Pillow | QR route | запись в БД |
| HTML Blueprints | Flask, services | browser | SQL напрямую |
| JS cart | localStorage, catalog API | browser | безопасное вычисление заказов |

### Последовательность: оформление

```text
checkout.js
  -> POST /api/orders {idempotency_key, items}
    -> orders_api.create_order
      -> OrderService.create_order
        -> CartService.validate
          -> CatalogService.get_product
        -> OrderRepository.get_by_idempotency_key
        -> OrderRepository.save(Order + OrderItem[])
        -> db.session.commit()
    <- 201 / 200 + ссылки
  -> localStorage.clearCart()
  -> GET /orders/<token>/success
    -> OrderService.get_order -> OrderRepository
    -> ReceiptService.build
    -> render_template(order_success.html)
  -> GET /orders/<token>/qr.png
    -> OrderRepository (проверка токена)
    -> QRCodeService.make_png(PUBLIC_BASE_URL + tracking path)
```

### Последовательность: автоматический трекинг

```text
GET /track/<token>
  -> OrderRepository.get_by_public_token
  -> TrackingService.get_state(order, now_utc)
  -> HTML timeline

каждые 5 секунд, пока вкладка видима:
GET /api/orders/<token>/tracking
  -> OrderRepository.get_by_public_token
  -> TrackingService.get_state(order, new_now_utc)
  -> JSON timeline
  -> tracking.js обновляет DOM

Важно: между вызовами ни один процесс не обновляет статус.
```

---

## 12. Security, privacy, reliability

### 12.1. Защита от подделки сумм

- Backend использует только `product_id + quantity`.
- Нельзя принимать `total_kopeks`, `unit_price`, `discount`, `is_paid`, `status` и любые признаки оплаты от клиента.
- Валидировать типы строго, включая `bool` как некорректное количество.

### 12.2. Токены доступа

- Токен создаётся `secrets.token_urlsafe(24)`; entropy >= 192 bit.
- Публичные ссылки содержат только токен, не ID.
- Токены не передаются третьим лицам через внешние ресурсы (никаких CDN/analytics/tracker); установить `Referrer-Policy: no-referrer` на страницах заказов.
- Не добавлять sitemap/index для страниц заказов: `<meta name="robots" content="noindex,nofollow">`.
- Так как нет логина, владение ссылкой даёт доступ к шуточному заказу. Никаких персональных данных в заказе — минимизируем риск.

### 12.3. Ограничения

- JSON максимум 16 KiB, <=15 товарных строк, <=50 единиц, <=10 каждой позиции.
- Противодействовать XSS через Jinja autoescape и JS `textContent` вместо `innerHTML` для данных API.
- Не включать в приложение реальные платежные интеграции.
- CSRF для unauthenticated create endpoint без cookie-аутентификации здесь не даёт доступа к данным, но запретить cross-origin CORS и принимать только `application/json`; при расширении до cookie-аккаунтов добавить полноценный CSRF.
- Избегать открытого редиректа и доверия Host header при QR.
- Защита от массового спама заказами (rate limiting по IP) — **желательная для публичного деплоя**, но в MVP без внешнего Redis не вводить зависимость; в README указать reverse-proxy rate limit как шаг перед открытой публикацией.

### 12.4. Надёжность

- Проверка JSON при старте, ясные сообщения об ошибке конфигурации.
- Ошибка SQLite/диска -> HTTP 500 с общим сообщением, подробности только в серверном логе.
- Идемпотентный POST защищает от случайных двойных заказов.
- `pytest` не должен работать на реальной `instance/shop.db`.

---

## 13. Тестирование: обязательные тест-кейсы

### 13.1. Fixtures

- `app` с `TESTING=True`, temp SQLite (`tmp_path` файл или `sqlite://` с корректной настройкой соединений), отдельным test catalog file только там, где нужен негативный тест.
- `client = app.test_client()`.
- `fixed_clock` с меняемым моментом времени, без `time.sleep`.
- Таблицы `create_all()` до теста и `drop_all()` после, изоляция данных.
- Для большинства тестов использовать настоящий каталог с 15 товарами; валидацию повреждённого JSON тестировать отдельно.

### 13.2. Тесты каталога

- Ровно 15 продуктов, 5 категорий, 3 товара в каждой.
- Все ID уникальны, каждое `price_kopeks` — int >=0.
- `get_product` существующий и неизвестный.
- Фильтр категории, поиск без регистра, пустой поиск, несоответствующий поиск.
- Повреждённый JSON, дублированный ID, несуществующая категория, отрицательная цена -> ошибка инициализации.

### 13.3. Тесты корзины

- Два товара и корректный подсчёт (`2*49900 + 1*89900 = 189700`).
- Пустой список, не-list, не-dict элемент.
- Неизвестный ID, дубликат ID.
- `quantity`: 0, -1, 11, 1.5, `"2"`, `true`, `null` -> 422.
- Список >15 позиций, сумма количеств >50.
- Попытка прислать клиентскую цену/дополнительное поле -> 422.
- Изначальный `catalog.json` не изменяется после валидации.

### 13.4. Тесты заказа и транзакций

- Создание заказа из двух товаров, проверка суммы, количества, полей снимка.
- Токен соответствует формату и отличается у разных заказов.
- Номер заказа уникален, внутренний ID не фигурирует в публичном JSON.
- Старые позиции/цены в SQLite сохраняются неизменными при изменении объекта каталога/последующей загрузке изменённого JSON.
- Повтор `POST` с тем же UUID+корзиной -> 200, тот же токен, одна запись в таблице.
- Тот же UUID с другой корзиной -> 409 и никаких новых записей.
- Сбой при записи строк заказа вызывает rollback целой транзакции (можно через mock/monkeypatch).
- Некорректный JSON, неверный Content-Type, слишком большой body.

### 13.5. Тесты автоматического трекинга (критически важно)

Для заказа, созданного в `2026-11-15T12:00:00Z`, проверить:

| elapsed | ожидаемый этап |
|---:|---|
| -1 сек (искусственный clock skew) | `accepted` |
| 0 сек | `accepted` |
| 29 сек | `accepted` |
| 30 сек | `packing` |
| 89 сек | `packing` |
| 90 сек | `courier` |
| 179 сек | `courier` |
| 180 сек | `multiverse` |
| 299 сек | `multiverse` |
| 300 сек | `delivered` |
| 24 часа | `delivered` |

Для каждой границы проверить `current_stage_index`, `is_final`, `next_stage_at`, `state` предыдущих/текущих/будущих. Проверить, что получение статуса **не изменяет строки в БД** и что новый API-запрос после искусственного продвижения clock меняет состояние без фонового процесса.

### 13.6. Тесты страниц и QR

- GET `/` -> 200, есть 15 карточек.
- GET `/cart`, `/checkout` -> 200.
- GET `/orders/<token>/success` содержит номер, строки, дисклеймер, QR img и ссылку.
- GET `/track/<token>` -> 200 и текущий статус.
- Неизвестный токен -> 404 для HTML/API/QR.
- QR endpoint -> `image/png`, PNG не пустой и генерируется для правильного URL (для содержимого QR допускается использовать декодер только если уже присутствует; иначе тестировать вызов QR service с ожидаемым URL и сигнатуру PNG).
- `no-store` для приватных страниц/API.

### 13.7. JavaScript

В минимальном MVP допустимо проверять JavaScript вручную по чеклисту ниже, если не вводится Node toolchain. Не устанавливать Jest/Vitest только ради небольшого проекта. Тем не менее конечный README должен содержать шаги ручной проверки: добавление/удаление товара, перезагрузка, 2 вкладки, двойной клик, сбой сети, переход по QR, автоматический переход через 30/90/180/300 секунд.

---

## 14. Порядок выполнения Codex (выполнять по этапам)

### Этап 1. Каркас

- Создать каталог, `requirements.txt`, `run.py`, `create_app`, конфиг, `.gitignore`, `.env.example`.
- Добавить `flask init-db`, обработчики ошибок, готовую базовую HTML-страницу и CSS.
- Проверить локальный запуск.

**Критерий:** приложение стартует, `/` возвращает 200, тест-клиент работает.

### Этап 2. Каталог

- Добавить JSON с 15 товарами/5 категориями, DTO, `CatalogService`, фильтры, поиск, HTML-карточки и `GET /api/catalog`.
- Написать тесты каталога.

**Критерий:** каталог и фильтры полностью работают, данные валидны.

### Этап 3. Корзина

- Реализовать `cart.js`, сохранение localStorage, страницу корзины, счётчик, лимиты.
- Реализовать `CartService`, тесты валидации.

**Критерий:** корзина переживает перезагрузку, сервер корректно пересчитывает итог.

### Этап 4. Заказы

- ORM `Order`, `OrderItem`, `OrderRepository`, `OrderService`, транзакции, токены, UUID idempotency.
- `POST /api/orders`, checkout UI и ошибки.
- Интеграционные тесты.

**Критерий:** заказ фиксируется в БД ровно один раз при повторном запросе, его нельзя подделать суммой.

### Этап 5. Чек и QR

- `ReceiptService`, страница успеха, QR service/route, noindex/no-store.
- Тесты ссылок и QR.

**Критерий:** ссылка по QR открывает именно нужный заказ, чек берёт сохранённые значения.

### Этап 6. Автоматический трекинг

- Загрузить JSON сценария, реализовать `TrackingService`, HTML timeline, JSON API, JS polling.
- Добавить тесты точных временных границ без ожидания.

**Критерий:** этап меняется сам после истечения заданного времени, даже после перезапуска сервера.

### Этап 7. Полировка и сдача

- Адаптивность, доступность, пустые состояния, обработка ошибок, безопасные заголовки.
- `pytest`, ручные smoke-тесты, README.
- Устранить ошибки и проверить чистую установку.

**Критерий:** выполнены все P0/P1 и Definition of Done из раздела 0.

---

## 15. Команды и документация

### 15.1. Ожидаемые команды

В `README.md` дать конкретные проверенные команды для Linux/macOS и краткую подсказку для Windows PowerShell. Базовый путь:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env            # Windows: Copy-Item .env.example .env
python -m flask --app run.py init-db
python -m flask --app run.py run --debug
pytest -q
```

Разработчику должно быть очевидно, где находится `instance/shop.db`, как сбросить **только локальную тестовую** базу и почему для обычной БД нельзя просто удалять данные без предупреждения.

### 15.2. `README.md` должен содержать

1. Краткое описание и важное предупреждение «никакой настоящей оплаты/доставки».
2. Стек и архитектуру (ASCII диаграмма зависимостей).
3. Установку/конфиг/запуск.
4. Описание всех HTML URL и API контрактов с примером `curl` для POST.
5. Объяснение корзины в localStorage и валидации цен на сервере.
6. Описание алгоритма автоматического трекинга и шкалу 0/30/90/180/300 секунд.
7. Инструкции по тестам и чеклист ручной проверки.
8. Разъяснение: SQLite + статический каталог удобны для MVP; для production нужны резервные копии, HTTPS, конфигурация `PUBLIC_BASE_URL`, ограничения частоты запросов и полноценный WSGI-сервер.
9. Принцип редактирования каталога и **версионирования сценариев**, чтобы не менять историю уже созданных заказов.

### 15.3. Дополнительные ограничения реализации

- Не писать весь проект в `app.py`.
- Не делать 20 абстрактных интерфейсов и фабрик ради шести сервисов.
- Не добавлять фоновые scheduler'ы и таблицы `tracking_events`, так как статусы выводятся из elapsed time.
- Не делать полноценную аутентификацию и профили.
- Не использовать реальные платёжные реквизиты; не вводить checkout-поля для адреса.
- Не менять согласованные маршруты и JSON-контракты без необходимости.
- Не генерировать фальшивые интеграции, ключи и несуществующие провайдеры.
- Не оставлять TODO вместо P0-функциональности.

---

## 16. Сквозные приёмочные сценарии (E2E-чеклист)

### Сценарий A — первая шуточная покупка

1. На `/` видны ровно 15 товаров; фильтр «Невидимые вещи» возвращает 3.
2. Добавить `invisible-socks` ×2 и `tomorrow-planner` ×1.
3. На `/cart` итог **1 897,00 ₽**, 3 единицы, 2 позиции.
4. Перезагрузить страницу — корзина не исчезла.
5. На `/checkout` ясно написано, что оплата не производится.
6. Отправить форму, получить страницу чека с теми же позициями и итогом.
7. Обновить страницу чека — заказ не дублируется.
8. Открыть QR/ссылку трекинга — тот же номер заказа.

### Сценарий B — стадия без фонового воркера

1. Создать заказ в момент T и открыть `/track/<token>`.
2. В T+0 получить `accepted`.
3. В T+30 секунд `packing`, в T+90 `courier`, в T+180 `multiverse`, в T+300 `delivered`.
4. Перезапустить Flask в середине — результат после запуска определяется из SQLite `created_at`, а не из памяти процесса.
5. Открыть ссылку в другом браузере — на том же серверном времени статус совпадает.

### Сценарий C — недоверенный клиент

1. Отправить `POST /api/orders` с ценой 1 коп. в поле строки -> 422, не принять цену.
2. Отправить неизвестный товар -> 422.
3. Отправить `quantity=true` -> 422.
4. Отправить один и тот же корректный запрос дважды с тем же idempotency key -> 201 затем 200, в БД ровно 1 заказ.
5. Попробовать `GET /track/1` или несуществующий токен -> 404.

### Сценарий D — случайные ошибки браузера

1. Испортить localStorage JSON — страница не падает; корзина сбрасывается с сообщением.
2. Отключить интернет при POST — кнопка позволяет повторить **тот же** запрос без дублирования.
3. В трекинге скрыть вкладку — polling останавливается; вернуться — статус тут же обновляется.
4. Проверить мобильную ширину 320/375/768/1280 px; горизонтальной прокрутки нет.

---

## 17. Внутренние решения по спорным вопросам

В отсутствие отдельных указаний считать согласованным следующее:

- **Только одно приложение Flask**, без микросервисов и отдельного фронтенд-сервера.
- **Оформление не требует регистрации** и вообще не содержит пользовательских персональных данных.
- **Корзина** — только `localStorage` на браузере; **заказы** — только SQLite на сервере.
- **Каталог** — 15 статических товаров в JSON; история заказов не привязана к актуальным ценам каталога.
- **Автоматический трекинг** детерминированный, короткий демонстрационный (5 минут), вычисляется из `created_at` и сценария, без scheduler/cron/Celery.
- **Каждый заказ проходит один и тот же сценарий `default-v1`**; разнообразие шуток достигается карточками, текстами и оформлением. Случайные ветвления трекинга исключены из MVP ради предсказуемости и тестируемости.
- **QR** — ссылка на публичный, неугадываемый токен; не QR оплаты.
- **Чек** — HTML, без PDF и без юридической силы.
- **Никаких реальных денежных операций, доставки или статусов внешней службы.**

---

## 18. Финальный отчёт Codex после реализации

После написания проекта в своём ответе:

1. Кратко перечисли реализованные возможности и итоговую структуру.
2. Покажи точные команды запуска и тестов.
3. Сообщи, какие тесты были **действительно выполнены** и с каким результатом. Не утверждай, что они прошли, если не запускал.
4. Назови любую осознанную несовместимость с этим ТЗ или невыполненный пункт; если не было — скажи явно.
5. Объясни, что происходит с заказом через 30/90/180/300 секунд и почему не требуется фоновая задача.
6. Не заканчивай работу на уровне скелета: отдай запускаемый и проверенный MVP.

**Конец спецификации.**
