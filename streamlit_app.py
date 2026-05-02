import io
import json
import os
import re
import tempfile
from collections import Counter, defaultdict
from contextlib import redirect_stdout
from datetime import datetime, date
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

REFERENCES_FILE = "references.json"
ROSTER_FILE = "roster.json"
OPEN_HISTORY_FILE = "open_items_history.json"
CLOSED_HISTORY_FILE = "closed_items_history.json"
MEETING_HISTORY_FILE = "meeting_history.json"

REGIONS = {
    "Europe":        ["europe", "germany", "france", "uk", "belgium", "netherlands", "spain", "italy"],
    "China":         ["china", "chinese", "beijing", "shanghai"],
    "Asia-Pacific":  ["asia", "japan", "singapore", "korea", "apac", "asia-pacific"],
    "LATAM":         ["latam", "latin america", "brazil", "mexico", "colombia"],
    "North America": ["north america", "na", "usa", "canada", "houston", "dallas"],
}

EQUIPMENT = {
    "Boom":         ["boom", "booms"],
    "Telehandler":  ["telehandler", "telehandlers"],
    "GX4":          ["gx4"],
    "GX9":          ["gx9"],
    "GT7":          ["gt7"],
    "GT9":          ["gt9"],
}

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

tab_process, tab_refs, tab_roster, tab_dash = st.tabs(["Process Transcript", "References", "Roster", "Dashboard"])


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


# ── Tab 4: Dashboard ──────────────────────────────────────────────────────────

with tab_dash:
    st.subheader("Dashboard")

    open_history  = json.loads(Path(OPEN_HISTORY_FILE).read_text(encoding="utf-8")) if Path(OPEN_HISTORY_FILE).exists() else []
    closed_items  = json.loads(Path(CLOSED_HISTORY_FILE).read_text(encoding="utf-8")) if Path(CLOSED_HISTORY_FILE).exists() else []
    meeting_hist  = json.loads(Path(MEETING_HISTORY_FILE).read_text(encoding="utf-8")) if Path(MEETING_HISTORY_FILE).exists() else []

    if not open_history and not closed_items:
        st.info("No data yet — process at least one transcript to see the dashboard.")
    else:
        # ── Key metrics ──
        current_open = len(open_history[0]["items"]) if open_history else 0
        total_closed = len(closed_items)
        total_meetings = len(open_history)

        # Avg days to close — match first appearance in open_history to close date
        DATE_FORMATS = ["%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]

        def parse_date(s: str):
            for fmt in DATE_FORMATS:
                try:
                    return datetime.strptime(s.strip(), fmt)
                except ValueError:
                    continue
            return None

        days_list = []
        reversed_history = list(reversed(open_history))
        for c_item in closed_items:
            req_id = str(c_item.get("request_id", "")).strip().upper()
            close_date_str = c_item.get("date_closed", "")
            first_seen = None
            for run in reversed_history:
                ids_in_run = [str(i.get("request_id", "")).strip().upper() for i in run.get("items", [])]
                if req_id in ids_in_run:
                    first_seen = run.get("meeting_date", "")
            if first_seen and close_date_str and first_seen != "Unknown" and close_date_str != "Unknown":
                d1 = parse_date(first_seen)
                d2 = parse_date(close_date_str)
                if d1 and d2:
                    days = (d2 - d1).days
                    if days > 0:
                        days_list.append(days)
        avg_days = round(sum(days_list) / len(days_list), 1) if days_list else None

        # Debug info
        debug_rows = []
        reversed_history2 = list(reversed(open_history))
        for c_item in closed_items:
            req_id2 = str(c_item.get("request_id", "")).strip().upper()
            close_str = c_item.get("date_closed", "Unknown")
            first = None
            for run in reversed_history2:
                if req_id2 in [str(i.get("request_id","")).strip().upper() for i in run.get("items",[])]:
                    first = run.get("meeting_date","")
            d1 = parse_date(first) if first else None
            d2 = parse_date(close_str) if close_str else None
            days_val = (d2 - d1).days if d1 and d2 else None
            debug_rows.append({"FOR ID": req_id2, "First Seen": first or "NOT IN HISTORY", "Date Closed": close_str, "Days": days_val})

        with st.expander("Debug: Days to Close calculation"):
            import pandas as pd
            st.dataframe(pd.DataFrame(debug_rows))

        # All items text for trend analysis
        all_context = []
        for run in open_history:
            for item in run.get("items", []):
                all_context.append(item.get("context_summary", "").lower())
        for c in closed_items:
            all_context.append(c.get("context_summary", "").lower())

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Open Items (Latest)", current_open)
        col2.metric("Total Closed (All Time)", total_closed)
        col3.metric("Meetings Processed", total_meetings)
        col4.metric("Avg Days to Close", f"{avg_days} days" if avg_days is not None else "N/A")

        st.divider()

        # ── Open vs Closed over time ──
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("**Open Items Per Meeting**")
            if open_history:
                chart_data = {
                    run.get("meeting_date", f"Run {i+1}"): len(run.get("items", []))
                    for i, run in enumerate(reversed(open_history))
                }
                import pandas as pd
                df_open = pd.DataFrame(list(chart_data.items()), columns=["Meeting", "Open Items"])
                df_open = df_open.set_index("Meeting")
                st.bar_chart(df_open)

        with col_right:
            st.markdown("**Flag Frequency (All Time)**")
            flag_counts = Counter()
            for run in open_history:
                for item in run.get("items", []):
                    for f in item.get("flags", []):
                        flag_counts[f] += 1
            for c in closed_items:
                pass  # closed items don't store flags in history
            if flag_counts:
                import pandas as pd
                df_flags = pd.DataFrame(list(flag_counts.items()), columns=["Flag", "Count"]).set_index("Flag")
                st.bar_chart(df_flags)
            else:
                st.info("No flags recorded yet.")

        st.divider()

        # ── Regional trends ──
        st.markdown("**Regional Trends — Frequency in Open Items**")
        region_counts_by_meeting = defaultdict(dict)
        for run in reversed(open_history):
            meeting_date = run.get("meeting_date", "Unknown")
            for region, keywords in REGIONS.items():
                count = sum(
                    1 for item in run.get("items", [])
                    if any(kw in item.get("context_summary", "").lower() for kw in keywords)
                )
                region_counts_by_meeting[meeting_date][region] = count

        if region_counts_by_meeting:
            import pandas as pd
            df_regions = pd.DataFrame(region_counts_by_meeting).T.fillna(0)
            df_regions = df_regions[[c for c in REGIONS.keys() if c in df_regions.columns]]
            st.bar_chart(df_regions)
        else:
            st.info("Not enough data for regional trends yet.")

        st.divider()

        # ── Equipment trends ──
        st.markdown("**Equipment Type Trends — Frequency Across All Items**")
        equip_counts = Counter()
        for text in all_context:
            for equip, keywords in EQUIPMENT.items():
                if any(kw in text for kw in keywords):
                    equip_counts[equip] += 1

        if equip_counts:
            import pandas as pd
            df_equip = pd.DataFrame(list(equip_counts.items()), columns=["Equipment", "Count"]).set_index("Equipment")
            st.bar_chart(df_equip)
        else:
            st.info("No equipment type data yet.")
