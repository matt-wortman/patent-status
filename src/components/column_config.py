"""Column definitions for tksheet-based tables."""

from __future__ import annotations

from typing import Any

PATENT_COLUMNS: list[dict[str, Any]] = [
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
    {
        "key": "publication_number",
        "header": "Publication #",
        "width": 140,
        "default_visible": False,
        "category": "Identifiers",
    },
    {"key": "docket_number", "header": "Docket #", "width": 150, "default_visible": False, "category": "Identifiers"},
    {"key": "customer_number", "header": "Customer #", "width": 90, "default_visible": False, "category": "Identifiers"},
    {
        "key": "confirmation_number",
        "header": "Confirm #",
        "width": 90,
        "default_visible": False,
        "category": "Identifiers",
    },
    # Classification (hidden by default)
    {"key": "art_unit", "header": "Art Unit", "width": 80, "default_visible": False, "category": "Classification"},
    {"key": "entity_status", "header": "Entity", "width": 80, "default_visible": False, "category": "Classification"},
    {
        "key": "application_type_label",
        "header": "App Type",
        "width": 90,
        "default_visible": False,
        "category": "Classification",
    },
    {"key": "first_inventor_to_file", "header": "FITF", "width": 60, "default_visible": False, "category": "Classification"},
    # People (hidden by default)
    {"key": "inventor", "header": "Inventor", "width": 150, "default_visible": False, "category": "People"},
    # Patent Term (hidden by default)
    {"key": "pta_total_days", "header": "PTA Days", "width": 80, "default_visible": False, "category": "Patent Term"},
]


def get_default_visible(columns: list[dict[str, Any]]) -> list[str]:
    return [c["key"] for c in columns if c.get("default_visible")]


def get_categories(columns: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for col in columns:
        category = col.get("category") or "Other"
        grouped.setdefault(category, []).append(col)
    return grouped

