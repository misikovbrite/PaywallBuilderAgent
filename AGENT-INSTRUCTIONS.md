# PaywallBuilderAgent — Полные инструкции агента

> Это файл для воспроизведения агента на другом компьютере.
> Содержимое ниже копировать в `~/.claude/skills/paywall.md`

---

## РЕЖИМ РАБОТЫ — ЧИТАТЬ ОБЯЗАТЕЛЬНО

Максимальная автономия. Единственные остановки:
1. Вопросы в начале (один AskUserQuestion)
2. Показ HTML-превью (ждать подтверждения)
3. Запрос Firebase Remote Config ключа (если не указан)

После каждого шага **НЕ спрашивать "продолжать?"** — делать сразу следующий.

---

## ШАГ 1 — ЗАГРУЗКА КОНТЕКСТА ПРИЛОЖЕНИЯ

Найти папку приложения и прочитать:

```bash
ls ~/Desktop/vibecode/ 2>/dev/null
ls ~/ | grep -i "{APP_NAME}" 2>/dev/null
```

Прочитать (если существуют):
- `CLAUDE.md` — архитектура, bundle ID, product IDs
- `PROJECT_SUMMARY.md` — статус, bundle suffix
- `docs/APP-SPEC.yaml` — фичи, ниша
- `docs/COMPETITOR-ANALYSIS.md` — боли, язык пользователей
- `*/Theme.swift` или `*/AppTheme.swift` — акцент цвет (hex)
- `*/ContentView.swift` или `*App.swift` — структура приложения
- `*/OnboardingView.swift` — есть ли онбординг, как завершается

