#!/usr/bin/env python3
"""
SubscriptionBuilderAgent — Создание подписок в App Store Connect.

Создаёт Weekly + Yearly подписки полностью через API (~530 API calls, ~5 минут).
Скриншот для ревью загружается автоматически (один и тот же для всех приложений).

ИСПОЛЬЗОВАНИЕ:
  1. Заполнить CONFIG (APP_ID обязателен — всё остальное по умолчанию)
  2. python3 subscription_creator.py

ПОСЛЕ СКРИПТА:
  - Подписки в статусе READY_TO_SUBMIT
  - Загрузить билд через Xcode Organizer
  - В ASC UI: Subscriptions → Add to Build (нужный Group)
  - Сабмит билда = сабмит подписок (они идут вместе)
"""

import jwt, time, requests, json, os, hashlib, base64
import sys

# ═══════════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ — менять для каждого нового приложения
# ═══════════════════════════════════════════════════════════════════

CONFIG = {
    # ─── ASC API (не менять) ───────────────────────────────────────
    "issuer_id":  "f7dc851a-bdcb-47d6-b5c7-857f48cadb17",
    "key_id":     "C37442BRFH",
    "key_path":   os.path.expanduser("~/.appstoreconnect/private_keys/AuthKey_C37442BRFH.p8"),

    # ─── Приложение (заполнить!) ───────────────────────────────────
    "app_id":           "XXXXXXXXXX",    # ← числовой App ID из ASC (напр. "6738893683")

    # ─── Подписки ──────────────────────────────────────────────────
    "group_name":       "App Name Premium",   # referenceName группы (напр. "AntiqueSnap Premium")
    "app_display_name": "App Name",           # для customAppName   (напр. "AntiqueSnap")
    "weekly_product_id":  "app_name_weekly",  # полный ID (напр. "com.britetodo.antique.weekly")
    "yearly_product_id":  "app_name_yearly",  # полный ID (напр. "com.britetodo.antique.yearly")

    # ─── Цены ─────────────────────────────────────────────────────
    # Стандарт: Weekly $5.99 / Yearly $19.99 USA / Yearly $12.99 остальные
    # Уточнить через GET /v1/subscriptions/{id}/pricePoints?filter[territory]=USA
    "weekly_price_level":      "10075",   # $5.99 USA
    "yearly_base_price_level": "10142",   # $12.99 (база для остальных стран, автоэквализация)
    "yearly_usa_price_level":  "10177",   # $19.99 USA (override поверх базовой)
    # Если USA и base одинаковые — поставить None:
    # "yearly_usa_price_level": None,

    # ─── Free trial ───────────────────────────────────────────────
    "trial_duration": "THREE_DAYS",  # THREE_DAYS | ONE_WEEK | TWO_WEEKS | ONE_MONTH

    # ─── Скриншот для ревью (один для всех приложений) ─────────────
    # Один и тот же файл используется для ВСЕХ подписок и ВСЕХ приложений
    "screenshot_path": os.path.expanduser(
        "~/Desktop/vibecode/app-builder/subscription-review-screenshot.png"
    ),
}

# ═══════════════════════════════════════════════════════════════════

BASE = "https://api.appstoreconnect.apple.com"

# Загрузить ключ
key_path = CONFIG["key_path"]
if not os.path.exists(key_path):
    # fallback на старый путь
    key_path = os.path.expanduser("~/Desktop/vibecode/screenshot generator/api/AuthKey_C37442BRFH.p8")
with open(key_path) as f:
    PRIVATE_KEY = f.read()

def get_token():
    return jwt.encode(
        {
            "iss": CONFIG["issuer_id"],
            "iat": int(time.time()),
            "exp": int(time.time()) + 1200,
            "aud": "appstoreconnect-v1"
        },
        PRIVATE_KEY, algorithm="ES256", headers={"kid": CONFIG["key_id"]}
    )

