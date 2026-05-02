import io
import json
import os
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

# ── helpers ───────────────────────────────────────────────────────────────────

def load_references() -> dict:
    p = Path(REFERENCES_FILE)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def save_references(data: dict):
    Path(REFERENCES_FILE).write_text(json.dumps(data, indent=2), encoding="utf-8")

def load_roster() -> dict:
    p = Path(ROSTER_FILE)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"members": [], "flag_rules": []}

def save_roster(data: dict):
    Path(ROSTER_FILE).write_text(json.dumps(data, indent=2), encoding="utf-8")

def run_processor(transcript_text: str, meeting_date: str):
    from processor import process_transcript
    full_text = f"Meeting Date: {meeting_date}\n\n{transcript_text}"
    output_path = tempfile.mktemp(suffix=".xlsx")
    log_buffer = io.StringIO()
    try:
        with redirect_stdout(log_buffer):
            result = process_transcript(full_text, output_path)
        excel_bytes = Path(output_path).read_bytes()
    except Exception as e:
        return None, None, None, f"ERROR: {e}"
    finally:
        if Path(output_path).exists():
            Path(output_path).unlink()
        draft_path = Path(output_path).with_suffix(".txt")
        if draft_path.exists():
            draft_path.unlink()
    return excel_bytes, result.get("_email_draft", ""), result, log_buffer.getvalue()


