# /inappevent — In-App Event Maker для App Store Connect

Создаёт In-App Event, генерирует картинки через GPT, загружает в ASC.
Цель: Fast Track модерация — билд рассматривают за 24-48 часов вместо 3-7 дней.

**Механика:** Ивент стартует через 3 часа после сабмита. Apple видит дедлайн → берёт в работу первым.
**Ивент и билд отправляются ОДНОВРЕМЕННО** — это критично.

---

## РЕЖИМ РАБОТЫ

Максимальная автономия. Единственная остановка:
- Один вопрос в начале (App ID + что обновилось)

После ответа — всё делать самостоятельно до финального отчёта.

---

## ШАГ 1 — ЧИТАТЬ КОНТЕКСТ ПРИЛОЖЕНИЯ

Прочитать (если существуют):
- `CLAUDE.md` — bundle_id, app_display_name, ниша приложения
- `docs/APP-SPEC.yaml` — фичи приложения, что делает продукт
- `docs/COMPETITOR-ANALYSIS.md` — язык пользователей, их боли
- Git log последних коммитов — что реально изменилось в этой версии:

```bash
git log --oneline -10
```

Определить:
| Переменная | Откуда |
|-----------|--------|
| `APP_ID` | спросить у пользователя |
| `APP_DISPLAY_NAME` | CLAUDE.md |
| `APP_KEY` | CLAUDE.md |
| `APP_NICHE` | APP-SPEC.yaml — суть приложения одной фразой |
| `BUNDLE_ID` | CLAUDE.md |
| `VERSION` | git log или PROJECT_SUMMARY.md |

---

## ШАГ 2 — ОДИН ВОПРОС (AskUserQuestion)

Задать одним вызовом AskUserQuestion:

**Вопрос 1**: Числовой App ID из ASC? (напр. "6738893683")

**Вопрос 2**: Что главное изменилось в этой версии для пользователей?
- Не про подписки и премиум — про реальную пользу
- Примеры: "добавили офлайн режим", "ускорили сканирование", "новые фильтры поиска"
- Если нет идей — напиши "автоматически" и агент сам придумает по git log

После ответа — генерировать тексты и запускать скрипт без остановок.

---

## ШАГ 3 — ПРИДУМАТЬ ТЕМУ И ТЕКСТЫ ИВЕНТА

> ❌ НЕ про подписки, НЕ про премиум, НЕ "Major Update"
> ✅ Про ценность для пользователя, связанную с нишей приложения

### Принцип выбора темы:
- Взять главное обновление из ответа пользователя (или из git log)
- Сформулировать как выгоду для пользователя, а не как фичу
- Использовать язык из COMPETITOR-ANALYSIS.md (как говорят реальные пользователи)

### Примеры тем по нишам:

| Ниша | Плохо (про фичу) | Хорошо (про пользу) |
|------|-----------------|---------------------|
| Трекер здоровья | "New charts added" | "See your progress at a glance" |
| Сканер антиквариата | "Improved AI accuracy" | "Get faster, sharper valuations" |
| Прогноз погоды | "Offline mode" | "Check forecasts anywhere, anytime" |
| Планировщик | "New templates" | "Start your week in seconds" |
| Авиация | "Updated turbulence data" | "Know turbulence before you fly" |

### Лимиты текстов:
- `name` ≤ 30 символов
- `shortDescription` ≤ 50 символов
- `longDescription` ≤ 120 символов

### Сгенерировать тексты (en-US) по шаблону:
```
name:             "{Глагол} + {ценность}" — max 30 chars
shortDescription: "Краткая польза без воды" — max 50 chars
longDescription:  "Расширенная польза + контекст приложения" — max 120 chars
```

---

## ШАГ 4 — ПРИДУМАТЬ ПРОМПТЫ ДЛЯ КАРТИНОК

> Картинки должны передавать атмосферу ниши, НЕ содержать текст.
> Apple сам наложит name/short/long поверх картинки.

### Правила промптов:
- Кинематографичный стиль, высокое качество
- "no text, no letters, no UI elements, no numbers"
- Горизонтальная (card) и вертикальная (detail) — один визуальный стиль
- Эмоционально связан с ценностью ивента

### Примеры по нишам:

**Трекер GLP-1:**
```
Card:   "Person standing on scale looking at results with satisfaction, morning light through window, clean minimal kitchen background, health wellness lifestyle, no text, cinematic"
Detail: "Close-up healthy meal prep on wooden table morning light vegetables and proteins, vertical composition, wellness lifestyle, no text"
```

**Сканер антиквариата:**
```
Card:   "Beautiful vintage porcelain vase on wooden table dramatic studio lighting, professional product photography, warm tones, no text"
Detail: "Collection of antique items coins jewelry watches arranged artistically on dark velvet, vertical composition, dramatic lighting, no text"
```

**Авиация/погода:**
```
Card:   "Wide panoramic view from airplane window showing wing over dramatic cloud layer at golden hour, cinematic aviation photography, no text"
Detail: "Vertical view airplane wing seen from window seat beautiful sunset sky soft orange blue gradient, no text no UI"
```

Адаптировать промпты под нишу текущего приложения из APP-SPEC.yaml.

---

## ШАГ 5 — ЗАПУСТИТЬ СКРИПТ

Скрипт находится: `~/Desktop/vibecode/app-builder/create-inapp-event.py`

Скопировать и запустить с правильным CONFIG:

```bash
cp ~/Desktop/vibecode/app-builder/create-inapp-event.py /tmp/inappevent_{APP_KEY}.py
```

Отредактировать секцию `# ── CONFIGURE THESE ──` в скопированном файле:

