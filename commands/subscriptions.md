# /subscriptions — Создание подписок в App Store Connect

Создаёт Weekly + Yearly подписки через ASC API и привязывает их к уже существующему PaywallView.
~530 API calls, ~5 минут, 0 ручных шагов в ASC UI.

---

## РЕЖИМ РАБОТЫ

Максимальная автономия. Единственная остановка:
- Один вопрос в начале (App ID из ASC)

После ответа — запустить скрипт и не останавливаться до финального отчёта.

---

## ШАГ 1 — ЧИТАТЬ КОНТЕКСТ ПРИЛОЖЕНИЯ

Найти папку приложения — проверить текущую директорию и ~/

```bash
ls *.xcodeproj 2>/dev/null || ls ~/ | grep -E "snap|track|planner|timer|note|app" | head -20
```

Прочитать обязательно (если существуют):
- `CLAUDE.md` — bundle_id, app_key, product IDs
- `*/SubscriptionService.swift` — текущие product IDs в коде
- `*/PaywallView.swift` — selectedPlanId, weeklyProduct, yearlyProduct

Определить переменные:
| Переменная | Откуда брать |
|-----------|-------------|
| `BUNDLE_ID` | CLAUDE.md → bundle_id |
| `APP_KEY` | CLAUDE.md → app_key |
| `APP_DISPLAY_NAME` | CLAUDE.md → app_display_name |
| `APP_FOLDER` | путь к папке с .xcodeproj |
| `TARGET_FOLDER` | папка с .swift файлами |
| `WEEKLY_PRODUCT_ID` | из SubscriptionService.swift или `{BUNDLE_ID}.weekly` |
| `YEARLY_PRODUCT_ID` | из SubscriptionService.swift или `{BUNDLE_ID}.yearly` |

---

## ШАГ 2 — ОДИН ВОПРОС (AskUserQuestion)

Спросить одним вызовом:

**Вопрос 1**: Числовой App ID из App Store Connect?
- Найти: ASC → Apps → выбрать приложение → URL `/id{числа}` или App Information → Apple ID
- Примеры: "6738893683", "6755043591"

Сразу после ответа — начать выполнение без дополнительных вопросов.

---

## ШАГ 3 — ЗАПУСТИТЬ СКРИПТ СОЗДАНИЯ ПОДПИСОК

Сгенерировать и запустить Python-скрипт прямо из Claude Code:

```python
# Создать /tmp/create_subs_{APP_KEY}.py со следующим содержимым:

import jwt, time, requests, json, os, hashlib, base64

CONFIG = {
    "issuer_id":  "f7dc851a-bdcb-47d6-b5c7-857f48cadb17",
    "key_id":     "C37442BRFH",
    "key_path":   os.path.expanduser("~/.appstoreconnect/private_keys/AuthKey_C37442BRFH.p8"),

    "app_id":           "{APP_ID}",             # ← из вопроса
    "group_name":       "{APP_DISPLAY_NAME} Premium",
    "app_display_name": "{APP_DISPLAY_NAME}",
    "weekly_product_id":  "{WEEKLY_PRODUCT_ID}",
    "yearly_product_id":  "{YEARLY_PRODUCT_ID}",

    "weekly_price_level":      "10075",   # $5.99/week
    "yearly_base_price_level": "10142",   # $12.99/year (мир)
    "yearly_usa_price_level":  "10177",   # $19.99/year (USA)
    "trial_duration":          "THREE_DAYS",

    "screenshot_path": os.path.expanduser(
        "~/Desktop/vibecode/app-builder/subscription-review-screenshot.png"
    ),
}
```

Полный рабочий код скрипта — в `~/PaywallBuilderAgent/subscription_creator.py`.
Скопировать его содержимое, подставить CONFIG и запустить:

```bash
cp ~/PaywallBuilderAgent/subscription_creator.py /tmp/create_subs_{APP_KEY}.py
# Заменить CONFIG в файле нужными значениями, затем:
python3 /tmp/create_subs_{APP_KEY}.py
```

