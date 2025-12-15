"""
Database module for Patent Status Tracker.
Uses SQLite stored in user's Documents folder.
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


def get_db_path() -> Path:
    """Get the database path in user's Documents folder."""
    documents = Path.home() / "Documents" / "PatentStatusTracker"
    documents.mkdir(parents=True, exist_ok=True)
    return documents / "patents.db"


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
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
            FOREIGN KEY (patent_id) REFERENCES patents(id),
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

    # Build update query dynamically
    fields = []
    values = []
    for key, value in kwargs.items():
        if key in ['title', 'applicant', 'inventor', 'filing_date', 'examiner',
                   'current_status', 'status_date', 'art_unit', 'customer_number', 'last_checked']:
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
