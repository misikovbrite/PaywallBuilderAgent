# SubscriptionBuilderAgent — Создание подписок в App Store Connect

> Создаёт Weekly + Yearly подписки полностью через API и подключает их к пейволу.
> ~530 API calls, ~5 минут, 0 ручных шагов в ASC UI.

---

## БЫСТРЫЙ СТАРТ

```bash
# 1. Заполнить CONFIG в скрипте:
nano ~/PaywallBuilderAgent/subscription_creator.py

# 2. Запустить:
pip3 install pyjwt requests  # если нет
python3 ~/PaywallBuilderAgent/subscription_creator.py
```

Единственное обязательное поле: **`app_id`** (числовой App ID из ASC).

---

## Стандартные параметры (не менять без причины)

| Параметр | Значение |
|---------|---------|
| Weekly price | $5.99/week, без триала |
| Weekly price level | `10075` |
| Yearly price (USA) | $19.99/year |
| Yearly USA price level | `10177` |
| Yearly price (остальные) | $12.99/year |
| Yearly base price level | `10142` |
| Trial | 3 дня (THREE_DAYS), только Yearly |
| Территории | 175 (все страны) |
| Локализация | только en-US |
| Скриншот | один для всех приложений |

---

## Что нужно заполнить в CONFIG

```python
CONFIG = {
    # ✅ Обязательно:
    "app_id":           "6738893683",              # числовой ID из ASC URL
    "group_name":       "AntiqueSnap Premium",     # referenceName группы
    "app_display_name": "AntiqueSnap",             # видно пользователю в App Store
    "weekly_product_id":  "com.britetodo.antique.weekly",
    "yearly_product_id":  "com.britetodo.antique.yearly",

    # ⬇️  Остальное обычно не менять:
    "weekly_price_level":      "10075",   # $5.99
    "yearly_base_price_level": "10142",   # $12.99 (мир)
    "yearly_usa_price_level":  "10177",   # $19.99 (USA)
    "trial_duration":          "THREE_DAYS",
}
```

**Где взять App ID:**
- App Store Connect → Apps → выбрать приложение → URL содержит `/id{APP_ID}`
- Или: Apps → App Information → Apple ID (числовой)

---

## Полная последовательность (что делает скрипт)

```
Шаг 1:  POST /v1/subscriptionGroups              → создать группу
Шаг 2:  POST /v1/subscriptionGroupLocalizations  → локализация группы (en-US)
Шаг 3:  POST /v1/subscriptions × 2              → создать Weekly + Yearly
Шаг 4:  POST /v1/subscriptionLocalizations × 2  → локализация подписок (en-US)
Шаг 5:  GET  /v1/territories (paginate)          → получить все 175 территорий
Шаг 6:  POST /v1/subscriptionAvailabilities × 2 → доступность (⚠️ ДО цен!)
Шаг 7:  POST /v1/subscriptionPrices × ~350      → цены для всех территорий
Шаг 8:  POST /v1/subscriptionIntroductoryOffers × 175 → триал для Yearly
Шаг 9:  POST/PUT/PATCH screenshot × 2           → скриншот для ревью
Шаг 10: GET  /v1/subscriptions × 2              → проверка статуса
Шаг 11: Вывод результатов + сохранение IDs в /tmp/subscriptions_{app_id}.json
```

---

## Критические правила (нарушение = 500 ошибки)

### ⚠️ Availability ВСЕГДА до цен
```
subscriptionAvailabilities → ОБЯЗАТЕЛЬНО создать ДО subscriptionPrices
```
Без этого — 500 Internal Server Error на каждый POST /v1/subscriptionPrices.
Ошибка не информативная, Apple просто отдаёт 500.

### ⚠️ Territory — to-one relationship (не массив!)
```python
# ❌ НЕ работает (territory — не массив):
"territories": {"data": [{"type": "territories", "id": "USA"}, ...]}

# ✅ Правильно — отдельный вызов на каждую:
"territory": {"data": {"type": "territories", "id": "USA"}}
```
→ 175 отдельных API вызовов для introductory offers

### ⚠️ subscriptionGroupSubmissions — только с билдом
```
POST /v1/subscriptionGroupSubmissions НЕ работает отдельно.
Подписки сабмитятся ТОЛЬКО вместе с новой версией приложения.
```

### ⚠️ productId необратим
```
Нельзя повторно использовать product ID после удаления.
com.britetodo.antique.weekly — если удалить, этот ID навсегда "сгорает".
```

---

## Price Points — таблица уровней

