# FOR Meeting Assistant

A Streamlit web app that reads SIOP (Sales, Inventory & Operations Planning) meeting transcripts and automatically extracts, tracks, and summarizes Firm Order Request (FOR) action items using the Claude AI API.

---

## Background

### Target User
The **SIOP Master Scheduler** — responsible for managing all Firm Order Requests (FORs) across a global team of approximately 15 individuals. This includes tracking every open request, actioning items once applicable (e.g., moving a machine to a different forecast group once materials are approved), and keeping all stakeholders aligned across bi-weekly FOR meetings.

### Current Workflow
FOR requests originate via email or are raised during bi-weekly FOR meetings. Every open request is discussed at each meeting — covering who needs to do what, what is blocked, and what has been resolved. The workflow ends once the request is fully completed.

With 15+ global participants on a call and a mix of long-running and new FOR requests being discussed simultaneously, it is difficult for the Master Scheduler to capture all notes, track owners, and keep the meeting running efficiently at the same time.

### Problem Statement
The SIOP Master Scheduler needed a way to automatically process a FOR meeting transcript and produce a structured list of all action items — including the context of each request, who owns it, what the current status is, priority level, and any flags for special situations (such as moving engines across country lines). The preferred output was an Excel sheet that could be saved in a shared Teams folder for all meeting participants to view.

### GenAI Fit
This problem is a strong fit for generative AI because the input is unstructured conversational language and the output requires interpretation, reasoning, and memory — not just keyword extraction. Specifically:

1. **Language** — The model reads and understands raw meeting transcript text, including informal speech, broken sentences, and indirect references to FOR IDs
2. **Reasoning** — The model infers who currently owns an action item based on conversational context, even when not explicitly stated
3. **Generation** — The model produces readable, structured outputs (e.g., "Waiting on materials approval from Lisa before Janet can update the forecast group") from fragmented discussion
4. **Agentic behavior** — The app acts as a persistent assistant across meetings: remembering items that have been open for multiple cycles, flagging carry-overs, and tracking cycle time from first appearance to resolution

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

## Architecture

### LLM Integration
The app makes a single Claude API call per transcript using `claude-sonnet-4-6`. The call is structured with a detailed system prompt and a user prompt that includes the full transcript text plus injected context. The model returns a strict JSON object — no free-text parsing required. If the response cannot be parsed, the app surfaces the error rather than silently failing.

### RAG (Retrieval-Augmented Generation)
Two local knowledge files are loaded at runtime and injected directly into the LLM prompt before each API call:

- **`roster.json`** — Team member names, titles, and emails. Gives the model the full list of known participants so it can confidently identify owners and flag low-confidence assignments when a name in the transcript doesn't match anyone on the roster.
- **`references.json`** — A lookup table mapping FOR IDs to external tracking numbers, notes, and related files. After the LLM returns its output, the app performs a second-pass enrichment step that attaches any matching reference data to open items before writing the Excel file.

This is a lightweight RAG pattern: no vector database or embeddings are used. Context is small and structured enough to fit directly in the prompt.

### Multi-Step Orchestration
Processing a single transcript involves multiple sequential steps coordinated by `processor.py`:

1. **Load context** — Roster and references are read from disk
2. **LLM call** — Claude extracts structured action items from the transcript
3. **ID assignment** — Any item missing a valid `FOR-NNN` ID is assigned one from the persistent counter
4. **First-seen tracking** — New FOR IDs are recorded with their first appearance date for cycle time calculation
5. **Reference enrichment** — Open items are matched against `references.json` and enriched
6. **Carry-over detection** — Open items are compared against historical runs to flag items with no status change across 3+ consecutive meetings
7. **Excel generation** — A 4-tab styled workbook is written using openpyxl
8. **Email draft generation** — A plain-text summary is generated from the structured result
9. **History persistence** — All history files are updated so the next run has full context

### No Fine-Tuning
The app uses the base `claude-sonnet-4-6` model with no fine-tuning. All domain-specific behavior (SIOP terminology, FOR request patterns, flag rules, confidence scoring) is achieved through prompt engineering alone — specifically a detailed system prompt that defines the output schema, flag rules, and confidence criteria.

### Tools & Tool Use
The app does not use Claude's tool-use (function calling) feature. The LLM is given a single structured prompt and expected to return a complete JSON object in one shot. This keeps latency low and the call count to one per transcript.

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
