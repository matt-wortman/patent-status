"""Column selector dialog for choosing visible columns."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk
from tkinter import messagebox

from .column_config import get_categories, get_default_visible


class ColumnSelectorDialog(ctk.CTkToplevel):
    def __init__(self, parent, columns: list[dict[str, Any]], visible_keys: list[str]):
        super().__init__(parent)

        self._columns = columns
        self._visible_keys = set(visible_keys)
        self._vars: dict[str, ctk.BooleanVar] = {}
        self._result: list[str] | None = None

        self.title("Select Columns")
        self.geometry("460x560")
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        ctk.CTkLabel(self, text="Select columns to display:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 8))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=15, pady=(0, 8))

        ctk.CTkButton(actions, text="Select All", width=100, command=self._select_all).pack(side="left", padx=(0, 8))
        ctk.CTkButton(actions, text="Deselect All", width=110, command=self._deselect_all).pack(side="left", padx=(0, 8))
        ctk.CTkButton(actions, text="Reset Defaults", width=120, command=self._reset_defaults).pack(side="left")

        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        grouped = get_categories(columns)
        for category, cols in grouped.items():
            ctk.CTkLabel(scroll, text=category, font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", pady=(10, 4))
            for col in cols:
                key = col["key"]
                var = ctk.BooleanVar(value=key in self._visible_keys)
                self._vars[key] = var
                ctk.CTkCheckBox(scroll, text=col.get("header", key), variable=var).pack(anchor="w", padx=10, pady=4)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=(0, 15))

        ctk.CTkButton(btns, text="OK", width=120, command=self._on_ok).pack(side="left", padx=10)
        ctk.CTkButton(btns, text="Cancel", width=120, command=self._on_cancel).pack(side="left", padx=10)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def get_result(self) -> list[str] | None:
        self.wait_window()
        return self._result

    def _select_all(self) -> None:
        for var in self._vars.values():
            var.set(True)

    def _deselect_all(self) -> None:
        for var in self._vars.values():
            var.set(False)

    def _reset_defaults(self) -> None:
        defaults = set(get_default_visible(self._columns))
        for key, var in self._vars.items():
            var.set(key in defaults)

    def _on_ok(self) -> None:
        selected = [c["key"] for c in self._columns if self._vars[c["key"]].get()]
        if not selected:
            # Keep dialog open; require at least one column.
            messagebox.showwarning("Warning", "Select at least one column.")
            return
        self._result = selected
        self.destroy()

    def _on_cancel(self) -> None:
        self._result = None
        self.destroy()
