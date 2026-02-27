"""
Meta Ad Library Scraper — Module 1 of the Creative Intelligence Agent
======================================================================

ABOUT THE META ACCESS TOKEN
-----------------------------
You need a **Meta (Facebook) Developer App token** with access to the
Ad Library API. Specifically:

1. Go to https://developers.facebook.com/ and create a developer account.
2. Create a new App (type: "Business" or "None / Other").
3. In your App dashboard, go to Tools → Graph API Explorer.
4. Generate a User Access Token with at minimum the scope:
       ads_read
   (Some endpoints also require `pages_read_engagement`.)
5. For long-lived access: exchange your short-lived token for a 60-day
   long-lived token via:
       GET /oauth/access_token
           ?grant_type=fb_exchange_token
           &client_id={app_id}
           &client_secret={app_secret}
           &fb_exchange_token={short_lived_token}
6. For production / server-to-server use, generate a System User token
   from your Meta Business Manager (business.facebook.com →
   Business Settings → System Users → Generate New Token).

Store the token in a `.env` file as:
    META_ACCESS_TOKEN=your_token_here

IMPORTANT: The Ad Library API is subject to Meta's usage policies.
Only use it for research, transparency, and competitive analysis as
permitted by Meta's terms of service.

API reference: https://www.facebook.com/ads/library/api/
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
BASE_URL = "https://graph.facebook.com/v19.0/ads_archive"

# Fields to retrieve for each ad
AD_FIELDS = ",".join([
    "ad_creative_bodies",
    "ad_creative_link_captions",
    "ad_creative_link_descriptions",
    "ad_creative_link_titles",
    "ad_delivery_start_time",
    "ad_snapshot_url",
    "page_name",
    "publisher_platforms",
    "ad_creative_link_titles",
])

MAX_ADS = 200          # Hard cap on total ads fetched
PAGE_LIMIT = 50        # Ads per API page (Meta allows up to 1000, keep lower to be safe)
PROFITABLE_DAYS = 30   # Ads running this long are flagged as likely profitable

TODAY = datetime.now(timezone.utc).date()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_access_token() -> str:
    """Return the Meta access token or exit with a helpful message."""
    if not META_ACCESS_TOKEN:
        print(
            "[ERROR] META_ACCESS_TOKEN is not set.\n"
            "  1. Copy .env.example to .env\n"
            "  2. Fill in your Meta access token\n"
            "  See the comment block at the top of this file for instructions."
        )
        sys.exit(1)
    return META_ACCESS_TOKEN


def days_active(start_time_str: str) -> int:
    """Calculate how many days an ad has been active from its start timestamp."""
    try:
        start_date = datetime.fromisoformat(start_time_str.replace("Z", "+00:00")).date()
        return (TODAY - start_date).days
    except (ValueError, AttributeError):
        return 0


def fetch_page(params: dict, retries: int = 4) -> dict:
    """
    Fetch a single page from the Meta Ad Library API.
    Retries up to `retries` times with exponential back-off on failure.
    """
    delay = 2
    for attempt in range(retries + 1):
        try:
            response = requests.get(BASE_URL, params=params, timeout=30)
            if response.status_code == 429:
                print(f"  [WARN] Rate limited. Waiting {delay}s before retry...")
                time.sleep(delay)
                delay *= 2
                continue
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            if attempt < retries:
                print(f"  [WARN] Request failed ({exc}). Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                print(f"  [ERROR] Request failed after {retries + 1} attempts: {exc}")
                sys.exit(1)
    return {}


def fetch_all_ads(search_query: str, country: str) -> list[dict]:
    """
    Paginate through the Meta Ad Library API and collect up to MAX_ADS ads.
    """
    token = get_access_token()
    params = {
        "access_token": token,
        "ad_reached_countries": country,
        "ad_active_status": "ACTIVE",
        "search_terms": search_query,
        "fields": AD_FIELDS,
        "limit": PAGE_LIMIT,
    }

    ads: list[dict] = []
    page_num = 0

    print(f"\nFetching ads for query='{search_query}', country={country}...")

    while True:
        page_num += 1
        print(f"  Fetching page {page_num} ({len(ads)} ads so far)...", end=" ", flush=True)
        data = fetch_page(params)

        page_ads = data.get("data", [])
        if not page_ads:
            print("empty page — done.")
            break

        ads.extend(page_ads)
        print(f"got {len(page_ads)} ads.")

        if len(ads) >= MAX_ADS:
            ads = ads[:MAX_ADS]
            print(f"  Reached cap of {MAX_ADS} ads.")
            break

        # Follow the pagination cursor
        next_cursor = data.get("paging", {}).get("cursors", {}).get("after")
        next_url = data.get("paging", {}).get("next")
        if not next_cursor and not next_url:
            print("  No more pages.")
            break

        if next_cursor:
            params["after"] = next_cursor
        else:
            # Extract `after` cursor from the next URL as a fallback
            import urllib.parse
            parsed = urllib.parse.urlparse(next_url)
            qs = urllib.parse.parse_qs(parsed.query)
            params["after"] = qs.get("after", [None])[0]
            if params["after"] is None:
                break

    return ads


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------

def enrich_ad(raw_ad: dict) -> dict:
    """Add computed fields to a raw ad record."""
    start_time = raw_ad.get("ad_delivery_start_time", "")
    active_days = days_active(start_time)

    # Detect media type heuristically from available fields
    bodies = raw_ad.get("ad_creative_bodies", [])
    media_type = raw_ad.get("media_type", "unknown")
    if media_type == "unknown":
        # Fallback: check publisher platforms or snapshot URL patterns
        snapshot = raw_ad.get("ad_snapshot_url", "")
        if "video" in snapshot.lower():
            media_type = "video"
        else:
            media_type = "image"

    return {
        "page_name": raw_ad.get("page_name", ""),
        "ad_creative_bodies": bodies,
        "ad_creative_link_captions": raw_ad.get("ad_creative_link_captions", []),
        "ad_creative_link_descriptions": raw_ad.get("ad_creative_link_descriptions", []),
        "ad_creative_link_titles": raw_ad.get("ad_creative_link_titles", []),
        "ad_delivery_start_time": start_time,
        "days_active": active_days,
        "likely_profitable": active_days >= PROFITABLE_DAYS,
        "media_type": media_type,
        "ad_snapshot_url": raw_ad.get("ad_snapshot_url", ""),
        "video_hd_url": raw_ad.get("video_hd_url", ""),
        "video_sd_url": raw_ad.get("video_sd_url", ""),
        "publisher_platforms": raw_ad.get("publisher_platforms", []),
    }


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(ads: list[dict], search_query: str) -> None:
    """Print a quick human-readable summary to the terminal."""
    total = len(ads)
    video_count = sum(1 for a in ads if a["media_type"] == "video")
    image_count = sum(1 for a in ads if a["media_type"] == "image")
    profitable_count = sum(1 for a in ads if a["likely_profitable"])

    # Count ads per page
    page_counts: dict[str, int] = {}
    for ad in ads:
        name = ad["page_name"] or "Unknown"
        page_counts[name] = page_counts.get(name, 0) + 1

    top_pages = sorted(page_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    print("\n" + "=" * 60)
    print(f"  SUMMARY — '{search_query}'")
    print("=" * 60)
    print(f"  Total ads found      : {total}")
    print(f"  Video ads            : {video_count}")
    print(f"  Image ads            : {image_count}")
    print(f"  Other / unknown      : {total - video_count - image_count}")
    print(f"  Likely profitable    : {profitable_count}  (running {PROFITABLE_DAYS}+ days)")
    print("\n  Top 3 pages by ad count:")
    for rank, (page, count) in enumerate(top_pages, start=1):
        print(f"    {rank}. {page}  ({count} ads)")
    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # --- Gather inputs -------------------------------------------------------
    if len(sys.argv) >= 3:
        search_query = sys.argv[1]
        country = sys.argv[2].upper()
    elif len(sys.argv) == 2:
        search_query = sys.argv[1]
        country = "IN"
    else:
        search_query = input("Enter search query: ").strip()
        if not search_query:
            print("[ERROR] search_query cannot be empty.")
            sys.exit(1)
        country_input = input("Enter country code [default: IN]: ").strip().upper()
        country = country_input if country_input else "IN"

    # --- Fetch ---------------------------------------------------------------
    raw_ads = fetch_all_ads(search_query, country)

    if not raw_ads:
        print(f"\n[INFO] No ads found for query='{search_query}' in country={country}.")
        sys.exit(0)

    # --- Enrich --------------------------------------------------------------
    enriched_ads = [enrich_ad(ad) for ad in raw_ads]

    # --- Save JSON -----------------------------------------------------------
    output_filename = f"{search_query}_ads_raw.json"
    output_path = os.path.join(os.getcwd(), output_filename)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enriched_ads, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Saved {len(enriched_ads)} ads to: {output_path}")

    # --- Summary -------------------------------------------------------------
    print_summary(enriched_ads, search_query)


if __name__ == "__main__":
    main()
