#!/bin/bash
# PaywallBuilderAgent — установка на новой машине
# Использование: curl -fsSL https://raw.githubusercontent.com/misikovbrite/PaywallBuilderAgent/main/install.sh | bash

set -e

REPO="https://raw.githubusercontent.com/misikovbrite/PaywallBuilderAgent/main"
COMMANDS_DIR="$HOME/.claude/commands"
AGENT_DIR="$HOME/PaywallBuilderAgent"

echo "📦 PaywallBuilderAgent — установка..."

# 1. Создать папки если нет
mkdir -p "$COMMANDS_DIR"
mkdir -p "$AGENT_DIR"

# 2. Скачать Claude Code команды
echo "→ Команды Claude Code..."
curl -fsSL "$REPO/commands/subscriptions.md" -o "$COMMANDS_DIR/subscriptions.md"
echo "  ✅ /subscriptions"

# Paywall команда (если есть в репо)
curl -fsSL "$REPO/commands/paywall.md" -o "$COMMANDS_DIR/paywall.md" 2>/dev/null && echo "  ✅ /paywall" || true

# 3. Скачать скрипт создания подписок
echo "→ subscription_creator.py..."
curl -fsSL "$REPO/subscription_creator.py" -o "$AGENT_DIR/subscription_creator.py"
chmod +x "$AGENT_DIR/subscription_creator.py"
echo "  ✅ ~/PaywallBuilderAgent/subscription_creator.py"

# 4. Скачать документацию
echo "→ Документация..."
curl -fsSL "$REPO/SUBSCRIPTION-BUILDER-AGENT.md" -o "$AGENT_DIR/SUBSCRIPTION-BUILDER-AGENT.md"
curl -fsSL "$REPO/AGENT-INSTRUCTIONS.md"          -o "$AGENT_DIR/AGENT-INSTRUCTIONS.md"
curl -fsSL "$REPO/MONETIZATION-STRATEGY.md"       -o "$AGENT_DIR/MONETIZATION-STRATEGY.md"
curl -fsSL "$REPO/ONBOARDING-PAYWALL-RULE.md"     -o "$AGENT_DIR/ONBOARDING-PAYWALL-RULE.md"
curl -fsSL "$REPO/APP-BUILDER-INTEGRATION.md"     -o "$AGENT_DIR/APP-BUILDER-INTEGRATION.md"
echo "  ✅ Документация"

# 5. Скачать reference Swift файлы
mkdir -p "$AGENT_DIR/reference"
echo "→ Reference Swift файлы..."
curl -fsSL "$REPO/reference/PaywallView.swift"         -o "$AGENT_DIR/reference/PaywallView.swift"
curl -fsSL "$REPO/reference/SubscriptionService.swift" -o "$AGENT_DIR/reference/SubscriptionService.swift"
curl -fsSL "$REPO/reference/FeatureGate.swift"         -o "$AGENT_DIR/reference/FeatureGate.swift"
curl -fsSL "$REPO/reference/PremiumBannerView.swift"   -o "$AGENT_DIR/reference/PremiumBannerView.swift"
echo "  ✅ reference/"

# 6. Проверить зависимости Python
echo "→ Проверка Python зависимостей..."
if ! python3 -c "import jwt, requests" 2>/dev/null; then
    echo "  ⚠️  Устанавливаем pyjwt и requests..."
    pip3 install pyjwt requests --quiet
    echo "  ✅ pyjwt requests"
else
    echo "  ✅ pyjwt requests (уже установлены)"
fi

echo ""
echo "✅ Установка завершена!"
echo ""
echo "Команды в Claude Code:"
echo "  /subscriptions  — создать подписки в ASC и подключить к Paywall"
echo "  /paywall        — создать PaywallView + SubscriptionService + FeatureGate"
echo ""
echo "Документация: ~/PaywallBuilderAgent/"
echo "Скрипт:       ~/PaywallBuilderAgent/subscription_creator.py"
echo ""
echo "⚠️  Не забудь положить ASC API ключ:"
echo "    ~/.appstoreconnect/private_keys/AuthKey_C37442BRFH.p8"
