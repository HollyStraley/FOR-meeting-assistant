"""
Core processing logic shared by app.py and watcher.py.
"""
import json
from datetime import datetime
from pathlib import Path

CLOSED_HISTORY_FILE = "closed_items_history.json"
MEETING_HISTORY_FILE = "meeting_history.json"
WATCH_HISTORY_FILE = "watch_items_history.json"
OPEN_HISTORY_FILE = "open_items_history.json"
DEFAULT_ROSTER_FILE = "roster.json"


def _load_json(path: str) -> list:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def _save_json(path: str, data):
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_roster(roster_path: str = DEFAULT_ROSTER_FILE) -> dict:
    return json.loads(Path(roster_path).read_text(encoding="utf-8"))


def detect_carry_overs(open_items: list[dict], open_history: list[dict]) -> list[dict]:
    for item in open_items:
        req_id = str(item.get("request_id", "")).strip().lower()
        current_status = item.get("status", "").strip().lower()
        consecutive = 0

        for past_run in open_history:
            past_lookup = {
                str(i.get("request_id", "")).strip().lower(): i.get("status", "").strip().lower()
                for i in past_run.get("items", [])
            }
            if req_id in past_lookup:
                consecutive += 1
                if past_lookup[req_id] != current_status:
                    break
            else:
                break

        item["consecutive_meetings"] = consecutive + 1
        item["carry_over_flag"] = (consecutive + 1) >= 3

    return open_items


def process_transcript(transcript_text: str, output_path: str, roster_path: str = DEFAULT_ROSTER_FILE) -> dict:
    from llm import extract_action_items
    from excel_output import save_excel

    roster = load_roster(roster_path)
    print(f"Roster loaded: {len(roster['members'])} members, {len(roster['flag_rules'])} flag rules")
    print("Calling Claude API to extract action items...")

    result = extract_action_items(transcript_text, roster)

    open_items = result.get("open_items", [])
    new_closed = result.get("closed_items", [])
    new_watch = result.get("watch_items", [])
    meeting = result.get("meeting", {})

    print(f"Meeting date: {meeting.get('date', 'Unknown')} | Duration: {meeting.get('duration', 'Unknown')}")
    print(f"Attendees: {', '.join(meeting.get('attendees', []))}")
    print(f"Open: {len(open_items)} | Closed: {len(new_closed)} | Watch: {len(new_watch)}")

    flagged = [i for i in open_items if i.get("flags")]
    if flagged:
        print(f"Flagged: {len(flagged)} item(s)")
        for item in flagged:
            print(f"  - {item['request_id']}: {', '.join(item['flags'])}")

    low_conf = [i for i in open_items if i.get("owner_confidence") == "Low" or i.get("priority_confidence") == "Low"]
    if low_conf:
        print(f"Low confidence: {len(low_conf)} item(s)")

    open_history = _load_json(OPEN_HISTORY_FILE)
    open_items = detect_carry_overs(open_items, open_history)
    result["open_items"] = open_items

    carry_overs = [i for i in open_items if i.get("carry_over_flag")]
    if carry_overs:
        print(f"Carry-overs (3+ meetings): {len(carry_overs)} item(s)")
        for item in carry_overs:
            print(f"  - {item['request_id']}: {item['consecutive_meetings']} consecutive meetings")

    open_history.insert(0, {
        "meeting_date": meeting.get("date", "Unknown"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "items": [{"request_id": i.get("request_id"), "status": i.get("status", "")} for i in open_items],
    })

    closed_history = _load_json(CLOSED_HISTORY_FILE)
    watch_history = _load_json(WATCH_HISTORY_FILE)
    meeting_history = _load_json(MEETING_HISTORY_FILE)

    meeting["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    meeting_history.insert(0, meeting)

    updated_closed, updated_watch = save_excel(result, closed_history, watch_history, meeting_history, output_path)

    _save_json(CLOSED_HISTORY_FILE, updated_closed)
    _save_json(WATCH_HISTORY_FILE, updated_watch)
    _save_json(OPEN_HISTORY_FILE, open_history)
    _save_json(MEETING_HISTORY_FILE, meeting_history)

    print(f"\nDone! Output: {output_path}")
    return result
