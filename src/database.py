"""
Database module for Patent Status Tracker.
Uses SQLite stored in user's Documents folder.
"""

import sqlite3
import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


def get_db_path() -> Path:
    """Get the database path in user's Documents folder."""
    documents = Path.home() / "Documents" / "PatentStatusTracker"
    documents.mkdir(parents=True, exist_ok=True)
    return documents / "patents.db"


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database():
    """Initialize the database schema."""
    conn = get_connection()
    cursor = conn.cursor()

    # Patents table - stores patent applications being tracked
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_number TEXT UNIQUE NOT NULL,
            title TEXT,
            applicant TEXT,
            inventor TEXT,
            filing_date TEXT,
            examiner TEXT,
            current_status TEXT,
            status_date TEXT,
            art_unit TEXT,
            customer_number TEXT,
            last_checked TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Events table - stores all events/transactions for each patent
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id INTEGER NOT NULL,
            event_code TEXT,
            event_description TEXT,
            event_date TEXT,
            first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
            is_new INTEGER DEFAULT 1,
            FOREIGN KEY (patent_id) REFERENCES patents(id) ON DELETE CASCADE,
            UNIQUE(patent_id, event_code, event_date)
        )
    """)

    # Settings table - stores user preferences
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Create indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_patent_id ON events(patent_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_first_seen ON events(first_seen)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_patents_app_num ON patents(application_number)")

    conn.commit()
    conn.close()

    # Run migrations for new columns and tables
    migrate_database()


def migrate_database():
    """Apply schema migrations for new API fields."""
    conn = get_connection()
    cursor = conn.cursor()

    # Check existing columns in patents table
    cursor.execute("PRAGMA table_info(patents)")
    existing_columns = {row['name'] for row in cursor.fetchall()}

    # All new columns to add to patents table
    new_patent_columns = [
        # Grant & Publication
        ('patent_number', 'TEXT'),
        ('grant_date', 'TEXT'),
        ('publication_number', 'TEXT'),
        ('publication_date', 'TEXT'),
        ('publication_date_bag', 'TEXT'),
        ('publication_sequence_number_bag', 'TEXT'),
        ('publication_category_bag', 'TEXT'),
        # PCT / International
        ('pct_publication_number', 'TEXT'),
        ('pct_publication_date', 'TEXT'),
        ('international_registration_number', 'TEXT'),
        ('international_registration_publication_date', 'TEXT'),
        ('national_stage_indicator', 'INTEGER'),
        # Application Type & Classification
        ('application_type_code', 'TEXT'),
        ('application_type_label', 'TEXT'),
        ('application_type_category', 'TEXT'),
        ('uspc_class', 'TEXT'),
        ('uspc_subclass', 'TEXT'),
        ('uspc_symbol', 'TEXT'),
        ('cpc_classification_bag', 'TEXT'),
        # Filing & Docket
        ('docket_number', 'TEXT'),
        ('confirmation_number', 'TEXT'),
        ('effective_filing_date', 'TEXT'),
        ('first_inventor_to_file', 'TEXT'),
        # Entity Status
        ('entity_status', 'TEXT'),
        ('small_entity_indicator', 'INTEGER'),
        # Status code
        ('status_code', 'INTEGER'),
        # Patent Term Adjustment
        ('pta_total_days', 'INTEGER'),
        ('pta_a_delay', 'INTEGER'),
        ('pta_b_delay', 'INTEGER'),
        ('pta_c_delay', 'INTEGER'),
        ('pta_applicant_delay', 'INTEGER'),
        ('pta_overlap_delay', 'REAL'),
        ('pta_non_overlap_delay', 'REAL'),
        ('expiration_date', 'TEXT'),
        ('pta_history_bag', 'TEXT'),
        # Raw JSON storage for complex/nested data
        ('applicant_bag', 'TEXT'),
        ('inventor_bag', 'TEXT'),
        ('foreign_priority_bag', 'TEXT'),
        ('attorney_bag', 'TEXT'),
        ('assignment_bag', 'TEXT'),
    ]

    # Add missing columns to patents table
    for col_name, col_type in new_patent_columns:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE patents ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass  # Column already exists

    # Create continuity table (for /continuity endpoint)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS continuity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id INTEGER NOT NULL,
            relationship_type TEXT,
            related_app_number TEXT,
            related_patent_number TEXT,
            filing_date TEXT,
            status_description TEXT,
            status_code INTEGER,
            continuity_type_code TEXT,
            continuity_type_description TEXT,
            first_inventor_to_file INTEGER,
            last_updated TEXT,
            FOREIGN KEY (patent_id) REFERENCES patents(id) ON DELETE CASCADE,
            UNIQUE(patent_id, relationship_type, related_app_number)
        )
    """)

    # Create documents table (for /documents endpoint)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id INTEGER NOT NULL,
            document_identifier TEXT,
            document_code TEXT,
            document_description TEXT,
            official_date TEXT,
            direction_category TEXT,
            download_options TEXT,
            page_count INTEGER,
            last_updated TEXT,
            FOREIGN KEY (patent_id) REFERENCES patents(id) ON DELETE CASCADE,
            UNIQUE(patent_id, document_identifier)
        )
    """)

    # Create assignments table (for /assignment endpoint)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patent_id INTEGER NOT NULL,
            reel_number TEXT,
            frame_number TEXT,
            reel_frame TEXT,
            page_count INTEGER,
            received_date TEXT,
            recorded_date TEXT,
            mailed_date TEXT,
            conveyance_text TEXT,
            assignor_bag TEXT,
            assignee_bag TEXT,
            document_url TEXT,
            last_updated TEXT,
            FOREIGN KEY (patent_id) REFERENCES patents(id) ON DELETE CASCADE
        )
    """)

    # Create indexes for new tables
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_continuity_patent_id ON continuity(patent_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_patent_id ON documents(patent_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_code ON documents(document_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_assignments_patent_id ON assignments(patent_id)")

    conn.commit()
    conn.close()


def add_patent(application_number: str) -> Optional[int]:
    """Add a new patent to track. Returns patent ID or None if already exists."""
    # Normalize application number (remove slashes, spaces)
    app_num = application_number.replace("/", "").replace(" ", "").replace(",", "")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO patents (application_number) VALUES (?)",
            (app_num,)
        )
        conn.commit()
        patent_id = cursor.lastrowid
        conn.close()
        return patent_id
    except sqlite3.IntegrityError:
        conn.close()
        return None


def remove_patent(application_number: str) -> bool:
    """Remove a patent from tracking."""
    app_num = application_number.replace("/", "").replace(" ", "").replace(",", "")

    conn = get_connection()
    cursor = conn.cursor()

    # Get patent ID
    cursor.execute("SELECT id FROM patents WHERE application_number = ?", (app_num,))
    row = cursor.fetchone()

    if row:
        patent_id = row['id']
        cursor.execute("DELETE FROM events WHERE patent_id = ?", (patent_id,))
        cursor.execute("DELETE FROM continuity WHERE patent_id = ?", (patent_id,))
        cursor.execute("DELETE FROM documents WHERE patent_id = ?", (patent_id,))
        cursor.execute("DELETE FROM assignments WHERE patent_id = ?", (patent_id,))
        cursor.execute("DELETE FROM patents WHERE id = ?", (patent_id,))
        conn.commit()
        conn.close()
        return True

    conn.close()
    return False


def get_all_patents() -> list:
    """Get all tracked patents."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM patents ORDER BY application_number
    """)
    patents = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return patents


def get_patent_by_app_number(application_number: str) -> Optional[dict]:
    """Get a patent by application number."""
    app_num = application_number.replace("/", "").replace(" ", "").replace(",", "")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patents WHERE application_number = ?", (app_num,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def update_patent(application_number: str, **kwargs):
    """Update patent metadata."""
    app_num = application_number.replace("/", "").replace(" ", "").replace(",", "")

    conn = get_connection()
    cursor = conn.cursor()

    # All allowed fields for patent updates
    allowed_fields = [
        # Original fields
        'title', 'applicant', 'inventor', 'filing_date', 'examiner',
        'current_status', 'status_date', 'art_unit', 'customer_number', 'last_checked',
        # Grant & Publication
        'patent_number', 'grant_date', 'publication_number', 'publication_date',
        'publication_date_bag', 'publication_sequence_number_bag', 'publication_category_bag',
        # PCT / International
        'pct_publication_number', 'pct_publication_date', 'international_registration_number',
        'international_registration_publication_date', 'national_stage_indicator',
        # Application Type & Classification
        'application_type_code', 'application_type_label', 'application_type_category',
        'uspc_class', 'uspc_subclass', 'uspc_symbol', 'cpc_classification_bag',
        # Filing & Docket
        'docket_number', 'confirmation_number', 'effective_filing_date', 'first_inventor_to_file',
        # Entity Status
        'entity_status', 'small_entity_indicator',
        # Status code
        'status_code',
        # Patent Term Adjustment
        'pta_total_days', 'pta_a_delay', 'pta_b_delay', 'pta_c_delay', 'pta_applicant_delay',
        'pta_overlap_delay', 'pta_non_overlap_delay', 'expiration_date', 'pta_history_bag',
        # Raw JSON storage
        'applicant_bag', 'inventor_bag', 'foreign_priority_bag', 'attorney_bag', 'assignment_bag',
    ]

    # Build update query dynamically
    fields = []
    values = []
    for key, value in kwargs.items():
        if key in allowed_fields and re.fullmatch(r"[a-z_]+", key):
            fields.append(f"{key} = ?")
            values.append(value)

    if fields:
        values.append(app_num)
        query = f"UPDATE patents SET {', '.join(fields)} WHERE application_number = ?"
        cursor.execute(query, values)
        conn.commit()

    conn.close()


def add_event(patent_id: int, event_code: str, event_description: str, event_date: str) -> bool:
    """Add an event for a patent. Returns True if new event, False if already exists."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO events (patent_id, event_code, event_description, event_date)
            VALUES (?, ?, ?, ?)
        """, (patent_id, event_code, event_description, event_date))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def get_recent_events(days: int = 7, event_types: list = None) -> list:
    """Get events that occurred at USPTO in the last N days.

    Args:
        days: Number of days to look back
        event_types: Optional list of event code prefixes to filter (e.g., ['CTNF', 'CTFR'])
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            e.*,
            p.application_number,
            p.title,
            p.applicant
        FROM events e
        JOIN patents p ON e.patent_id = p.id
        WHERE date(e.event_date) >= date('now', ?)
    """
    params = [f'-{days} days']

    if event_types:
        placeholders = ','.join('?' * len(event_types))
        query += f" AND e.event_code IN ({placeholders})"
        params.extend(event_types)

    query += " ORDER BY e.event_date DESC, p.application_number"

    cursor.execute(query, params)
    events = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return events


