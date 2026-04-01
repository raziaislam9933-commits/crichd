#!/usr/bin/env python3
"""
CricHD Cricket Stream Scraper
Scrapes live cricket m3u8 streams from CricHD and outputs:
  - JSON file with all stream data (m3u8 URLs, channel info, headers)
  - M3U playlist file compatible with IPTV players (NS Player, VLC, Tivimate, etc.)

Author: Auto-generated
"""

import urllib.request
import urllib.error
import re
import json
import time
import os
import sys
from datetime import datetime, timezone

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STREAMS_DIR = os.path.join(BASE_DIR, "streams")
JSON_OUTPUT = os.path.join(STREAMS_DIR, "crichd_streams.json")
M3U_OUTPUT = os.path.join(STREAMS_DIR, "crichd_cricket.m3u")

# CricHD channel definitions
# channel_id: ID used on CricHD pages (for playerado.top/embed2.php)
# fid: Internal player ID (mapped from CricHD -> dadocric.st -> player0003.com)
# name: Human-readable channel name
# group: Grouping for M3U playlist
# logo: Channel logo URL (optional)
# lang: Channel language
CHANNELS = [
    # --- English Channels ---
    {"channel_id": "willow",    "fid": "dowill",     "name": "Willow Cricket",        "group": "English",    "logo": "", "lang": "English"},
    {"channel_id": "willowhd",  "fid": "hdowill",    "name": "Willow HD",             "group": "English",    "logo": "", "lang": "English"},
    {"channel_id": "starsp",    "fid": "star1kim",   "name": "Star Sports 1",         "group": "English",    "logo": "", "lang": "English"},
    {"channel_id": "starsp2",   "fid": "str2cws",    "name": "Star Sports 2",         "group": "English",    "logo": "", "lang": "English"},
    {"channel_id": "crich2",    "fid": "dodosky2",   "name": "Sky Sports Cricket",    "group": "English",    "logo": "", "lang": "English"},
    {"channel_id": "tensp",     "fid": "tensp",      "name": "Ten Sports",            "group": "English",    "logo": "", "lang": "English"},
    {"channel_id": "foxsports", "fid": "foxcric",    "name": "Fox Sports Cricket",    "group": "English",    "logo": "", "lang": "English"},

    # --- Hindi / Regional ---
    {"channel_id": "starsp3",    "fid": "str1hil",     "name": "Star Sports Hindi",     "group": "Hindi",     "logo": "", "lang": "Hindi"},
    {"channel_id": "willowextra","fid": "dwil2",       "name": "Willow Xtra",           "group": "Hindi",     "logo": "", "lang": "Hindi"},
    {"channel_id": "starsp1tam", "fid": "star1tamil",  "name": "Star Sports Tamil",     "group": "Regional",  "logo": "", "lang": "Tamil"},
    {"channel_id": "starsp1telu","fid": "star1telu",   "name": "Star Sports Telugu",    "group": "Regional",  "logo": "", "lang": "Telugu"},

    # --- Pakistan Channels ---
    {"channel_id": "ptvsp",    "fid": "ptvscpr",    "name": "PTV Sports",          "group": "Pakistan",  "logo": "", "lang": "Urdu"},
    {"channel_id": "asports",  "fid": "asportsd",   "name": "A Sports",            "group": "Pakistan",  "logo": "", "lang": "Urdu"},
    {"channel_id": "geosuper", "fid": "geosp",      "name": "Geo Super",           "group": "Pakistan",  "logo": "", "lang": "Urdu"},
    {"channel_id": "tsports",  "fid": "tsportshd",  "name": "T Sports HD",         "group": "Pakistan",  "logo": "", "lang": "Bengali"},

    # --- Other International ---
    {"channel_id": "supersport", "fid": "sscricket", "name": "SuperSport Cricket",  "group": "International", "logo": "", "lang": "English"},
    {"channel_id": "astrosports","fid": "astrocric", "name": "Astro Cricket",       "group": "International", "logo": "", "lang": "English"},
    {"channel_id": "criclife1",  "fid": "cl1stream", "name": "CricLife 1",          "group": "International", "logo": "", "lang": "English"},
    {"channel_id": "criclife2",  "fid": "cl2stream", "name": "CricLife 2",          "group": "International", "logo": "", "lang": "English"},
    {"channel_id": "sonyten1",   "fid": "sonyten1",  "name": "Sony Sports Ten 1",   "group": "International", "logo": "", "lang": "English"},
    {"channel_id": "sonyten2",   "fid": "sonyten2",  "name": "Sony Sports Ten 2",   "group": "International", "logo": "", "lang": "English"},
    {"channel_id": "sonyten5",   "fid": "sonyten5",  "name": "Sony Sports Ten 5",   "group": "International", "logo": "", "lang": "English"},
    {"channel_id": "willow2",    "fid": "willow2",   "name": "Willow 2",            "group": "International", "logo": "", "lang": "English"},
]

