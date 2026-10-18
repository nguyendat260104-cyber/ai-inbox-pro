#!/usr/bin/env python3
"""
Affiliate Link Redirection & Click Tracking Engine
Resolves short slugs (e.g. 'make', 'hostinger') to target affiliate links with subid tracking parameters.
Logs clicks locally to config/links.json and metrics/daily/click_log.json.
"""

import sys
import os
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def get_base_dir() -> Path:
    return Path(__file__).resolve().parent.parent

def resolve_redirect(slug: str, subid: Optional[str] = None, channel: Optional[str] = None, base_dir: Optional[Path] = None) -> Optional[str]:
    if base_dir is None:
        base_dir = get_base_dir()

    config_path = base_dir / "config" / "links.json"
    if not config_path.exists():
        return None

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    links = data.get("links", {})
    clean_slug = slug.strip().lower()
    if clean_slug not in links:
        return None

    entry = links[clean_slug]
    dest_base = entry.get("destination_url", "")
    aff_param = entry.get("affiliate_param", "ref")
    aff_id = entry.get("affiliate_id", "")
    sub_param = entry.get("subid_param", "subid")
    target_sub = subid or entry.get("target_subid", "organic")

    separator = "&" if "?" in dest_base else "?"
    final_url = f"{dest_base}{separator}{aff_param}={aff_id}&{sub_param}={target_sub}"
    if channel:
        final_url += f"&utm_source={channel}"

    # Increment click count locally
    entry["clicks_total"] = entry.get("clicks_total", 0) + 1
    entry["last_clicked_at"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    # Log click event
    click_log_file = base_dir / "metrics" / "daily" / "click_log.json"
    click_log_file.parent.mkdir(parents=True, exist_ok=True)
    events = []
    if click_log_file.exists():
        try:
            with open(click_log_file, "r", encoding="utf-8") as lf:
                events = json.load(lf)
        except Exception:
            events = []

    events.append({
        "slug": clean_slug,
        "name": entry.get("name"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subid": target_sub,
        "channel": channel or "direct",
        "redirected_to": final_url
    })

    try:
        with open(click_log_file, "w", encoding="utf-8") as lf:
            json.dump(events[-500:], lf, indent=2, ensure_ascii=False)
    except Exception:
        pass

    return final_url

def main():
    parser = argparse.ArgumentParser(description="Resolve affiliate short link and log clicks.")
    parser.add_argument("--slug", required=True, help="Slug key (e.g. make, hostinger, elevenlabs)")
    parser.add_argument("--subid", help="Optional tracking subid override")
    parser.add_argument("--channel", help="Optional channel source (e.g. tiktok, youtube)")

    args = parser.parse_args()
    target = resolve_redirect(slug=args.slug, subid=args.subid, channel=args.channel)
    if target:
        print(f"🔗 Target Redirect URL:")
        print(f"   {target}")
    else:
        print(f"❌ Unknown slug: '{args.slug}'. Check config/links.json", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