### Ожидаемый вывод скрипта:
```
✅ Config OK
Step 1/11: Creating subscription group...
  Group created: {GROUP_ID}
Step 2/11: Localizing group (en-US)... OK
Step 3/11: Creating subscriptions...
  Weekly: {WEEKLY_ID}
  Yearly: {YEARLY_ID}
...
Step 10/11: Verifying...
  Weekly: state=READY_TO_SUBMIT, prices=175/175
  Yearly: state=READY_TO_SUBMIT, prices=175/175
```

Если ошибка — смотреть раздел "Частые ошибки" ниже и чинить.

---

## ШАГ 4 — ПРОВЕРИТЬ PRODUCT IDs В PaywallView.swift

После создания подписок — проверить что PaywallView.swift и SubscriptionService.swift
используют **ровно те же** product IDs что были переданы в скрипт.

Найти файлы:
```bash
find {APP_FOLDER} -name "SubscriptionService.swift" -o -name "PaywallView.swift"
```

Прочитать и проверить:

**В SubscriptionService.swift должно быть:**
```swift
private let productIds: Set<String> = [
    "{WEEKLY_PRODUCT_ID}",
    "{YEARLY_PRODUCT_ID}"
]

var weeklyProduct: Product? {
    products.first { $0.id == "{WEEKLY_PRODUCT_ID}" }
}
var yearlyProduct: Product? {
    products.first { $0.id == "{YEARLY_PRODUCT_ID}" }
}
```

**В PaywallView.swift должно быть:**
```swift
@State private var selectedPlanId = "{YEARLY_PRODUCT_ID}"  // yearly по умолчанию!

private var weeklyProduct: Product? {
    subscriptionService.products.first { $0.id == "{WEEKLY_PRODUCT_ID}" }
}
private var yearlyProduct: Product? {
    subscriptionService.products.first { $0.id == "{YEARLY_PRODUCT_ID}" }
}

// CTA кнопка:
Text(selectedPlanId == "{YEARLY_PRODUCT_ID}" ? "Start Free Trial" : "Subscribe")

// "No payment now":
if selectedPlanId == "{YEARLY_PRODUCT_ID}" { ... }

// Картинка триала:
planCard(..., subtitle: "3-day free trial", planId: "{YEARLY_PRODUCT_ID}")
```

Если что-то не совпадает — исправить в файлах через Edit.

---

## ШАГ 5 — ПРОВЕРИТЬ StoreKit CONFIGURATION (для тестов)

Найти `Configuration.storekit` в проекте:
```bash
find {APP_FOLDER} -name "*.storekit"
```

Если файл есть — проверить что product IDs там совпадают.
Если файла нет — создать `/tmp/{APP_KEY}.storekit` для справки:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>identifier</key>
    <string>{GROUP_ID}</string>
    <key>nonRenewingSubscriptions</key>
    <array/>
    <key>products</key>
    <array/>
    <key>settings</key>
    <dict>
        <key>_storeKitErrors</key>
        <array/>
    </dict>
    <key>subscriptionGroups</key>
    <array>
        <dict>
            <key>id</key>
            <string>{GROUP_ID}</string>
            <key>localizations</key>
            <array>
                <dict>
                    <key>customAppName</key>
                    <string>{APP_DISPLAY_NAME}</string>
                    <key>locale</key>
                    <string>en_US</string>
                    <key>name</key>
                    <string>Premium</string>
                </dict>
            </array>
            <key>subscriptions</key>
            <array>
                <dict>
                    <key>adHocOffers</key>
                    <array/>
                    <key>displayPrice</key>
                    <string>5.99</string>
                    <key>familyShareable</key>
                    <false/>
                    <key>groupNumber</key>
                    <integer>2</integer>
                    <key>internalID</key>
                    <string>{WEEKLY_ID}</string>
                    <key>introductoryOffer</key>
                    <dict/>
                    <key>localizations</key>
                    <array>
                        <dict>
                            <key>description</key>
                            <string>All features unlocked for a week</string>
                            <key>displayName</key>
                            <string>Weekly</string>
                            <key>locale</key>
                            <string>en_US</string>
                        </dict>
                    </array>
                    <key>productID</key>
                    <string>{WEEKLY_PRODUCT_ID}</string>
                    <key>recurringSubscriptionPeriod</key>
                    <string>P1W</string>
                    <key>referenceName</key>
                    <string>Weekly</string>
                    <key>type</key>
                    <string>RecurringSubscription</string>
                </dict>
                <dict>
                    <key>adHocOffers</key>
                    <array/>
                    <key>displayPrice</key>
                    <string>19.99</string>
                    <key>familyShareable</key>
                    <false/>
                    <key>groupNumber</key>
                    <integer>1</integer>
                    <key>internalID</key>
                    <string>{YEARLY_ID}</string>
                    <key>introductoryOffer</key>
                    <dict>
                        <key>duration</key>
                        <string>P3D</string>
                        <key>mode</key>
                        <string>freeTrial</string>
                        <key>offerID</key>
                        <string></string>
                        <key>type</key>
                        <string>introductory</string>
                    </dict>
                    <key>localizations</key>
                    <array>
                        <dict>
                            <key>description</key>
                            <string>All features unlocked for a year</string>
                            <key>displayName</key>
                            <string>Yearly</string>
                            <key>locale</key>
                            <string>en_US</string>
                        </dict>
                    </array>
                    <key>productID</key>
                    <string>{YEARLY_PRODUCT_ID}</string>
                    <key>recurringSubscriptionPeriod</key>
                    <string>P1Y</string>
                    <key>referenceName</key>
                    <string>Yearly</string>
                    <key>type</key>
                    <string>RecurringSubscription</string>
                </dict>
            </array>
        </dict>
    </array>
    <key>version</key>
    <dict>
        <key>major</key>
        <integer>2</integer>
        <key>minor</key>
        <integer>0</integer>
    </dict>
