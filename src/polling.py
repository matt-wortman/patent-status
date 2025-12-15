"""Background polling service for checking USPTO updates.

This module provides a background service that periodically polls the USPTO API
to check for updates to tracked patents. It fetches data from multiple USPTO
endpoints (application, adjustment, continuity, documents, assignments, attorney,
and foreign priority) and updates the local database.

The PollingService class runs in a background thread and can be configured with
custom polling intervals and callback functions for update notifications.
"""

import threading
import time
import json
import logging
from datetime import datetime
from typing import Any, Callable, Optional

from . import database as db
from . import uspto_api

logger = logging.getLogger(__name__)


def _update_patent_from_api(patent_id: int, app_num: str) -> dict[str, Any]:
    """Fetch all supported USPTO endpoints for a single patent and update the database.

    Fetches data from multiple USPTO API endpoints:
    - Application data (metadata and events)
    - Patent term adjustment (PTA)
    - Continuity (parent/child relationships)
    - Documents (file wrapper)
    - Assignments (ownership)
    - Attorney/agent information
    - Foreign priority claims

    Args:
        patent_id: Database ID of the patent to update.
        app_num: Normalized application number.

    Returns:
        dict: Dictionary with keys:
            - metadata: Application metadata dictionary
            - new_events: List of newly discovered events
            - total_events: Total number of events in USPTO record

    Raises:
        ValueError: If USPTO response cannot be parsed.
        USPTOApiError: If required API calls fail.
    """
    raw_data = uspto_api.fetch_application(app_num)
    parsed = uspto_api.parse_application_data(raw_data)
    if not parsed:
        raise ValueError("Could not parse USPTO response")

    metadata = parsed["metadata"]
    update_fields: dict[str, Any] = dict(metadata)
    # Avoid passing the function's positional parameter again via kwargs.
    update_fields.pop("application_number", None)
    update_fields["last_checked"] = datetime.now().isoformat()

    # PTA (optional)
    try:
        pta_raw = uspto_api.fetch_adjustment(app_num)
        pta = uspto_api.parse_adjustment_data(pta_raw)
        if pta:
            expiration = uspto_api.calculate_expiration_date(
                metadata.get("filing_date") or "",
                pta.get("pta_total_days", 0),
            )
            update_fields.update(pta)
            update_fields["expiration_date"] = expiration
    except uspto_api.USPTOApiError as exc:
        logger.debug("Optional PTA fetch failed for %s: %s", app_num, exc)
    except Exception:
        logger.exception("Optional PTA fetch crashed for %s", app_num)

    # Continuity (optional)
    try:
        cont_raw = uspto_api.fetch_continuity(app_num)
        continuity = uspto_api.parse_continuity_data(cont_raw)
        db.save_continuity(patent_id, continuity.get("parents", []), continuity.get("children", []))
    except uspto_api.USPTOApiError as exc:
        logger.debug("Optional continuity fetch failed for %s: %s", app_num, exc)
    except Exception:
        logger.exception("Optional continuity fetch crashed for %s", app_num)

    # Documents (optional)
    try:
        docs_raw = uspto_api.fetch_documents(app_num)
        documents = uspto_api.parse_documents_data(docs_raw)
        db.save_documents(patent_id, documents)
    except uspto_api.USPTOApiError as exc:
        logger.debug("Optional documents fetch failed for %s: %s", app_num, exc)
    except Exception:
        logger.exception("Optional documents fetch crashed for %s", app_num)

    # Assignments (optional)
    try:
        assign_raw = uspto_api.fetch_assignment(app_num)
        assignments = uspto_api.parse_assignment_data(assign_raw)
        db.save_assignments(patent_id, assignments)
        update_fields["assignment_bag"] = json.dumps(assignments)
    except uspto_api.USPTOApiError as exc:
        logger.debug("Optional assignments fetch failed for %s: %s", app_num, exc)
    except Exception:
        logger.exception("Optional assignments fetch crashed for %s", app_num)

    # Attorney (optional)
    try:
        attorney_raw = uspto_api.fetch_attorney(app_num)
        attorney_json = uspto_api.parse_attorney_data(attorney_raw)
        update_fields["attorney_bag"] = attorney_json
    except uspto_api.USPTOApiError as exc:
        logger.debug("Optional attorney fetch failed for %s: %s", app_num, exc)
    except Exception:
        logger.exception("Optional attorney fetch crashed for %s", app_num)

    # Foreign Priority (optional)
    try:
        priority_raw = uspto_api.fetch_foreign_priority(app_num)
        priority_json = uspto_api.parse_foreign_priority_data(priority_raw)
        update_fields["foreign_priority_bag"] = priority_json
    except uspto_api.USPTOApiError as exc:
        logger.debug("Optional foreign priority fetch failed for %s: %s", app_num, exc)
    except Exception:
        logger.exception("Optional foreign priority fetch crashed for %s", app_num)

    # Single consolidated update
    db.update_patent(app_num, **update_fields)

    # Add new events
    new_events: list[dict[str, Any]] = []
    for event in parsed["events"]:
        is_new = db.add_event(
            patent_id,
            event["event_code"],
            event["event_description"],
            event["event_date"],
        )
        if is_new:
            new_events.append(event)

    return {
        "metadata": metadata,
        "new_events": new_events,
        "total_events": len(parsed["events"]),
    }