# Player URLs
EMBED_URL = "https://playerado.top/embed2.php?id={channel_id}"
PLAYER_URL = "https://player0003.com/atplay.php?v={fid}&hello={v_con}&expires={v_dt}"

# Required headers
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
REFERER = "https://player0003.com/"
ORIGIN = "https://playerado.top"

REQUEST_TIMEOUT = 15  # seconds
RETRY_COUNT = 2
RETRY_DELAY = 3  # seconds


# ============================================================
# HTTP HELPERS
# ============================================================

def create_opener():
    """Create a URL opener with browser headers."""
    opener = urllib.request.build_opener()
    opener.addheaders = [
        ("User-Agent", USER_AGENT),
        ("Accept", "*/*"),
        ("Accept-Language", "en-US,en;q=0.9"),
    ]
    return opener


def fetch_url(opener, url, extra_headers=None, timeout=REQUEST_TIMEOUT):
    """Fetch a URL with optional extra headers. Returns response text or None."""
    for attempt in range(RETRY_COUNT + 1):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", USER_AGENT)
            if extra_headers:
                for key, val in extra_headers.items():
                    req.add_header(key, val)
            resp = opener.open(req, timeout=timeout)
            return resp.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            if e.code == 403 and attempt < RETRY_COUNT:
                time.sleep(RETRY_DELAY)
                continue
            print(f"  HTTP {e.code} for {url}")
            return None
        except urllib.error.URLError as e:
            if attempt < RETRY_COUNT:
                time.sleep(RETRY_DELAY)
                continue
            print(f"  URL Error: {e.reason} for {url}")
            return None
        except Exception as e:
            if attempt < RETRY_COUNT:
                time.sleep(RETRY_DELAY)
                continue
            print(f"  Error: {e} for {url}")
            return None
    return None


# ============================================================
# SCRAPER LOGIC
# ============================================================

def get_embed_params(opener, channel_id):
    """
    Step 1: Fetch embed page to get v_con, v_dt, and fid.
    Returns dict with v_con, v_dt, fid or None.
    """
    url = EMBED_URL.format(channel_id=channel_id)
    html = fetch_url(opener, url, {"Referer": ORIGIN})

    if not html:
        return None

    v_con_m = re.search(r'v_con="([^"]+)"', html)
    v_dt_m = re.search(r'v_dt="([^"]+)"', html)

    if not v_con_m or not v_dt_m:
        return None

    return {
        "v_con": v_con_m.group(1),
        "v_dt": v_dt_m.group(1),
    }


def get_player_page(opener, fid, v_con, v_dt):
    """
    Step 2: Fetch the player page that contains obfuscated m3u8 URL.
    Returns raw HTML or None.
    """
    url = PLAYER_URL.format(fid=fid, v_con=v_con, v_dt=v_dt)
    html = fetch_url(opener, url, {"Referer": ORIGIN, "Origin": ORIGIN})
    return html


