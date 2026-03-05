# Reference Implementation — GLP-1 Tracker

Эталонные файлы взяты из **GLP-1 Tracker** (Brite Technologies, App Store).
Это production-код, прошедший Apple Review.

## Файлы

| Файл | Описание |
|------|---------|
| `PaywallView.swift` | Полный пейвол: timeline, plan cards, reviews, features carousel, sticky bar |
| `SubscriptionService.swift` | StoreKit 2: покупка, восстановление, кэширование, transaction listener |
| `FeatureGate.swift` | Лимиты: freeInjectionLimit=1, gates для weight/health/PDF |
| `PremiumBannerView.swift` | PremiumLockedOverlay (frosted glass) + PremiumBannerView (inline) |

## Как использовать

При генерации нового пейвола:
1. Взять структуру из `PaywallView.swift`
2. Заменить цвета на `ACCENT_HEX` нового приложения
3. Заменить product IDs (`com.kovneier.glptracker.*` → `{BUNDLE_ID}.*`)
4. Заменить Analytics префикс (`glp1_` → `{APP_KEY}_`)
5. Адаптировать тексты фич, отзывов, timeline под нишу приложения

## Bundle ID эталона

GLP-1 Tracker использует нестандартный bundle: `com.kovneier.glptracker`
(не `com.britetodo.*` — исторически).

Новые приложения используют `com.britetodo.{app_key}`.