```python
APP_ID = "{APP_ID}"
DEEP_LINK = "https://apps.apple.com/app/id{APP_ID}"

REFERENCE_NAME = "{APP_DISPLAY_NAME} v{VERSION} Update"  # internal name
EVENT_NAME = "{сгенерированный name}"       # max 30 chars
SHORT_DESC = "{сгенерированный short}"      # max 50 chars
LONG_DESC  = "{сгенерированный long}"       # max 120 chars

BADGE    = "MAJOR_UPDATE"
PURPOSE  = "ATTRACT_NEW_USERS"
PRIORITY = "HIGH"

START_HOURS  = 3   # часа — создаёт срочность для ревьюера
DURATION_DAYS = 5  # дней

CARD_PROMPT   = "{горизонтальный промпт}"
DETAIL_PROMPT = "{вертикальный промпт}"
```

Запустить:
```bash
python3 /tmp/inappevent_{APP_KEY}.py
```

### Ожидаемый вывод:
```
Step 1: Getting territories...
Step 2: Creating event... Event created: ID={EVENT_ID}
Step 3: Setting localization... Created localization en-US
Step 4: Generating images...
  Generated: https://cppflow.com/assets/...
Step 5: Preparing images (resize + remove alpha)...
Step 6: Uploading images... Uploaded EVENT_CARD: COMPLETE
Step 7: Final status check...
  State: DRAFT   ← нормально, Submit через ASC UI
✅ Event ready!
```

Если ошибка `IMAGE_ALPHA_NOT_ALLOWED` — изображение содержит alpha-канал. Скрипт конвертирует автоматически, но если не сработало — см. раздел ошибок.

---

## ШАГ 6 — ОБНОВИТЬ WHAT'S NEW

Найти What's New / Release Notes в проекте или документации и предложить текст:

```
What's New (en-US, max 4000 chars):

{краткое описание главного обновления для пользователей}
• {фича 1 — польза для пользователя}
• {фича 2 — польза для пользователя}
• {фича 3 — польза для пользователя}
+ Performance improvements and bug fixes
```

> What's New загружается в ASC через API или вручную при создании новой версии.
> Текст должен совпадать по духу с темой ивента.

---

## ШАГ 7 — ФИНАЛЬНЫЙ ОТЧЁТ

```
✅ In-App Event создан

Приложение: {APP_DISPLAY_NAME} (ID: {APP_ID})
Event ID:   {EVENT_ID}

Название:   {EVENT_NAME}
Описание:   {SHORT_DESC}
Start:      через 3 часа → {конкретное время UTC}
End:        {конкретное время UTC} (+5 дней)
Картинки:   EVENT_CARD 1920×1080 ✓ | EVENT_DETAILS_PAGE 1080×1920 ✓
Статус:     DRAFT (готов к сабмиту)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ПОСЛЕДНИЙ ШАГ — сделать ОДНОВРЕМЕННО:

1. ASC UI → {APP_DISPLAY_NAME} → In-App Events
   → выбрать "{REFERENCE_NAME}" → Submit for Review

2. Сразу после (в течение 1-2 минут):
   ASC UI → выбрать версию → Submit for Review
   (или через API: POST /v1/appStoreVersionSubmissions)

⚡ Оба сабмита должны попасть к ревьюеру в одной сессии.
   Разрыв — не более нескольких минут.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

What's New (загрузить в ASC):
{сгенерированный текст What's New}
```

---

## ПАРАМЕТРЫ ИВЕНТА (справка)

| Параметр | Значение | Нельзя менять |
|---------|---------|--------------|
| `badge` | `MAJOR_UPDATE` | Нет, для обновления |
| `purpose` | `ATTRACT_NEW_USERS` | Нет, цель — новые юзеры |
| `priority` | `HIGH` | Нет, максимальный приоритет |
| `purchaseRequirement` | `NO_COST_ASSOCIATED` | Нет, ивент бесплатный |
| Start | текущее время + 3 часа | Нет, именно +3 для срочности |
| Duration | 5 дней | Можно ±1 |

---

## КРИТИЧЕСКИЕ ПРАВИЛА

1. **Никакого текста на картинках** — Apple наложит сам из name/short/long
2. **RGB, не RGBA** — иначе ошибка `IMAGE_ALPHA_NOT_ALLOWED`. Скрипт конвертирует сам
3. **НЕ передавать `sourceFileChecksum`** в commit запросе для appEventScreenshots (ошибка `ENTITY_ERROR.ATTRIBUTE.UNKNOWN`)
4. **Ивент и билд одновременно** — оба сабмита в одной сессии, иначе Fast Track не сработает
5. **Тема — не про премиум** — про реальную ценность для пользователя

---

## ЧАСТЫЕ ОШИБКИ

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `IMAGE_ALPHA_NOT_ALLOWED` | PNG с прозрачностью | Скрипт конвертирует автоматически в RGB |
| `ENTITY_ERROR.ATTRIBUTE.UNKNOWN: sourceFileChecksum` | Лишний атрибут | В appEventScreenshots его нет (только в subscriptionScreenshots) |
| 404 на territories | Старый endpoint | Использовать `/v2/appAvailabilities/{id}/territoryAvailabilities` |
| Картинка не генерируется | CPPFlow недоступен | Использовать прямой OpenAI API (fallback в скрипте) |
| Ивент не видно в App Store | Статус DRAFT | Submit через ASC UI |

---

## СВЯЗАННЫЕ КОМАНДЫ

- `/subscriptions` — создать Weekly + Yearly подписки (запускать до /inappevent)
- `/paywall` — создать PaywallView + SubscriptionService (запускать первым в R2)

### Правильный порядок R2:
```
/paywall → /subscriptions → [загрузить билд] → /inappevent → Submit оба одновременно
```
