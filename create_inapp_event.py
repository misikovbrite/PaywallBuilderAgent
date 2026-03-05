#!/usr/bin/env python3
"""
Create In-App Event for App Store Connect.

Usage:
    python3 create-inapp-event.py

Requirements:
    pip3 install PyJWT requests Pillow

ASC Credentials (from cppflow-system.md):
    - Issuer ID: f7dc851a-bdcb-47d6-b5c7-857f48cadb17
    - Key ID: C37442BRFH
    - Key path: ~/Downloads/AuthKey_C37442BRFH.p8
"""

import jwt
import time
import requests
import json
import os
import hashlib
import sys
from datetime import datetime, timedelta, timezone

# ─── ASC CREDENTIALS ───────────────────────────────────────────────
ISSUER_ID = "f7dc851a-bdcb-47d6-b5c7-857f48cadb17"
KEY_ID = "C37442BRFH"
KEY_PATH = os.path.expanduser("~/Downloads/AuthKey_C37442BRFH.p8")
BASE_URL = "https://api.appstoreconnect.apple.com"


def get_token():
    """Generate JWT token for ASC API."""
    with open(KEY_PATH, "r") as f:
        private_key = f.read()
    now = int(time.time())
    payload = {
        "iss": ISSUER_ID,
        "iat": now,
        "exp": now + 1200,
        "aud": "appstoreconnect-v1",
    }
    return jwt.encode(payload, private_key, algorithm="ES256", headers={"kid": KEY_ID})


def get_headers():
    return {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json",
    }


def get_all_territories(app_id: str) -> list[str]:
    """Get all territory codes for an app."""
    r = requests.get(
        f"{BASE_URL}/v2/appAvailabilities/{app_id}/territoryAvailabilities",
        params={"limit": 200, "include": "territory"},
        headers=get_headers(),
    )
    r.raise_for_status()
    return [inc["id"] for inc in r.json().get("included", []) if inc["type"] == "territories"]


def create_event(
    app_id: str,
    reference_name: str,
    deep_link: str,
    badge: str = "MAJOR_UPDATE",
    purpose: str = "ATTRACT_NEW_USERS",
    priority: str = "HIGH",
    start_hours_from_now: int = 3,
    duration_days: int = 5,
    territories: list[str] | None = None,
) -> dict:
    """
    Create an In-App Event.

    Badge options: LIVE_EVENT, PREMIERE, CHALLENGE, COMPETITION,
                   NEW_SEASON, MAJOR_UPDATE, SPECIAL_EVENT

    Purpose options: APPROPRIATE_FOR_ALL_USERS, ATTRACT_NEW_USERS,
                     KEEP_ACTIVE_USERS_INFORMED, BRING_BACK_LAPSED_USERS
    """
    if territories is None:
        territories = get_all_territories(app_id)
        print(f"  Using all {len(territories)} territories")

    now = datetime.now(timezone.utc)
    event_start = now + timedelta(hours=start_hours_from_now)
    event_end = event_start + timedelta(days=duration_days)

    # Round to nearest hour
    event_start = event_start.replace(minute=0, second=0, microsecond=0)
    event_end = event_end.replace(minute=0, second=0, microsecond=0)

    body = {
        "data": {
            "type": "appEvents",
            "attributes": {
                "referenceName": reference_name,
                "badge": badge,
                "deepLink": deep_link,
                "purchaseRequirement": "NO_COST_ASSOCIATED",
                "primaryLocale": "en-US",
                "priority": priority,
                "purpose": purpose,
                "territorySchedules": [
                    {
                        "territories": territories,
                        "publishStart": event_start.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                        "eventStart": event_start.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                        "eventEnd": event_end.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                    }
                ],
            },
            "relationships": {
                "app": {"data": {"type": "apps", "id": app_id}}
            },
        }
    }

    r = requests.post(f"{BASE_URL}/v1/appEvents", headers=get_headers(), json=body)
    r.raise_for_status()
    data = r.json()["data"]
    print(f"  Event created: ID={data['id']}, state={data['attributes']['eventState']}")
    return data


