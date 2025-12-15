# Patent Status Tracker - UI Improvements Plan

**Status: IMPLEMENTED** (2025-12-15)

---

## Issues to Fix

Based on user feedback from testing:

1. **Text too small** - Need adjustable font size
2. **Column visibility** - Users want to choose which columns to display
3. **Updates filtering wrong** - Currently filters by `first_seen` (when downloaded), should filter by `event_date` (when it happened at USPTO)
4. **Updates not grouped** - Should group by application number with collapse/expand
5. **Filter by event type** - Want to filter which event types to show
6. **Sort by column** - Click column headers to sort
7. **Settings scroll** - Export button cut off, needs scrollbar

---

## User Preferences (Confirmed)

- **Expand state**: Persist between sessions (store in settings)
- **Date filter**: Event date only (not first_seen)
- **Scope**: Full improvements to BOTH tabs

---

## Implementation Plan

### File: `/home/matt/code_projects/patent-status-tracker/src/database.py`

**Change 1: Fix `get_recent_events()` filtering**
- Line 210: Change `WHERE date(e.first_seen)` to `WHERE date(e.event_date)`
- This makes "last 7 days" mean USPTO event dates, not download dates

**Change 2: Add new query for grouped events**
```python
def get_recent_events_grouped(days: int = 7, event_types: list = None) -> dict:
    """Get events grouped by application number."""
    # Returns: {app_number: {'patent': {...}, 'events': [...]}}
```

---

### File: `/home/matt/code_projects/patent-status-tracker/src/ui.py`

**Change 3: Add font size setting**
- Add `font_size` setting (default 10, range 8-16)
- Store in database settings
- Apply to ttk.Treeview via ttk.Style
- Add font size control in Settings tab

**Change 4: Make Settings tab scrollable**
- Wrap all settings content in `CTkScrollableFrame`
- Line 238-376: Move all frames inside scrollable container

**Change 5: Add column visibility controls**
- Add "Columns" button next to each table
- Create popup dialog with checkboxes for each column
- Store preferences in database settings
- Show/hide columns based on preferences

**Change 6: Restructure Updates tab with grouping**
- Change from flat list to hierarchical view
- Parent nodes: Application # + Title (collapsible)
- Child nodes: Individual events
- Use ttk.Treeview with `show="tree headings"` for expand/collapse

**Change 7: Add event type filter**
- Add multi-select dropdown for event types (Office Action, IDS, Response, etc.)
- Filter events before display

**Change 8: Add column sorting**
- Bind `<Button-1>` on headings
- Track sort column and direction
- Re-sort data on click
- Show sort indicator (▲/▼) in header

---

## Detailed UI Changes

### Settings Tab (Scrollable)
```
┌─ Settings ─────────────────────────────────────┐
│ ┌─ Display ──────────────────────────────────┐ │
│ │ Font Size: [10 ▼] (8-16)      [Apply]      │ │
│ └────────────────────────────────────────────┘ │
│ ┌─ USPTO API Key ────────────────────────────┐ │
│ │ [***************] [Show] [Save Key]        │ │
│ └────────────────────────────────────────────┘ │
│ ┌─ Auto-Refresh ─────────────────────────────┐ │
│ │ Check every: [24 ▼] hours    [Save]        │ │
│ └────────────────────────────────────────────┘ │
│ ┌─ Links ────────────────────────────────────┐ │
│ └────────────────────────────────────────────┘ │
│ ┌─ Export ───────────────────────────────────┐ │
│ │ [Export to CSV]                            │ │
│ └────────────────────────────────────────────┘ │
└────────────────────────────────────────────────┘
```

### Updates Tab (Grouped)
```
┌─ Updates ──────────────────────────────────────┐
│ Last: [7 days▼]  Type: [All▼]  [Columns] [⟳]  │
├────────────────────────────────────────────────┤
│ ▼ 17/940,142 - GENERATING AND TESTING... (3)  │
│   │ 2025-12-08 │ BRCE  │ RCE Begin            │
│   │ 2025-06-17 │ WIDS  │ IDS Filed            │
│   │ 2025-06-16 │ CTFR  │ Final Rejection      │
│ ▶ 18/413,823 - MODEL-INFORMED PRECISION... (2)│
│ ▼ 18/635,578 - ADJUSTABLE DEVICE... (1)       │
│   │ 2025-06-16 │ CTNF  │ Non-Final Rejection  │
└────────────────────────────────────────────────┘
  Click header to sort ▲▼
```

---

## Implementation Order

1. **Settings scroll** - Quick fix, prevents hidden content
2. **Font size** - High visibility improvement
3. **Fix event date filtering** - Critical bug fix (database.py)
4. **Column sorting** - Apply to BOTH tabs
5. **Grouped updates view** - With persistent expand state
6. **Column visibility** - Apply to BOTH tabs
7. **Event type filter** - Updates tab

---

## Additional Database Changes

**Store expand state:**
```python
# In settings table, store as JSON
# Key: "expanded_patents", Value: '["17940142", "18413823"]'
```

**Store column visibility:**
```python
# Key: "updates_columns", Value: '["date", "event", "description"]'
# Key: "patents_columns", Value: '["app_number", "title", "status"]'
```

---

## Event Type Categories

For filtering, group event codes:
- **Office Actions**: CTNF, CTFR, NOA, MCTNF, MCTFR
- **Responses**: A..., RESP, RCE, BRCE
- **IDS**: WIDS, IDSC, M844
- **Administrative**: DOCK, OIPE, COMP, EML_NTF
- **Other**: Everything else
