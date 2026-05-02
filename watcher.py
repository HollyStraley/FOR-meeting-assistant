"""
FOR Meeting Assistant — Folder Watcher
Watches the `transcripts/` folder for new .txt files and auto-processes them.
Excel output is saved to the `output/` folder.

Usage: python watcher.py
"""
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

WATCH_FOLDER = Path("transcripts")
OUTPUT_FOLDER = Path("output")
ROSTER_FILE = "roster.json"
POLL_INTERVAL = 5  # seconds between checks


def setup_folders():
    WATCH_FOLDER.mkdir(exist_ok=True)
    OUTPUT_FOLDER.mkdir(exist_ok=True)


def get_processed_log() -> set:
    log_path = Path(".processed_transcripts.log")
    if log_path.exists():
        return set(log_path.read_text(encoding="utf-8").splitlines())
    return set()


def mark_processed(filename: str):
    log_path = Path(".processed_transcripts.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(filename + "\n")


def process_file(txt_path: Path):
    from processor import process_transcript

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_FOLDER / f"FOR_actions_{txt_path.stem}_{timestamp}.xlsx"

    print(f"\n{'='*60}")
    print(f"New transcript detected: {txt_path.name}")
    print(f"Output: {output_path}")
    print(f"{'='*60}")

    try:
        transcript_text = txt_path.read_text(encoding="utf-8")
        process_transcript(transcript_text, str(output_path), ROSTER_FILE)
        mark_processed(txt_path.name)
        print(f"Processed successfully: {output_path.name}")
    except Exception as e:
        print(f"ERROR processing {txt_path.name}: {e}")


def main():
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.")
        sys.exit(1)

    if not Path(ROSTER_FILE).exists():
        print(f"ERROR: Roster file not found: {ROSTER_FILE}")
        sys.exit(1)

    setup_folders()
    processed = get_processed_log()

    print(f"FOR Meeting Assistant — Folder Watcher")
    print(f"Watching: {WATCH_FOLDER.resolve()}")
    print(f"Output:   {OUTPUT_FOLDER.resolve()}")
    print(f"Drop any .txt transcript file into the watched folder to auto-process.")
    print(f"Press Ctrl+C to stop.\n")

    try:
        while True:
            txt_files = sorted(WATCH_FOLDER.glob("*.txt"))
            for txt_path in txt_files:
                if txt_path.name not in processed:
                    process_file(txt_path)
                    processed.add(txt_path.name)
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\nWatcher stopped.")


if __name__ == "__main__":
    main()