# ── tabs ──────────────────────────────────────────────────────────────────────

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
        transcript_text = st.text_area("Paste transcript here", height=300,
                                       placeholder="Paste your meeting transcript...")

    st.divider()

    if st.button("▶ Process Transcript", type="primary", disabled=not transcript_text.strip()):
        with st.spinner("Calling Claude API — this may take 20-40 seconds..."):
            excel_bytes, email_draft, result, log = run_processor(transcript_text, str(meeting_date))

        if excel_bytes:
            st.success("Done!")

            col1, col2 = st.columns(2)
            with col1:
                filename = f"FOR_actions_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
                st.download_button(
                    label="⬇ Download Excel",
                    data=excel_bytes,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            with col2:
                draft_filename = f"FOR_email_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
                st.download_button(
                    label="⬇ Download Email Draft",
                    data=email_draft.encode("utf-8"),
                    file_name=draft_filename,
                    mime="text/plain",
                )

            st.subheader("📧 Email Draft")
            st.caption("Copy and paste this into Teams or Outlook.")
            st.text_area("", value=email_draft, height=400, label_visibility="collapsed")

            with st.expander("Processing log"):
                st.code(log)
        else:
            st.error("Processing failed.")
            st.code(log)


# ── Tab 2: References ─────────────────────────────────────────────────────────

with tab_refs:
    st.subheader("References")
    st.caption("Add tracking numbers or notes for specific FOR IDs. Optional — leave empty if not needed.")

    refs = load_references()

    if refs:
        st.markdown("**Current entries:**")
        for for_id, data in list(refs.items()):
            with st.expander(f"**{for_id}** — {data.get('tracking_number', '(no tracking #)')}"):
                col1, col2 = st.columns([5, 1])
                with col1:
                    new_tracking = st.text_input("Tracking number", value=data.get("tracking_number", ""), key=f"trk_{for_id}")
                    new_notes = st.text_input("Notes", value=data.get("notes", ""), key=f"notes_{for_id}")
                    new_files = st.text_input("File names (comma separated)", value=", ".join(data.get("files", [])), key=f"files_{for_id}")
                with col2:
                    st.write(""); st.write("")
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
        st.info("No references saved yet.")

    st.divider()
    st.markdown("**Add new entry:**")
    col1, col2, col3, col4 = st.columns([1, 2, 3, 1])
    with col1:
        new_id = st.text_input("FOR ID", placeholder="FOR-001")
    with col2:
        new_tracking = st.text_input("Tracking #", placeholder="COMP-12345")
    with col3:
        new_notes = st.text_input("Notes", placeholder="Optional notes")
    with col4:
        st.write(""); st.write("")
        if st.button("➕ Add", type="primary"):
            if new_id.strip():
                refs[new_id.strip()] = {"tracking_number": new_tracking.strip(), "notes": new_notes.strip(), "files": []}
                save_references(refs)
                st.success(f"Added {new_id.strip()}")
                st.rerun()
            else:
                st.warning("FOR ID is required.")


# ── Tab 3: Roster ─────────────────────────────────────────────────────────────

with tab_roster:
    roster = load_roster()

    # ── Members ──
    st.subheader("Members")
    members = roster.get("members", [])

    for idx, m in enumerate(members):
        with st.expander(f"**{m['name']}** — {m['title']}"):
            col1, col2 = st.columns([5, 1])
            with col1:
                m["name"]       = st.text_input("Name",       value=m.get("name", ""),       key=f"mname_{idx}")
                m["full_name"]  = st.text_input("Full name",  value=m.get("full_name", ""),  key=f"mfull_{idx}")
                m["email"]      = st.text_input("Email",      value=m.get("email", ""),      key=f"memail_{idx}")
                m["title"]      = st.text_input("Title",      value=m.get("title", ""),      key=f"mtitle_{idx}")
                m["department"] = st.text_input("Department", value=m.get("department", ""), key=f"mdept_{idx}")
            with col2:
                st.write(""); st.write("")
                if st.button("Save", key=f"msave_{idx}"):
                    roster["members"][idx] = m
                    save_roster(roster)
                    st.success("Saved.")
                    st.rerun()
                if st.button("🗑 Delete", key=f"mdel_{idx}"):
                    roster["members"].pop(idx)
                    save_roster(roster)
                    st.rerun()

    st.divider()
    st.markdown("**Add new member:**")
    with st.form("add_member"):
        col1, col2, col3 = st.columns(3)
        with col1:
            nm_name  = st.text_input("Name")
            nm_full  = st.text_input("Full name")
        with col2:
            nm_email = st.text_input("Email")
            nm_title = st.text_input("Title")
        with col3:
            nm_dept  = st.text_input("Department")
        if st.form_submit_button("➕ Add Member", type="primary"):
            if nm_name.strip():
                roster["members"].append({
                    "name": nm_name.strip(), "full_name": nm_full.strip(),
                    "email": nm_email.strip(), "title": nm_title.strip(),
                    "department": nm_dept.strip(),
                })
                save_roster(roster)
                st.success(f"Added {nm_name.strip()}")
                st.rerun()
            else:
                st.warning("Name is required.")

    # ── Flag Rules ──
    st.divider()
    st.subheader("Flag Rules")
    flag_rules = roster.get("flag_rules", [])

    for idx, rule in enumerate(flag_rules):
        with st.expander(f"**{rule['rule']}**"):
            col1, col2 = st.columns([5, 1])
            with col1:
                rule["rule"]        = st.text_input("Rule ID",     value=rule.get("rule", ""),        key=f"rid_{idx}")
                rule["description"] = st.text_input("Description", value=rule.get("description", ""), key=f"rdesc_{idx}")
                kw_str              = st.text_input("Keywords (comma separated)", value=", ".join(rule.get("keywords", [])), key=f"rkw_{idx}")
                rule["keywords"]    = [k.strip() for k in kw_str.split(",") if k.strip()]
            with col2:
                st.write(""); st.write("")
                if st.button("Save", key=f"rsave_{idx}"):
                    roster["flag_rules"][idx] = rule
                    save_roster(roster)
                    st.success("Saved.")
                    st.rerun()
                if st.button("🗑 Delete", key=f"rdel_{idx}"):
                    roster["flag_rules"].pop(idx)
                    save_roster(roster)
                    st.rerun()

    st.divider()
    st.markdown("**Add new flag rule:**")
    with st.form("add_flag"):
        col1, col2 = st.columns(2)
        with col1:
            fr_rule = st.text_input("Rule ID", placeholder="engine_country_move")
            fr_desc = st.text_input("Description", placeholder="Flag cross-border engine moves")
        with col2:
            fr_kw = st.text_input("Keywords (comma separated)", placeholder="moving to, ship to, export")
        if st.form_submit_button("➕ Add Flag Rule", type="primary"):
            if fr_rule.strip():
                roster["flag_rules"].append({
                    "rule": fr_rule.strip(),
                    "description": fr_desc.strip(),
                    "keywords": [k.strip() for k in fr_kw.split(",") if k.strip()],
                })
                save_roster(roster)
                st.success(f"Added rule: {fr_rule.strip()}")
                st.rerun()
            else:
                st.warning("Rule ID is required.")
