# Интеграция PaywallBuilderAgent с App Builder Pipeline

---

## Место в pipeline

App Builder использует трёхэтапный релиз:

```
R0: Документация + иконка + онбординг (никакого кода)
R1: Приложение БЕЗ монетизации, БЕЗ Firebase → App Store Review → Одобрение
R2: /paywall + Firebase + локализация + In-App Event → App Store Update
```

> **PaywallBuilderAgent запускается в самом начале R2, ПОСЛЕ того как R1 одобрен Apple.**

---

## R1 — жёсткие ограничения (PaywallBuilderAgent НЕ нарушает их)

> Агент не трогает R1 код. Но должен понимать, что там НЕТ:

```
⛔ Нет PaywallView, SubscriptionService, FeatureGate
⛔ Нет Firebase — ни GoogleService-Info.plist, ни FirebaseApp.configure()
⛔ Нет TARGETED_DEVICE_FAMILY "1,2" — только "1" (iPhone only)
⛔ Нет лимитов, кнопок "Upgrade", "Go Premium", упоминаний цен
```

Причина: Apple часто отклоняет приложения с нерабочими подписками при первом ревью.

---

## R2 — что делает PaywallBuilderAgent

### Шаги в правильном порядке:

1. **`/paywall`** → создать PaywallView + SubscriptionService + FeatureGate + PremiumBannerView
2. **Firebase** → добавить в `project.yml`, добавить `GoogleService-Info.plist`
3. **Remote Config** → добавить ключ `{APP_KEY}_close_button_delay` в Firebase Console
4. **Подписки ASC** → создать группу + weekly + yearly через API или вручную
5. **In-App Event** → создать и отправить одновременно с R2 (без него — медленная модерация)
6. **Локализации** → 22 языка (отдельный этап)
7. **iPad** → `TARGETED_DEVICE_FAMILY: "1,2"` если нужен iPad (отдельный этап)

---

## Firebase в project.yml (точный формат)

```yaml
name: AppName
options:
  bundleIdPrefix: com.britetodo
  deploymentTarget:
    iOS: "17.0"
  xcodeVersion: "16.0"
  generateEmptyDirectories: true

packages:
  firebase-ios-sdk:
    url: https://github.com/firebase/firebase-ios-sdk
    version: 11.6.0          # ← точная версия, не "from:"

settings:
  MARKETING_VERSION: "1.0.0"
  CURRENT_PROJECT_VERSION: "1"
  SWIFT_VERSION: "5.9"
  DEVELOPMENT_TEAM: 5487HDH2B9
  CODE_SIGN_STYLE: Automatic

targets:
  AppName:
    type: application
    platform: iOS
    sources:
      - AppName
    dependencies:
      - package: firebase-ios-sdk
        product: FirebaseAnalytics
      - package: firebase-ios-sdk
        product: FirebaseRemoteConfig
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: com.britetodo.appname
        GENERATE_INFOPLIST_FILE: true
        INFOPLIST_KEY_UIApplicationSceneManifest_Generation: true
        INFOPLIST_KEY_UILaunchScreen_Generation: true
        INFOPLIST_KEY_UISupportedInterfaceOrientations_iPhone: "UIInterfaceOrientationPortrait"
        INFOPLIST_KEY_UISupportedInterfaceOrientations: "UIInterfaceOrientationPortrait UIInterfaceOrientationPortraitUpsideDown UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight"
        INFOPLIST_KEY_CFBundleDisplayName: "App Display Name"
        ASSETCATALOG_COMPILER_APPICON_NAME: AppIcon
        TARGETED_DEVICE_FAMILY: "1"   # R2: "1,2" если нужен iPad
```

После изменения project.yml:
```bash
cd {APP_FOLDER}
xcodegen generate
```

---

## GoogleService-Info.plist

- Файл выдаётся в Firebase Console при добавлении iOS-приложения
- Добавить в `{APP_FOLDER}/{APP_SCHEME}/GoogleService-Info.plist`
- **Добавить в `.gitignore`** (там уже должно быть из R0):

```gitignore
.DS_Store
build/
*.xcuserdata
DerivedData/
*.ipa
GoogleService-Info.plist     ← этот файл не коммитить
```

---

## App.swift — Firebase инициализация (R2)

