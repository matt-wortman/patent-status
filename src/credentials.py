"""Secure credential storage using Windows Credential Manager.

This module provides secure storage and retrieval of the USPTO API key using
Windows Credential Manager via the keyring library. Credentials are stored
securely in the Windows vault and are not saved in plain text files.

The module uses the service name "PatentStatusTracker" to namespace credentials
in the Windows Credential Manager.
"""

import keyring
import logging
from typing import Optional

SERVICE_NAME = "PatentStatusTracker"
USPTO_KEY_NAME = "uspto_api_key"

logger = logging.getLogger(__name__)


def store_api_key(api_key: str) -> bool:
    """Store the USPTO API key securely in Windows Credential Manager.

    Args:
        api_key: The USPTO API key string to store.

    Returns:
        bool: True on success, False on failure.
    """
    try:
        keyring.set_password(SERVICE_NAME, USPTO_KEY_NAME, api_key)
        return True
    except Exception:
        logger.exception("Error storing API key")
        return False


def get_api_key() -> Optional[str]:
    """Retrieve the USPTO API key from Windows Credential Manager.

    Returns:
        str: The API key if found.
        None: If no API key is stored.
    """
    try:
        return keyring.get_password(SERVICE_NAME, USPTO_KEY_NAME)
    except Exception:
        logger.exception("Error retrieving API key")
        return None


def delete_api_key() -> bool:
    """Delete the USPTO API key from Windows Credential Manager.

    Returns:
        bool: True on success (or if key doesn't exist), False on other failures.
    """
    try:
        keyring.delete_password(SERVICE_NAME, USPTO_KEY_NAME)
        return True
    except keyring.errors.PasswordDeleteError:
        # Key doesn't exist
        return True
    except Exception:
        logger.exception("Error deleting API key")
        return False


def has_api_key() -> bool:
    """Check if an API key is stored.

    Returns:
        bool: True if API key exists, False otherwise.
    """
    return get_api_key() is not None
