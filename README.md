# PaywallBuilderAgent 🚀

> Claude Code агент для автоматической интеграции полноценной системы монетизации в iOS-приложения.

---

## Что это

**PaywallBuilderAgent** — специализированный агент на базе Claude Code, который встраивает production-ready paywall в существующее iOS SwiftUI приложение за один запуск.

### Результат работы агента:
- `PaywallView.swift` — полноценный пейвол с Remote Config крестиком, таймлайном, отзывами
- `SubscriptionService.swift` — StoreKit 2 сервис (weekly + yearly, caching, transaction listener)
- `FeatureGate.swift` — система ограничений для бесплатных пользователей
- `PremiumBannerView.swift` — frosted glass overlay + inline upsell banner
- Интеграция пейвола в конец онбординга (обязательно)
- Контекстуальные блокировки во всех основных экранах

---

## Стек (строго)

| Компонент | Технология |
|-----------|-----------|
| Подписки | **StoreKit 2 нативный** (без RevenueCat!) |
| Analytics | Firebase Analytics |
| Remote Config | Firebase Remote Config |
| UI | SwiftUI |
| iOS Target | iOS 17+ |

---

## Быстрый старт

### На любом Mac с Claude Code:

```bash
# 1. Склонировать репо агента
git clone https://github.com/misikovbrite/PaywallBuilderAgent ~/PaywallBuilderAgent

# 2. Открыть проект вашего приложения в Claude Code
cd ~/ваш-ios-проект

# 3. Запустить агента
/paywall
```

### Установка skill в Claude Code:

Добавить в `~/.claude/skills/paywall.md` содержимое файла [`AGENT-INSTRUCTIONS.md`](./AGENT-INSTRUCTIONS.md).

---

## Структура репозитория

```
PaywallBuilderAgent/
├── README.md                        # Этот файл
├── AGENT-INSTRUCTIONS.md            # Полные инструкции агента (/paywall skill)
├── MONETIZATION-STRATEGY.md         # Стратегия монетизации и hard restrictions
├── ONBOARDING-PAYWALL-RULE.md       # Правило: пейвол обязателен в конце онбординга
├── APP-BUILDER-INTEGRATION.md       # Интеграция с App Builder pipeline
└── reference/
    ├── PaywallView.swift            # Эталонная реализация (GLP-1 Tracker)
    ├── SubscriptionService.swift    # Эталонный StoreKit 2 сервис
    ├── FeatureGate.swift            # Эталонные gates
    └── PremiumBannerView.swift      # Эталонные баннеры
```

---

## Эталонное приложение

Все паттерны основаны на **GLP-1 Tracker** — приложении Brite Technologies, прошедшем App Store Review.

Эталонный код находится в `reference/` и должен использоваться как основа при генерации нового пейвола.

---

## Правило онбординга (критически важно)

> **Пейвол ВСЕГДА показывается в конце онбординга.**

Это не опциональное требование. Онбординг без пейвола в конце — незаконченная реализация.
Подробности: [`ONBOARDING-PAYWALL-RULE.md`](./ONBOARDING-PAYWALL-RULE.md)

---

## Ограничения

- ❌ НЕ использовать RevenueCat или другие SDK
- ❌ НЕ добавлять текст "Premium Feature" на заблокированных карточках
- ❌ НЕ делать крестик видимым сразу — только через Remote Config delay
- ❌ НЕ добавлять "Manage Subscription" в Settings
- ❌ НЕ показывать цены на скриншотах App Store

---

## Связанные системы

- **App Builder**: [`misikovbrite/app-builder`](https://github.com/misikovbrite/app-builder) — полный pipeline iOS → App Store
- **CPPFlow**: скриншоты и шаблоны приложений
- **Brite Technologies**: Team ID `5487HDH2B9`