```swift
import FirebaseCore
import FirebaseRemoteConfig

@main
struct {APP_SCHEME}App: App {
    init() {
        FirebaseApp.configure()    // ← только в R2!

        // Предзагрузка Remote Config
        let remoteConfig = RemoteConfig.remoteConfig()
        remoteConfig.setDefaults(["{APP_KEY}_close_button_delay": 5.0 as NSNumber])
        remoteConfig.fetch(withExpirationDuration: 3600) { _, _ in
            remoteConfig.activate { _, _ in }
        }

        // Предзагрузка StoreKit продуктов
        Task {
            await SubscriptionService.shared.initialize()
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(SubscriptionService.shared)
        }
        .modelContainer(for: [...])  // существующие SwiftData модели
    }
}
```

---

## Remote Config — настройка в Firebase Console

1. Firebase Console → Remote Config → Создать параметр
2. **Ключ**: `{APP_KEY}_close_button_delay`
3. **Тип данных**: Number
4. **Значение по умолчанию**: `5`
5. Опубликовать

| Значение | Поведение |
|---------|-----------|
| `0` | Крестик сразу |
| `5` | Через 5 секунд *(дефолт)* |
| `10` | Через 10 секунд (агрессивно) |
| `-1` | Никогда (хардпейвол) |

---

## In-App Event для R2 (ОБЯЗАТЕЛЬНО)

> ⚡ **R2 нельзя отправлять без In-App Event.**
> Без него версия попадёт в общую очередь — ожидание 3–7 дней.
> С ивентом Apple берёт в работу первым — 24–48 часов.

### Параметры ивента для R2:

| Поле | Значение |
|------|---------|
| Badge | `MAJOR_UPDATE` |
| Purpose | `ATTRACT_NEW_USERS` |
| Priority | `HIGH` |
| Start time | **через 2–3 часа** после сабмита |
| Duration | **4 дня** |

### Тексты (en-US):
- **name** (≤30): `Premium Features Unlocked`
- **shortDescription** (≤50): `New: subscriptions and advanced tools`
- **longDescription** (≤120): `Unlock the full power of {APP_DISPLAY_NAME} with our Premium subscription. New features added.`

### Изображения:
- Card: 1920×1080 (landscape)
- Detail: 1080×1920 (portrait)
- **Без текста на изображении** — Apple наложит сам
- RGB PNG, без альфа-канала
- Генерировать через CPPFlow/GPT

### Процесс:
1. Создать In-App Event в ASC UI
2. Заполнить тексты на всех 22 локалях
3. Загрузить изображения
4. Отправить на ревью **одновременно** с подачей версии R2

---

## Подписки в ASC (R2)

### Создать через ASC UI или API:

**Группа подписок:**
- Название: `{APP_DISPLAY_NAME} Premium`
- Тип: Auto-Renewable Subscription

**Yearly (основной продукт):**
| Поле | Значение |
|------|---------|
| Product ID | `{BUNDLE_ID}.yearly` |
| Reference name | Yearly |
| Price tier | 8 (~$39.99) |
| Trial | Free Trial 3 дня |

**Weekly (быстрый вход):**
| Поле | Значение |
|------|---------|
| Product ID | `{BUNDLE_ID}.weekly` |
| Reference name | Weekly |
| Price tier | 5 (~$4.99) |
| Trial | Нет |

> ⚠️ Подписки должны быть в статусе **Ready to Submit** до загрузки билда.
> После загрузки билда: **Subscriptions → Add to Build** в ASC UI.

---

## Что читает агент из App Builder документации

### Из CLAUDE.md:
```yaml
bundle_id: com.britetodo.{suffix}
app_key: {suffix}
app_display_name: {name}
accent_hex: "#RRGGBB"
weekly_product_id: com.britetodo.{suffix}.weekly
yearly_product_id: com.britetodo.{suffix}.yearly
target_folder: ~/{repo}/{scheme}/
```

### Из docs/APP-SPEC.yaml:
```yaml
analytics:
  provider: "firebase"
  remote_config: true

premium:
  unlimited_items: true
  export_pdf: true
  cloud_sync: true
  # → эти фичи идут в FeatureGate + PaywallView features section
```

### Из docs/COMPETITOR-ANALYSIS.md:
- Боли пользователей → тексты отзывов в PaywallView reviews carousel
- Язык пользователей → заголовки в PaywallView ("Stay Consistent. See Results.")

---

## Ключи и доступы (Brite Technologies)