def update_event(
    event_id: str,
    territories: list[str] | None = None,
    start_hours_from_now: int | None = None,
    duration_days: int | None = None,
    **kwargs,
) -> dict:
    """Update an existing event. Pass any attribute as kwarg."""
    attrs = {k: v for k, v in kwargs.items() if v is not None}

    if start_hours_from_now is not None and duration_days is not None and territories is not None:
        now = datetime.now(timezone.utc)
        event_start = (now + timedelta(hours=start_hours_from_now)).replace(minute=0, second=0, microsecond=0)
        event_end = (event_start + timedelta(days=duration_days)).replace(minute=0, second=0, microsecond=0)
        attrs["territorySchedules"] = [
            {
                "territories": territories,
                "publishStart": event_start.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                "eventStart": event_start.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                "eventEnd": event_end.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            }
        ]

    body = {"data": {"type": "appEvents", "id": event_id, "attributes": attrs}}
    r = requests.patch(f"{BASE_URL}/v1/appEvents/{event_id}", headers=get_headers(), json=body)
    r.raise_for_status()
    return r.json()["data"]


def set_localization(
    event_id: str,
    name: str,
    short_description: str,
    long_description: str,
    locale: str = "en-US",
) -> str:
    """
    Set event localization texts.
    Returns localization ID.

    Limits: name=30 chars, short=50 chars, long=120 chars.
    """
    # Check existing localizations
    r = requests.get(
        f"{BASE_URL}/v1/appEvents/{event_id}/localizations",
        headers=get_headers(),
    )
    r.raise_for_status()
    localizations = r.json()["data"]

    loc = next((l for l in localizations if l["attributes"]["locale"] == locale), None)

    attrs = {
        "name": name[:30],
        "shortDescription": short_description[:50],
        "longDescription": long_description[:120],
    }

    if loc:
        # Update existing
        body = {"data": {"type": "appEventLocalizations", "id": loc["id"], "attributes": attrs}}
        r = requests.patch(
            f"{BASE_URL}/v1/appEventLocalizations/{loc['id']}",
            headers=get_headers(),
            json=body,
        )
        r.raise_for_status()
        loc_id = loc["id"]
        print(f"  Updated localization {locale}: {loc_id}")
    else:
        # Create new
        body = {
            "data": {
                "type": "appEventLocalizations",
                "attributes": {"locale": locale, **attrs},
                "relationships": {
                    "appEvent": {"data": {"type": "appEvents", "id": event_id}}
                },
            }
        }
        r = requests.post(
            f"{BASE_URL}/v1/appEventLocalizations",
            headers=get_headers(),
            json=body,
        )
        r.raise_for_status()
        loc_id = r.json()["data"]["id"]
        print(f"  Created localization {locale}: {loc_id}")

    return loc_id


def upload_event_image(
    localization_id: str,
    image_path: str,
    asset_type: str,
) -> str:
    """
    Upload an image to an event localization.

    asset_type: "EVENT_CARD" (1920x1080) or "EVENT_DETAILS_PAGE" (1080x1920)

    IMPORTANT: Images must be RGB (no alpha channel!).
    If your image has alpha, convert first:
        from PIL import Image
        img = Image.open("file.png").convert("RGB")
        img.save("file_rgb.png")
    """
    file_size = os.path.getsize(image_path)
    file_name = os.path.basename(image_path)

    # Step 1: Create reservation
    body = {
        "data": {
            "type": "appEventScreenshots",
            "attributes": {
                "fileName": file_name,
                "fileSize": file_size,
                "appEventAssetType": asset_type,
            },
            "relationships": {
                "appEventLocalization": {
                    "data": {"type": "appEventLocalizations", "id": localization_id}
                }
            },
        }
    }

    r = requests.post(
        f"{BASE_URL}/v1/appEventScreenshots",
        headers=get_headers(),
        json=body,
    )
    r.raise_for_status()
    data = r.json()["data"]
    screenshot_id = data["id"]

    # Step 2: Upload chunks
    for op in data["attributes"]["uploadOperations"]:
        upload_headers = {h["name"]: h["value"] for h in op["requestHeaders"]}
        with open(image_path, "rb") as f:
            chunk = f.read()
            offset = op.get("offset", 0)
            length = op.get("length", len(chunk))
        r = requests.put(op["url"], headers=upload_headers, data=chunk[offset : offset + length])
        r.raise_for_status()

    # Step 3: Commit
    commit = {
        "data": {
            "type": "appEventScreenshots",
            "id": screenshot_id,
            "attributes": {"uploaded": True},
        }
    }
    r = requests.patch(
        f"{BASE_URL}/v1/appEventScreenshots/{screenshot_id}",
        headers=get_headers(),
        json=commit,
    )
    r.raise_for_status()
    state = r.json()["data"]["attributes"]["assetDeliveryState"]
    print(f"  Uploaded {asset_type}: {state['state']}")

    if state["state"] == "FAILED":
        print(f"  ERROR: {state.get('errors')}")
        print("  TIP: Make sure image has NO alpha channel (RGB, not RGBA)")
        sys.exit(1)

    return screenshot_id


