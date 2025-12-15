"""tksheet wrapper providing consistent table behavior and preferences."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import customtkinter as ctk
from tksheet import Sheet
from tksheet.sorting import natural_sort_key

from .. import database as db
from .column_selector import ColumnSelectorDialog


@dataclass(frozen=True)
class TablePreferences:
    visible_columns: list[str]
    column_widths: dict[str, int]
    sort_column: str | None = None
    sort_ascending: bool = True


class DataTable(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        table_id: str,
        columns: list[dict[str, Any]],
        on_select: Callable[[dict[str, Any]], None] | None = None,
        on_double_click: Callable[[dict[str, Any]], None] | None = None,
        on_right_click: Callable[[Any, dict[str, Any]], None] | None = None,
        font_size: int = 10,
    ):
        super().__init__(parent)

        self._table_id = table_id
        self._columns = columns
        self._col_by_key = {c["key"]: c for c in columns}
        self._rows: list[dict[str, Any]] = []

        self._on_select_cb = on_select
        self._on_double_click_cb = on_double_click
        self._on_right_click_cb = on_right_click

        self._font_size = font_size
        self._header_press_xy: tuple[int, int] | None = None

        self._prefs = self._load_preferences()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.sheet = Sheet(
            self,
            show_row_index=False,
            headers=[],
            show_x_scrollbar=True,
            show_y_scrollbar=True,
        )
        self.sheet.grid(row=0, column=0, sticky="nsew")

        self._setup_bindings()
        self.apply_theme()
        self.set_font_size(self._font_size)

        # Apply initial column configuration
        self._apply_visible_columns(redraw=False)

    # ---- Public API ----
    def set_data(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self._refresh_sheet(redraw=True)

    def get_data(self) -> list[dict[str, Any]]:
        return list(self._rows)

    def get_selected_row(self) -> dict[str, Any] | None:
        sel = self.sheet.get_currently_selected()
        if not sel:
            return None
        row_index = getattr(sel, "row", None)
        if row_index is None or row_index < 0 or row_index >= len(self._rows):
            return None
        return self._rows[row_index]

    def get_visible_columns(self) -> list[str]:
        return list(self._prefs.visible_columns)

    def set_visible_columns(self, keys_in_order: list[str]) -> None:
        keys = self._validate_visible_keys(keys_in_order)
        self._prefs = TablePreferences(
            visible_columns=keys,
            column_widths=self._prefs.column_widths,
            sort_column=self._prefs.sort_column,
            sort_ascending=self._prefs.sort_ascending,
        )
        self._apply_visible_columns(redraw=True)
        self._save_preferences()

    def show_column_selector(self) -> None:
        dialog = ColumnSelectorDialog(self.winfo_toplevel(), self._columns, self._prefs.visible_columns)
        selected = dialog.get_result()
        if selected is None:
            return

        current = self._prefs.visible_columns
        selected_set = set(selected)

        # Preserve existing order for keys still selected
        new_order = [k for k in current if k in selected_set]

        # Append newly selected keys in column-config order
        existing = set(new_order)
        for col in self._columns:
            key = col["key"]
            if key in selected_set and key not in existing:
                new_order.append(key)
                existing.add(key)

        self.set_visible_columns(new_order)

    def apply_theme(self, mode: str | None = None) -> None:
        mode = mode or ctk.get_appearance_mode()
        if mode == "Dark":
            self.sheet.set_options(
                table_bg="#2b2b2b",
                table_fg="#ffffff",
                table_grid_fg="#3a3a3a",
                table_selected_cells_bg="#3d6abf",
                table_selected_cells_fg="#ffffff",
                header_bg="#1f1f1f",
                header_fg="#ffffff",
                header_grid_fg="#3a3a3a",
                header_selected_cells_bg="#3d6abf",
                header_selected_cells_fg="#ffffff",
                index_bg="#1f1f1f",
                index_fg="#ffffff",
                index_grid_fg="#3a3a3a",
            )
        else:
            self.sheet.set_options(
                table_bg="#ffffff",
                table_fg="#000000",
                table_grid_fg="#d9d9d9",
                table_selected_cells_bg="#bcd4ff",
                table_selected_cells_fg="#000000",
                header_bg="#f0f0f0",
                header_fg="#000000",
                header_grid_fg="#d9d9d9",
                header_selected_cells_bg="#bcd4ff",
                header_selected_cells_fg="#000000",
                index_bg="#f0f0f0",
                index_fg="#000000",
                index_grid_fg="#d9d9d9",
            )

    def set_font_size(self, size: int) -> None:
        self._font_size = size
        self.sheet.set_options(
            font=("Segoe UI", size, "normal"),
            header_font=("Segoe UI", size, "bold"),
            index_font=("Segoe UI", size, "normal"),
        )

    # ---- Internals ----
    def _setup_bindings(self) -> None:
        self.sheet.enable_bindings(
            (
                "single_select",
                "drag_select",
                "column_width_resize",
                "column_select",
                "column_drag_and_drop",
                "copy",
                "rc_select",
            )
        )
        # Defensive: keep table read-only even if defaults change
        self.sheet.disable_bindings(("edit_cell", "delete", "paste", "cut"))

        # Track column resizing and reorder to persist prefs
        self.sheet.extra_bindings(
            [
                ("column_width_resize", self._on_column_width_resize),
                ("end_move_columns", self._on_columns_moved),
                ("cell_select", self._on_cell_select),
            ]
        )

        # Header click sorting (avoid sorting on drag/resize)
        self.sheet.CH.bind("<ButtonPress-1>", self._on_header_press, add="+")
        self.sheet.CH.bind("<ButtonRelease-1>", self._on_header_release, add="+")

        # Row double-click and right-click behaviors
        self.sheet.MT.bind("<Double-Button-1>", self._on_double_click, add="+")
        self.sheet.MT.bind("<Button-3>", self._on_right_click, add="+")

    def _validate_visible_keys(self, keys: list[str]) -> list[str]:
        valid = [k for k in keys if k in self._col_by_key]
        if not valid:
            # Fall back to defaults if caller passes nothing usable.
            valid = [c["key"] for c in self._columns if c.get("default_visible")]
        return valid

    def _headers_for_visible(self) -> list[str]:
        headers: list[str] = []
        for key in self._prefs.visible_columns:
            base = self._col_by_key[key].get("header", key)
            if self._prefs.sort_column == key:
                indicator = "▲" if self._prefs.sort_ascending else "▼"
                headers.append(f"{base} {indicator}")
            else:
                headers.append(f"{base} ↕")
        return headers

    def _row_values(self, row: dict[str, Any]) -> list[Any]:
        values: list[Any] = []
        for key in self._prefs.visible_columns:
            value = row.get(key, "")
            values.append("" if value is None else value)
        return values

    def _refresh_sheet(self, redraw: bool) -> None:
        self.sheet.headers(self._headers_for_visible(), reset_col_positions=False, redraw=False)
        self.sheet.set_sheet_data([self._row_values(r) for r in self._rows], redraw=False)
        self._apply_column_widths(redraw=redraw)
        if redraw:
            self.sheet.refresh()

    def _apply_visible_columns(self, redraw: bool) -> None:
        # If visible columns changed, rebuild headers and sheet data to match.
        self._refresh_sheet(redraw=redraw)

    def _apply_column_widths(self, redraw: bool) -> None:
        widths: list[int] = []
        for key in self._prefs.visible_columns:
            width = self._prefs.column_widths.get(key)
            if not isinstance(width, int) or width <= 0:
                width = int(self._col_by_key[key].get("width", 120))
            widths.append(width)
        self.sheet.set_column_widths(widths, reset=False)
        if redraw:
            self.sheet.refresh()

    def _on_cell_select(self, _event_data: Any) -> None:
        if self._on_select_cb is None:
            return
        row = self.get_selected_row()
        if row is not None:
            self._on_select_cb(row)

    def _on_double_click(self, event: Any) -> None:
        if self._on_double_click_cb is None:
            return
        row_index = self.sheet.MT.identify_row(y=event.y)
        if row_index is None or row_index < 0 or row_index >= len(self._rows):
            return
        self.sheet.select_row(row_index)
        self._on_double_click_cb(self._rows[row_index])

    def _on_right_click(self, event: Any) -> None:
        if self._on_right_click_cb is None:
            return
        row_index = self.sheet.MT.identify_row(y=event.y)
        if row_index is None or row_index < 0 or row_index >= len(self._rows):
            return
        self.sheet.select_row(row_index)
        self._on_right_click_cb(event, self._rows[row_index])

    def _on_header_press(self, event: Any) -> None:
        self._header_press_xy = (event.x, event.y)

    def _on_header_release(self, event: Any) -> None:
        if self._header_press_xy is None:
            return
        press_x, press_y = self._header_press_xy
        self._header_press_xy = None

        # Ignore if user dragged (reorder) or resized
        if abs(event.x - press_x) > 6 or abs(event.y - press_y) > 6:
            return

        disp_col = self.sheet.MT.identify_col(x=event.x, allow_end=False)
        if disp_col is None:
            return
        if disp_col < 0 or disp_col >= len(self._prefs.visible_columns):
            return

        key = self._prefs.visible_columns[disp_col]
        self._sort_by_column_key(key)

    def _sort_by_column_key(self, key: str) -> None:
        if not self._rows:
            return

        if self._prefs.sort_column == key:
            ascending = not self._prefs.sort_ascending
        else:
            ascending = True

        self._rows.sort(key=lambda r: natural_sort_key(r.get(key)), reverse=not ascending)

        self._prefs = TablePreferences(
            visible_columns=self._prefs.visible_columns,
            column_widths=self._prefs.column_widths,
            sort_column=key,
            sort_ascending=ascending,
        )
        self._refresh_sheet(redraw=True)
        self._save_preferences()

    def _on_column_width_resize(self, event_data: Any) -> None:
        resized = getattr(event_data, "resized_columns", None) or event_data.get("resized_columns", {})
        if not resized:
            return

        new_widths = dict(self._prefs.column_widths)
        for col_idx, sizes in resized.items():
            if col_idx is None:
                continue
            if 0 <= col_idx < len(self._prefs.visible_columns):
                key = self._prefs.visible_columns[col_idx]
                new_size = sizes.get("new_size")
                if isinstance(new_size, int) and new_size > 0:
                    new_widths[key] = new_size

        self._prefs = TablePreferences(
            visible_columns=self._prefs.visible_columns,
            column_widths=new_widths,
            sort_column=self._prefs.sort_column,
            sort_ascending=self._prefs.sort_ascending,
        )
        self._save_preferences()

    def _on_columns_moved(self, event_data: Any) -> None:
        moved = getattr(event_data, "moved", None) or event_data.get("moved", {})
        data_map = (moved.get("columns") or {}).get("data") if isinstance(moved, dict) else None
        if not isinstance(data_map, dict) or not data_map:
            # Fallback: read current column order from sheet headers
            self._save_preferences()
            return

        old = self._prefs.visible_columns
        n = len(old)
        new: list[str | None] = [None] * n
        moved_old_idxs: set[int] = set()
        moved_pairs: list[tuple[int, str]] = []

        for old_idx, new_idx in data_map.items():
            if not (isinstance(old_idx, int) and isinstance(new_idx, int)):
                continue
            if not (0 <= old_idx < n and 0 <= new_idx < n):
                continue
            moved_old_idxs.add(old_idx)
            moved_pairs.append((new_idx, old[old_idx]))

        for new_idx, key in sorted(moved_pairs, key=lambda p: p[0]):
            new[new_idx] = key

        unmoved = [old[i] for i in range(n) if i not in moved_old_idxs]
        it = iter(unmoved)
        for i in range(n):
            if new[i] is None:
                new[i] = next(it)

        new_keys = self._validate_visible_keys([k for k in new if k is not None])

        # Capture current widths in the new order
        widths_list = self.sheet.get_column_widths()
        width_map: dict[str, int] = dict(self._prefs.column_widths)
        for idx, key in enumerate(new_keys):
            if idx < len(widths_list) and isinstance(widths_list[idx], (int, float)):
                width_map[key] = int(widths_list[idx])

        self._prefs = TablePreferences(
            visible_columns=new_keys,
            column_widths=width_map,
            sort_column=self._prefs.sort_column,
            sort_ascending=self._prefs.sort_ascending,
        )
        self._save_preferences()

    def _load_preferences(self) -> TablePreferences:
        prefs = db.load_table_preferences(self._table_id)
        validated = db.validate_table_preferences(prefs, self._columns) if prefs else db.default_table_preferences(self._columns)
        return TablePreferences(
            visible_columns=validated["visible_columns"],
            column_widths=validated["column_widths"],
            sort_column=validated.get("sort_column"),
            sort_ascending=validated.get("sort_ascending", True),
        )

    def _save_preferences(self) -> None:
        db.save_table_preferences(
            self._table_id,
            {
                "visible_columns": list(self._prefs.visible_columns),
                "column_widths": dict(self._prefs.column_widths),
                "sort_column": self._prefs.sort_column,
                "sort_ascending": self._prefs.sort_ascending,
            },
        )
