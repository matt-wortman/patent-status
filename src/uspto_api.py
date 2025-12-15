"""
USPTO Open Data Portal API client.
Handles all communication with the USPTO API.
"""

import requests
from typing import Optional, Dict, List, Any
from datetime import datetime

from .credentials import get_api_key


USPTO_API_BASE = "https://api.uspto.gov/api/v1/patent/applications"


class USPTOApiError(Exception):
    """Custom exception for USPTO API errors."""
    pass


def _get_headers() -> Dict[str, str]:
    """Get headers with API key for USPTO requests."""
    api_key = get_api_key()
    if not api_key:
        raise USPTOApiError("No API key configured. Please add your USPTO API key in Settings.")

    return {
        "X-API-Key": api_key,
        "Accept": "application/json"
    }


def normalize_app_number(app_number: str) -> str:
    """Normalize application number by removing slashes, spaces, commas."""
    return app_number.replace("/", "").replace(" ", "").replace(",", "")


def format_app_number(app_number: str) -> str:
    """Format application number for display (e.g., 17/940,142)."""
    app_num = normalize_app_number(app_number)
    if len(app_num) >= 8:
        return f"{app_num[:2]}/{app_num[2:5]},{app_num[5:]}"
    return app_num


def fetch_application(application_number: str) -> Dict[str, Any]:
    """
    Fetch full application data from USPTO API.

    Args:
        application_number: The patent application number (with or without formatting)

    Returns:
        Dictionary containing application metadata and events

    Raises:
        USPTOApiError: If the API request fails
    """
    app_num = normalize_app_number(application_number)

    try:
        response = requests.get(
            f"{USPTO_API_BASE}/{app_num}",
            headers=_get_headers(),
            timeout=30
        )

        if response.status_code == 401:
            raise USPTOApiError("Invalid API key. Please check your USPTO API key in Settings.")
        elif response.status_code == 404:
            raise USPTOApiError(f"Application {format_app_number(app_num)} not found.")
        elif response.status_code != 200:
            raise USPTOApiError(f"USPTO API error: {response.status_code} - {response.text}")

        data = response.json()

        if data.get('count', 0) == 0:
            raise USPTOApiError(f"Application {format_app_number(app_num)} not found.")

        return data

    except requests.exceptions.Timeout:
        raise USPTOApiError("USPTO API request timed out. Please try again.")
    except requests.exceptions.ConnectionError:
        raise USPTOApiError("Could not connect to USPTO API. Please check your internet connection.")
    except requests.exceptions.RequestException as e:
        raise USPTOApiError(f"Request error: {str(e)}")


def parse_application_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse raw USPTO API response into a cleaner format.

    Returns:
        Dictionary with:
        - metadata: Application metadata (title, status, etc.)
        - events: List of events/transactions
    """
    if not raw_data.get('patentFileWrapperDataBag'):
        return None

    wrapper = raw_data['patentFileWrapperDataBag'][0]
    metadata = wrapper.get('applicationMetaData', {})

    # Extract inventor names
    inventors = []
    for inv in metadata.get('inventorBag', []):
        name = inv.get('inventorNameText', '')
        if name:
            inventors.append(name)

    # Extract applicant
    applicants = []
    for app in metadata.get('applicantBag', []):
        name = app.get('applicantNameText', '')
        if name:
            applicants.append(name)

    # Parse events
    events = []
    for event in wrapper.get('eventDataBag', []):
        events.append({
            'event_code': event.get('eventCode', ''),
            'event_description': event.get('eventDescriptionText', ''),
            'event_date': event.get('eventDate', '')
        })

    return {
        'metadata': {
            'application_number': wrapper.get('applicationNumberText', ''),
            'title': metadata.get('inventionTitle', ''),
            'applicant': applicants[0] if applicants else '',
            'inventor': ', '.join(inventors),
            'filing_date': metadata.get('filingDate', ''),
            'current_status': metadata.get('applicationStatusDescriptionText', ''),
            'status_date': metadata.get('applicationStatusDate', ''),
            'examiner': metadata.get('examinerNameText', ''),
            'art_unit': metadata.get('groupArtUnitNumber', ''),
            'customer_number': str(metadata.get('customerNumber', ''))
        },
        'events': events
    }


def validate_api_key(api_key: str) -> bool:
    """
    Validate an API key by making a test request.
    Returns True if valid, False otherwise.
    """
    try:
        response = requests.get(
            f"{USPTO_API_BASE}/17940142",  # Test with a known application
            headers={
                "X-API-Key": api_key,
                "Accept": "application/json"
            },
            timeout=15
        )
        return response.status_code == 200
    except:
        return False


def get_patent_center_url(application_number: str) -> str:
    """Get the Patent Center URL for an application."""
    app_num = normalize_app_number(application_number)
    return f"https://patentcenter.uspto.gov/applications/{app_num}"


def get_public_pair_url(application_number: str) -> str:
    """Get the Public PAIR URL for an application."""
    app_num = normalize_app_number(application_number)
    return f"https://portal.uspto.gov/pair/PublicPair?appNumber={app_num}"


# Event codes that indicate significant status changes
SIGNIFICANT_EVENT_CODES = {
    'CTNF': 'Non-Final Rejection',
    'CTFR': 'Final Rejection',
    'NOA': 'Notice of Allowance',
    'IEXX': 'Initial Examination',
    'DOCK': 'Docketed to Examiner',
    'ABN': 'Abandonment',
    'ISSUE': 'Patent Issued',
    'RCE': 'RCE Filed',
    'BRCE': 'RCE - Begin',
    'IDSC': 'IDS Considered',
    'WIDS': 'IDS Filed',
    'RESP': 'Response Filed',
    'A...': 'Amendment/Response',
}


def is_significant_event(event_code: str) -> bool:
    """Check if an event code represents a significant status change."""
    # Check exact match
    if event_code in SIGNIFICANT_EVENT_CODES:
        return True

    # Check for partial matches (some codes have variants)
    significant_prefixes = ['CT', 'NOA', 'ABN', 'ISSUE', 'RCE', 'MAIL']
    for prefix in significant_prefixes:
        if event_code.startswith(prefix):
            return True

    return False
