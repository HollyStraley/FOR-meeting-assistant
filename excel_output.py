from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


COLUMNS = [
    ("ID", 6),
    ("Context Summary", 45),
    ("Requester", 18),
    ("Current Owner", 20),
    ("Priority", 12),
    ("Status", 28),
    ("Due Date", 14),
    ("Flags", 30),
    ("Flag Notes", 40),
]

PRIORITY_COLORS = {
    "High":   "FFCCCC",
    "Medium": "FFF2CC",
    "Low":    "CCFFCC",
}

HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(bold=True, color="FFFFFF", name="Calibri", size=11)
FLAG_FILL   = PatternFill("solid", fgColor="FFE0B2")

thin = Side(style="thin", color="BFBFBF")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)


def _header_row(ws):
    for col_idx, (label, width) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
        ws.column_dimensions[get_column_letter(col_idx)].width = width
    ws.row_dimensions[1].height = 28


def _data_row(ws, row_idx: int, item: dict):
    flags = item.get("flags") or []
    flag_str = ", ".join(flags) if flags else ""
    priority = item.get("priority", "Medium")

    values = [
        item.get("request_id", row_idx - 1),
        item.get("context_summary", ""),
        item.get("requester", ""),
        item.get("current_owner", ""),
        priority,
        item.get("status", ""),
        item.get("due_date", "Not specified"),
        flag_str,
        item.get("flag_notes", ""),
    ]

    row_fill = PatternFill("solid", fgColor=PRIORITY_COLORS.get(priority, "FFFFFF"))

    for col_idx, value in enumerate(values, start=1):
        cell = ws.cell(row=row_idx, column=col_idx, value=value)
        cell.border = BORDER
        cell.alignment = Alignment(vertical="top", wrap_text=True)

        if col_idx == 5:  # Priority column
            cell.fill = row_fill
            cell.font = Font(bold=True, name="Calibri", size=10)
        elif flag_str and col_idx == 8:  # Flags column
            cell.fill = FLAG_FILL
        else:
            cell.fill = PatternFill("solid", fgColor="F9F9F9" if row_idx % 2 == 0 else "FFFFFF")

    ws.row_dimensions[row_idx].height = 55


def save_excel(action_items: list[dict], output_path: str):
    wb = Workbook()
    ws = wb.active
    ws.title = "FOR Action Items"

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}1"

    _header_row(ws)

    for i, item in enumerate(action_items, start=2):
        _data_row(ws, i, item)

    # Summary row
    summary_row = len(action_items) + 2
    total_cell = ws.cell(row=summary_row, column=1, value=f"Total items: {len(action_items)}")
    total_cell.font = Font(bold=True, name="Calibri", size=10)

    flagged = sum(1 for item in action_items if item.get("flags"))
    flagged_cell = ws.cell(row=summary_row, column=8, value=f"Flagged: {flagged}")
    flagged_cell.font = Font(bold=True, name="Calibri", size=10)
    if flagged:
        flagged_cell.fill = FLAG_FILL

    generated_cell = ws.cell(
        row=summary_row + 1, column=1,
        value=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    generated_cell.font = Font(italic=True, color="888888", name="Calibri", size=9)

    wb.save(output_path)
    print(f"Excel saved: {output_path}")