### App Store Connect API
| Параметр | Значение |
|---------|---------|
| KEY_ID | `C37442BRFH` |
| ISSUER_ID | `f7dc851a-bdcb-47d6-b5c7-857f48cadb17` |
| KEY_PATH | `~/.appstoreconnect/private_keys/AuthKey_C37442BRFH.p8` |
| TEAM_ID | `5487HDH2B9` |

---

## Product IDs — конвенция именования

```
com.britetodo.{app_key}.weekly    → недельная подписка
com.britetodo.{app_key}.yearly    → годовая подписка

# Если нужен Super Pro (отдельная группа):
com.britetodo.{app_key}.super_pro_yearly_v2
```

---

## Структура папок (стандарт App Builder)

```
~/{APP_REPO}/
├── CLAUDE.md                    ← агент читает первым
├── PROJECT_SUMMARY.md
├── docs/
│   ├── APP-SPEC.yaml            ← analytics.provider + premium features
│   ├── COMPETITOR-ANALYSIS.md  ← боли → отзывы в paywall
│   └── ASO.md
├── project.yml                  ← добавить Firebase packages + deps
├── GoogleService-Info.plist     ← добавить в R2 (в .gitignore!)
├── {APP_SCHEME}.xcodeproj/
└── {APP_SCHEME}/
    ├── {APP_SCHEME}App.swift    ← добавить FirebaseApp.configure()
    ├── ContentView.swift
    ├── OnboardingView.swift     ← добавить paywall в конце
    ├── Theme.swift              ← читать accent цвет
    ├── PaywallView.swift        ← создать (агент)
    ├── SubscriptionService.swift ← создать (агент)
    ├── FeatureGate.swift        ← создать (агент)
    └── PremiumBannerView.swift  ← создать (агент)
```

---

## Сборка после интеграции

```bash
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer

# Проверка компиляции:
xcodebuild \
  -project {APP_FOLDER}/{APP_SCHEME}.xcodeproj \
  -scheme {APP_SCHEME} \
  -sdk iphonesimulator \
  -destination 'platform=iOS Simulator,name=iPhone 16 Pro' \
  build 2>&1 | grep -E "error:|Build succeeded|Build FAILED"

# Архив (через Xcode GUI — CLI signing не работает!):
# open {APP_FOLDER}/{APP_SCHEME}.xcodeproj
# Product → Archive → Distribute App → App Store Connect → Upload
```

---

## Полный чеклист R2

### Код:
- [ ] `PaywallView.swift` создан
- [ ] `SubscriptionService.swift` создан
- [ ] `FeatureGate.swift` создан (лимит согласован с пользователем)
- [ ] `PremiumBannerView.swift` создан
- [ ] `OnboardingView.swift` — пейвол показывается в конце ✓
- [ ] `*App.swift` — `FirebaseApp.configure()` добавлен ✓
- [ ] `*App.swift` — Remote Config preload добавлен ✓
- [ ] `*App.swift` — `SubscriptionService.shared.initialize()` добавлен ✓
- [ ] Все основные View — FeatureGate блокировки добавлены ✓
- [ ] `project.yml` — Firebase packages добавлены (версия 11.6.0)
- [ ] `xcodegen generate` запущен после изменения project.yml
- [ ] Build succeeded на симуляторе ✓

### Firebase:
- [ ] `GoogleService-Info.plist` добавлен в target (в .gitignore)
- [ ] Remote Config параметр `{APP_KEY}_close_button_delay` создан (Number, default: 5)
- [ ] Remote Config опубликован

### App Store Connect:
- [ ] Группа подписок создана: `{APP_DISPLAY_NAME} Premium`
- [ ] `{BUNDLE_ID}.yearly` создан (Tier 8, 3-day trial)
- [ ] `{BUNDLE_ID}.weekly` создан (Tier 5, no trial)
- [ ] Подписки в статусе Ready to Submit
- [ ] Билд загружен через Xcode Organizer
- [ ] Subscriptions → Add to Build ✓

### In-App Event (до сабмита):
- [ ] Создан в ASC UI
- [ ] Тексты на en-US заполнены
- [ ] Тексты локализованы (22 локали)
- [ ] Изображения загружены (1920×1080 + 1080×1920)
- [ ] Badge: MAJOR_UPDATE, Priority: HIGH
- [ ] Start через 2–3 часа после сабмита

### Финал:
- [ ] In-App Event отправлен на ревью
- [ ] R2 версия отправлена на ревью (одновременно с ивентом)
