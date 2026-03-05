# Правило: Пейвол в конце онбординга (ОБЯЗАТЕЛЬНО)

---

## Суть правила

> **Пейвол ВСЕГДА показывается в конце онбординга — без исключений.**

Это не пожелание. Это архитектурное требование всех iOS-приложений Brite Technologies.

---

## Почему это критично

### Момент максимальной мотивации
Пользователь только что прошёл весь онбординг. Он понял ценность продукта, ответил на вопросы о себе, почувствовал персонализацию. **Это пик его готовности заплатить.**

### Конверсия
Пейвол после онбординга конвертирует в 3–5× лучше, чем:
- Пейвол при первом попадании в premium-фичу
- Пейвол из Settings
- Пейвол через X дней использования

### Без пейвола — деньги уходят
Пользователь, который прошёл онбординг и НЕ увидел пейвол, скорее всего никогда не конвертируется. Момент упущен.

---

## Правильная реализация

### В OnboardingView.swift:

```swift
struct OnboardingView: View {
    @AppStorage("hasCompletedOnboarding") private var hasCompletedOnboarding = false
    @State private var showPaywall = false
    @State private var currentPage = 0

    var body: some View {
        ZStack {
            // ... страницы онбординга ...
        }
        // Пейвол показывается ПЕРЕД завершением онбординга:
        .fullScreenCover(isPresented: $showPaywall) {
            PaywallView(source: "onboarding", onComplete: {
                showPaywall = false
                hasCompletedOnboarding = true  // ← завершение ПОСЛЕ пейвола
            })
            .environmentObject(SubscriptionService.shared)
        }
    }

    // Эта функция вызывается на последней странице онбординга:
    private func finishOnboarding() {
        // НЕ: hasCompletedOnboarding = true (сразу завершать нельзя!)
        // ДА: показать пейвол:
        showPaywall = true
    }
}
```

### ⚠️ Частые ошибки:

```swift
// ❌ НЕПРАВИЛЬНО — завершение до пейвола:
private func finishOnboarding() {
    hasCompletedOnboarding = true  // пользователь попадёт в приложение без пейвола
}

// ❌ НЕПРАВИЛЬНО — пейвол в отдельном App flow без онбординга:
// (пользователь может закрыть приложение до пейвола)

// ✅ ПРАВИЛЬНО — пейвол блокирует завершение онбординга:
private func finishOnboarding() {
    showPaywall = true  // пейвол → onComplete → hasCompletedOnboarding = true
}
```

---

## Сценарий: нет OnboardingView

Если в приложении нет онбординга — создать минимальный (3–5 экранов) и добавить пейвол в конце.

**Минимальный онбординг:**
1. Welcome экран (название + иконка + CTA "Get Started")
2. 2–3 feature экрана (главные ценности приложения)
3. Paywall (финальный экран)

**Никогда не запускать приложение напрямую в ContentView** без онбординга + пейвола при первом запуске.

---

## Сценарий: уже есть OnboardingView без пейвола

Если онбординг есть, но пейвол отсутствует:

1. Найти функцию завершения онбординга (обычно `completeOnboarding()`, `finishOnboarding()`, или установка `@AppStorage("hasCompletedOnboarding")`)
2. Добавить `@State private var showPaywall = false`
3. Заменить прямое завершение на `showPaywall = true`
4. Добавить `.fullScreenCover` с PaywallView
5. Перенести `hasCompletedOnboarding = true` в `onComplete` пейвола

---

## Что происходит, если пользователь закрыл пейвол (крестик)

Пейвол закрывается → `onComplete()` вызывается → `hasCompletedOnboarding = true`.

Пользователь попадает в приложение как бесплатный пользователь. Монетизация работает через:
- Контекстуальные блокировки (FeatureGate)
- PremiumBannerView в списках
- Paywall при попытке использовать premium-фичи

---

## Checklist перед сабмитом в App Store

- [ ] OnboardingView показывает PaywallView в конце
- [ ] `hasCompletedOnboarding = true` устанавливается только внутри `onComplete` пейвола
- [ ] При повторном запуске (онбординг уже пройден) пейвол не показывается снова
- [ ] Крестик управляется Remote Config (не виден сразу)
- [ ] PP + ToU ссылки на paywall экране
- [ ] Restore Purchases кнопка видима