def extract_m3u8_from_player(html):
    """
    Step 3: Extract m3u8 URL from the player page JavaScript.
    The m3u8 is built from a char array join pattern, plus appended
    token from hidden spans.
    """
    if not html:
        return None

    # Method 1: Look for char array join pattern that contains .m3u8
    char_arrays = re.findall(
        r'\[(?:\"[^\"]+\",\s*)+\"[^\"]+\"\]\.join\(\"\"\)',
        html
    )

    for arr in char_arrays:
        chars = re.findall(r'"([^"]+)"', arr)
        joined = "".join(chars)
        if ".m3u8" in joined:
            # Fix escaped slashes
            joined = joined.replace("\\/", "/")
            return joined

    # Method 2: Direct URL search
    direct = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', html)
    if direct:
        return direct[0].replace("\\/", "/")

    return None


def extract_channel_fid(html):
    """Extract the actual fid from player page if it differs from config."""
    if not html:
        return None
    m = re.search(r'fid="([^"]+)"', html)
    return m.group(1) if m else None


def scrape_channel(opener, channel):
    """
    Full pipeline for one channel:
      embed page -> player page -> extract m3u8
    Returns stream dict or None.
    """
    channel_id = channel["channel_id"]
    configured_fid = channel["fid"]

    # Step 1: Get embed params
    params = get_embed_params(opener, channel_id)
    if not params:
        return None

    # Step 2: Get player page
    player_html = get_player_page(
        opener,
        configured_fid,
        params["v_con"],
        params["v_dt"]
    )
    if not player_html:
        return None

    # Optionally discover the real fid from player page
    real_fid = extract_channel_fid(player_html)
    if real_fid and real_fid != configured_fid:
        # Retry with discovered fid
        player_html = get_player_page(
            opener,
            real_fid,
            params["v_con"],
            params["v_dt"]
        )

    # Step 3: Extract m3u8 URL
    m3u8_url = extract_m3u8_from_player(player_html)
    if not m3u8_url:
        return None

    # Determine the server
    server = "unknown"
    if "/hls/" in m3u8_url:
        server = m3u8_url.split("/hls/")[0]

    # Extract token info for reference
    md5_m = re.search(r'md5=([^&]+)', m3u8_url)
    expires_m = re.search(r'expires=(\d+)', m3u8_url)

    return {
        "name": channel["name"],
        "channel_id": channel_id,
        "group": channel["group"],
        "lang": channel["lang"],
        "logo": channel.get("logo", ""),
        "m3u8_url": m3u8_url,
        "server": server,
        "referer": REFERER,
        "user_agent": USER_AGENT,
        "md5": md5_m.group(1) if md5_m else "",
        "expires": int(expires_m.group(1)) if expires_m else 0,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "status": "online",
    }


def scrape_all_channels():
    """Scrape all configured channels. Returns list of stream dicts."""
    opener = create_opener()
    results = []

    print(f"Starting scrape of {len(CHANNELS)} channels...")
    print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    for i, channel in enumerate(CHANNELS, 1):
        name = channel["name"]
        channel_id = channel["channel_id"]
        print(f"[{i:2d}/{len(CHANNELS)}] {name} ({channel_id})...", end=" ", flush=True)

        stream = scrape_channel(opener, channel)

        if stream:
            results.append(stream)
            print(f"OK -> {stream['server'].split('//')[1]}")
        else:
            # Still add as offline entry
            results.append({
                "name": name,
                "channel_id": channel_id,
                "group": channel["group"],
                "lang": channel["lang"],
                "logo": channel.get("logo", ""),
                "m3u8_url": "",
                "server": "",
                "referer": REFERER,
                "user_agent": USER_AGENT,
                "md5": "",
                "expires": 0,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "status": "offline",
            })
            print("OFFLINE")

        # Small delay to be polite
        time.sleep(0.5)

    online_count = sum(1 for r in results if r["status"] == "online")
    print("=" * 60)
    print(f"Done! {online_count}/{len(CHANNELS)} channels online")

    return results


# ============================================================
# OUTPUT GENERATORS
# ============================================================

def write_json(streams):
    """Write the JSON file with all stream data."""
    data = {
        "source": "CricHD",
        "description": "Auto-scraped cricket live stream links from CricHD",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_channels": len(streams),
        "online_channels": sum(1 for s in streams if s["status"] == "online"),
        "offline_channels": sum(1 for s in streams if s["status"] == "offline"),
        "required_headers": {
            "User-Agent": USER_AGENT,
            "Referer": REFERER,
        },
        "streams": streams,
    }

    os.makedirs(os.path.dirname(JSON_OUTPUT), exist_ok=True)
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nJSON saved: {JSON_OUTPUT}")


