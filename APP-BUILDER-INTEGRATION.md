# Интеграция PaywallBuilderAgent с App Builder Pipeline

---

## Место в pipeline

App Builder использует двухэтапный релиз:

```
R0: Документация + иконка + онбординг
R1: Приложение БЕЗ монетизации → App Store Review
R2: Монетизация → /paywall → App Store Update
```

**PaywallBuilderAgent запускается в начале R2.**

---

## Порядок R2

```
1. /paywall — интеграция монетизации (этот агент)
2. Создать подписки в App Store Connect
3. Настроить Remote Config в Firebase Console
4. Сборка и тестирование на симуляторе
5. Архив + загрузка через Xcode Organizer
6. Подача на ревью App Store
```

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
features:
  free:
    - feature 1 (для FeatureGate)
  premium:
    - feature 2 (для PaywallView features section)
    - feature 3
    - feature 4
```

### Из docs/COMPETITOR-ANALYSIS.md:
- Боли пользователей → тексты отзывов в PaywallView
- Язык пользователей → тексты features и timeline

### Из Theme.swift / AppTheme.swift:
```swift
// Агент берёт accent цвет и адаптирует под него PaywallView
static let accent = Color(red: R, green: G, blue: B)
```

---

## Структура папок приложения (стандарт App Builder)

```
~/{APP_REPO}/
├── CLAUDE.md                    ← агент читает в первую очередь
├── PROJECT_SUMMARY.md
├── docs/
│   ├── APP-SPEC.yaml
│   ├── COMPETITOR-ANALYSIS.md
│   └── ASO.md
├── {APP_SCHEME}.xcodeproj/
├── {APP_SCHEME}/
│   ├── {APP_SCHEME}App.swift    ← @main, добавить Firebase init
│   ├── ContentView.swift
│   ├── OnboardingView.swift     ← добавить paywall в конце
│   ├── Theme.swift              ← читать accent цвет
│   ├── PaywallView.swift        ← создать
│   ├── SubscriptionService.swift ← создать
│   ├── FeatureGate.swift        ← создать
│   └── PremiumBannerView.swift  ← создать
└── project.yml                  ← добавить Firebase если нет
```

---

## Ключи и доступы (Brite Technologies)

### App Store Connect API
| Параметр | Значение |
|---------|---------|
| KEY_ID | `C37442BRFH` |
| ISSUER_ID | `f7dc851a-bdcb-47d6-b5c7-857f48cadb17` |
| KEY_PATH | `~/.appstoreconnect/private_keys/AuthKey_C37442BRFH.p8` |
| TEAM_ID | `5487HDH2B9` |

### Firebase
- Проект создаётся отдельно для каждого приложения
- `GoogleService-Info.plist` добавляется в target
- Remote Config ключ: `{APP_KEY}_close_button_delay`

---

## Product IDs — конвенция именования

```
com.britetodo.{app_key}.weekly   → недельная подписка
com.britetodo.{app_key}.yearly   → годовая подписка

# Дополнительно (если Super Pro):
com.britetodo.{app_key}.super_pro_yearly_v2
```

**Примеры:**
- `com.britetodo.antique.weekly`
- `com.britetodo.antique.yearly`
- `com.britetodo.glptracker.weekly` (для GLP-1 Tracker использовался другой bundle: `com.kovneier.glptracker`)

---

## Сборка после интеграции

```bash
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer

# Симулятор (проверка компиляции):
xcodebuild \
  -project ~/{APP_REPO}/{APP_SCHEME}.xcodeproj \
  -scheme {APP_SCHEME} \
  -sdk iphonesimulator \
  -destination 'platform=iOS Simulator,name=iPhone 16 Pro' \
  build 2>&1 | grep -E "error:|Build succeeded|Build FAILED"

# Архив для App Store:
xcodebuild archive \
  -project ~/{APP_REPO}/{APP_SCHEME}.xcodeproj \
  -scheme {APP_SCHEME} \
  -archivePath /tmp/{APP_KEY}.xcarchive \
  CODE_SIGN_STYLE=Automatic \
  DEVELOPMENT_TEAM=5487HDH2B9

# Загрузка — через Xcode Organizer (рекомендуется):
open /tmp/{APP_KEY}.xcarchive
# Distribute App → App Store Connect → Upload
```

---

## После интеграции: чеклист

### App Store Connect:
- [ ] Создать группу подписок `{APP_DISPLAY_NAME} Premium`
- [ ] Добавить `{BUNDLE_ID}.yearly` (Tier 8, 3-day trial)
- [ ] Добавить `{BUNDLE_ID}.weekly` (Tier 5, no trial)
- [ ] Подписки активны (не в Draft)

### Firebase Console:
- [ ] Создать Remote Config параметр `{APP_KEY}_close_button_delay`
- [ ] Тип: Number, значение по умолчанию: `5`
- [ ] Опубликовать изменения

### Код:
- [ ] `GoogleService-Info.plist` добавлен в target
- [ ] `PaywallView.swift` создан
- [ ] `SubscriptionService.swift` создан
- [ ] `FeatureGate.swift` создан
- [ ] `PremiumBannerView.swift` создан
- [ ] `OnboardingView.swift` — пейвол в конце ✓
- [ ] `*App.swift` — Firebase init + Remote Config preload ✓
- [ ] Все основные View — FeatureGate блокировки ✓
- [ ] Build succeeded на симуляторе ✓