</dict>
</plist>
```

---

## ШАГ 6 — ФИНАЛЬНЫЙ ОТЧЁТ

```
✅ Подписки созданы в App Store Connect

Приложение: {APP_DISPLAY_NAME} (App ID: {APP_ID})

Группа:  {GROUP_NAME} (ID: {GROUP_ID})
Weekly:  {WEEKLY_PRODUCT_ID}  →  $5.99/week
Yearly:  {YEARLY_PRODUCT_ID}  →  $19.99/year (USA) / $12.99 (мир)
         3-day free trial ✓

Цены: 175 территорий ✓
Скриншот для ревью: загружен ✓
Статус: READY_TO_SUBMIT ✓

PaywallView.swift: product IDs проверены ✓
SubscriptionService.swift: product IDs проверены ✓

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
СЛЕДУЮЩИЙ ШАГ (единственный ручной):

1. Загрузить билд: Xcode → Product → Archive
                           → Distribute App → App Store Connect → Upload

2. Когда билд появится в ASC (10–15 мин):
   ASC → {APP_DISPLAY_NAME} → Monetization → Subscriptions
   → "{GROUP_NAME}" → Add to Build → выбрать загруженный билд → Save

3. Submit for Review — билд + подписки уходят вместе
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## ЧАСТЫЕ ОШИБКИ

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `500` на subscriptionPrices | availability не создана до цен | Это BUG в скрипте — порядок шагов 6 перед 7 обязателен |
| `422` productId already exists | product ID уже существует в ASC | Использовать другой suffix или удалить существующий |
| `401 Unauthorized` | проблема с ключом | Проверить путь к .p8 файлу |
| `429 Too Many Requests` | rate limit | Скрипт делает retry автоматически |
| Скрипт падает на Шаге 7 с 500 | не выполнен Шаг 6 | Запустить заново с исправленным порядком |
| `No such file: subscription-review-screenshot.png` | нет скриншота | Проверить путь `~/Desktop/vibecode/app-builder/` |
| PaywallView показывает "..." вместо цены | product IDs не совпадают | Исправить IDs в SubscriptionService.swift |

---

## КРИТИЧЕСКИЕ ПРАВИЛА (из App Builder документации)

1. **`subscriptionAvailabilities` СТРОГО до `subscriptionPrices`** — иначе 500 на каждом запросе
2. **territory = to-one** в introductoryOffers — 175 отдельных вызовов, не массив
3. **subscriptionGroupSubmissions не работает отдельно** — только вместе с билдом
4. **productId необратим** — нельзя переиспользовать после удаления
5. **Yearly по умолчанию выбран** в PaywallView (selectedPlanId = yearly)
6. **"No payment now"** показывается только при выбранном yearly
7. **Один скриншот для всех** — `subscription-review-screenshot.png` из app-builder
