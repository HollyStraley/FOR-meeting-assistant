"""
FOR Meeting Assistant
Usage: python app.py <transcript_file> [--output <excel_file>] [--roster <roster_file>]
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CLOSED_HISTORY_FILE = "closed_items_history.json"
MEETING_HISTORY_FILE = "meeting_history.json"
WATCH_HISTORY_FILE = "watch_items_history.json"


def load_closed_history() -> list[dict]:
    path = Path(CLOSED_HISTORY_FILE)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def save_closed_history(history: list[dict]):
    Path(CLOSED_HISTORY_FILE).write_text(
        json.dumps(history, indent=2), encoding="utf-8"
    )


def load_meeting_history() -> list[dict]:
    path = Path(MEETING_HISTORY_FILE)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def save_meeting_history(history: list[dict]):
    Path(MEETING_HISTORY_FILE).write_text(
        json.dumps(history, indent=2), encoding="utf-8"
    )


def load_watch_history() -> list[dict]:
    path = Path(WATCH_HISTORY_FILE)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def save_watch_history(history: list[dict]):
    Path(WATCH_HISTORY_FILE).write_text(
        json.dumps(history, indent=2), encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(description="FOR Meeting Assistant — transcript to Excel action items")
    parser.add_argument("transcript", help="Path to the meeting transcript (.txt file)")
    parser.add_argument("--output", "-o", help="Output Excel file path (default: FOR_actions_<date>.xlsx)")
    parser.add_argument("--roster", "-r", default="roster.json", help="Path to roster JSON (default: roster.json)")
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.")
        print("Set it in a .env file or export it in your shell.")
        sys.exit(1)

    transcript_path = Path(args.transcript)
    if not transcript_path.exists():
        print(f"ERROR: Transcript file not found: {transcript_path}")
        sys.exit(1)

    roster_path = Path(args.roster)
    if not roster_path.exists():
        print(f"ERROR: Roster file not found: {roster_path}")
        sys.exit(1)

    transcript = transcript_path.read_text(encoding="utf-8")
    roster = json.loads(roster_path.read_text(encoding="utf-8"))

    output_path = args.output or f"FOR_actions_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

    print(f"Reading transcript: {transcript_path}")
    print(f"Roster loaded: {len(roster['members'])} members, {len(roster['flag_rules'])} flag rules")
    print("Calling Claude API to extract action items...")

    from llm import extract_action_items
    result = extract_action_items(transcript, roster)

    open_items = result.get("open_items", [])
    new_closed = result.get("closed_items", [])
    new_watch = result.get("watch_items", [])
    meeting = result.get("meeting", {})


    print(f"Meeting date: {meeting.get('date', 'Unknown')} | Duration: {meeting.get('duration', 'Unknown')}")
    print(f"Attendees: {', '.join(meeting.get('attendees', []))}")
    print(f"Open items: {len(open_items)} | Newly closed: {len(new_closed)} | Watch items: {len(new_watch)}")

    flagged = [i for i in open_items if i.get("flags")]
    if flagged:
        print(f"Flagged open items: {len(flagged)}")
        for item in flagged:
            print(f"  - {item['request_id']}: {', '.join(item['flags'])}")

    low_confidence = [i for i in open_items if i.get("owner_confidence") == "Low" or i.get("priority_confidence") == "Low"]
    if low_confidence:
        print(f"Low confidence items: {len(low_confidence)}")
        for item in low_confidence:
            print(f"  - {item['request_id']}: {item.get('confidence_notes', '')}")

    closed_history = load_closed_history()
    prev_closed_count = len(closed_history)

    watch_history = load_watch_history()
    prev_watch_count = len(watch_history)

    meeting_history = load_meeting_history()
    meeting["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    meeting_history.insert(0, meeting)

    from excel_output import save_excel
    updated_closed_history, updated_watch_history = save_excel(
        result, closed_history, watch_history, meeting_history, output_path
    )

    save_closed_history(updated_closed_history)
    save_watch_history(updated_watch_history)
    save_meeting_history(meeting_history)

    print(f"Closed history: {prev_closed_count} existing + {len(updated_closed_history) - prev_closed_count} new = {len(updated_closed_history)} total")
    print(f"Watch history: {prev_watch_count} existing + {len(updated_watch_history) - prev_watch_count} new = {len(updated_watch_history)} total")
    print(f"Meeting history: {len(meeting_history)} total meeting(s) on record")
    print(f"\nDone! Open: {output_path}")


if __name__ == "__main__":
    main()