def get_recent_events_grouped(days: int = 7, event_types: list = None) -> dict:
    """Get events grouped by application number.

    Returns:
        dict: {app_number: {'patent': {...}, 'events': [...]}}
    """
    events = get_recent_events(days, event_types)

    grouped = {}
    for event in events:
        app_num = event['application_number']
        if app_num not in grouped:
            grouped[app_num] = {
                'patent': {
                    'application_number': app_num,
                    'title': event['title'],
                    'applicant': event['applicant']
                },
                'events': []
            }
        grouped[app_num]['events'].append(event)

    return grouped


def get_all_event_codes() -> list:
    """Get all unique event codes in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT event_code FROM events ORDER BY event_code")
    codes = [row['event_code'] for row in cursor.fetchall()]
    conn.close()
    return codes


def get_events_for_patent(patent_id: int) -> list:
    """Get all events for a specific patent."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM events
        WHERE patent_id = ?
        ORDER BY event_date DESC
    """, (patent_id,))

    events = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return events


def mark_events_seen(patent_id: int):
    """Mark all events for a patent as seen (not new)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE events SET is_new = 0 WHERE patent_id = ?", (patent_id,))
    conn.commit()
    conn.close()


def get_setting(key: str, default: str = None) -> Optional[str]:
    """Get a setting value."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else default


def set_setting(key: str, value: str):
    """Set a setting value."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
    """, (key, value))
    conn.commit()
    conn.close()


# ---- Table Preference Helpers (tksheet) ----

def save_table_preferences(table_id: str, prefs: dict[str, Any]) -> None:
    """Save table preferences as JSON in the settings table."""
    set_setting(f"{table_id}_table_prefs", json.dumps(prefs))


def load_table_preferences(table_id: str) -> dict[str, Any] | None:
    """Load table preferences from settings; returns None if missing or corrupted."""
    raw = get_setting(f"{table_id}_table_prefs", None)
    if raw:
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    # Backward-compatible migration (old per-table visible columns lists)
    if table_id == "patents":
        legacy = get_setting("patents_columns", None)
        if not legacy:
            return None
        try:
            cols = json.loads(legacy)
        except json.JSONDecodeError:
            return None
        if not isinstance(cols, list):
            return None
        mapping = {
            "status": "current_status",
            "expiration": "expiration_date",
        }
        visible = [mapping.get(c, c) for c in cols if isinstance(c, str)]
        return {"visible_columns": visible, "column_widths": {}}

    return None


def default_table_preferences(columns: list[dict[str, Any]]) -> dict[str, Any]:
    """Build default preferences from column definitions."""
    visible = [c["key"] for c in columns if c.get("default_visible")]
    widths = {c["key"]: int(c.get("width", 120)) for c in columns}
    return {
        "visible_columns": visible,
        "column_widths": widths,
        "sort_column": None,
        "sort_ascending": True,
    }


def validate_table_preferences(prefs: dict[str, Any], columns: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Validate and migrate table preferences.
    - Drops unknown column keys
    - Appends any new default-visible columns
    - Filters invalid widths
    - Resets to defaults if nothing remains
    """
    valid_keys = [c["key"] for c in columns if isinstance(c.get("key"), str)]
    valid_key_set = set(valid_keys)
    default_visible = [c["key"] for c in columns if c.get("default_visible") and c.get("key") in valid_key_set]

    visible_raw = prefs.get("visible_columns", [])
    if not isinstance(visible_raw, list):
        visible_raw = []
    visible = [k for k in visible_raw if isinstance(k, str) and k in valid_key_set]

    # If prefs are empty/corrupted, fall back to defaults
    if not visible:
        visible = list(default_visible)

    # Append any new columns that are default-visible and not already present
    existing = set(visible)
    for key in default_visible:
        if key not in existing:
            visible.append(key)
            existing.add(key)

    widths_raw = prefs.get("column_widths", {})
    widths: dict[str, int] = {}
    if isinstance(widths_raw, dict):
        for k, v in widths_raw.items():
            if isinstance(k, str) and k in valid_key_set and isinstance(v, int) and v > 0:
                widths[k] = v

    sort_column = prefs.get("sort_column")
    if not isinstance(sort_column, str) or sort_column not in valid_key_set:
        sort_column = None
    sort_ascending = bool(prefs.get("sort_ascending", True))

    return {
        "visible_columns": visible,
        "column_widths": widths,
        "sort_column": sort_column,
        "sort_ascending": sort_ascending,
    }


