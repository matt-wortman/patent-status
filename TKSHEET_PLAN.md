# Patent Status Tracker - Flexible Data Table Plan

## Overview

Replace the current `ttk.Treeview` tables with [tksheet](https://github.com/ragardner/tksheet) to provide:
- **Field selector** - Users pick which columns to display
- **Column sorting** - Click headers to sort
- **Column resizing** - Drag column edges
- **Column reordering** - Drag and drop columns
- **Persistent preferences** - Save column visibility/order/widths

---

## Why tksheet?

| Feature | ttk.Treeview (current) | tksheet |
|---------|------------------------|---------|
| Sorting | Manual (implemented) | Built-in |
| Column resize | Manual drag | Built-in |
| Column reorder | Not supported | Built-in drag & drop |
| Hide columns | Not supported | Built-in |
| Column visibility dialog | Manual | Can build on top |
| Theming | System theme | Light/dark + custom colors |

---

## Implementation Phases

### Phase 0: Prototype & Validation
Quick throwaway script to prove tksheet plays nicely with CustomTkinter before the refactor (not committed):
- Embed a Sheet in a CTk frame
- Verify column resize/reorder, double/right-click events, theme colors, font size changes, and no visual glitches
- Exit criteria: all checks pass

---

### Phase 1: Add Dependency
**File:** `requirements.txt`

```
tksheet>=7.0.0,<8.0.0
```

---

### Phase 2: Create TkSheet Wrapper Component
**File:** `src/components/data_table.py` (new)

Create a reusable wrapper class that provides:
- Consistent configuration for both tables (All Patents, Updates)
- Default **read-only** sheets (no in-cell editing) until an explicit edit use-case exists
- Column visibility management
- Preference persistence via database settings
- Right-click context menu for column visibility
- Event parity with current Treeview behaviors (row select, double-click, context menu hooks)

```python
class DataTable:
    def __init__(
        self,
        parent,
        table_id: str,
        columns: list[dict],
        on_select: callable | None = None,
        on_double_click: callable | None = None,
        on_right_click: callable | None = None,
    ):
        """Wrapper around tksheet.Sheet for consistent table behavior."""
```

Key methods/helpers:
- `set_data(rows: list[dict])` - Load data from list of dicts
- `get_visible_columns()` -> list of column keys
- `set_visible_columns(columns: list)` - Show/hide columns
- `show_column_selector()` - Open dialog to pick visible columns
- `save_preferences()` / `load_preferences()` - Persist/restore visibility/order/width/sort
- `bind_events()` - Re-attach existing callbacks (select, double-click, right-click) using tksheet bindings
- `apply_theme()` / `set_font_size()` - Sync with CustomTkinter appearance and font settings
- `_setup_bindings()` - Enable useful bindings, disable edits

---

### Phase 3: Define All Available Columns
**File:** `src/components/column_config.py`

Define all patent fields that can be displayed (with categories for the selector dialog):

```python
PATENT_COLUMNS = [
    # Core fields (visible)
    {"key": "app_number", "header": "Application #", "width": 110, "default_visible": True, "category": "Core"},
    {"key": "title", "header": "Title", "width": 280, "default_visible": True, "category": "Core"},
    {"key": "current_status", "header": "Status", "width": 180, "default_visible": True, "category": "Core"},
    {"key": "status_date", "header": "Status Date", "width": 95, "default_visible": True, "category": "Core"},
    {"key": "patent_number", "header": "Patent #", "width": 90, "default_visible": True, "category": "Core"},
    {"key": "expiration_date", "header": "Expiration", "width": 95, "default_visible": True, "category": "Core"},
    {"key": "applicant", "header": "Applicant", "width": 150, "default_visible": True, "category": "Core"},
    {"key": "examiner", "header": "Examiner", "width": 130, "default_visible": True, "category": "Core"},

    # Dates (hidden by default)
    {"key": "filing_date", "header": "Filing Date", "width": 95, "default_visible": False, "category": "Dates"},
    {"key": "grant_date", "header": "Grant Date", "width": 95, "default_visible": False, "category": "Dates"},
    {"key": "publication_date", "header": "Pub Date", "width": 95, "default_visible": False, "category": "Dates"},
    {"key": "effective_filing_date", "header": "Eff. Filing", "width": 95, "default_visible": False, "category": "Dates"},

    # Identifiers (hidden by default)
    {"key": "publication_number", "header": "Publication #", "width": 140, "default_visible": False, "category": "Identifiers"},
    {"key": "docket_number", "header": "Docket #", "width": 150, "default_visible": False, "category": "Identifiers"},
    {"key": "customer_number", "header": "Customer #", "width": 90, "default_visible": False, "category": "Identifiers"},
    {"key": "confirmation_number", "header": "Confirm #", "width": 80, "default_visible": False, "category": "Identifiers"},

    # Classification (hidden by default)
    {"key": "art_unit", "header": "Art Unit", "width": 70, "default_visible": False, "category": "Classification"},
    {"key": "entity_status", "header": "Entity", "width": 80, "default_visible": False, "category": "Classification"},
    {"key": "application_type_label", "header": "App Type", "width": 80, "default_visible": False, "category": "Classification"},
    {"key": "first_inventor_to_file", "header": "FITF", "width": 50, "default_visible": False, "category": "Classification"},

    # People (hidden by default)
    {"key": "inventor", "header": "Inventor", "width": 150, "default_visible": False, "category": "People"},

    # Patent Term (hidden by default)
    {"key": "pta_total_days", "header": "PTA Days", "width": 70, "default_visible": False, "category": "Patent Term"},
]

def get_default_visible(columns: list[dict]) -> list[str]:
    return [c["key"] for c in columns if c.get("default_visible")]

def get_categories(columns: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for col in columns:
        cat = col.get("category", "Other")
        grouped.setdefault(cat, []).append(col)
    return grouped
```

---

### Phase 4: Create Column Selector Dialog
**File:** `src/components/column_selector.py` (new)

Dialog with checkboxes for each column:
- Grouped by category (Core, Dates, Classification, etc.)
- "Select All" / "Deselect All" buttons
- "Reset to Defaults" button
- OK / Cancel buttons

```python
class ColumnSelectorDialog(ctk.CTkToplevel):
    def __init__(self, parent, columns: list[dict], visible_columns: list[str]):
        # Show checkbox for each column
        # Return selected column keys on OK
```

---

### Phase 5: Replace All Patents Table
**File:** `src/ui.py`

In `_build_patents_tab()`:
1. Remove current `ttk.Treeview` setup
2. Create `DataTable` instance with `PATENT_COLUMNS`
3. Add "Columns" button that calls `data_table.show_column_selector()`
4. Update `_load_patents()` to use new data table

tksheet configuration:
```python
from tksheet import Sheet

self.patents_sheet = Sheet(
    parent,
    headers=[col["header"] for col in visible_columns],
    show_x_scrollbar=True,
    show_y_scrollbar=True,
)

# Enable features
self.patents_sheet.enable_bindings((
    "single_select",
    "row_select",
    "column_width_resize",
    "column_select",
    "drag_select",
    "column_drag_and_drop",
    "copy",
    "right_click_popup_menu",
    "rc_select",
))

# Enable sorting on header click
self.patents_sheet.popup_menu_add_command("Sort Ascending", self._sort_asc)
self.patents_sheet.popup_menu_add_command("Sort Descending", self._sort_desc)

# Lock to read-only (no in-cell edits)
self.patents_sheet.disable_bindings((
    "edit_cell",
    "delete",
    "paste",
))

# Re-bind prior Treeview actions
self.patents_sheet.extra_bindings([
    ("cell_select", self._on_select),
    ("end_edit_cell", lambda *args: "break"),  # defensive: prevent edits
    ("double_click", self._on_double_click),
    ("right_click", self._on_right_click),
])

# Theme updates on appearance change
self.parent.bind("<<AppearanceModeChanged>>", lambda e: self._apply_theme())
```

---

### Phase 6: Persist User Preferences
**File:** `src/database.py`

Store in settings table as JSON:
- `patents_visible_columns` - List of visible column keys in order
- `patents_column_widths` - Dict of column key -> width
- `updates_visible_columns` - Same for updates table
- `updates_column_widths`
- Optional: `sort_column` and `sort_ascending` per table

Load on startup, save on:
- Column visibility change
- Column width change (after drag)
- Column reorder (after drag)
- Sort change

Validation/migration on load:
- Drop unknown column keys; append any new columns using their defaults
- If data is missing/corrupted, reset to defaults and log
- Keep the format forward-compatible (use keys, not indices)

---

### Phase 7: Theme Integration
**File:** `src/ui.py` or `src/components/data_table.py`

Match tksheet colors to CustomTkinter appearance:

```python
def _apply_theme(self):
    mode = ctk.get_appearance_mode()
    if mode == "Dark":
        self.sheet.set_options(
            table_bg="#2b2b2b",
            table_fg="#ffffff",
            header_bg="#1f1f1f",
            header_fg="#ffffff",
            index_bg="#1f1f1f",
            index_fg="#ffffff",
            table_grid_fg="#3a3a3a",
            header_grid_fg="#3a3a3a",
            table_selected_cells_bg="#3d6abf",
            table_selected_cells_fg="#ffffff",
            header_selected_cells_bg="#3d6abf",
            header_selected_cells_fg="#ffffff",
            table_hover_bg="#323232",
            header_hover_bg="#2a2a2a",
            font=("Segoe UI", 10),
            header_font=("Segoe UI Semibold", 10),
        )
    else:
        self.sheet.set_options(
            table_bg="#ffffff",
            table_fg="#000000",
            header_bg="#f0f0f0",
            header_fg="#000000",
            index_bg="#f0f0f0",
            index_fg="#000000",
            table_grid_fg="#d9d9d9",
            header_grid_fg="#d9d9d9",
            table_selected_cells_bg="#bcd4ff",
            table_selected_cells_fg="#000000",
            header_selected_cells_bg="#bcd4ff",
            header_selected_cells_fg="#000000",
            table_hover_bg="#f5f7fb",
            header_hover_bg="#e6e6e6",
            font=("Segoe UI", 10),
            header_font=("Segoe UI Semibold", 10),
        )

def set_font_size(self, size: int):
    # Apply font size to both cells and headers
    self.sheet.set_options(
        font=("Segoe UI", size),
        header_font=("Segoe UI Semibold", size),
    )
```

---

### Phase 8: Convert Updates Tab to tksheet (when grouping parity exists)
**File:** `src/ui.py`

Only convert once grouping parity is solved; otherwise, keep the existing Treeview as a hybrid approach.

**Updates table columns:**
```python
UPDATES_COLUMNS = [
    {"key": "event_date", "header": "Event Date", "width": 95, "default_visible": True},
    {"key": "app_number", "header": "Application #", "width": 110, "default_visible": True},
    {"key": "title", "header": "Title", "width": 250, "default_visible": True},
    {"key": "event_code", "header": "Code", "width": 70, "default_visible": True},
    {"key": "event_description", "header": "Description", "width": 250, "default_visible": True},
    {"key": "applicant", "header": "Applicant", "width": 150, "default_visible": False},
    {"key": "examiner", "header": "Examiner", "width": 130, "default_visible": False},
    {"key": "patent_number", "header": "Patent #", "width": 90, "default_visible": False},
]
```

**Changes:**
- Preserve current grouping/expand-collapse UX:
  - Simulate group headers as non-selectable rows, with expand/collapse state tracked in DataTable
  - Alternatively, keep Treeview temporarily if grouping cannot be replicated cleanly, and defer tksheet swap until grouping is implemented
- Events sorted by date (most recent first) by default
- Same column visibility, resize, reorder features as All Patents
- Double-click row to open patent in USPTO
- Sheet locked to read-only; rebind prior select/double-click/right-click actions

---

## Files to Modify/Create

| File | Action |
|------|--------|
| `requirements.txt` | Add `tksheet>=7.0.0,<8.0.0` |
| `src/components/__init__.py` | Create (new package) |
| `src/components/data_table.py` | Create (new - DataTable wrapper) |
| `src/components/column_config.py` | Create (new - column definitions/helpers) |
| `src/components/column_selector.py` | Create (new - dialog) |
| `src/ui.py` | Replace Treeview with DataTable |
| `src/database.py` | Add preference storage functions |

---

## Implementation Order

1. Phase 0 prototype to validate tksheet + CustomTkinter integration
2. Add tksheet dependency
3. Define column configs (needed for wrapper and dialog)
4. Create `DataTable` wrapper with basic functionality
5. Create `ColumnSelectorDialog`
6. Implement preference persistence helpers
7. Replace All Patents table with new DataTable
8. Add theme matching and font-size sync
9. Define `UPDATES_COLUMNS` and convert Updates tab only after grouping parity or choose hybrid

---

## User Experience

**Before:**
- Fixed columns, manual column visibility dialog
- Sorting works, but no resize or reorder

**After:**
- Click "Columns" button -> checkbox dialog to show/hide fields
- Drag column edges to resize
- Drag column headers to reorder
- Click headers to sort (or right-click menu)
- All preferences saved automatically

---

## Testing Checklist
- Prototype: embed Sheet in CTk, resize/reorder columns, double/right-click events, theme colors apply, font size changes, no visual glitches
- Patents table: visibility/resizing/reorder persists after restart; sort toggles work; copy (Ctrl+C) works; double-click/right-click actions preserved; empty state handled
- Theme/font: light/dark switch updates table; font size changes apply to headers/cells
- Preferences: missing/extra keys migrate correctly (unknown dropped, new defaults added); corrupted JSON resets to defaults
- Performance: scrolls smoothly with 100+ rows

---

## Risks and Mitigations
- tksheet API changes: pin to <8.0.0
- Preference corruption: validate/migrate on load; reset to defaults on failure
- Theme mismatch: set selection/hover/gridline colors and bind to appearance mode changes
- Grouping complexity: keep Treeview temporarily if grouping cannot be cleanly simulated to avoid UX regression

---

## Sources

- [tksheet GitHub](https://github.com/ragardner/tksheet)
- [tksheet Wiki](https://github.com/ragardner/tksheet/wiki/Version-7)
- [tksheet PyPI](https://pypi.org/project/tksheet/)