def write_m3u(streams):
    """
    Write an M3U playlist file compatible with IPTV players.
    Supports NS Player, VLC, Tivimate, Perfect Player, etc.

    Format used:
      #EXTM3U header with metadata
      #EXTINF lines with channel info
      URL|Referer=...&User-Agent=...
    """
    os.makedirs(os.path.dirname(M3U_OUTPUT), exist_ok=True)

    lines = []
    lines.append('#EXTM3U')
    lines.append(f'# Generated by CricHD Scraper on {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")} UTC')
    lines.append(f'# Total channels: {len(streams)}')
    lines.append(f'# Online: {sum(1 for s in streams if s["status"] == "online")}')
    lines.append(f'# Required: User-Agent={USER_AGENT}')
    lines.append(f'# Required: Referer={REFERER}')
    lines.append('')

    for stream in streams:
        if stream["status"] != "online" or not stream["m3u8_url"]:
            # Add commented-out offline entry
            lines.append(f'# OFFLINE: {stream["name"]} ({stream["channel_id"]})')
            lines.append('')

        name = stream["name"]
        group = stream["group"]
        logo = stream.get("logo", "")
        m3u8_url = stream["m3u8_url"]
        lang = stream.get("lang", "")

        # EXTINF with full metadata
        extinf = f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="Cricket - {group}"'
        if lang:
            extinf += f' tvg-language="{lang}"'
        extinf += f',{name}'

        lines.append(extinf)

        # VLC-specific options (some players need this)
        lines.append(f'#EXTVLCOPT:http-user-agent={USER_AGENT}')
        lines.append(f'#EXTVLCOPT:http-referrer={REFERER}')

        # Stream URL with headers appended (pipe format for NS Player / Tivimate / etc.)
        lines.append(f'{m3u8_url}|Referer={urllib.parse.quote(REFERER)}&User-Agent={urllib.parse.quote(USER_AGENT)}')
        lines.append('')

    with open(M3U_OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"M3U saved: {M3U_OUTPUT}")


def write_simple_m3u(streams):
    """
    Write a simpler M3U file without pipe headers.
    Use this if your player doesn't support pipe-separated headers.
    The player will need to be configured separately with headers.
    """
    simple_path = os.path.join(STREAMS_DIR, "crichd_cricket_simple.m3u")

    lines = []
    lines.append('#EXTM3U')
    lines.append(f'# CricHD Cricket Streams - Simple format (no embedded headers)')
    lines.append(f'# Configure your player with: Referer={REFERER}')
    lines.append(f'# Configure your player with: User-Agent={USER_AGENT}')
    lines.append('')

    for stream in streams:
        if stream["status"] != "online" or not stream["m3u8_url"]:
            continue

        name = stream["name"]
        group = stream["group"]
        logo = stream.get("logo", "")

        lines.append(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="Cricket - {group}",{name}')
        lines.append(stream["m3u8_url"])
        lines.append('')

    with open(simple_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Simple M3U saved: {simple_path}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  CricHD Cricket Stream Scraper")
    print("  Scraping live cricket m3u8 streams...")
    print("=" * 60)
    print()

    # Scrape all channels
    streams = scrape_all_channels()

    # Generate outputs
    print()
    write_json(streams)
    write_m3u(streams)
    write_simple_m3u(streams)

    # Summary
    online = [s for s in streams if s["status"] == "online"]
    print()
    print("=" * 60)
    print("  ONLINE CHANNELS:")
    print("=" * 60)
    for s in online:
        print(f"  {s['name']:30s} | {s['group']:15s} | {s['lang']:10s}")

    print()
    print("Files updated:")
    print(f"  - {JSON_OUTPUT}")
    print(f"  - {M3U_OUTPUT}")
    print(f"  - {os.path.join(STREAMS_DIR, 'crichd_cricket_simple.m3u')}")
