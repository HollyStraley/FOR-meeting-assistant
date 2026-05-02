import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

REFERENCES_FILE = "references.json"
ROSTER_FILE = "roster.json"

st.set_page_config(page_title="FOR Meeting Assistant", page_icon="📋", layout="wide")
st.title("📋 FOR Meeting Assistant")

# ── helpers ──────────────────────────────────────────────────────────────────

def load_references() -> dict:
    p = Path(REFERENCES_FILE)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_references(data: dict):
    Path(REFERENCES_FILE).write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_roster() -> dict:
    p = Path(ROSTER_FILE)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def run_processor(transcript_text: str, meeting_date: str) -> tuple[bytes | None, str]:
    """Run the processor and return (excel_bytes, log_output)."""
    from processor import process_transcript

    full_text = f"Meeting Date: {meeting_date}\n\n{transcript_text}"
    output_path = tempfile.mktemp(suffix=".xlsx")

    log_buffer = io.StringIO()
    try:
        with redirect_stdout(log_buffer):
            process_transcript(full_text, output_path)
        excel_bytes = Path(output_path).read_bytes()
    except Exception as e:
        return None, f"ERROR: {e}"
    finally:
        if Path(output_path).exists():
            Path(output_path).unlink()

    return excel_bytes, log_buffer.getvalue()


# ── tabs ─────────────────────────────────────────────────────────────────────

tab_process, tab_refs, tab_roster = st.tabs(["Process Transcript", "References", "Roster"])


# ── Tab 1: Process Transcript ─────────────────────────────────────────────────

with tab_process:
    if not os.getenv("ANTHROPIC_API_KEY"):
        st.error("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
        st.stop()

    col1, col2 = st.columns([2, 1])
    with col1:
        input_method = st.radio("Input method", ["Upload .txt file", "Paste transcript"], horizontal=True)
    with col2:
        meeting_date = st.date_input("Meeting date", value=datetime.today())

    transcript_text = ""

    if input_method == "Upload .txt file":
        uploaded = st.file_uploader("Drop your transcript file here", type=["txt"])
        if uploaded:
            transcript_text = uploaded.read().decode("utf-8")
            st.success(f"File loaded: {uploaded.name}")
    else:
        transcript_text = st.text_area("Paste transcript here", height=300, placeholder="Paste your meeting transcript...")

    st.divider()

    if st.button("▶ Process Transcript", type="primary", disabled=not transcript_text.strip()):
        with st.spinner("Calling Claude API — this may take 20-40 seconds..."):
            excel_bytes, log = run_processor(transcript_text, str(meeting_date))

        st.subheader("Processing Log")
        st.code(log)

        if excel_bytes:
            filename = f"FOR_actions_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            st.success("Done! Download your Excel file below.")
            st.download_button(
                label="⬇ Download Excel",
                data=excel_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.error("Processing failed. See log above for details.")


# ── Tab 2: References ─────────────────────────────────────────────────────────

with tab_refs:
    st.subheader("References")
    st.caption("Add tracking numbers, notes, or file names for specific FOR requests. Leave this empty if not needed for a meeting.")

    refs = load_references()

    # Display existing entries
    if refs:
        st.markdown("**Current entries:**")
        for for_id, data in list(refs.items()):
            with st.expander(f"**{for_id}** — {data.get('tracking_number', '(no tracking #)')}"):
                col1, col2 = st.columns([4, 1])
                with col1:
                    new_tracking = st.text_input("Tracking number", value=data.get("tracking_number", ""), key=f"trk_{for_id}")
                    new_notes = st.text_input("Notes", value=data.get("notes", ""), key=f"notes_{for_id}")
                    new_files = st.text_input("File names (comma separated)", value=", ".join(data.get("files", [])), key=f"files_{for_id}")
                with col2:
                    st.write("")
                    st.write("")
                    if st.button("Save", key=f"save_{for_id}"):
                        refs[for_id] = {
                            "tracking_number": new_tracking,
                            "notes": new_notes,
                            "files": [f.strip() for f in new_files.split(",") if f.strip()],
                        }
                        save_references(refs)
                        st.success("Saved.")
                        st.rerun()
                    if st.button("🗑 Delete", key=f"del_{for_id}"):
                        del refs[for_id]
                        save_references(refs)
                        st.rerun()
    else:
        st.info("No references saved yet. Add one below.")

    st.divider()
    st.markdown("**Add a new entry:**")
    col1, col2, col3, col4 = st.columns([1, 2, 3, 1])
    with col1:
        new_id = st.text_input("FOR ID", placeholder="FOR-001")
    with col2:
        new_tracking = st.text_input("Tracking number", placeholder="COMP-12345")
    with col3:
        new_notes = st.text_input("Notes", placeholder="Optional notes")
    with col4:
        st.write("")
        st.write("")
        if st.button("➕ Add", type="primary"):
            if new_id.strip():
                refs[new_id.strip()] = {
                    "tracking_number": new_tracking.strip(),
                    "notes": new_notes.strip(),
                    "files": [],
                }
                save_references(refs)
                st.success(f"Added {new_id.strip()}")
                st.rerun()
            else:
                st.warning("FOR ID is required.")


# ── Tab 3: Roster ─────────────────────────────────────────────────────────────

with tab_roster:
    st.subheader("Meeting Roster")
    roster = load_roster()

    members = roster.get("members", [])
    if members:
        st.markdown("**Members:**")
        for m in members:
            st.markdown(f"- **{m['name']}** — {m['title']} ({m['department']}) · `{m['email']}`")
    else:
        st.info("No members found in roster.json.")

    st.divider()
    st.subheader("Flag Rules")
    flag_rules = roster.get("flag_rules", [])
    if flag_rules:
        for rule in flag_rules:
            with st.expander(f"**{rule['rule']}**"):
                st.write(rule["description"])
                st.caption("Keywords: " + ", ".join(rule["keywords"]))
    else:
        st.info("No flag rules found in roster.json.")
