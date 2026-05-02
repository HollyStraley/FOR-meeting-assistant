"""
FOR Meeting Assistant
Usage: python app.py <transcript_file> [--output <excel_file>] [--roster <roster_file>]
"""
import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


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

    from datetime import datetime
    output_path = args.output or f"FOR_actions_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

    print(f"Reading transcript: {transcript_path}")
    print(f"Roster loaded: {len(roster['members'])} members, {len(roster['flag_rules'])} flag rules")
    print("Calling Claude API to extract action items...")

    from llm import extract_action_items
    action_items = extract_action_items(transcript, roster)

    print(f"Extracted {len(action_items)} action item(s).")

    flagged = [i for i in action_items if i.get("flags")]
    if flagged:
        print(f"  Flagged items: {len(flagged)}")
        for item in flagged:
            print(f"    - Item {item['request_id']}: {', '.join(item['flags'])}")

    from excel_output import save_excel
    save_excel(action_items, output_path)
    print(f"\nDone! Open: {output_path}")


if __name__ == "__main__":
    main()