def generate_event_image(prompt: str, size: str = "1536x1024") -> str:
    """
    Generate image via CPPFlow GPT Image API.
    Returns URL of generated image.

    Sizes: 1536x1024 (horizontal), 1024x1536 (vertical), 1024x1024 (square)
    """
    r = requests.post(
        "https://cppflow.com/api/openai.php?action=generate-image",
        json={"prompt": prompt, "size": size, "background": "opaque"},
    )
    r.raise_for_status()
    url = r.json()["url"]
    print(f"  Generated: {url}")
    return url


def download_and_prepare(url: str, output_path: str, target_size: tuple[int, int]) -> str:
    """Download image, resize to target, ensure RGB (no alpha)."""
    from PIL import Image
    from io import BytesIO

    r = requests.get(url)
    r.raise_for_status()
    img = Image.open(BytesIO(r.content))

    # Remove alpha if present
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    else:
        img = img.convert("RGB")

    img = img.resize(target_size, Image.LANCZOS)
    img.save(output_path)
    print(f"  Saved: {output_path} ({target_size[0]}x{target_size[1]}, {os.path.getsize(output_path)} bytes)")
    return output_path


def check_event_status(event_id: str):
    """Print full event status."""
    headers = get_headers()

    r = requests.get(f"{BASE_URL}/v1/appEvents/{event_id}", headers=headers)
    r.raise_for_status()
    ev = r.json()["data"]["attributes"]
    print(f"\n{'='*50}")
    print(f"EVENT: {ev['referenceName']}")
    print(f"  State:    {ev['eventState']}")
    print(f"  Badge:    {ev['badge']}")
    print(f"  Priority: {ev['priority']}")
    print(f"  Purpose:  {ev['purpose']}")
    print(f"  Purchase: {ev['purchaseRequirement']}")
    for s in ev.get("territorySchedules", []):
        print(f"  Territories: {len(s['territories'])} countries")
        print(f"  Publish:  {s['publishStart']}")
        print(f"  Start:    {s['eventStart']}")
        print(f"  End:      {s['eventEnd']}")

    r2 = requests.get(f"{BASE_URL}/v1/appEvents/{event_id}/localizations", headers=headers)
    r2.raise_for_status()
    for loc in r2.json()["data"]:
        a = loc["attributes"]
        print(f"\n  LOCALIZATION [{a['locale']}]:")
        print(f"    Name:  {a['name']}")
        print(f"    Short: {a['shortDescription']}")
        print(f"    Long:  {a['longDescription']}")

        r3 = requests.get(
            f"{BASE_URL}/v1/appEventLocalizations/{loc['id']}/appEventScreenshots",
            headers=headers,
        )
        r3.raise_for_status()
        for s in r3.json().get("data", []):
            sa = s["attributes"]
            print(f"    Image: {sa['appEventAssetType']} → {sa['assetDeliveryState']['state']}")

    print(f"\n  STATUS: {'READY (submit in ASC)' if ev['eventState'] == 'DRAFT' else ev['eventState']}")
    print(f"{'='*50}")


# ─── MAIN: EXAMPLE USAGE ──────────────────────────────────────────

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════╗
║   In-App Event Creator for App Store Connect     ║
╚══════════════════════════════════════════════════╝

