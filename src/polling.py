"""
Background polling service for checking USPTO updates.
"""

import threading
import time
from datetime import datetime
from typing import Callable, Optional

from . import database as db
from . import uspto_api


class PollingService:
    """
    Background service that polls USPTO API for updates.
    """

    def __init__(self, on_update: Optional[Callable] = None, on_error: Optional[Callable] = None):
        """
        Initialize the polling service.

        Args:
            on_update: Callback function called when updates are found (receives list of new events)
            on_error: Callback function called on errors (receives error message)
        """
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._interval_minutes = 60 * 24  # Default: daily
        self._on_update = on_update
        self._on_error = on_error
        self._last_poll: Optional[datetime] = None

    def start(self, interval_minutes: int = None):
        """Start the polling service."""
        if self._running:
            return

        if interval_minutes:
            self._interval_minutes = interval_minutes

        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the polling service."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def set_interval(self, minutes: int):
        """Set the polling interval in minutes."""
        self._interval_minutes = minutes

    def get_last_poll_time(self) -> Optional[datetime]:
        """Get the last poll time."""
        return self._last_poll

    def poll_now(self) -> dict:
        """
        Perform an immediate poll of all tracked patents.

        Returns:
            Dictionary with:
            - success: bool
            - new_events: list of new events found
            - errors: list of error messages
        """
        result = {
            'success': True,
            'new_events': [],
            'errors': [],
            'updated_patents': 0
        }

        patents = db.get_all_patents()

        for patent in patents:
            try:
                app_num = patent['application_number']
                patent_id = patent['id']

                # Fetch from USPTO
                raw_data = uspto_api.fetch_application(app_num)
                parsed = uspto_api.parse_application_data(raw_data)

                if not parsed:
                    continue

                # Update patent metadata
                db.update_patent(
                    app_num,
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

                # Add new events
                new_count = 0
                for event in parsed['events']:
                    is_new = db.add_event(
                        patent_id,
                        event['event_code'],
                        event['event_description'],
                        event['event_date']
                    )
                    if is_new:
                        new_count += 1
                        result['new_events'].append({
                            'application_number': app_num,
                            'title': parsed['metadata']['title'],
                            **event
                        })

                if new_count > 0:
                    result['updated_patents'] += 1

                # Small delay between requests to be nice to the API
                time.sleep(0.5)

            except uspto_api.USPTOApiError as e:
                result['errors'].append(f"{patent['application_number']}: {str(e)}")
            except Exception as e:
                result['errors'].append(f"{patent['application_number']}: Unexpected error - {str(e)}")

        self._last_poll = datetime.now()

        if result['errors']:
            result['success'] = len(result['errors']) < len(patents)  # Partial success

        return result

    def _poll_loop(self):
        """Background polling loop."""
        while self._running:
            try:
                result = self.poll_now()

                if result['new_events'] and self._on_update:
                    self._on_update(result['new_events'])

                if result['errors'] and self._on_error:
                    self._on_error(result['errors'])

            except Exception as e:
                if self._on_error:
                    self._on_error([f"Polling error: {str(e)}"])

            # Wait for next poll interval
            for _ in range(self._interval_minutes * 60):
                if not self._running:
                    break
                time.sleep(1)


def refresh_single_patent(application_number: str) -> dict:
    """
    Refresh a single patent's data.

    Returns:
        Dictionary with updated metadata and any new events
    """
    app_num = uspto_api.normalize_app_number(application_number)
    patent = db.get_patent_by_app_number(app_num)

    if not patent:
        raise ValueError(f"Patent {application_number} not found in database")

    raw_data = uspto_api.fetch_application(app_num)
    parsed = uspto_api.parse_application_data(raw_data)

    if not parsed:
        raise ValueError("Could not parse USPTO response")

    # Update patent metadata
    db.update_patent(
        app_num,
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

    # Add new events
    new_events = []
    for event in parsed['events']:
        is_new = db.add_event(
            patent['id'],
            event['event_code'],
            event['event_description'],
            event['event_date']
        )
        if is_new:
            new_events.append(event)

    return {
        'metadata': parsed['metadata'],
        'new_events': new_events,
        'total_events': len(parsed['events'])
    }
