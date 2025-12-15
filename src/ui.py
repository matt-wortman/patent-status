"""
Main UI for Patent Status Tracker using CustomTkinter.
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
import webbrowser
from datetime import datetime
from typing import Optional
import json
import logging

from . import database as db
from . import uspto_api
from .components.column_config import PATENT_COLUMNS
from .components.data_table import DataTable
from .credentials import get_api_key, store_api_key, has_api_key
from .polling import PollingService, refresh_single_patent


# Set appearance
ctk.set_appearance_mode("system")  # Follow system theme
ctk.set_default_color_theme("blue")

# Event type categories for filtering
EVENT_CATEGORIES = {
    "Office Actions": ["CTNF", "CTFR", "NOA", "MCTNF", "MCTFR"],
    "Responses": ["RESP", "RCE", "BRCE"],
    "IDS": ["WIDS", "IDSC", "M844"],
    "Administrative": ["DOCK", "OIPE", "COMP", "EML_NTF"],
}


class PatentStatusTracker(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # Window setup
        self.title("Patent Status Tracker")
        self.geometry("1100x700")
        self.minsize(900, 600)

        # Initialize database
        db.init_database()

        # Initialize polling service
        self.polling_service = PollingService(
            on_update=self._on_polling_update,
            on_error=self._on_polling_error
        )

        # Sorting state for tables
        self.updates_sort_col = None
        self.updates_sort_reverse = False
        self.patents_sort_col = None
        self.patents_sort_reverse = False

        # Expanded patents state (for grouped updates view)
        self._load_expanded_state()

        # Updates "days back" state (allows arbitrary values via entry field)
        try:
            self._last_valid_days = int(db.get_setting("updates_days", "7") or "7")
            if self._last_valid_days < 1:
                self._last_valid_days = 7
        except ValueError:
            self._last_valid_days = 7

        # Event type filter state
        self.selected_event_types = None  # None means show all

        # Initialize font size and treeview style
        self._init_treeview_style()

        # Build UI
        self._create_widgets()

        # Check for API key on startup
        self.after(500, self._check_api_key)

        # Load initial data
        self.after(1000, self._refresh_views)

    def _init_treeview_style(self):
        """Initialize ttk.Treeview style with configurable font size."""
        self.style = ttk.Style()
        self.font_size = int(db.get_setting("font_size", "10"))
        self._apply_font_size()

    def _apply_font_size(self):
        """Apply font size to treeview widgets."""
        self.style.configure("Treeview", font=("Segoe UI", self.font_size), rowheight=self.font_size + 12)
        self.style.configure("Treeview.Heading", font=("Segoe UI", self.font_size, "bold"))
        if hasattr(self, "patents_table"):
            self.patents_table.set_font_size(self.font_size)

    def _load_expanded_state(self):
        """Load expanded patents state from settings."""
        expanded_json = db.get_setting("expanded_patents", "[]")
        try:
            self.expanded_patents = set(json.loads(expanded_json))
        except:
            self.expanded_patents = set()

    def _save_expanded_state(self):
        """Save expanded patents state to settings."""
        db.set_setting("expanded_patents", json.dumps(list(self.expanded_patents)))

    def _create_widgets(self):
        """Create all UI widgets."""
        # Main container
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Create tabs
        self.tab_updates = self.tabview.add("Updates")
        self.tab_patents = self.tabview.add("All Patents")
        self.tab_settings = self.tabview.add("Settings")

        # Build each tab
        self._build_updates_tab()
        self._build_patents_tab()
        self._build_settings_tab()

        # Status bar
        self.status_frame = ctk.CTkFrame(self, height=30)
        self.status_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Ready",
            anchor="w"
        )
        self.status_label.pack(side="left", padx=10)

        self.last_check_label = ctk.CTkLabel(
            self.status_frame,
            text="Last checked: Never",
            anchor="e"
        )
        self.last_check_label.pack(side="right", padx=10)

    def _build_updates_tab(self):
        """Build the Updates tab with grouped hierarchical view."""
        self.tab_updates.grid_columnconfigure(0, weight=1)
        self.tab_updates.grid_rowconfigure(1, weight=1)

        # Controls frame
        controls = ctk.CTkFrame(self.tab_updates)
        controls.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(controls, text="Last:").pack(side="left", padx=(10, 5))

        self.days_var = ctk.StringVar(value=str(self._last_valid_days))
        self.days_entry = ctk.CTkEntry(
            controls,
            textvariable=self.days_var,
            width=70
        )
        self.days_entry.pack(side="left", padx=2)
        self.days_entry.bind("<Return>", lambda _e: self._on_days_changed(self.days_var.get()))
        self.days_entry.bind("<FocusOut>", lambda _e: self._on_days_changed(self.days_var.get()))
        ctk.CTkLabel(controls, text="days").pack(side="left", padx=(0, 15))

        # Event type filter
        ctk.CTkLabel(controls, text="Type:").pack(side="left", padx=(0, 5))
        self.event_type_var = ctk.StringVar(value="All")
        self.event_type_combo = ctk.CTkComboBox(
            controls,
            values=["All", "Office Actions", "Responses", "IDS", "Administrative", "Other"],
            variable=self.event_type_var,
            width=130,
            command=self._on_event_type_changed
        )
        self.event_type_combo.pack(side="left", padx=2)

        # Columns button
        self.updates_cols_btn = ctk.CTkButton(
            controls,
            text="Columns",
            command=lambda: self._show_columns_dialog("updates"),
            width=80
        )
        self.updates_cols_btn.pack(side="left", padx=15)

        self.refresh_btn = ctk.CTkButton(
            controls,
            text="⟳ Refresh",
            command=self._on_refresh_click,
            width=100
        )
        self.refresh_btn.pack(side="right", padx=10)

        # Expand/Collapse all buttons
        ctk.CTkButton(
            controls,
            text="Expand All",
            command=self._expand_all_updates,
            width=80
        ).pack(side="right", padx=2)

        ctk.CTkButton(
            controls,
            text="Collapse All",
            command=self._collapse_all_updates,
            width=90
        ).pack(side="right", padx=2)

        # Updates table with hierarchical view
        table_frame = ctk.CTkFrame(self.tab_updates)
        table_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        # Create Treeview for updates - now with tree column for expand/collapse
        columns = ("date", "event", "description")
        self.updates_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="tree headings",
            selectmode="browse"
        )

        # Tree column (for expand/collapse and app#/title)
        self.updates_tree.heading("#0", text="Application / Event", anchor="w")
        self.updates_tree.column("#0", width=350, minwidth=250)

        self.updates_tree.heading("date", text="Date ↕", command=lambda: self._sort_updates("date"))
        self.updates_tree.heading("event", text="Code ↕", command=lambda: self._sort_updates("event"))
        self.updates_tree.heading("description", text="Description ↕", command=lambda: self._sort_updates("description"))

        self.updates_tree.column("date", width=100, minwidth=80)
        self.updates_tree.column("event", width=80, minwidth=60)
        self.updates_tree.column("description", width=350, minwidth=200)

        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.updates_tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.updates_tree.xview)
        self.updates_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.updates_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # Bind events
        self.updates_tree.bind("<Double-1>", self._on_update_double_click)
        self.updates_tree.bind("<<TreeviewOpen>>", self._on_tree_expand)
        self.updates_tree.bind("<<TreeviewClose>>", self._on_tree_collapse)

        # Help text
        help_label = ctk.CTkLabel(
            self.tab_updates,
            text="Click ▶ to expand | Double-click to open in USPTO | Click column headers to sort",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        help_label.grid(row=2, column=0, pady=(0, 5))

    def _build_patents_tab(self):
        """Build the All Patents tab."""
        self.tab_patents.grid_columnconfigure(0, weight=1)
        self.tab_patents.grid_rowconfigure(1, weight=1)

        # Controls frame
        controls = ctk.CTkFrame(self.tab_patents)
        controls.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(controls, text="Add Patent:").pack(side="left", padx=10)

        self.add_entry = ctk.CTkEntry(
            controls,
            placeholder_text="Application # (e.g., 17/940,142)",
            width=200
        )
        self.add_entry.pack(side="left", padx=5)
        self.add_entry.bind("<Return>", lambda e: self._on_add_patent())

        self.add_btn = ctk.CTkButton(
            controls,
            text="Add",
            command=self._on_add_patent,
            width=80
        )
        self.add_btn.pack(side="left", padx=5)

        # Columns button
        self.patents_cols_btn = ctk.CTkButton(
            controls,
            text="Columns",
            command=lambda: self._show_columns_dialog("patents"),
            width=80
        )
        self.patents_cols_btn.pack(side="left", padx=15)

        self.remove_btn = ctk.CTkButton(
            controls,
            text="Remove Selected",
            command=self._on_remove_patent,
            width=120,
            fg_color="darkred",
            hover_color="red"
        )
        self.remove_btn.pack(side="right", padx=10)

        # Patents table
        table_frame = ctk.CTkFrame(self.tab_patents)
        table_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        self.patents_table = DataTable(
            table_frame,
            table_id="patents",
            columns=PATENT_COLUMNS,
            on_double_click=self._on_patent_row_double_click,
            on_right_click=self._on_patent_row_right_click,
            font_size=self.font_size,
        )
        self.patents_table.grid(row=0, column=0, sticky="nsew")

        # Help text
        help_label = ctk.CTkLabel(
            self.tab_patents,
            text="Click headers to sort | Drag headers to reorder | Drag edges to resize | Double-click to open in USPTO | Right-click for options",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        help_label.grid(row=2, column=0, pady=(0, 5))

    def _build_settings_tab(self):
        """Build the Settings tab with scrollable content."""
        self.tab_settings.grid_columnconfigure(0, weight=1)
        self.tab_settings.grid_rowconfigure(0, weight=1)

        # Scrollable container for all settings
        scroll_frame = ctk.CTkScrollableFrame(self.tab_settings)
        scroll_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        scroll_frame.grid_columnconfigure(0, weight=1)

        # Display settings section (FIRST - font size)
        display_frame = ctk.CTkFrame(scroll_frame)
        display_frame.grid(row=0, column=0, padx=15, pady=15, sticky="ew")

        ctk.CTkLabel(
            display_frame,
            text="Display Settings",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))

        font_row = ctk.CTkFrame(display_frame, fg_color="transparent")
        font_row.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(font_row, text="Font Size:").pack(side="left")

        self.font_size_var = ctk.StringVar(value=str(self.font_size))
        self.font_size_combo = ctk.CTkComboBox(
            font_row,
            values=["8", "9", "10", "11", "12", "14", "16"],
            variable=self.font_size_var,
            width=70
        )
        self.font_size_combo.pack(side="left", padx=10)

        ctk.CTkLabel(font_row, text="(8-16)").pack(side="left")

        self.apply_font_btn = ctk.CTkButton(
            font_row,
            text="Apply",
            command=self._on_apply_font_size,
            width=80
        )
        self.apply_font_btn.pack(side="left", padx=20)

        ctk.CTkLabel(display_frame, text="").pack(pady=3)  # Spacer

        # API Key section
        api_frame = ctk.CTkFrame(scroll_frame)
        api_frame.grid(row=1, column=0, padx=15, pady=10, sticky="ew")

        ctk.CTkLabel(
            api_frame,
            text="USPTO API Key",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            api_frame,
            text="Your API key is stored securely in Windows Credential Manager.",
            text_color="gray"
        ).pack(anchor="w", padx=15)

        key_row = ctk.CTkFrame(api_frame, fg_color="transparent")
        key_row.pack(fill="x", padx=15, pady=10)

        self.api_key_entry = ctk.CTkEntry(
            key_row,
            placeholder_text="Enter USPTO API Key",
            width=350,
            show="*"
        )
        self.api_key_entry.pack(side="left", padx=(0, 10))

        self.show_key_var = ctk.BooleanVar(value=False)
        self.show_key_cb = ctk.CTkCheckBox(
            key_row,
            text="Show",
            variable=self.show_key_var,
            command=self._toggle_key_visibility,
            width=60
        )
        self.show_key_cb.pack(side="left")

        self.save_key_btn = ctk.CTkButton(
            key_row,
            text="Save Key",
            command=self._on_save_api_key,
            width=100
        )
        self.save_key_btn.pack(side="left", padx=10)

        self.api_status_label = ctk.CTkLabel(
            api_frame,
            text="",
            text_color="green"
        )
        self.api_status_label.pack(anchor="w", padx=15, pady=(0, 15))

        # Polling interval section
        poll_frame = ctk.CTkFrame(scroll_frame)
        poll_frame.grid(row=2, column=0, padx=15, pady=10, sticky="ew")

        ctk.CTkLabel(
            poll_frame,
            text="Auto-Refresh Interval",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))

        interval_row = ctk.CTkFrame(poll_frame, fg_color="transparent")
        interval_row.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(interval_row, text="Check USPTO every:").pack(side="left")

        self.interval_var = ctk.StringVar(value=db.get_setting("poll_interval", "24"))
        self.interval_combo = ctk.CTkComboBox(
            interval_row,
            values=["1", "6", "12", "24", "48", "168"],
            variable=self.interval_var,
            width=80
        )
        self.interval_combo.pack(side="left", padx=10)

        ctk.CTkLabel(interval_row, text="hours").pack(side="left")

        self.save_interval_btn = ctk.CTkButton(
            interval_row,
            text="Save",
            command=self._on_save_interval,
            width=80
        )
        self.save_interval_btn.pack(side="left", padx=20)

        ctk.CTkLabel(poll_frame, text="").pack(pady=3)  # Spacer

        # Links section
        links_frame = ctk.CTkFrame(scroll_frame)
        links_frame.grid(row=3, column=0, padx=15, pady=10, sticky="ew")

        ctk.CTkLabel(
            links_frame,
            text="Useful Links",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        links = [
            ("Get USPTO API Key", "https://data.uspto.gov/apis/getting-started"),
            ("Patent Center", "https://patentcenter.uspto.gov/"),
            ("USPTO Open Data Portal", "https://data.uspto.gov/")
        ]

        for text, url in links:
            link = ctk.CTkButton(
                links_frame,
                text=text,
                command=lambda u=url: webbrowser.open(u),
                fg_color="transparent",
                text_color=("blue", "lightblue"),
                hover_color=("gray90", "gray20"),
                anchor="w"
            )
            link.pack(anchor="w", padx=15, pady=2)

        ctk.CTkLabel(links_frame, text="").pack(pady=5)  # Spacer

        # Export section
        export_frame = ctk.CTkFrame(scroll_frame)
        export_frame.grid(row=4, column=0, padx=15, pady=10, sticky="ew")

        ctk.CTkLabel(
            export_frame,
            text="Export Data",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        export_row = ctk.CTkFrame(export_frame, fg_color="transparent")
        export_row.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkButton(
            export_row,
            text="Export to CSV",
            command=self._on_export_csv,
            width=120
        ).pack(side="left")

    # ---- Event Handlers ----

    def _check_api_key(self):
        """Check if API key is configured on startup."""
        if has_api_key():
            self.api_status_label.configure(text="API key configured", text_color="green")
            # Start polling
            interval = int(db.get_setting("poll_interval", "24"))
            self.polling_service.start(interval_minutes=interval * 60)
        else:
            self.api_status_label.configure(text="No API key - please add one", text_color="orange")
            messagebox.showinfo(
                "Setup Required",
                "Welcome! Please go to Settings and enter your USPTO API key to get started.\n\n"
                "You can get a free API key from:\nhttps://data.uspto.gov/apis/getting-started"
            )
            self.tabview.set("Settings")

    def _refresh_views(self):
        """Refresh both data views."""
        self._load_updates()
        self._load_patents()

    def _load_updates(self):
        """Load recent events into the updates table with grouping by application."""
        # Clear existing
        for item in self.updates_tree.get_children():
            self.updates_tree.delete(item)

        days = self._get_days_value()

        # Get event types to filter based on selection
        event_types = self._get_selected_event_types()

        # Get grouped events
        grouped = db.get_recent_events_grouped(days, event_types)

        # Sort groups by most recent event date
        sorted_groups = sorted(
            grouped.items(),
            key=lambda x: max(e['event_date'] for e in x[1]['events']) if x[1]['events'] else '',
            reverse=True
        )

        for app_num, data in sorted_groups:
            patent = data['patent']
            events = data['events']

            # Format display text for parent node
            formatted_num = uspto_api.format_app_number(app_num)
            title = patent['title'] or 'Unknown Title'
            if len(title) > 40:
                title = title[:37] + "..."
            parent_text = f"{formatted_num} - {title} ({len(events)})"

            # Insert parent node
            parent_id = self.updates_tree.insert(
                "", "end",
                text=parent_text,
                values=("", "", ""),
                tags=(app_num, "parent"),
                open=app_num in self.expanded_patents
            )

            # Insert child events
            for event in events:
                self.updates_tree.insert(
                    parent_id, "end",
                    text="",
                    values=(
                        event['event_date'],
                        event['event_code'],
                        event['event_description']
                    ),
                    tags=(app_num, "child")
                )

    def _get_selected_event_types(self):
        """Get list of event codes based on filter selection."""
        filter_val = self.event_type_var.get()
        if filter_val == "All":
            return None
        elif filter_val in EVENT_CATEGORIES:
            return EVENT_CATEGORIES[filter_val]
        elif filter_val == "Other":
            # Get all codes that aren't in any category
            all_known = []
            for codes in EVENT_CATEGORIES.values():
                all_known.extend(codes)
            all_codes = db.get_all_event_codes()
            return [c for c in all_codes if c not in all_known]
        return None

    def _on_event_type_changed(self, value):
        """Handle event type filter change."""
        self._load_updates()

    def _on_tree_expand(self, event):
        """Handle tree item expansion."""
        item = self.updates_tree.focus()
        tags = self.updates_tree.item(item, 'tags')
        if tags and 'parent' in tags:
            app_num = tags[0]
            self.expanded_patents.add(app_num)
            self._save_expanded_state()

    def _on_tree_collapse(self, event):
        """Handle tree item collapse."""
        item = self.updates_tree.focus()
        tags = self.updates_tree.item(item, 'tags')
        if tags and 'parent' in tags:
            app_num = tags[0]
            self.expanded_patents.discard(app_num)
            self._save_expanded_state()

    def _expand_all_updates(self):
        """Expand all parent nodes in updates tree."""
        for item in self.updates_tree.get_children():
            self.updates_tree.item(item, open=True)
            tags = self.updates_tree.item(item, 'tags')
            if tags:
                self.expanded_patents.add(tags[0])
        self._save_expanded_state()

    def _collapse_all_updates(self):
        """Collapse all parent nodes in updates tree."""
        for item in self.updates_tree.get_children():
            self.updates_tree.item(item, open=False)
        self.expanded_patents.clear()
        self._save_expanded_state()

    def _sort_updates(self, col):
        """Sort updates tree by column."""
        # Get all parent items with their data
        items = []
        for parent in self.updates_tree.get_children():
            parent_data = {
                'id': parent,
                'text': self.updates_tree.item(parent, 'text'),
                'tags': self.updates_tree.item(parent, 'tags'),
                'open': self.updates_tree.item(parent, 'open'),
                'children': []
            }
            for child in self.updates_tree.get_children(parent):
                child_data = {
                    'values': self.updates_tree.item(child, 'values'),
                    'tags': self.updates_tree.item(child, 'tags')
                }
                parent_data['children'].append(child_data)
            items.append(parent_data)

        # Toggle sort direction
        if self.updates_sort_col == col:
            self.updates_sort_reverse = not self.updates_sort_reverse
        else:
            self.updates_sort_col = col
            self.updates_sort_reverse = False

        # Sort by the most recent child event in each group
        col_idx = {"date": 0, "event": 1, "description": 2}.get(col, 0)

        def get_sort_key(item):
            if item['children']:
                return item['children'][0]['values'][col_idx] or ''
            return ''

        items.sort(key=get_sort_key, reverse=self.updates_sort_reverse)

        # Clear and rebuild
        for item in self.updates_tree.get_children():
            self.updates_tree.delete(item)

        for item in items:
            parent_id = self.updates_tree.insert(
                "", "end",
                text=item['text'],
                values=("", "", ""),
                tags=item['tags'],
                open=item['open']
            )
            for child in item['children']:
                self.updates_tree.insert(
                    parent_id, "end",
                    text="",
                    values=child['values'],
                    tags=child['tags']
                )

        # Update heading to show sort direction
        indicator = "▲" if not self.updates_sort_reverse else "▼"
        for c in ["date", "event", "description"]:
            text = {"date": "Date", "event": "Code", "description": "Description"}[c]
            if c == col:
                text = f"{text} {indicator}"
            else:
                text = f"{text} ↕"
            self.updates_tree.heading(c, text=text)

    def _show_columns_dialog(self, table_type):
        """Show dialog to select visible columns."""
        if table_type == "patents":
            if hasattr(self, "patents_table"):
                self.patents_table.show_column_selector()
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Select Columns")
        dialog.geometry("300x350")
        dialog.transient(self)
        dialog.grab_set()

        # Center on parent
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(
            dialog,
            text="Select columns to display:",
            font=ctk.CTkFont(size=14)
        ).pack(pady=15)

        # Updates-only: (All Patents uses tksheet selector)
        all_cols = [("date", "Date"), ("event", "Event Code"), ("description", "Description")]
        setting_key = "updates_columns"
        tree = self.updates_tree

        # Load current visibility settings
        visible_json = db.get_setting(setting_key, None)
        if visible_json:
            try:
                visible_cols = json.loads(visible_json)
            except:
                visible_cols = [c[0] for c in all_cols]
        else:
            visible_cols = [c[0] for c in all_cols]

        # Create checkboxes
        col_vars = {}
        for col_id, col_name in all_cols:
            var = ctk.BooleanVar(value=col_id in visible_cols)
            col_vars[col_id] = var
            ctk.CTkCheckBox(
                dialog,
                text=col_name,
                variable=var
            ).pack(anchor="w", padx=30, pady=5)

        def apply_columns():
            # Get selected columns
            selected = [col_id for col_id, var in col_vars.items() if var.get()]
            if not selected:
                messagebox.showwarning("Warning", "Select at least one column.")
                return

            # Save to settings
            db.set_setting(setting_key, json.dumps(selected))

            # Apply to treeview - show/hide columns by setting width
            for col_id, _ in all_cols:
                if col_id in selected:
                    # Restore default width
                    if table_type == "updates":
                        widths = {"date": 100, "event": 80, "description": 350}
                    else:
                        widths = {"app_number": 110, "title": 300, "status": 200,
                                  "status_date": 100, "applicant": 200, "examiner": 150}
                    tree.column(col_id, width=widths.get(col_id, 100), minwidth=50)
                else:
                    tree.column(col_id, width=0, minwidth=0)

            dialog.destroy()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(btn_frame, text="Apply", command=apply_columns, width=100).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=dialog.destroy, width=100).pack(side="left", padx=10)

    def _on_apply_font_size(self):
        """Apply the selected font size."""
        try:
            new_size = int(self.font_size_var.get())
            if 8 <= new_size <= 16:
                self.font_size = new_size
                db.set_setting("font_size", str(new_size))
                self._apply_font_size()
                messagebox.showinfo("Applied", f"Font size set to {new_size}. Tables updated.")
            else:
                messagebox.showwarning("Invalid", "Font size must be between 8 and 16.")
        except ValueError:
            messagebox.showwarning("Invalid", "Please enter a valid number.")

    def _patent_to_row(self, patent: dict) -> dict:
        app_raw = patent.get("application_number") or ""
        return {
            "application_number": app_raw,
            "app_number": uspto_api.format_app_number(app_raw) if app_raw else "",
            "title": patent.get("title") or "",
            "current_status": patent.get("current_status") or "Not fetched",
            "status_date": patent.get("status_date") or "",
            "patent_number": patent.get("patent_number") or "",
            "expiration_date": patent.get("expiration_date") or "",
            "applicant": patent.get("applicant") or "",
            "examiner": patent.get("examiner") or "",
            "inventor": patent.get("inventor") or "",
            "filing_date": patent.get("filing_date") or "",
            "grant_date": patent.get("grant_date") or "",
            "publication_number": patent.get("publication_number") or "",
            "publication_date": patent.get("publication_date") or "",
            "art_unit": patent.get("art_unit") or "",
            "docket_number": patent.get("docket_number") or "",
            "entity_status": patent.get("entity_status") or "",
            "application_type_label": patent.get("application_type_label") or "",
            "customer_number": patent.get("customer_number") or "",
            "confirmation_number": patent.get("confirmation_number") or "",
            "pta_total_days": patent.get("pta_total_days") if patent.get("pta_total_days") is not None else "",
            "effective_filing_date": patent.get("effective_filing_date") or "",
            "first_inventor_to_file": patent.get("first_inventor_to_file") or "",
            "last_checked": patent.get("last_checked") or "",
        }

    def _load_patents(self):
        """Load all patents into the patents table."""
        patents = db.get_all_patents()
        rows = [self._patent_to_row(p) for p in patents]

        if hasattr(self, "patents_table"):
            self.patents_table.set_data(rows)

    def _get_days_value(self) -> int:
        raw = (self.days_var.get() or "").strip()
        try:
            days = int(raw)
            if days < 1:
                raise ValueError
            return days
        except ValueError:
            return self._last_valid_days

    def _on_days_changed(self, _value=None):
        """Handle days filter change."""
        raw = (self.days_var.get() or "").strip()
        try:
            days = int(raw)
            if days < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid", "Please enter a valid number of days (>= 1).")
            self.days_var.set(str(self._last_valid_days))
            return

        self._last_valid_days = days
        db.set_setting("updates_days", str(days))
        self._load_updates()

    def _on_refresh_click(self):
        """Handle refresh button click."""
        if not has_api_key():
            messagebox.showerror("Error", "Please configure your USPTO API key in Settings first.")
            return

        self.refresh_btn.configure(state="disabled", text="Refreshing...")
        self.status_label.configure(text="Checking USPTO for updates...")
        self.update()

        def do_refresh():
            result = self.polling_service.poll_now()
            self.after(0, lambda: self._refresh_complete(result))

        import threading
        threading.Thread(target=do_refresh, daemon=True).start()

    def _refresh_complete(self, result):
        """Handle refresh completion."""
        self.refresh_btn.configure(state="normal", text="Refresh Now")

        if result['new_events']:
            self.status_label.configure(
                text=f"Found {len(result['new_events'])} new events across {result['updated_patents']} patents"
            )
        else:
            self.status_label.configure(text="No new updates found")

        self.last_check_label.configure(
            text=f"Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        if result['errors']:
            messagebox.showwarning(
                "Some Errors Occurred",
                f"Encountered {len(result['errors'])} errors:\n\n" +
                "\n".join(result['errors'][:5])
            )

        self._refresh_views()

    def _on_add_patent(self):
        """Handle adding a new patent."""
        app_num = self.add_entry.get().strip()
        if not app_num:
            return

        if not has_api_key():
            messagebox.showerror("Error", "Please configure your USPTO API key in Settings first.")
            return

        self.add_btn.configure(state="disabled", text="Adding...")
        self.update()

        try:
            # Try to fetch from USPTO first to validate
            raw_data = uspto_api.fetch_application(app_num)
            parsed = uspto_api.parse_application_data(raw_data)

            if not parsed:
                raise ValueError("Could not parse USPTO response")

            # Add to database
            normalized = uspto_api.normalize_app_number(app_num)
            patent_id = db.add_patent(normalized)

            if patent_id is None:
                messagebox.showinfo("Info", "This patent is already being tracked.")
            else:
                # Update with fetched data
                db.update_patent(
                    normalized,
                    title=parsed['metadata']['title'],
                    applicant=parsed['metadata']['applicant'],
                    inventor=parsed['metadata']['inventor'],
                    filing_date=parsed['metadata']['filing_date'],
                    current_status=parsed['metadata']['current_status'],
                    status_date=parsed['metadata']['status_date'],
                    examiner=parsed['metadata']['examiner'],
                    art_unit=parsed['metadata']['art_unit'],
                    customer_number=parsed['metadata']['customer_number'],
                    last_checked=datetime.now().isoformat()
                )

                # Get the patent ID for adding events
                patent = db.get_patent_by_app_number(normalized)

                # Add events
                for event in parsed['events']:
                    db.add_event(
                        patent['id'],
                        event['event_code'],
                        event['event_description'],
                        event['event_date']
                    )

                self.add_entry.delete(0, "end")
                self._refresh_views()
                messagebox.showinfo(
                    "Success",
                    f"Added: {parsed['metadata']['title']}\nStatus: {parsed['metadata']['current_status']}"
                )

        except uspto_api.USPTOApiError as e:
            messagebox.showerror("USPTO Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add patent: {str(e)}")
        finally:
            self.add_btn.configure(state="normal", text="Add")

    def _on_remove_patent(self):
        """Handle removing a patent."""
        if not hasattr(self, "patents_table"):
            return

        row = self.patents_table.get_selected_row()
        if not row:
            messagebox.showinfo("Info", "Please select a patent to remove.")
            return

        app_num = row.get("application_number")
        if not app_num:
            return

        if messagebox.askyesno("Confirm", f"Remove patent {uspto_api.format_app_number(app_num)} from tracking?"):
            db.remove_patent(app_num)
            self._refresh_views()

    def _on_update_double_click(self, event):
        """Handle double-click on update row."""
        selection = self.updates_tree.selection()
        if selection:
            item = self.updates_tree.item(selection[0])
            tags = item['tags']
            if tags:
                # First tag is always the app number
                app_num = tags[0]
                self._show_link_dialog(app_num)

    def _on_patent_row_double_click(self, row_data: dict):
        """Handle double-click on a patent row in the tksheet table."""
        app_num = row_data.get("application_number")
        if app_num:
            self._show_link_dialog(app_num)

    def _on_patent_row_right_click(self, event, row_data: dict):
        """Handle right-click on a patent row in the tksheet table."""
        self._show_patent_context_menu(event, row_data=row_data)

    def _show_link_dialog(self, app_num: str):
        """Show dialog with links to USPTO sites."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Open in USPTO")
        dialog.geometry("380x220")
        dialog.transient(self)
        dialog.grab_set()

        # Center on parent
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(
            dialog,
            text=f"Open {uspto_api.format_app_number(app_num)} in:",
            font=ctk.CTkFont(size=14)
        ).pack(pady=15)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(0, 10), fill="x")

        ctk.CTkButton(
            btn_frame,
            text="Patent Center",
            command=lambda: [webbrowser.open(uspto_api.get_patent_center_url(app_num)), dialog.destroy()],
        ).pack(fill="x", pady=5)

        ctk.CTkButton(
            btn_frame,
            text="Patent Center (Docs)",
            command=lambda: [webbrowser.open(uspto_api.get_patent_center_documents_url(app_num)), dialog.destroy()],
        ).pack(fill="x", pady=5)

        ctk.CTkButton(
            btn_frame,
            text="Public PAIR",
            command=lambda: [webbrowser.open(uspto_api.get_public_pair_url(app_num)), dialog.destroy()],
        ).pack(fill="x", pady=5)

        ctk.CTkLabel(
            dialog,
            text="If Patent Center shows /401, try Public PAIR.",
            text_color="gray",
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 12))

    def _show_patent_context_menu(self, event, row_data: Optional[dict] = None):
        """Show context menu for patents table."""
        if row_data is None and hasattr(self, "patents_table"):
            row_data = self.patents_table.get_selected_row()

        if not row_data:
            return

        app_num = row_data.get("application_number")

        if not app_num:
            return

        menu = ctk.CTkToplevel(self)
        menu.overrideredirect(True)
        menu.geometry(f"+{event.x_root}+{event.y_root}")
        menu.transient(self)

        def close_menu():
            menu.destroy()

        menu.bind("<FocusOut>", lambda e: close_menu())

        ctk.CTkButton(
            menu,
            text="Open in Patent Center",
            command=lambda: [webbrowser.open(uspto_api.get_patent_center_url(app_num)), close_menu()],
            width=180,
            anchor="w"
        ).pack(fill="x")

        ctk.CTkButton(
            menu,
            text="Open Patent Center (Docs)",
            command=lambda: [webbrowser.open(uspto_api.get_patent_center_documents_url(app_num)), close_menu()],
            width=180,
            anchor="w"
        ).pack(fill="x")

        ctk.CTkButton(
            menu,
            text="Open in Public PAIR",
            command=lambda: [webbrowser.open(uspto_api.get_public_pair_url(app_num)), close_menu()],
            width=180,
            anchor="w"
        ).pack(fill="x")

        ctk.CTkButton(
            menu,
            text="Refresh This Patent",
            command=lambda: [self._refresh_single(app_num), close_menu()],
            width=180,
            anchor="w"
        ).pack(fill="x")

        menu.focus_set()

    def _refresh_single(self, app_num: str):
        """Refresh a single patent."""
        try:
            refresh_single_patent(app_num)
            self._refresh_views()
            self.status_label.configure(text=f"Refreshed {uspto_api.format_app_number(app_num)}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _toggle_key_visibility(self):
        """Toggle API key visibility."""
        if self.show_key_var.get():
            self.api_key_entry.configure(show="")
        else:
            self.api_key_entry.configure(show="*")

    def _on_save_api_key(self):
        """Save the API key."""
        key = self.api_key_entry.get().strip()

        if not key:
            messagebox.showerror("Error", "Please enter an API key.")
            return

        self.save_key_btn.configure(state="disabled", text="Validating...")
        self.update()

        # Validate the key
        if uspto_api.validate_api_key(key):
            if store_api_key(key):
                self.api_status_label.configure(text="API key saved and validated!", text_color="green")
                self.api_key_entry.delete(0, "end")

                # Start polling if not already running
                interval = int(db.get_setting("poll_interval", "24"))
                self.polling_service.start(interval_minutes=interval * 60)
            else:
                self.api_status_label.configure(text="Failed to save key", text_color="red")
        else:
            self.api_status_label.configure(text="Invalid API key", text_color="red")

        self.save_key_btn.configure(state="normal", text="Save Key")

    def _on_save_interval(self):
        """Save the polling interval."""
        interval = self.interval_var.get()
        db.set_setting("poll_interval", interval)

        # Update running service
        self.polling_service.set_interval(int(interval) * 60)

        messagebox.showinfo("Saved", f"Polling interval set to {interval} hours.")

    def _on_export_csv(self):
        """Export patents to CSV."""
        from tkinter import filedialog
        import csv

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfilename="patent_status_export.csv"
        )

        if not filepath:
            return

        patents = db.get_all_patents()

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            columns_by_key = {c["key"]: c for c in PATENT_COLUMNS}
            header_by_key = {k: v["header"] for k, v in columns_by_key.items()}
            header_by_key["last_checked"] = "Last Checked"

            if hasattr(self, "patents_table"):
                keys = [k for k in self.patents_table.get_visible_columns() if k in columns_by_key]
            else:
                keys = [c["key"] for c in PATENT_COLUMNS if c.get("default_visible")]

            # Preserve old export behavior by always including last_checked at the end.
            if "last_checked" not in keys:
                keys.append("last_checked")

            writer = csv.writer(f)
            writer.writerow([header_by_key.get(k, k) for k in keys])

            for patent in patents:
                row = self._patent_to_row(patent)
                writer.writerow([row.get(k, "") for k in keys])

        messagebox.showinfo("Exported", f"Data exported to:\n{filepath}")

    def _on_polling_update(self, new_events):
        """Callback when polling finds new events."""
        self.after(0, lambda: self._handle_polling_update(new_events))

    def _handle_polling_update(self, new_events):
        """Handle polling update on main thread."""
        self._refresh_views()
        self.status_label.configure(text=f"Found {len(new_events)} new events")

        # Show notification
        if new_events:
            # Could add system tray notification here
            pass

    def _on_polling_error(self, errors):
        """Callback when polling encounters errors."""
        self.after(0, lambda: self.status_label.configure(
            text=f"Polling error: {len(errors)} failures"
        ))

    def on_closing(self):
        """Handle window close."""
        self.polling_service.stop()
        self.destroy()


def run_app():
    """Run the application."""
    # Basic file logging for troubleshooting (Documents/PatentStatusTracker/app.log)
    try:
        log_dir = db.get_db_path().parent
        log_dir.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=str(log_dir / "app.log"),
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    except Exception:
        # Logging should never prevent the app from starting.
        pass

    app = PatentStatusTracker()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
