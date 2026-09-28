import json
import os
import re
import sys
from datetime import datetime, timezone

import requests

# version 1.2.1
# Monitors road closures from the Nepal DOR Navigate page
# (https://navigate.dor.gov.np/app/road-closure-history) and posts status-driven
# Discord embed notifications when closures are added, modified, or cleared.

API_URL = "https://navigate.dor.gov.np/api/Road_closure_history_api/getHistoryPaginated"
API_HEADERS = {"Content-Type": "application/json"}

# Shared target for all embeds of a closure. When multiple embeds in one message
# carry the same `url`, Discord's client merges them into a single gallery card.
SOURCE_URL = "https://navigate.dor.gov.np/app/road-closure-history"

WEBHOOK_URLS = [
    os.environ.get("DISCORD_WEBHOOK_URL_KID4RM90S"),
    os.environ.get("DISCORD_WEBHOOK_URL_WAZENEPAL"),
]

# Filter out any that are None/empty
WEBHOOK_URLS = [url for url in WEBHOOK_URLS if url]

STATE_FILE = "dor_closure_state.json"

# Nepali calendar data (days per month for each BS year 2000-2099)
# Source: NepaliBStoAD.js library (https://kid4rm90s.github.io/NepaliBStoAD/NepaliBStoAD.js)
# Reference: AD 1944-01-01 = BS 2000-09-17
BS_MONTHS = [
    [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], # 2000
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2001
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], # 2002
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], # 2003
    [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30], # 2004
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2005
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], # 2006
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], # 2007
    [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30], # 2008
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2009
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], # 2010
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], # 2011
    [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30], # 2012
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2013
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], # 2014
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], # 2015
    [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30], # 2016
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2017
    [31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30], # 2018
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], # 2019
    [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30], # 2020
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2021
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30], # 2022
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], # 2023
    [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30], # 2024
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2025
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], # 2026
    [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], # 2027
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2028
    [31, 31, 32, 31, 32, 30, 30, 29, 30, 29, 30, 30], # 2029
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], # 2030
    [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], # 2031
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2032
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], # 2033
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], # 2034
    [30, 32, 31, 32, 31, 31, 29, 30, 30, 29, 29, 31], # 2035
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2036
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], # 2037
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], # 2038
    [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30], # 2039
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2040
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], # 2041
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], # 2042
    [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30], # 2043
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2044
    [31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30], # 2045
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], # 2046
    [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30], # 2047
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2048
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30], # 2049
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], # 2050
    [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30], # 2051
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2052
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30], # 2053
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], # 2054
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2055
    [31, 31, 32, 31, 32, 30, 30, 29, 30, 29, 30, 30], # 2056
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], # 2057
    [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], # 2058
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2059
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], # 2060
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], # 2061
    [30, 32, 31, 32, 31, 31, 29, 30, 29, 30, 29, 31], # 2062
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2063
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], # 2064
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], # 2065
    [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 29, 31], # 2066
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2067
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], # 2068
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], # 2069
    [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30], # 2070
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2071
    [31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30], # 2072
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], # 2073
    [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30], # 2074
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2075
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30], # 2076
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], # 2077
    [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30], # 2078
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2079
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30], # 2080
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], # 2081
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2082
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2083
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], # 2084
    [31, 31, 31, 32, 31, 31, 30, 29, 30, 30, 29, 31], # 2085
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2086
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], # 2087
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], # 2088
    [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30], # 2089
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2090
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], # 2091
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], # 2092
    [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30], # 2093
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2094
    [31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30], # 2095
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], # 2096
    [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30], # 2097
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], # 2098
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30], # 2099
]