Определить переменные:
| Переменная | Описание |
|-----------|---------|
| `BUNDLE_ID` | `com.britetodo.{suffix}` |
| `APP_KEY` | suffix без пробелов (пр. "antique") |
| `APP_DISPLAY_NAME` | отображаемое имя |
| `ACCENT_HEX` | hex акцентного цвета (#RRGGBB) |
| `ACCENT_LIGHT_HEX` | светлый вариант (осветлить на 20%) |
| `WEEKLY_PRODUCT_ID` | `{BUNDLE_ID}.weekly` |
| `YEARLY_PRODUCT_ID` | `{BUNDLE_ID}.yearly` |
| `APP_FOLDER` | абсолютный путь к папке с .xcodeproj |
| `TARGET_FOLDER` | папка с .swift файлами |
| `REMOTE_CONFIG_KEY` | `{APP_KEY}_close_button_delay` |

---

## ШАГ 2 — ВОПРОСЫ ПОЛЬЗОВАТЕЛЮ (один вызов AskUserQuestion)

Задать ВСЕ вопросы одним вызовом:

- **Вопрос 1**: Какой Firebase Remote Config ключ? (пр. `antique_close_button_delay`)
  → Если нет — использовать `{APP_KEY}_close_button_delay`

- **Вопрос 2**: Ключевые фичи для пейвола?
  → Если не знает — определить из APP-SPEC или структуры приложения

- **Вопрос 3**: Жёсткость монетизации?
  - **Минимально**: 3 бесплатных объекта, потом пейвол
  - **Стандартно**: 1 бесплатный, остальное заблокировано *(рекомендуется)*
  - **Максимально**: всё заблокировано кроме просмотра

После ответов — немедленно начать работу.

---

## ШАГ 3 — ГЕНЕРАЦИЯ PaywallView.swift

Создать `{TARGET_FOLDER}/PaywallView.swift`.

> **Эталон**: `reference/PaywallView.swift` в этом репозитории (GLP-1 Tracker).
> Адаптировать цвета, тексты и product IDs — структуру не менять.

### Структура пейвола (строго соблюдать порядок):

```
1. ZStack: background.ignoresSafeArea()
2. ScrollView:
   a. Title + крестик (showCloseButton — Remote Config)
   b. "How Your Free Trial Works" → Timeline (4 шага)
   c. Plan Cards (Weekly + Yearly горизонтально, height: 90)
   d. Trial info text (динамический по выбранному плану)
   e. 🛡️ "14-Day Money-Back Guarantee" badge
   f. Spacer(50)
   g. Features Section (6 строк реальных фич)
   h. Spacer(50)
   i. Reviews carousel (горизонтальный ScrollView, 6 карточек, width:220)
   j. Spacer(40)
   k. Features emoji carousel (горизонтальный ScrollView, 6 карточек)
   l. Spacer(40)
   m. Terms + ссылки (ToU + PP)
   n. Spacer(120) — место под sticky bar
3. .safeAreaInset(edge: .bottom): stickyBottomBar
```

### Крестик (без фона, без круга):
```swift
Image(systemName: "xmark")
    .font(.system(size: 16, weight: .medium))
    .foregroundColor(secondaryText.opacity(0.4))
    .frame(width: 36, height: 36)
```

### Plan Cards (цены — тусклые, тонкие, без галочки):
```swift
HStack(spacing: 0) {
    Text(price).font(.system(size: 12, weight: .regular))
    Text(period).font(.system(size: 10, weight: .light))
}
.foregroundColor(secondaryText)
// Выбранная карточка: accent border + accent.opacity(0.08) background
```

### Sticky Bottom Bar (.safeAreaInset):
```swift
VStack(spacing: 6) {
    // CTA: "Start Free Trial" (yearly) / "Subscribe" (weekly)
    Button { purchase() } label: { ... }

    // "No payment now" — только yearly:
    if selectedPlanId == YEARLY_PRODUCT_ID {
        Text("No payment now")
            .font(.system(size: 13, weight: .medium))
            .foregroundColor(accent)
            .transition(.opacity)
    }

    Button { restorePurchases() } label: {
        Text("Restore Purchases")
            .font(.system(size: 13, weight: .medium))
            .foregroundColor(secondaryText)
    }
}
.padding(.top, 10)
.padding(.bottom, 8)
.animation(.easeInOut(duration: 0.2), value: selectedPlanId)
```

### iPad адаптация:
```swift
@Environment(\.horizontalSizeClass) private var horizontalSizeClass
private var isIPad: Bool { horizontalSizeClass == .regular }

// Контент: .frame(maxWidth: isIPad ? 700 : .infinity)
// CTA кнопка: .frame(maxWidth: isIPad ? 440 : .infinity)
```

### Remote Config (задержка крестика):
```swift
.onAppear {
    Analytics.logEvent("{APP_KEY}_paywall_shown", parameters: ["source": source])

    let remoteConfig = RemoteConfig.remoteConfig()
    let delay = remoteConfig.configValue(forKey: "{REMOTE_CONFIG_KEY}").numberValue.doubleValue

    DispatchQueue.main.asyncAfter(deadline: .now() + delay) {
        withAnimation(.easeIn(duration: 0.3)) {
            showCloseButton = true
        }
    }
}
```

### Analytics события (префикс APP_KEY):
```
{APP_KEY}_paywall_shown        (source)
{APP_KEY}_paywall_dismissed    (source)
{APP_KEY}_purchase_started     (plan)
{APP_KEY}_purchase_completed   (plan, price)
{APP_KEY}_purchase_cancelled   (plan)
{APP_KEY}_purchase_failed      (error)
{APP_KEY}_restore_purchases    (success: bool)
```

### Ссылки (всегда эти):
```swift
Link("Terms of Use", destination: URL(string: "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/")!)
Link("Privacy Policy", destination: URL(string: "https://britetodo.com/privacypolicy.php")!)
```

---

## ШАГ 4 — ГЕНЕРАЦИЯ SubscriptionService.swift

Создать `{TARGET_FOLDER}/SubscriptionService.swift`.

> **Эталон**: `reference/SubscriptionService.swift` в этом репозитории.

Обязательные адаптации:
- `productIds`: Set = [`WEEKLY_PRODUCT_ID`, `YEARLY_PRODUCT_ID`]
- `cacheKey`: `"{APP_KEY}_pro_state"`
- `expirationKey`: `"{APP_KEY}_expiration_date"`
- `weeklyProduct` / `yearlyProduct` — с правильными product IDs
- Все Analytics события с префиксом APP_KEY

```swift
@MainActor
final class SubscriptionService: ObservableObject {
    static let shared = SubscriptionService()

    @Published private(set) var proState: ProState = .notPurchased
    @Published private(set) var products: [Product] = []
    @Published private(set) var isLoading = false
    @Published private(set) var isPurchasing = false
    @Published private(set) var error: Error?
    @Published private(set) var expirationDate: Date?

    var isPro: Bool { proState.hasAccess }
    // ... (полный код из reference/SubscriptionService.swift)
}

enum ProState: String, Codable {
    case notPurchased, active, inGrace, billingRetry, expired
    var hasAccess: Bool { self == .active || self == .inGrace || self == .billingRetry }
}

enum PurchaseError: LocalizedError {
    case pending, unknown, noActiveSubscription, verificationFailed, userCancelled
}
```

---

## ШАГ 5 — ГЕНЕРАЦИЯ FeatureGate.swift

Создать `{TARGET_FOLDER}/FeatureGate.swift`.

```swift
import Foundation

enum FeatureGate {
    static let freeItemLimit = {LIMIT}  // 0, 1 или 3 по ответу пользователя

    static func canAddItem(currentCount: Int, isPro: Bool) -> Bool {
        isPro || currentCount < freeItemLimit
    }

    // Адаптировать под фичи конкретного приложения:
    static func canAccessPremiumFeature(isPro: Bool) -> Bool { isPro }
    static func canExportPDF(isPro: Bool) -> Bool { isPro }
    // ... другие gates согласно APP-SPEC
}
```

**Лимиты:**
- Минимально → `freeItemLimit = 3`
- Стандартно → `freeItemLimit = 1`
- Максимально → `freeItemLimit = 0`

---

## ШАГ 6 — ГЕНЕРАЦИЯ PremiumBannerView.swift

Создать `{TARGET_FOLDER}/PremiumBannerView.swift`.

> **Эталон**: `reference/PremiumBannerView.swift` в этом репозитории.

```swift
// Frosted glass overlay — только блюр, тапабельный
struct PremiumLockedOverlay: View {
    let title: String
    let subtitle: String
    let onUpgrade: () -> Void

    var body: some View {
        Rectangle()
            .fill(.ultraThinMaterial)
            .ignoresSafeArea()
            .onTapGesture { onUpgrade() }
    }
}

// Inline upsell banner
struct PremiumBannerView: View {
    let message: String
    let onUpgrade: () -> Void
    // ... (полный код из reference/PremiumBannerView.swift)
}
```

---

## ШАГ 7 — HTML ПРЕВЬЮ ПЕЙВОЛА

Создать `/tmp/{APP_KEY}_paywall_preview.html` — интерактивная визуализация в iPhone-фрейме.

### Структура HTML:
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{APP_DISPLAY_NAME} Paywall Preview</title>
  <style>
    body { background: #0a0a0a; display: flex; justify-content: center;
           align-items: flex-start; min-height: 100vh; margin: 0; padding: 40px 0;
           font-family: -apple-system, sans-serif; }
    .phone { width: 393px; height: 852px; background: #fff; border-radius: 52px;
             position: relative; overflow: hidden;
             box-shadow: 0 0 0 12px #1a1a1a, 0 40px 80px rgba(0,0,0,0.8); }
    .island { position: absolute; top: 14px; left: 50%; transform: translateX(-50%);
              width: 126px; height: 37px; background: #000; border-radius: 20px; z-index: 100; }
    .content { position: absolute; top: 0; left: 0; right: 0; bottom: 80px;
               overflow-y: auto; padding: 60px 24px 20px; background: {BACKGROUND_HEX}; }
    .sticky-bar { position: absolute; bottom: 0; left: 0; right: 0; height: 80px;
                  background: {BACKGROUND_HEX}; padding: 8px 32px; }
  </style>
</head>
<body>
  <!-- Все секции: timeline, plan cards, badge, features, reviews, carousel, terms -->
  <!-- JS переключение планов, "No payment now" toggle -->
</body>
</html>
```

**Требования:**
- Интерактивное переключение планов через JS
- "No payment now" появляется/исчезает при выборе yearly
- Reviews — горизонтальный скролл, 6 карточек по 220px
- Крестик видимый (в реале — Remote Config)
- Цвета точно соответствуют ACCENT_HEX

После создания:
```bash
open /tmp/{APP_KEY}_paywall_preview.html
```

> ⏸ **ОСТАНОВИТЬСЯ** — спросить подтверждение перед интеграцией.

---

## ШАГ 8 — ИНТЕГРАЦИЯ В ОНБОРДИНГ (ОБЯЗАТЕЛЬНО!)

> 🔴 **КРИТИЧЕСКОЕ ПРАВИЛО**: Пейвол ВСЕГДА показывается в конце онбординга.
> Это не опционально. Без пейвола в конце онбординга — монетизация не работает.

Найти `OnboardingView.swift` и добавить:

```swift
// В OnboardingView:
@State private var showPaywall = false

// finishOnboarding() — НЕ завершать сразу, сначала показать пейвол:
private func finishOnboarding() {
    showPaywall = true  // ← пейвол перед завершением
}

// fullScreenCover с PaywallView:
.fullScreenCover(isPresented: $showPaywall) {
    PaywallView(source: "onboarding", onComplete: {
        showPaywall = false
        hasCompletedOnboarding = true  // завершение ПОСЛЕ пейвола
    })
    .environmentObject(SubscriptionService.shared)
}
```

**Если нет OnboardingView** — добавить пейвол в ContentView как first-launch:
```swift
// ContentView.swift:
@AppStorage("hasSeenPaywall") private var hasSeenPaywall = false
@State private var showPaywall = false

.fullScreenCover(isPresented: $showPaywall) {
    PaywallView(source: "first_launch", onComplete: {
        showPaywall = false
        hasSeenPaywall = true
    })
    .environmentObject(SubscriptionService.shared)
}
.onAppear {
    if !hasSeenPaywall && !SubscriptionService.shared.isPro {
        showPaywall = true
    }
}
```

---

## ШАГ 9 — ИНТЕГРАЦИЯ В MAIN APP ENTRY

Найти `*App.swift` (`@main` struct) и добавить:

```swift
import FirebaseCore
import FirebaseRemoteConfig

@main
struct {APP_SCHEME}App: App {
    init() {
        FirebaseApp.configure()

        let remoteConfig = RemoteConfig.remoteConfig()
        remoteConfig.setDefaults(["{REMOTE_CONFIG_KEY}": 5.0 as NSNumber])
        remoteConfig.fetch(withExpirationDuration: 3600) { _, _ in
            remoteConfig.activate { _, _ in }
        }

        Task {
            await SubscriptionService.shared.initialize()
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(SubscriptionService.shared)
        }
    }
}
```

---

## ШАГ 10 — МОНЕТИЗАЦИЯ ВО ВСЕХ ЭКРАНАХ

Добавить во все основные View файлы:

```swift
// Начало каждого View:
@ObservedObject private var subscriptionService = SubscriptionService.shared
@State private var showPaywall = false

// .fullScreenCover на PaywallView:
.fullScreenCover(isPresented: $showPaywall) {
    PaywallView(source: "{screen_name}", onComplete: { showPaywall = false })
        .environmentObject(SubscriptionService.shared)
}
```

### Паттерны блокировок:

**1. Лимит создания (кнопка +):**
```swift
Button {
    if FeatureGate.canAddItem(currentCount: items.count, isPro: subscriptionService.isPro) {
        showAddForm = true
    } else {
        showPaywall = true
    }
} label: { Image(systemName: "plus") }
```

**2. Frosted glass на заблокированных секциях:**
```swift
.overlay {
    if !subscriptionService.isPro {
        RoundedRectangle(cornerRadius: 16)
            .fill(.ultraThinMaterial)
            .onTapGesture { showPaywall = true }
    }
}
```

**3. Полный overlay заблокированной вкладки:**
```swift
ZStack {
    mainContent
    if !subscriptionService.isPro {
        PremiumLockedOverlay(title: "", subtitle: "", onUpgrade: { showPaywall = true })
    }
}
```

**4. Inline PremiumBannerView (внизу списков):**
```swift
if !subscriptionService.isPro {
    PremiumBannerView(
        message: "Unlock unlimited {items} and more",
        onUpgrade: { showPaywall = true }
    )
    .padding(.horizontal)
    .padding(.bottom, 8)
}
```

> **Правило**: НЕ показывать текст "Premium Feature" на заблокированных карточках.
> Только frosted glass + баннер снизу.

---

## ШАГ 11 — FIREBASE DEPENDENCIES

Проверить наличие Firebase:
```bash
grep -r "Firebase" {APP_FOLDER}/project.yml 2>/dev/null
grep -r "Firebase" {APP_FOLDER}/Package.swift 2>/dev/null
```

Если нет — добавить в `project.yml`:
```yaml
packages:
  FirebaseSDK:
    url: https://github.com/firebase/firebase-ios-sdk
    from: 11.0.0

targets:
  {APP_SCHEME}:
    dependencies:
      - package: FirebaseSDK
        product: FirebaseAnalytics
      - package: FirebaseSDK
        product: FirebaseRemoteConfig
```

Регенерировать:
```bash
cd {APP_FOLDER} && xcodegen generate
```

---

## ШАГ 12 — СБОРКА И ПРОВЕРКА

```bash
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer

xcodebuild \
  -project {APP_FOLDER}/{APP_SCHEME}.xcodeproj \
  -scheme {APP_SCHEME} \
  -sdk iphonesimulator \
  -destination 'platform=iOS Simulator,name=iPhone 16 Pro' \
  build 2>&1 | grep -E "error:|warning:|Build succeeded|Build FAILED"
```

Итеративно фиксить ошибки (обычно 1–3 раунда):
- Missing imports (Firebase, StoreKit)
- Product ID строки не совпадают
- @EnvironmentObject не передан

---

## ШАГ 13 — ФИНАЛЬНЫЙ ОТЧЁТ

```
✅ Paywall интегрирован в {APP_DISPLAY_NAME}

Создано:
• PaywallView.swift — пейвол с Remote Config крестиком
• SubscriptionService.swift — StoreKit 2, weekly + yearly
• FeatureGate.swift — лимиты бесплатного использования
• PremiumBannerView.swift — frosted overlay + inline banner

Интеграция:
• OnboardingView — пейвол в конце онбординга ✓
• [перечислить какие Views получили монетизацию]

Remote Config:
⚠️ Добавить ключ "{REMOTE_CONFIG_KEY}" в Firebase Console
• Тип: Number
• Дефолт: 5 (секунды до крестика)
• 0 = крестик сразу | -1 = никогда

ASC:
1. Создать подписки: {WEEKLY_PRODUCT_ID} + {YEARLY_PRODUCT_ID}
2. Загрузить билд через Xcode Organizer
```

---

## ОГРАНИЧЕНИЯ (НИКОГДА не делать)

| ❌ Запрещено | ✅ Правильно |
|-------------|------------|
| RevenueCat или другие SDK | Нативный StoreKit 2 |
| "Premium Feature" текст на карточках | Frosted glass + баннер снизу |
| Крестик видимый сразу | Remote Config delay |
| "Manage Subscription" в Settings | iOS системные настройки |
| Дату окончания триала в Settings | Только в AppStore |
| Цены на скриншотах App Store | Скриншоты без цен |
| Пейвол только из Settings | Контекстуальные триггеры + онбординг |