class PollingService:
    """Background service that polls USPTO API for updates.

    Runs in a daemon thread and periodically checks all tracked patents for updates.
    Supports configurable polling intervals and callback functions for notifications.
    """

    def __init__(self, on_update: Optional[Callable] = None, on_error: Optional[Callable] = None):
        """Initialize the polling service.

        Args:
            on_update: Optional callback function called when updates are found.
                      Receives a list of new event dictionaries.
            on_error: Optional callback function called on errors.
                     Receives a list of error message strings.
        """
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._interval_minutes = 60 * 24  # Default: daily
        self._on_update = on_update
        self._on_error = on_error
        self._last_poll: Optional[datetime] = None

    def start(self, interval_minutes: int = None):
        """Start the polling service in a background thread.

        Args:
            interval_minutes: Optional polling interval in minutes. If not provided,
                            uses the previously set interval (default: 1440 = 24 hours).
        """
        if self._running:
            return

        if interval_minutes:
            self._interval_minutes = interval_minutes

        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the polling service and wait for the background thread to finish."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def set_interval(self, minutes: int):
        """Set the polling interval in minutes.

        Args:
            minutes: Polling interval in minutes.
        """
        self._interval_minutes = minutes

    def get_last_poll_time(self) -> Optional[datetime]:
        """Get the last poll time.

        Returns:
            datetime: Timestamp of last poll, or None if never polled.
        """
        return self._last_poll

    def poll_now(self) -> dict:
        """Perform an immediate poll of all tracked patents.

        Fetches updates for all patents in the database and saves any new events.
        Respects the poll_delay_seconds setting to avoid overwhelming the USPTO API.

        Returns:
            dict: Dictionary with keys:
                - success (bool): True if all patents updated successfully
                - new_events (list): List of new event dictionaries found
                - errors (list): List of error message strings
                - updated_patents (int): Number of patents with new events
        """
        result = {
            'success': True,
            'new_events': [],
            'errors': [],
            'updated_patents': 0
        }

        patents = db.get_all_patents()
        try:
            delay_seconds = float(db.get_setting("poll_delay_seconds", "1.0") or "1.0")
        except ValueError:
            delay_seconds = 1.0

        for patent in patents:
            try:
                app_num = patent['application_number']
                patent_id = patent['id']
                update = _update_patent_from_api(patent_id, app_num)
                metadata = update["metadata"]

                if update["new_events"]:
                    result['updated_patents'] += 1
                    for event in update["new_events"]:
                        result["new_events"].append(
                            {
                                "application_number": app_num,
                                "title": metadata.get("title"),
                                **event,
                            }
                        )

                # Increased delay due to additional API calls (6 extra endpoints per patent)
                time.sleep(delay_seconds)

            except uspto_api.USPTOApiError as e:
                result['errors'].append(f"{patent['application_number']}: {str(e)}")
            except Exception as e:
                result['errors'].append(f"{patent['application_number']}: Unexpected error - {str(e)}")

        self._last_poll = datetime.now()

        if result['errors']:
            result['success'] = len(result['errors']) < len(patents)  # Partial success

        return result

    def _poll_loop(self):
        """Background polling loop (private method).

        Continuously polls for updates at the configured interval until stopped.
        Calls the on_update and on_error callbacks as appropriate.
        """
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
    """Refresh a single patent's data from all USPTO endpoints.

    Fetches the latest data for one patent and updates the database. Useful for
    on-demand refreshes triggered by user actions.

    Args:
        application_number: Patent application number (formatted or normalized).

    Returns:
        dict: Dictionary with keys:
            - metadata: Application metadata dictionary
            - new_events: List of newly discovered events
            - total_events: Total number of events

    Raises:
        ValueError: If patent is not found in the database.
        USPTOApiError: If API calls fail.
    """
    app_num = uspto_api.normalize_app_number(application_number)
    patent = db.get_patent_by_app_number(app_num)

    if not patent:
        raise ValueError(f"Patent {application_number} not found in database")

    patent_id = patent['id']

    return _update_patent_from_api(patent_id, app_num)
