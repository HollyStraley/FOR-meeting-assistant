"""
FOR Meeting Assistant
Usage:
  python app.py <transcript_file>         # process a .txt file
  python app.py --paste                   # paste transcript directly in terminal
  python app.py <file> --output out.xlsx  # custom output path
  python app.py <file> --roster my.json   # custom roster
"""
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="FOR Meeting Assistant — transcript to Excel action items")
    parser.add_argument("transcript", nargs="?", help="Path to the meeting transcript (.txt file)")
    parser.add_argument("--paste", action="store_true", help="Paste transcript text directly in the terminal")
    parser.add_argument("--output", "-o", help="Output Excel file path (default: FOR_actions_<date>.xlsx)")
    parser.add_argument("--roster", "-r", default="roster.json", help="Path to roster JSON (default: roster.json)")
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.")
        sys.exit(1)

    if not args.paste and not args.transcript:
        parser.print_help()
        sys.exit(1)

    roster_path = Path(args.roster)
    if not roster_path.exists():
        print(f"ERROR: Roster file not found: {roster_path}")
        sys.exit(1)

    output_path = args.output or f"FOR_actions_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

    if args.paste:
        print("Paste your transcript below.")
        print("When done, press Enter then Ctrl+Z then Enter (Windows) or Ctrl+D (Mac/Linux).")
        print("-" * 60)
        try:
            transcript_text = sys.stdin.read()
        except KeyboardInterrupt:
            print("\nCancelled.")
            sys.exit(0)
        if not transcript_text.strip():
            print("ERROR: No transcript text received.")
            sys.exit(1)
    else:
        transcript_path = Path(args.transcript)
        if not transcript_path.exists():
            print(f"ERROR: Transcript file not found: {transcript_path}")
            sys.exit(1)
        transcript_text = transcript_path.read_text(encoding="utf-8")
        print(f"Reading transcript: {transcript_path}")

    from processor import process_transcript
    process_transcript(transcript_text, output_path, args.roster)


if __name__ == "__main__":
    main()
