# FOR Meeting Assistant

A Streamlit web app that reads SIOP (Sales, Inventory & Operations Planning) meeting transcripts and automatically extracts, tracks, and summarizes Firm Order Request (FOR) action items using the Claude AI API.

---

## What It Does

Paste or upload a meeting transcript and the app will:

- Identify every open and closed FOR action item discussed
- Assign and track unique FOR IDs (FOR-001, FOR-002, etc.) persistently across meetings
- Flag items that need attention based on configurable rules
- Detect carry-over items that have appeared in 3+ consecutive meetings with no status change
- Generate a formatted Excel workbook with 4 tabs
- Generate a copy-ready email draft summary for Teams or Outlook
- Track meeting history and trends over time on a live dashboard

---

## Features

### Core Processing (powered by Claude API)
- **LLM-powered extraction** — Uses `claude-sonnet-4-6` to read raw transcript text and extract structured action item data. No templates or keyword matching required; the model reads conversational language and infers context.
- **Structured JSON output** — The model returns a strict JSON schema including: requester, current owner, priority, status, action items, due date, flags, confidence scores, and a context summary per item.
- **Confidence scoring** — Each open item includes `owner_confidence` and `priority_confidence` (High / Medium / Low) with notes explaining any uncertainty. Useful when names or priorities are ambiguous in the transcript.
- **Watch items** — Items mentioned in conversation that are not yet formal FOR requests are captured separately (e.g., "we should keep an eye on this" or "nothing formal yet but worth watching").
- **Roster-aware extraction** — A `roster.json` file of team members (name, title, email) is injected into the LLM prompt as context, improving owner identification accuracy.
- **References lookup** — A `references.json` file maps FOR IDs to external tracking numbers, notes, and related files. Matched data is automatically attached to open items in the Excel output.

### FOR ID Management
- Auto-assigns `FOR-NNN` IDs to any item the LLM couldn't match to an existing ID
- Persists a counter (`for_id_counter.json`) so IDs never repeat across runs
- Records the first time each FOR ID is ever seen (`for_id_first_seen.json`) to enable cycle time tracking

### Flag Rules
Configurable rules in `roster.json` that the LLM uses to flag items automatically:
- **engine_country_move** — Triggered by keywords like: boom, booms, telehandler, telehandlers, engine, country, move, reallocation. Flags items that may involve cross-border engine or equipment movements.
- **long_pending** — Flags items that have been open without resolution for an extended period.

### Carry-Over Detection
- Compares open items across historical meeting runs
- Flags any item that has appeared in **3 or more consecutive meetings** with the same status
- Color-coded in Excel: yellow (3 meetings), amber (4), red (5+)
- Carry-over items are also highlighted in the email draft

### Excel Output (4 tabs)
1. **Open Action Items** — All currently open FORs with owner, priority, status, due date, flags, confidence scores, and carry-over indicator
2. **Closed Items** — Running historical log of all items ever closed, accumulated across every meeting processed
3. **Watch Items** — Informal pre-FOR items captured from conversation
4. **Meeting Summary** — Running log of all meeting summaries (date, duration, attendees, key discussion points), newest first

### Email Draft
After every run, a plain-text email draft is generated and saved alongside the Excel file. Sections include:
- Open action items with owner, priority, due date, and carry-over tags
- Flagged items with flag notes
- Carry-over summary
- Closed items resolved this meeting
- Watch items

### Streamlit Web UI (4 tabs)
- **Process Transcript** — Paste transcript text or enter the meeting date manually; run processing and download the Excel output and email draft directly from the browser
- **References** — View and edit the `references.json` file (tracking numbers, notes, linked files per FOR ID)
- **Roster** — View and edit team member list and flag rules
- **Dashboard** — Charts and metrics built from accumulated meeting history:
  - Open vs. closed item counts over time
  - Items by priority
  - Flagged item trends
  - Regional shift analysis (Europe, China, Asia-Pacific, LATAM, North America)
  - Equipment type breakdown (Boom, Telehandler, GX4, GX9, GT7, GT9)
  - Average days to close
  - Carry-over item trends

### Folder Watcher (`watcher.py`)
An optional background process that polls a `transcripts/` folder every 5 seconds. Drop a `.txt` transcript file into the folder and it is automatically processed — no UI interaction needed.

---

## Transcript Types Tested

The app was tested against a range of deliberately challenging transcript formats to validate robustness:

| Transcript | What It Tested |
|---|---|
| Standard SIOP meeting | Baseline: mix of open and closed FOR items discussed by name and ID |
| Items closed at meeting start | Verifying closed items go to the Closed tab and persist across runs |
| No direct FOR ID references | Model infers context and matches items without explicit IDs mentioned |
| Broken/non-native English | Fragmented sentences, grammar errors, mixed phrasing — model still extracts correctly |
| Watch items only | Conversation with no formal FORs but several items flagged as worth monitoring |
| Multi-region discussion | Items spanning Europe, China, LATAM, Asia-Pacific — regional trend detection |
| Carry-over scenario | Same items reappearing across 3+ meeting runs with no status change |
| Engine/equipment flag triggers | Transcripts mentioning booms, telehandlers, country reallocations — flag rule testing |
| Confidence scoring edge cases | Ambiguous ownership language, unclear priorities — Low confidence correctly assigned |

---

## Tech Stack

| Component | Technology |
|---|---|
| AI / LLM | Anthropic Claude API (`claude-sonnet-4-6`) |
| Web UI | Streamlit |
| Excel output | openpyxl |
| Environment config | python-dotenv |
| Hosting | Streamlit Community Cloud |
| Version control | GitHub |

---

## Project Structure

```
FOR meeting assistant/
├── streamlit_app.py        # Streamlit web UI
├── processor.py            # Core processing logic (shared by app + watcher)
├── llm.py                  # Claude API call + JSON parsing
├── prompts.py              # System and user prompts
├── excel_output.py         # Excel workbook generation (4 tabs, color coding)
├── email_draft.py          # Email draft generator
├── watcher.py              # Auto folder watcher
├── roster.json             # Team member list + flag rules
├── references.json         # External tracking references per FOR ID
├── requirements.txt        # Python dependencies
├── launch_app.bat          # One-click launcher (Windows)
└── .env                    # API key (not committed)
```

---

## Setup

### Requirements
- Python 3.10+
- Anthropic API key

### Install
```bash
git clone https://github.com/HollyStraley/FOR-meeting-assistant
cd FOR-meeting-assistant
pip install -r requirements.txt
```

### Configure
Create a `.env` file in the project root:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Run
```bash
python -m streamlit run streamlit_app.py
```
Or double-click `launch_app.bat` on Windows.

### Streamlit Cloud
Set your API key under **App Settings → Secrets**:
```toml
ANTHROPIC_API_KEY = "sk-ant-your-key-here"
```

---

## Persistent Data Files

These files are auto-created on first run and excluded from version control:

| File | Purpose |
|---|---|
| `open_items_history.json` | Rolling history of open items per meeting run |
| `closed_items_history.json` | Cumulative log of all closed items |
| `watch_items_history.json` | Cumulative log of all watch items |
| `meeting_history.json` | Meeting metadata log (date, duration, attendees) |
| `for_id_counter.json` | Auto-increment counter for FOR ID assignment |
| `for_id_first_seen.json` | First appearance date per FOR ID (used for cycle time) |

---

*Built with Claude Code + Anthropic Claude API*
