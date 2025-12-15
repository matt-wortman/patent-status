"""
USPTO Open Data Portal API client.
Handles all communication with the USPTO API.
"""

import json
import requests
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

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
    return str(app_number).replace("/", "").replace(" ", "").replace(",", "")


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


def parse_application_data(raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse raw USPTO API response into a cleaner format.

    Returns:
        Dictionary with:
        - metadata: Application metadata (all available fields)
        - events: List of events/transactions
    """
    bag = raw_data.get('patentFileWrapperDataBag') or []
    if not isinstance(bag, list) or not bag:
        return None

    wrapper = bag[0]
    metadata = wrapper.get('applicationMetaData', {})

    # Extract inventor names (for display)
    inventors = []
    for inv in metadata.get('inventorBag', []):
        name = inv.get('inventorNameText', '')
        if name:
            inventors.append(name)

    # Extract applicant (for display)
    applicants = []
    for app in metadata.get('applicantBag', []):
        name = app.get('applicantNameText', '')
        if name:
            applicants.append(name)

    # Entity status data
    entity_data = metadata.get('entityStatusData', {})

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
            # Original fields
            'application_number': wrapper.get('applicationNumberText', ''),
            'title': metadata.get('inventionTitle', ''),
            'applicant': applicants[0] if applicants else '',
            'inventor': ', '.join(inventors),
            'filing_date': metadata.get('filingDate', ''),
            'current_status': metadata.get('applicationStatusDescriptionText', ''),
            'status_date': metadata.get('applicationStatusDate', ''),
            'examiner': metadata.get('examinerNameText', ''),
            'art_unit': metadata.get('groupArtUnitNumber', ''),
            'customer_number': str(metadata.get('customerNumber', '')),

            # Grant & Publication
            'patent_number': metadata.get('patentNumber', ''),
            'grant_date': metadata.get('grantDate', ''),
            'publication_number': metadata.get('earliestPublicationNumber', ''),
            'publication_date': metadata.get('earliestPublicationDate', ''),
            'publication_date_bag': json.dumps(metadata.get('publicationDateBag', [])),
            'publication_sequence_number_bag': json.dumps(metadata.get('publicationSequenceNumberBag', [])),
            'publication_category_bag': json.dumps(metadata.get('publicationCategoryBag', [])),

            # PCT / International
            'pct_publication_number': metadata.get('pctPublicationNumber', ''),
            'pct_publication_date': metadata.get('pctPublicationDate', ''),
            'international_registration_number': metadata.get('internationalRegistrationNumber', ''),
            'international_registration_publication_date': metadata.get('internationalRegistrationPublicationDate', ''),
            'national_stage_indicator': 1 if metadata.get('nationalStageIndicator') else 0,

            # Application Type & Classification
            'application_type_code': metadata.get('applicationTypeCode', ''),
            'application_type_label': metadata.get('applicationTypeLabelName', ''),
            'application_type_category': metadata.get('applicationTypeCategory', ''),
            'uspc_class': metadata.get('class', ''),
            'uspc_subclass': metadata.get('subclass', ''),
            'uspc_symbol': metadata.get('uspcSymbolText', ''),
            'cpc_classification_bag': json.dumps(metadata.get('cpcClassificationBag', [])),

            # Filing & Docket
            'docket_number': metadata.get('docketNumber', ''),
            'confirmation_number': str(metadata.get('applicationConfirmationNumber', '')),
            'effective_filing_date': metadata.get('effectiveFilingDate', ''),
            'first_inventor_to_file': metadata.get('firstInventorToFileIndicator', ''),

            # Entity Status
            'entity_status': entity_data.get('businessEntityStatusCategory', ''),
            'small_entity_indicator': 1 if entity_data.get('smallEntityStatusIndicator') else 0,

            # Status code
            'status_code': metadata.get('applicationStatusCode'),

            # Raw JSON storage for complex/nested data
            'applicant_bag': json.dumps(metadata.get('applicantBag', [])),
            'inventor_bag': json.dumps(metadata.get('inventorBag', [])),
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
    except requests.exceptions.RequestException:
        return False


def get_patent_center_url(application_number: str) -> str:
    """Get the Patent Center URL for an application."""
    app_num = normalize_app_number(application_number)
    return f"https://patentcenter.uspto.gov/applications/{app_num}"


def get_patent_center_documents_url(application_number: str) -> str:
    """Get a Patent Center documents URL for an application (often more reliable than the landing page)."""
    app_num = normalize_app_number(application_number)
    return f"https://patentcenter.uspto.gov/applications/{app_num}/ifw/docs"


def get_public_pair_url(application_number: str) -> str:
    """Get the Public PAIR URL for an application."""
    app_num = normalize_app_number(application_number)
    return f"https://portal.uspto.gov/pair/PublicPair?appNumber={app_num}"


# ---- Patent Term Adjustment (PTA) Endpoint ----

def fetch_adjustment(application_number: str) -> Dict[str, Any]:
    """Fetch patent term adjustment (PTA) data from USPTO API."""
    app_num = normalize_app_number(application_number)

    try:
        response = requests.get(
            f"{USPTO_API_BASE}/{app_num}/adjustment",
            headers=_get_headers(),
            timeout=30
        )

        if response.status_code == 404:
            return {}  # No PTA data available
        elif response.status_code != 200:
            raise USPTOApiError(f"Adjustment API error: {response.status_code}")

        return response.json()
    except requests.exceptions.RequestException as e:
        raise USPTOApiError(f"Adjustment request error: {str(e)}")


def parse_adjustment_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse PTA response into structured data."""
    if not raw_data:
        return {}

    return {
        'pta_total_days': raw_data.get('adjustmentTotalQuantity', 0),
        'pta_a_delay': raw_data.get('aDelayQuantity', 0),
        'pta_b_delay': raw_data.get('bDelayQuantity', 0),
        'pta_c_delay': raw_data.get('cDelayQuantity', 0),
        'pta_applicant_delay': raw_data.get('applicantDayDelayQuantity', 0),
        'pta_overlap_delay': raw_data.get('overlappingDayQuantity', 0),
        'pta_non_overlap_delay': raw_data.get('nonOverlappingDayQuantity', 0),
        'pta_history_bag': json.dumps(raw_data.get('patentTermAdjustmentHistoryDataBag', [])),
    }


def calculate_expiration_date(filing_date: str, pta_days: int) -> str:
    """Calculate patent expiration date (filing + 20 years + PTA)."""
    if not filing_date:
        return ''

    try:
        filing = datetime.strptime(filing_date, '%Y-%m-%d')
        # Add 20 years (handle leap day safely)
        try:
            expiration = filing.replace(year=filing.year + 20)
        except ValueError:
            if filing.month == 2 and filing.day == 29:
                expiration = filing.replace(year=filing.year + 20, day=28)
            else:
                raise
        # Add PTA days
        expiration = expiration + timedelta(days=int(pta_days or 0))
        return expiration.strftime('%Y-%m-%d')
    except ValueError:
        return ''


# ---- Continuity Endpoint ----

def fetch_continuity(application_number: str) -> Dict[str, Any]:
    """Fetch parent/child continuity data from USPTO API."""
    app_num = normalize_app_number(application_number)

    try:
        response = requests.get(
            f"{USPTO_API_BASE}/{app_num}/continuity",
            headers=_get_headers(),
            timeout=30
        )

        if response.status_code == 404:
            return {'parentContinuityBag': [], 'childContinuityBag': []}
        elif response.status_code != 200:
            raise USPTOApiError(f"Continuity API error: {response.status_code}")

        return response.json()
    except requests.exceptions.RequestException as e:
        raise USPTOApiError(f"Continuity request error: {str(e)}")


def parse_continuity_data(raw_data: Dict[str, Any]) -> Dict[str, list]:
    """Parse continuity response into parent and child lists."""
    parents = []
    for parent in raw_data.get('parentContinuityBag', []):
        parents.append({
            'app_number': parent.get('parentApplicationNumberText', ''),
            'patent_number': parent.get('parentPatentNumber', ''),
            'filing_date': parent.get('parentApplicationFilingDate', ''),
            'status': parent.get('parentApplicationStatusDescriptionText', ''),
            'status_code': parent.get('parentApplicationStatusCode', 0),
            'continuity_type': parent.get('claimParentageTypeCode', ''),
            'continuity_description': parent.get('claimParentageTypeCodeDescriptionText', ''),
            'first_inventor_to_file': 1 if parent.get('firstInventorToFileIndicator') else 0,
        })

    children = []
    for child in raw_data.get('childContinuityBag', []):
        children.append({
            'app_number': child.get('childApplicationNumberText', ''),
            'patent_number': child.get('childPatentNumber', ''),
            'filing_date': child.get('childApplicationFilingDate', ''),
            'status': child.get('childApplicationStatusDescriptionText', ''),
            'status_code': child.get('childApplicationStatusCode', 0),
            'continuity_type': child.get('claimParentageTypeCode', ''),
            'continuity_description': child.get('claimParentageTypeCodeDescriptionText', ''),
            'first_inventor_to_file': 1 if child.get('firstInventorToFileIndicator') else 0,
        })

    return {'parents': parents, 'children': children}


# ---- Documents Endpoint ----

def fetch_documents(application_number: str) -> Dict[str, Any]:
    """Fetch file wrapper documents from USPTO API."""
    app_num = normalize_app_number(application_number)

    try:
        response = requests.get(
            f"{USPTO_API_BASE}/{app_num}/documents",
            headers=_get_headers(),
            timeout=30
        )

        if response.status_code == 404:
            return {'documentBag': []}
        elif response.status_code != 200:
            raise USPTOApiError(f"Documents API error: {response.status_code}")

        return response.json()
    except requests.exceptions.RequestException as e:
        raise USPTOApiError(f"Documents request error: {str(e)}")


def parse_documents_data(raw_data: Dict[str, Any]) -> list:
    """Parse documents response into list of document info."""
    documents = []
    for doc in raw_data.get('documentBag', []):
        # Store all download options as JSON
        download_options = doc.get('downloadOptionBag', [])

        # Calculate total page count
        page_count = 0
        for option in download_options:
            if option.get('pageTotalQuantity'):
                page_count = option.get('pageTotalQuantity')
                break

        # Parse official date (remove time component if present)
        official_date = doc.get('officialDate', '')
        if official_date and 'T' in official_date:
            official_date = official_date.split('T')[0]

        documents.append({
            'document_id': doc.get('documentIdentifier', ''),
            'document_code': doc.get('documentCode', ''),
            'description': doc.get('documentCodeDescriptionText', ''),
            'date': official_date,
            'direction': doc.get('documentDirectionCategory', ''),
            'download_options': json.dumps(download_options),
            'page_count': page_count,
        })

    return documents


# ---- Assignment Endpoint ----

def fetch_assignment(application_number: str) -> Dict[str, Any]:
    """Fetch assignment/ownership data from USPTO API."""
    app_num = normalize_app_number(application_number)

    try:
        response = requests.get(
            f"{USPTO_API_BASE}/{app_num}/assignment",
            headers=_get_headers(),
            timeout=30
        )

        if response.status_code == 404:
            return {'patentAssignmentBag': []}
        elif response.status_code != 200:
            raise USPTOApiError(f"Assignment API error: {response.status_code}")

        return response.json()
    except requests.exceptions.RequestException as e:
        raise USPTOApiError(f"Assignment request error: {str(e)}")


def parse_assignment_data(raw_data: Dict[str, Any]) -> list:
    """Parse assignment response into list of assignment records."""
    assignments = []
    for assignment in raw_data.get('patentAssignmentBag', []):
        assignments.append({
            'reel_number': assignment.get('reelNumber', ''),
            'frame_number': assignment.get('frameNumber', ''),
            'reel_frame': assignment.get('reelAndFrameNumber', ''),
            'page_count': assignment.get('pageTotalQuantity', 0),
            'received_date': assignment.get('assignmentReceivedDate', ''),
            'recorded_date': assignment.get('assignmentRecordedDate', ''),
            'mailed_date': assignment.get('assignmentMailedDate', ''),
            'conveyance_text': assignment.get('conveyanceText', ''),
            'assignor_bag': json.dumps(assignment.get('assignorBag', [])),
            'assignee_bag': json.dumps(assignment.get('assigneeBag', [])),
            'document_url': assignment.get('assignmentDocumentLocationURI', ''),
        })

    return assignments


# ---- Attorney Endpoint ----

def fetch_attorney(application_number: str) -> Dict[str, Any]:
    """Fetch attorney/agent data from USPTO API."""
    app_num = normalize_app_number(application_number)

    try:
        response = requests.get(
            f"{USPTO_API_BASE}/{app_num}/attorney",
            headers=_get_headers(),
            timeout=30
        )

        if response.status_code == 404:
            return {}
        elif response.status_code != 200:
            raise USPTOApiError(f"Attorney API error: {response.status_code}")

        return response.json()
    except requests.exceptions.RequestException as e:
        raise USPTOApiError(f"Attorney request error: {str(e)}")


def parse_attorney_data(raw_data: Dict[str, Any]) -> str:
    """Parse attorney response and return as JSON string for storage."""
    return json.dumps(raw_data) if raw_data else '[]'


# ---- Foreign Priority Endpoint ----

def fetch_foreign_priority(application_number: str) -> Dict[str, Any]:
    """Fetch foreign priority claims from USPTO API."""
    app_num = normalize_app_number(application_number)

    try:
        response = requests.get(
            f"{USPTO_API_BASE}/{app_num}/foreign-priority",
            headers=_get_headers(),
            timeout=30
        )

        if response.status_code == 404:
            return {'foreignPriorityBag': []}
        elif response.status_code != 200:
            raise USPTOApiError(f"Foreign priority API error: {response.status_code}")

        return response.json()
    except requests.exceptions.RequestException as e:
        raise USPTOApiError(f"Foreign priority request error: {str(e)}")


def parse_foreign_priority_data(raw_data: Dict[str, Any]) -> str:
    """Parse foreign priority response and return as JSON string for storage."""
    return json.dumps(raw_data.get('foreignPriorityBag', []))


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
