#!/usr/bin/env python3
"""
Pulls pending assignments (Completed = false, has a Due Date) from a
Notion Homework database and writes an ICS calendar feed to
docs/homework.ics. That file, once pushed to a repo with GitHub Pages
enabled, becomes a public URL you can subscribe to from Fantastical,
Apple Calendar, Google Calendar, etc.

Requires two environment variables (set as GitHub Actions secrets):
  NOTION_TOKEN        - your Notion internal integration secret
  NOTION_DATABASE_ID  - the Homework database ID
"""

import os
import sys
from datetime import datetime, timezone

import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
NOTION_VERSION = "2022-06-28"
OUTPUT_PATH = "docs/homework.ics"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def fetch_assignments():
    """Query Notion for all pending pages with a Due Date, paging through results."""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    base_payload = {
        "filter": {
            "and": [
                {"property": "Due Date", "date": {"is_not_empty": True}},
                {"property": "Completed", "checkbox": {"equals": False}},
            ]
        },
        "sorts": [{"property": "Due Date", "direction": "ascending"}],
        "page_size": 100,
    }

    results = []
    cursor = None
    while True:
        body = dict(base_payload)
        if cursor:
            body["start_cursor"] = cursor
        resp = requests.post(url, headers=HEADERS, json=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        results.extend(data["results"])
        if not data.get("has_more"):
            break
        cursor = data["next_cursor"]
    return results


def escape_text(text):
    """Escape text per RFC 5545 (backslash, semicolon, comma, newline)."""
    if not text:
        return ""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def get_plain_text(rich_text_list):
    return "".join(t.get("plain_text", "") for t in rich_text_list)


def page_to_event_lines(page):
    props = page["properties"]

    name = get_plain_text(props.get("Name", {}).get("title", [])) or "Untitled assignment"

    course = ""
    if props.get("Course", {}).get("select"):
        course = props["Course"]["select"]["name"]

    a_type = ""
    if props.get("Type", {}).get("select"):
        a_type = props["Type"]["select"]["name"]

    comments = get_plain_text(props.get("Comments", {}).get("rich_text", []))

    due = props.get("Due Date", {}).get("date")
    if not due or not due.get("start"):
        return None
    start_raw = due["start"]
    is_datetime = "T" in start_raw

    summary = f"{name} ({course})" if course else name

    desc_lines = []
    if a_type:
        desc_lines.append(f"Type: {a_type}")
    if comments:
        desc_lines.append(comments)
    description = "\\n".join(escape_text(l) for l in desc_lines)

    uid = f"{page['id']}@notion-homework"
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{dtstamp}"]

    if is_datetime:
        dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
        dt_utc = dt.astimezone(timezone.utc)
        lines.append(f"DTSTART:{dt_utc.strftime('%Y%m%dT%H%M%SZ')}")
    else:
        lines.append(f"DTSTART;VALUE=DATE:{start_raw.replace('-', '')}")

    lines.append(f"SUMMARY:{escape_text(summary)}")
    if description:
        lines.append(f"DESCRIPTION:{description}")
    lines.append("END:VEVENT")
    return lines


def build_ics(pages):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//notion-homework-sync//EN",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:Homework",
    ]
    for page in pages:
        event_lines = page_to_event_lines(page)
        if event_lines:
            lines.extend(event_lines)
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main():
    pages = fetch_assignments()
    ics_content = build_ics(pages)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(ics_content)
    print(f"Wrote {len(pages)} assignments to {OUTPUT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