def api(method, path, payload=None, params=None):
    """API wrapper с auto-retry на 429 (rate limit)."""
    for attempt in range(4):
        headers = {
            "Authorization": f"Bearer {get_token()}",
            "Content-Type": "application/json"
        }
        url = f"{BASE}{path}"
        try:
            if method == "GET":
                r = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == "POST":
                r = requests.post(url, headers=headers, json=payload, timeout=30)
            elif method == "PATCH":
                r = requests.patch(url, headers=headers, json=payload, timeout=30)
            else:
                raise ValueError(f"Unknown method: {method}")
        except requests.exceptions.Timeout:
            print(f"  Timeout on attempt {attempt+1}, retrying...")
            time.sleep(5)
            continue

        if r.status_code == 429:
            print(f"  Rate limited, waiting 5s... (attempt {attempt+1})")
            time.sleep(5)
            continue
        return r
    return r

def get_all_pages(path, params=None):
    """Paginate через все страницы."""
    all_data = []
    url = f"{BASE}{path}"
    p = dict(params or {})
    p["limit"] = 200
    while url:
        headers = {"Authorization": f"Bearer {get_token()}", "Content-Type": "application/json"}
        r = requests.get(url, headers=headers, params=p, timeout=30)
        data = r.json()
        all_data.extend(data.get("data", []))
        url = data.get("links", {}).get("next")
        p = {}
    return all_data

def build_pp_id(sub_id, territory, price_level):
    """Собрать price point ID из компонентов (base64 кодирование)."""
    raw = json.dumps({"s": sub_id, "t": territory, "p": price_level}, separators=(",", ":"))
    return base64.b64encode(raw.encode()).decode().rstrip("=")

# ═══════════════════════════════════════════════════════════════════
# Проверка конфигурации
# ═══════════════════════════════════════════════════════════════════
def validate_config():
    assert CONFIG["app_id"] != "XXXXXXXXXX", \
        "❌ Заполни CONFIG['app_id'] — числовой App ID из ASC!"
    assert CONFIG["weekly_product_id"] != "app_name_weekly", \
        "❌ Заполни CONFIG['weekly_product_id']!"
    assert CONFIG["yearly_product_id"] != "app_name_yearly", \
        "❌ Заполни CONFIG['yearly_product_id']!"
    assert os.path.exists(CONFIG["screenshot_path"]), \
        f"❌ Нет скриншота: {CONFIG['screenshot_path']}"
    assert os.path.exists(key_path), \
        f"❌ Нет API ключа: {key_path}"
    print("✅ Config OK")