# ---- Continuity Table Functions ----

def save_continuity(patent_id: int, parents: list, children: list):
    """Save continuity data for a patent (replaces existing data)."""
    conn = get_connection()
    cursor = conn.cursor()

    # Clear existing continuity data for this patent
    cursor.execute("DELETE FROM continuity WHERE patent_id = ?", (patent_id,))

    now = datetime.now().isoformat()

    # Insert parent records
    for parent in parents:
        cursor.execute("""
            INSERT INTO continuity
            (patent_id, relationship_type, related_app_number, related_patent_number,
             filing_date, status_description, status_code, continuity_type_code,
             continuity_type_description, first_inventor_to_file, last_updated)
            VALUES (?, 'parent', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (patent_id, parent.get('app_number'), parent.get('patent_number'),
              parent.get('filing_date'), parent.get('status'), parent.get('status_code'),
              parent.get('continuity_type'), parent.get('continuity_description'),
              parent.get('first_inventor_to_file'), now))

    # Insert child records
    for child in children:
        cursor.execute("""
            INSERT INTO continuity
            (patent_id, relationship_type, related_app_number, related_patent_number,
             filing_date, status_description, status_code, continuity_type_code,
             continuity_type_description, first_inventor_to_file, last_updated)
            VALUES (?, 'child', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (patent_id, child.get('app_number'), child.get('patent_number'),
              child.get('filing_date'), child.get('status'), child.get('status_code'),
              child.get('continuity_type'), child.get('continuity_description'),
              child.get('first_inventor_to_file'), now))

    conn.commit()
    conn.close()


def get_continuity(patent_id: int) -> dict:
    """Get continuity data for a patent."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM continuity WHERE patent_id = ? ORDER BY filing_date
    """, (patent_id,))

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    parents = [r for r in rows if r['relationship_type'] == 'parent']
    children = [r for r in rows if r['relationship_type'] == 'child']

    return {'parents': parents, 'children': children}