This script creates a complete In-App Event:
  1. Creates/updates the event with dates & territories
  2. Sets localization texts (name, short, long)
  3. Generates & uploads images (card + detail)

BEFORE RUNNING:
  - Set APP_ID and texts below
  - pip3 install PyJWT requests Pillow
  - Ensure ~/Downloads/AuthKey_C37442BRFH.p8 exists
""")

    # ── CONFIGURE THESE ──────────────────────────────────────
    APP_ID = "6758868326"  # Turbulence Forecast
    DEEP_LINK = "https://apps.apple.com/us/app/turbulence-forecast-flight/id6758868326"

    REFERENCE_NAME = "Interactive Turbulence Check v1.2"
    EVENT_NAME = "Know Turbulence Before You Fly"  # max 30 chars
    SHORT_DESC = "Enter your route — see turbulence in under a min."  # max 50 chars
    LONG_DESC = "New interactive experience: check turbulence for any flight in seconds. 14-day forecasts, live pilot reports & more."  # max 120 chars

    BADGE = "MAJOR_UPDATE"  # LIVE_EVENT, PREMIERE, CHALLENGE, COMPETITION, NEW_SEASON, MAJOR_UPDATE, SPECIAL_EVENT
    PURPOSE = "ATTRACT_NEW_USERS"  # APPROPRIATE_FOR_ALL_USERS, ATTRACT_NEW_USERS, KEEP_ACTIVE_USERS_INFORMED, BRING_BACK_LAPSED_USERS
    PRIORITY = "HIGH"  # NORMAL, HIGH

    START_HOURS = 3  # hours from now — модератор видит что событие вот-вот запустится → приоритизирует ревью
    DURATION_DAYS = 5  # event duration

    # Image prompts (NO TEXT on images!)
    CARD_PROMPT = "Wide panoramic view from airplane window showing airplane wing over dramatic cloud layer at golden hour, deep blue sky above transitioning to warm orange near horizon, cumulus clouds below lit by sunset, professional cinematic aviation photography, no text, vibrant colors, high contrast"
    DETAIL_PROMPT = "Vertical composition airplane wing seen from window seat beautiful calm sunset sky with soft orange and blue gradient scattered clouds below peaceful serene flight atmosphere professional aviation photography no text no UI elements clean minimal composition calming mood"
    # ─────────────────────────────────────────────────────────

    print("Step 1: Getting territories...")
    territories = get_all_territories(APP_ID)

    print(f"\nStep 2: Creating event...")
    event = create_event(
        app_id=APP_ID,
        reference_name=REFERENCE_NAME,
        deep_link=DEEP_LINK,
        badge=BADGE,
        purpose=PURPOSE,
        priority=PRIORITY,
        start_hours_from_now=START_HOURS,
        duration_days=DURATION_DAYS,
        territories=territories,
    )
    event_id = event["id"]

    print(f"\nStep 3: Setting localization...")
    loc_id = set_localization(
        event_id=event_id,
        name=EVENT_NAME,
        short_description=SHORT_DESC,
        long_description=LONG_DESC,
    )

    print(f"\nStep 4: Generating images...")
    card_url = generate_event_image(CARD_PROMPT, "1536x1024")
    detail_url = generate_event_image(DETAIL_PROMPT, "1024x1536")

    print(f"\nStep 5: Preparing images (resize + remove alpha)...")
    card_path = download_and_prepare(card_url, "/tmp/event_card_1920x1080.png", (1920, 1080))
    detail_path = download_and_prepare(detail_url, "/tmp/event_detail_1080x1920.png", (1080, 1920))

    print(f"\nStep 6: Uploading images...")
    upload_event_image(loc_id, card_path, "EVENT_CARD")
    upload_event_image(loc_id, detail_path, "EVENT_DETAILS_PAGE")

    print(f"\nStep 7: Final status check...")
    # Wait for Apple processing
    import time as t
    t.sleep(5)
    check_event_status(event_id)

    print(f"\n✅ Event ready! Go to App Store Connect → Submit for review.")
    print(f"   Event ID: {event_id}")