def gregorian_to_nepali(ad_year, ad_month, ad_day):
    """Convert AD date to BS date using NepaliBStoAD algorithm."""
    try:
        # Reference point: AD 1944-01-01 = BS 2000-09-17
        ref_ad = datetime(1944, 1, 1, tzinfo=timezone.utc)
        ad_date = datetime(ad_year, ad_month, ad_day, tzinfo=timezone.utc)

        # Calculate days difference
        days_diff = (ad_date - ref_ad).days

        # Start from reference BS date
        bs_year, bs_month, bs_day = 2000, 9, 17

        # Add days to BS date
        while days_diff > 0:
            if bs_year < 2000 or bs_year > 2099:
                print(f"Warning: Year {bs_year} out of supported range (2000-2099)")
                break

            year_idx = bs_year - 2000
            if year_idx >= len(BS_MONTHS):
                print(f"Warning: Year index {year_idx} out of range")
                break

            if bs_month < 1 or bs_month > 12:
                print(f"Error: Invalid month {bs_month}")
                return None

            days_in_month = BS_MONTHS[year_idx][bs_month - 1]
            days_left = days_in_month - bs_day + 1

            if days_diff >= days_left:
                days_diff -= days_left
                bs_day = 1
                bs_month += 1
                if bs_month > 12:
                    bs_month = 1
                    bs_year += 1
            else:
                bs_day += days_diff
                days_diff = 0

        return bs_year, bs_month, bs_day
    except (ValueError, TypeError, IndexError) as e:
        print(f"Conversion error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return None


def to_nepali_digits(s: str) -> str:
    """Convert Arabic digits (0-9) to Nepali digits (०-९)."""
    arabic_to_nepali = str.maketrans("0123456789", "०१२३४५६७८९")
    return s.translate(arabic_to_nepali)


def convert_dt_to_bs(dt_str):
    """Convert a 'YYYY-MM-DD[ HH:MM[:SS]]' string to BS (with Nepali digits).

    DOR timestamps are already in Nepal local time, so only the calendar date
    is converted and the time component is kept as-is (digit-shifted to Nepali).
    Returns None if the string cannot be parsed or conversion fails.
    """
    if not dt_str:
        return None
    m = re.match(
        r"(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?",
        str(dt_str).strip(),
    )
    if not m:
        return None
    ad_year, ad_month, ad_day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    result = gregorian_to_nepali(ad_year, ad_month, ad_day)
    if not result:
        return None
    bs_year, bs_month, bs_day = result
    date_bs = f"{bs_year:04d}-{bs_month:02d}-{bs_day:02d}"
    if m.group(4):
        time_bs = f"{m.group(4)}:{m.group(5)}"
        if m.group(6):
            time_bs += f":{m.group(6)}"
        return to_nepali_digits(f"{date_bs} {time_bs}")
    return to_nepali_digits(date_bs)


def snapshot(record):
    """Extract the subset of fields we display/track into a stable dict."""
    return {
        "id": record.get("id"),
        "date_created": record.get("date_created"),
        "road_refno": record.get("road_refno"),
        "road_name": record.get("road_name"),
        "closure_type": (record.get("closure_type") or "").strip().upper(),
        "closure_reason": record.get("closure_reason"),
        "efforts_being_made": record.get("efforts_being_made"),
        "remarks": record.get("remarks"),
        "district": record.get("district"),
        "location": record.get("location"),
        "link_code": record.get("link_code"),
        "division": record.get("division"),
        "repair_eta": record.get("repair_eta"),
        "actual_repair_time": record.get("actual_repair_time"),
        "date_roadblock_start": record.get("date_roadblock_start"),
        "date_roadblock_end_estimated": record.get("date_roadblock_end_estimated"),
        "date_roadblock_end": record.get("date_roadblock_end"),
        "latitude": record.get("latitude"),
        "longitude": record.get("longitude"),
        "chainage": record.get("chainage"),
        "end_chainage": record.get("end_chainage"),
        "contact_person": record.get("contact_person"),
        "created_by_user_id": record.get("created_by_user_id"),
        "last_updated_by_user_id": record.get("last_updated_by_user_id"),
        "created_by_user_name": record.get("created_by_user_name"),
        "last_updated_by_user_name": record.get("last_updated_by_user_name"),
        "images": list(record.get("images") or []),
    }


def fingerprint(rec):
    """Stable fingerprint of a snapshot for change detection."""
    return json.dumps(snapshot(rec), sort_keys=True, ensure_ascii=False)


def fetch_all_closures():
    """Fetch the full closure history via the paginated JSON endpoint.

    The API returns {"data": {"data": [...], "total_rows": N}} with a fixed
    page size of 10, so we loop pages (page=1, 2, ...) until we have collected
    total_rows records.
    """
    records = []
    page = 1
    total_rows = None

    while total_rows is None or len(records) < total_rows:
        payload = {"year": 0, "month": 0, "page": page}
        response = requests.post(API_URL, data=json.dumps(payload), headers=API_HEADERS, timeout=30)
        response.raise_for_status()
        inner = (response.json().get("data") or {})

        total_rows = int(inner.get("total_rows") or 0)
        batch = inner.get("data") or []
        records.extend(batch)

        if not batch:
            break
        page += 1

    return records


def load_state():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        print(f"Warning: Could not read state file {STATE_FILE}: {e}")
        return None


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def detect_changes(records, state):
    """Return (current_snapshots, new_ids, modified_ids, removed_ids).

    current_snapshots: {id: snapshot} for all fetched records.
    removed_ids are ids present in the previous state but no longer returned.
    """
    current = {r["id"]: snapshot(r) for r in records if r.get("id") is not None}

    new_ids = [cid for cid in current if cid not in state]
    modified_ids = [
        cid
        for cid in current
        if cid in state and fingerprint(current[cid]) != fingerprint(state[cid])
    ]
    removed_ids = [sid for sid in state if sid not in current]
    return current, new_ids, modified_ids, removed_ids


def build_embed(record, action):
    """Build a status-driven Discord embed for a closure change.

    Title/color/emoji reflect the closure's current status:
      CLOSED  -> blocked  (red, "🚧 Road Blocked")
      PARTIAL -> partial  (yellow, "🚦 Road Partially Open")
      OPEN    -> open     (green, "✅ Road Cleared")
    `record` may be a full API record or a stored snapshot (used for removed).
    """
    # A removed closure (gone from the API) is shown as cleared.
    status = "open" if action == "REMOVED" else classify_status(record.get("closure_type"))
    meta = build_status_meta(record)[status]

    road = record.get("road_name") or "Unknown road"
    images = record.get("images") or []
    lat = record.get("latitude")
    lon = record.get("longitude")

    fields = []
    fields.append({"name": "🆔 Navigate ID", "value": str(record.get("id") or "-"), "inline": True})
    fields.append({"name": "📊 Status", "value": meta["label"], "inline": True})
    fields.append({
        "name": "🛣️ Road Name",
        "value": f"{record.get('road_refno') or '-'} - {road}",
        "inline": False,
    })
    location = f"{record.get('district') or ''} {record.get('location') or ''}".strip()
    fields.append({"name": "📍 Location", "value": location or "-", "inline": False})

    if record.get("date_roadblock_start"):
        fields.append({
            "name": "⛔ Started",
            "value": fmt_ad_bs(record.get("date_roadblock_start")),
            "inline": True,
        })

    # Blocked-only: repair ETA + estimated end (only while there is no actual end).
    if status == "blocked" and not record.get("date_roadblock_end"):
        if record.get("repair_eta"):
            fields.append({"name": "⏳ Repair ETA", "value": str(record.get("repair_eta")), "inline": True})
        if record.get("date_roadblock_end_estimated"):
            fields.append({
                "name": "⏱️ Estimated",
                "value": fmt_ad_bs(record.get("date_roadblock_end_estimated")),
                "inline": True,
            })

    # Ended only for partial/open.
    if status in ("partial", "open") and record.get("date_roadblock_end"):
        fields.append({"name": "🛠️ Actual Repair Time", "value": str(record.get("actual_repair_time")), "inline": True})
        fields.append({
            "name": "🏁 Ended",
            "value": fmt_ad_bs(record.get("date_roadblock_end")),
            "inline": True,
        })

    fields.append({"name": "📋 Closure Reason", "value": record.get("closure_reason") or "-", "inline": False})
    fields.append({"name": "🔧 Efforts", "value": record.get("efforts_being_made") or "-", "inline": False})
    fields.append({"name": "📝 Remarks", "value": record.get("remarks") or "-", "inline": False})

    if lat is not None and lon is not None:
        fields.append({"name": "🌐 Coordinates", "value": f"{lat}, {lon}", "inline": True})
        wme_url = f"https://www.waze.com/editor?env=row&lat={lat}&lon={lon}&zoomLevel=17&marker=true"
        fields.append({"name": "🗺️ Open in WME", "value": f"[Open in Waze Map Editor]({wme_url})", "inline": False})

    embed = {
        "title": meta["title"],
        "color": meta["color"],
        "fields": fields,
        "footer": {"text": "source: DoR Navigate · navigate.dor.gov.np"},
    }
    if images:
        embed["image"] = {"url": images[0]}

    return embed


def build_embeds(record, action):
    """Build every Discord embed for a closure change as a single list.

    Discord allows only one image per embed but up to 10 embeds per message.
    To keep all of a closure's photos in ONE unified gallery card (same accent
    bar / title), every embed here shares the same `url`: when multiple embeds
    in a message carry an identical `url`, Discord's client merges them into a
    single multi-image card. The primary card (from build_embed) shows the
    first image; each additional image becomes its own image embed that also
    shares that common target url.
    """
    embeds = [build_embed(record, action)]
    images = record.get("images") or []
    # build_embed already used images[0]; add the rest (main + 9 = 10 max).
    for url in images[1:10]:
        embeds.append({"image": {"url": url}})
    # Share one target url across every embed so Discord groups them into a
    # single gallery card (unofficial client-side behaviour).
    for e in embeds:
        e["url"] = SOURCE_URL
    return embeds


def build_status_meta(record):
    """Build the status metadata table for a given closure record.

    Titles include the record's road_refno, so this must be called with the
    actual record (module-level constants cannot reference a per-record value).
    Returns a dict keyed by status: blocked / partial / open.
    """
    road = record.get("road_refno") or "Road"
    return {
        "blocked": {"title": f"🚧 {road} Blocked", "label": "Road Blocked", "color": 0xE74C3C},
        "partial": {"title": f"🚦 {road} Partially Opened", "label": "Road Partially Opened", "color": 0xF1C40F},
        "open": {"title": f"✅ {road} Cleared", "label": "Road Opened", "color": 0x2ECC71},
    }


def classify_status(closure_type):
    """Map a DOR closure_type to a status key: blocked / partial / open."""
    t = (closure_type or "").strip().upper()
    if "CLOSED" in t:
        return "blocked"
    if "PARTIAL" in t:
        return "partial"
    return "open"


def fmt_ad_bs(dt_str):
    """Return 'AD (वि.सं. BS)' for a date string, or None if empty."""
    if not dt_str:
        return None
    bs = convert_dt_to_bs(dt_str)
    return f"{dt_str} (वि.सं. {bs})" if bs else str(dt_str)


def send_embed(embed_or_embeds, dry_run=False):
    # Accept a single embed (kept for preview/test tools) or a list of embeds
    # (from build_embeds) so all images of one closure post in a single message.
    embeds = embed_or_embeds if isinstance(embed_or_embeds, list) else [embed_or_embeds]
    payload = {"embeds": embeds}
    if dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print("-" * 70)
        return 0

    success = 0
    for url in WEBHOOK_URLS:
        try:
            response = requests.post(url, json=payload)
            if response.status_code in (200, 204):
                success += 1
                print(f"Update sent to webhook {url[:30]}... successfully!")
            else:
                print(f"Failed to send to webhook {url[:30]}... (HTTP {response.status_code})")
        except requests.exceptions.RequestException as e:
            print(f"Error sending update to webhook {url[:30]}... Error: {e}")
    return success


def run_monitor(dry_run=False):
    if not WEBHOOK_URLS and not dry_run:
        print("Error: No DISCORD_WEBHOOK_URL_KID4RM90S / DISCORD_WEBHOOK_URL_NAVIGATE environment variables are set.")
        raise ValueError("No Discord webhooks are configured")

    records = fetch_all_closures()
    print(f"Fetched {len(records)} records.")

    state = load_state()

    if state is None:
        # First run: seed silently so we don't flood notifications.
        save_state({r["id"]: snapshot(r) for r in records if r.get("id") is not None})
        print(f"First run: seeded {len(records)} closures. No notifications sent.")
        return

    current, new_ids, modified_ids, removed_ids = detect_changes(records, state)
    print(f"Changes -> new: {len(new_ids)}, modified: {len(modified_ids)}, removed: {len(removed_ids)}")

    total_sent = 0
    for cid in new_ids:
        embeds = build_embeds(current[cid], "NEW")
        total_sent += send_embed(embeds, dry_run=dry_run)
    for cid in modified_ids:
        embeds = build_embeds(current[cid], "MODIFIED")
        total_sent += send_embed(embeds, dry_run=dry_run)
    for sid in removed_ids:
        embeds = build_embeds(state[sid], "REMOVED")
        total_sent += send_embed(embeds, dry_run=dry_run)

    # Persist the new active state (removed ids drop out).
    save_state(current)
    print(f"State saved to {STATE_FILE}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    try:
        run_monitor(dry_run=dry_run)
    except Exception as e:  # noqa: BLE001 - top-level fatal error handler
        print(f"Fatal error: {e}")
        sys.exit(1)