# ---- Documents Table Functions ----

def save_documents(patent_id: int, documents: list):
    """Save document data for a patent (upserts existing data)."""
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now().isoformat()

    for doc in documents:
        cursor.execute("""
            INSERT OR REPLACE INTO documents
            (patent_id, document_identifier, document_code, document_description,
             official_date, direction_category, download_options, page_count, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (patent_id, doc.get('document_id'), doc.get('document_code'),
              doc.get('description'), doc.get('date'), doc.get('direction'),
              doc.get('download_options'), doc.get('page_count'), now))

    conn.commit()
    conn.close()


def get_documents(patent_id: int, doc_types: list = None) -> list:
    """Get documents for a patent, optionally filtered by document code."""
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM documents WHERE patent_id = ?"
    params = [patent_id]

    if doc_types:
        placeholders = ','.join('?' * len(doc_types))
        query += f" AND document_code IN ({placeholders})"
        params.extend(doc_types)

    query += " ORDER BY official_date DESC"

    cursor.execute(query, params)
    documents = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return documents


# ---- Assignments Table Functions ----

def save_assignments(patent_id: int, assignments: list):
    """Save assignment data for a patent."""
    conn = get_connection()
    cursor = conn.cursor()

    # Clear existing assignment data for this patent
    cursor.execute("DELETE FROM assignments WHERE patent_id = ?", (patent_id,))

    now = datetime.now().isoformat()

    for assignment in assignments:
        cursor.execute("""
            INSERT INTO assignments
            (patent_id, reel_number, frame_number, reel_frame, page_count,
             received_date, recorded_date, mailed_date, conveyance_text,
             assignor_bag, assignee_bag, document_url, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (patent_id, assignment.get('reel_number'), assignment.get('frame_number'),
              assignment.get('reel_frame'), assignment.get('page_count'),
              assignment.get('received_date'), assignment.get('recorded_date'),
              assignment.get('mailed_date'), assignment.get('conveyance_text'),
              assignment.get('assignor_bag'), assignment.get('assignee_bag'),
              assignment.get('document_url'), now))

    conn.commit()
    conn.close()


def get_assignments(patent_id: int) -> list:
    """Get assignments for a patent."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM assignments WHERE patent_id = ? ORDER BY recorded_date DESC
    """, (patent_id,))

    assignments = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return assignments