| Level | USD | Применение |
|-------|-----|-----------|
| 10036 | $0.99 | |
| 10049 | $1.99 | |
| 10062 | $2.99 | |
| 10075 | $5.99 | **Weekly стандарт** |
| 10088 | $6.99 | |
| 10102 | $8.99 | |
| 10115 | $9.99 | |
| 10129 | $10.99 | |
| 10142 | $12.99 | **Yearly база (мир)** |
| 10152 | $14.99 | |
| 10162 | $16.99 | |
| 10177 | $19.99 | **Yearly USA** |
| 10192 | $24.99 | |
| 10207 | $29.99 | |
| 10222 | $34.99 | |
| 10237 | $39.99 | |

**Как проверить точный уровень:**
```bash
# После создания подписки — запросить доступные price points для USA:
GET /v1/subscriptions/{sub_id}/pricePoints?filter[territory]=USA
# Вернёт все уровни с customerPrice — найти нужный
```

---

## Скриншот для ревью

- Путь: `~/Desktop/vibecode/app-builder/subscription-review-screenshot.png`
- **Один и тот же скриншот** для ВСЕХ приложений и ВСЕХ подписок
- Загружается 3-step: `POST reserve → PUT binary → PATCH commit`
- Обязателен для каждой подписки (Apple требует)

---

## Подключение к билду (после скрипта)

> Это единственный ручной шаг — в ASC UI.

1. Загрузить билд через Xcode Organizer
2. ASC UI → выбрать приложение → **Monetization**
3. **Subscriptions** → найти созданную группу → **Add to Build**
4. Выбрать новый билд → Save
5. Submit for Review → подписки и билд уходят на ревью вместе

**Что это значит в Xcode Organizer:**
```
Product → Archive → Distribute App → App Store Connect → Upload
```
После загрузки ~ 10–15 минут обработки, потом билд появится в ASC.

---

## Подключение к PaywallView (автоматически)

Product IDs в `PaywallView.swift` и `SubscriptionService.swift` должны совпадать с созданными:

```swift
// SubscriptionService.swift — проверить product IDs:
private let productIds: Set<String> = [
    "com.britetodo.antique.weekly",    // ← совпадает с CONFIG["weekly_product_id"]
    "com.britetodo.antique.yearly"     // ← совпадает с CONFIG["yearly_product_id"]
]

// PaywallView.swift — проверить:
private var weeklyProduct: Product? {
    subscriptionService.products.first { $0.id == "com.britetodo.antique.weekly" }
}
private var yearlyProduct: Product? {
    subscriptionService.products.first { $0.id == "com.britetodo.antique.yearly" }
}

// Проверить selectedPlanId default:
@State private var selectedPlanId = "com.britetodo.antique.yearly"  // yearly по умолчанию
```

---

## Тест подписок локально (без реальных денег)

1. Создать `Configuration.storekit` в Xcode:
   - File → New → StoreKit Configuration File
   - Add Subscription Group → Add Product
   - Product ID: `com.britetodo.{app_key}.weekly` / `.yearly`
   - Price: $5.99 / $19.99

2. Запустить приложение с StoreKit configuration:
   - Edit Scheme → Run → Options → StoreKit Configuration → выбрать файл

3. В симуляторе покупки работают без реальных денег.

---

## Часто встречаемые ошибки

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `500 Internal Server Error` при POST /subscriptionPrices | Не создана availability | Шаг 6 должен быть ДО шага 7 |
| `422 Unprocessable Entity` productId | productId уже существует или был удалён | Использовать другой product ID |
| `401 Unauthorized` | Просроченный JWT токен | get_token() вызывается автоматически |
| `429 Too Many Requests` | Rate limit | Скрипт делает retry через 5 сек автоматически |
| Цены не установились для USA | yearly_usa_price_level не применился | Проверить логи "Overriding Yearly USA price" |

---

## Роль в общем pipeline

```
R0: Документация + иконка
R1: Приложение без монетизации → App Store → Одобрено
R2:
  ├── /paywall           → PaywallView + SubscriptionService + FeatureGate
  ├── subscription_creator.py  ← ЭТОТ СКРИПТ
  │   └── подписки созданы в ASC
  ├── Xcode Organizer    → загрузить билд
  ├── ASC: Add to Build  → подключить подписки к билду
  ├── In-App Event       → создать для Fast Track модерации
  └── Submit for Review  → подписки + билд + ивент вместе
```

---

## ASC API реквизиты (Brite Technologies)

```
KEY_PATH:  ~/.appstoreconnect/private_keys/AuthKey_C37442BRFH.p8
KEY_ID:    C37442BRFH
ISSUER_ID: f7dc851a-bdcb-47d6-b5c7-857f48cadb17
TEAM_ID:   5487HDH2B9
```