# ═══════════════════════════════════════════════════════════════════
# Основной процесс
# ═══════════════════════════════════════════════════════════════════
def main():
    validate_config()
    print(f"\nCreating subscriptions for App ID: {CONFIG['app_id']}")
    print(f"  Weekly:  {CONFIG['weekly_product_id']} @ $5.99/week")
    print(f"  Yearly:  {CONFIG['yearly_product_id']} @ $19.99/year (USA), $12.99/year (other)")
    print(f"  Trial:   {CONFIG['trial_duration']} for Yearly")
    print()

    # ─── Шаг 1: Создать группу подписок ──────────────────────────
    print("Step 1/11: Creating subscription group...")
    r = api("POST", "/v1/subscriptionGroups", {
        "data": {
            "type": "subscriptionGroups",
            "attributes": {"referenceName": CONFIG["group_name"]},
            "relationships": {
                "app": {"data": {"type": "apps", "id": CONFIG["app_id"]}}
            }
        }
    })
    assert r.status_code == 201, f"Failed (HTTP {r.status_code}): {r.text}"
    GROUP_ID = r.json()["data"]["id"]
    print(f"  Group created: {GROUP_ID}")

    # ─── Шаг 2: Локализация группы (en-US) ───────────────────────
    print("Step 2/11: Localizing group (en-US)...")
    r = api("POST", "/v1/subscriptionGroupLocalizations", {
        "data": {
            "type": "subscriptionGroupLocalizations",
            "attributes": {
                "name": "Premium",
                "locale": "en-US",
                "customAppName": CONFIG["app_display_name"]
            },
            "relationships": {
                "subscriptionGroup": {"data": {"type": "subscriptionGroups", "id": GROUP_ID}}
            }
        }
    })
    assert r.status_code == 201, f"Failed (HTTP {r.status_code}): {r.text}"
    print("  OK")

    # ─── Шаг 3: Создать подписки ─────────────────────────────────
    print("Step 3/11: Creating subscriptions (Weekly + Yearly)...")
    subs = {}
    for sub_name, product_id, period, group_level in [
        ("Weekly", CONFIG["weekly_product_id"], "ONE_WEEK", 2),
        ("Yearly", CONFIG["yearly_product_id"], "ONE_YEAR", 1),
    ]:
        r = api("POST", "/v1/subscriptions", {
            "data": {
                "type": "subscriptions",
                "attributes": {
                    "name": sub_name,
                    "productId": product_id,
                    "subscriptionPeriod": period,
                    "groupLevel": group_level,
                    "familySharable": False,
                    "reviewNote": f"{sub_name} subscription providing full access to all premium features."
                },
                "relationships": {
                    "group": {"data": {"type": "subscriptionGroups", "id": GROUP_ID}}
                }
            }
        })
        assert r.status_code == 201, f"Failed {sub_name} (HTTP {r.status_code}): {r.text}"
        subs[sub_name] = r.json()["data"]["id"]
        print(f"  {sub_name}: {subs[sub_name]}")

    WEEKLY_ID = subs["Weekly"]
    YEARLY_ID = subs["Yearly"]

    # ─── Шаг 4: Локализация подписок (en-US) ─────────────────────
    print("Step 4/11: Localizing subscriptions (en-US)...")
    for sub_name, sub_id, desc in [
        ("Weekly", WEEKLY_ID, "All features unlocked for a week"),
        ("Yearly", YEARLY_ID, "All features unlocked for a year"),
    ]:
        r = api("POST", "/v1/subscriptionLocalizations", {
            "data": {
                "type": "subscriptionLocalizations",
                "attributes": {
                    "name": sub_name,
                    "description": desc,
                    "locale": "en-US"
                },
                "relationships": {
                    "subscription": {"data": {"type": "subscriptions", "id": sub_id}}
                }
            }
        })
        assert r.status_code == 201, f"Failed {sub_name} (HTTP {r.status_code}): {r.text}"
    print("  OK")

    # ─── Шаг 5: Получить все территории ──────────────────────────
    print("Step 5/11: Fetching all territories...")
    all_territories = get_all_pages("/v1/territories")
    territory_ids = [t["id"] for t in all_territories]
    territory_data = [{"type": "territories", "id": t["id"]} for t in all_territories]
    print(f"  {len(territory_ids)} territories loaded")

    # ─── Шаг 6: Доступность (ОБЯЗАТЕЛЬНО ДО цен!) ────────────────
    print("Step 6/11: Setting availability (all territories)...")
    print("  ⚠️  Must be before prices or you'll get 500 errors!")
    for sub_name, sub_id in [("Weekly", WEEKLY_ID), ("Yearly", YEARLY_ID)]:
        r = api("POST", "/v1/subscriptionAvailabilities", {
            "data": {
                "type": "subscriptionAvailabilities",
                "attributes": {"availableInNewTerritories": True},
                "relationships": {
                    "subscription": {"data": {"type": "subscriptions", "id": sub_id}},
                    "availableTerritories": {"data": territory_data}
                }
            }
        })
        assert r.status_code == 201, f"Failed {sub_name} availability (HTTP {r.status_code}): {r.text}"
        print(f"  {sub_name}: OK")

    # ─── Шаг 7: Цены для всех территорий ─────────────────────────
    print("Step 7/11: Setting prices (~350 API calls)...")

    def set_all_prices(sub_id, sub_name, base_price_level):
        """Установить цены: USA + 174 equalized через equalizations endpoint."""
        # Установить USA цену
        usa_pp = build_pp_id(sub_id, "USA", base_price_level)
        r = api("POST", "/v1/subscriptionPrices", {
            "data": {
                "type": "subscriptionPrices",
                "relationships": {
                    "subscription": {"data": {"type": "subscriptions", "id": sub_id}},
                    "subscriptionPricePoint": {"data": {"type": "subscriptionPricePoints", "id": usa_pp}}
                }
            }
        })
        if r.status_code != 201:
            print(f"  ⚠️  USA price error for {sub_name}: {r.text}")

        # Получить equalizations (174 остальных территории)
        eqs = get_all_pages(f"/v1/subscriptionPricePoints/{usa_pp}/equalizations")

        # Установить цену для каждой территории
        ok, err = 0, 0
        for i, eq in enumerate(eqs):
            r = api("POST", "/v1/subscriptionPrices", {
                "data": {
                    "type": "subscriptionPrices",
                    "relationships": {
                        "subscription": {"data": {"type": "subscriptions", "id": sub_id}},
                        "subscriptionPricePoint": {"data": {"type": "subscriptionPricePoints", "id": eq["id"]}}
                    }
                }
            })
            if r.status_code == 201:
                ok += 1
            else:
                err += 1
            if (i + 1) % 50 == 0:
                print(f"    {sub_name}: {i+1}/{len(eqs)} done...")

        print(f"  {sub_name}: {ok+1} prices set, {err} errors")

    # Weekly: одна цена для всех
    set_all_prices(WEEKLY_ID, "Weekly", CONFIG["weekly_price_level"])

    # Yearly: базовая цена для всех территорий кроме USA
    set_all_prices(YEARLY_ID, "Yearly", CONFIG["yearly_base_price_level"])

    # Override USA для Yearly ($19.99 вместо $12.99)
    if CONFIG.get("yearly_usa_price_level") and \
       CONFIG["yearly_usa_price_level"] != CONFIG["yearly_base_price_level"]:
        print("  Overriding Yearly price for USA...")
        usa_pp = build_pp_id(YEARLY_ID, "USA", CONFIG["yearly_usa_price_level"])
        r = api("POST", "/v1/subscriptionPrices", {
            "data": {
                "type": "subscriptionPrices",
                "attributes": {"preserveCurrentPrice": False},
                "relationships": {
                    "subscription": {"data": {"type": "subscriptions", "id": YEARLY_ID}},
                    "subscriptionPricePoint": {"data": {"type": "subscriptionPricePoints", "id": usa_pp}}
                }
            }
        })
        if r.status_code == 201:
            print("  Yearly USA: $19.99 ✓")
        else:
            print(f"  ⚠️  Yearly USA override failed: {r.text}")

    # ─── Шаг 8: Free Trial для Yearly (175 вызовов!) ──────────────
    print(f"Step 8/11: Creating {CONFIG['trial_duration']} trial for Yearly (175 API calls)...")
    print("  ⚠️  territory is to-one — need separate call per territory!")
    ok, err = 0, 0
    for i, terr in enumerate(territory_ids):
        r = api("POST", "/v1/subscriptionIntroductoryOffers", {
            "data": {
                "type": "subscriptionIntroductoryOffers",
                "attributes": {
                    "duration": CONFIG["trial_duration"],
                    "offerMode": "FREE_TRIAL",
                    "numberOfPeriods": 1
                },
                "relationships": {
                    "subscription": {"data": {"type": "subscriptions", "id": YEARLY_ID}},
                    "territory": {"data": {"type": "territories", "id": terr}}
                }
            }
        })
        if r.status_code == 201:
            ok += 1
        else:
            err += 1
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{len(territory_ids)}...")

    print(f"  Trials: {ok} created, {err} errors")

    # ─── Шаг 9: Скриншот для ревью ────────────────────────────────
    print("Step 9/11: Uploading review screenshots...")
    screenshot_path = CONFIG["screenshot_path"]
    file_size = os.path.getsize(screenshot_path)
    with open(screenshot_path, "rb") as f:
        file_data = f.read()
    file_md5 = hashlib.md5(file_data).hexdigest()

    for sub_name, sub_id in [("Weekly", WEEKLY_ID), ("Yearly", YEARLY_ID)]:
        # Reserve
        r = api("POST", "/v1/subscriptionAppStoreReviewScreenshots", {
            "data": {
                "type": "subscriptionAppStoreReviewScreenshots",
                "attributes": {
                    "fileName": "subscription-review-screenshot.png",
                    "fileSize": file_size
                },
                "relationships": {
                    "subscription": {"data": {"type": "subscriptions", "id": sub_id}}
                }
            }
        })
        assert r.status_code == 201, f"Failed reserve {sub_name}: {r.text}"
        ss_data = r.json()["data"]
        ss_id = ss_data["id"]

        # Upload binary (chunk upload)
        for op in ss_data["attributes"].get("uploadOperations", []):
            upload_headers = {h["name"]: h["value"] for h in op.get("requestHeaders", [])}
            offset = op.get("offset", 0)
            length = op.get("length", file_size)
            chunk = file_data[offset: offset + length]
            requests.put(op["url"], headers=upload_headers, data=chunk, timeout=60)

        # Commit
        r = api("PATCH", f"/v1/subscriptionAppStoreReviewScreenshots/{ss_id}", {
            "data": {
                "type": "subscriptionAppStoreReviewScreenshots",
                "id": ss_id,
                "attributes": {
                    "uploaded": True,
                    "sourceFileChecksum": file_md5
                }
            }
        })
        assert r.status_code == 200, f"Failed commit {sub_name}: {r.text}"
        print(f"  {sub_name}: screenshot uploaded ✓")

    # ─── Шаг 10: Проверка статуса ─────────────────────────────────
    print("\nStep 10/11: Verifying...")
    for sub_name, sub_id in [("Weekly", WEEKLY_ID), ("Yearly", YEARLY_ID)]:
        r = api("GET", f"/v1/subscriptions/{sub_id}")
        state = r.json()["data"]["attributes"].get("state", "?")
        r2 = api("GET", f"/v1/subscriptions/{sub_id}/prices", params={"limit": 1})
        total_prices = r2.json().get("meta", {}).get("paging", {}).get("total", 0)
        print(f"  {sub_name}: state={state}, prices={total_prices}/175")

    # ─── Шаг 11: Итог ─────────────────────────────────────────────
    print("\nStep 11/11: Done!")
    print(f"""
{'='*55}
  ✅ SUBSCRIPTIONS CREATED

  App ID:    {CONFIG['app_id']}
  Group ID:  {GROUP_ID}
  Weekly:    {WEEKLY_ID}
             {CONFIG['weekly_product_id']}
  Yearly:    {YEARLY_ID}
             {CONFIG['yearly_product_id']}

  State: READY_TO_SUBMIT

  СЛЕДУЮЩИЕ ШАГИ:
  1. Загрузить билд через Xcode Organizer
  2. ASC UI → {CONFIG['app_display_name']} → Monetization
     → Subscriptions → Add to Build → выбрать "{CONFIG['group_name']}"
  3. Сабмит билда = сабмит подписок (идут вместе)

  ⚠️  subscriptionGroupSubmissions работает ТОЛЬКО
      вместе с новой версией приложения!
{'='*55}
""")

    # Сохранить IDs для дальнейшего использования
    result = {
        "app_id": CONFIG["app_id"],
        "group_id": GROUP_ID,
        "weekly_id": WEEKLY_ID,
        "yearly_id": YEARLY_ID,
        "weekly_product_id": CONFIG["weekly_product_id"],
        "yearly_product_id": CONFIG["yearly_product_id"],
    }
    output_path = f"/tmp/subscriptions_{CONFIG['app_id']}.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"  IDs сохранены: {output_path}")

if __name__ == "__main__":
    main()
