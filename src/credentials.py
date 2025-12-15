"""
Secure credential storage using Windows Credential Manager.
Uses the keyring library which interfaces with Windows Credential Manager.
"""

import keyring

SERVICE_NAME = "PatentStatusTracker"
USPTO_KEY_NAME = "uspto_api_key"


def store_api_key(api_key: str) -> bool:
    """
    Store the USPTO API key securely in Windows Credential Manager.
    Returns True on success, False on failure.
    """
    try:
        keyring.set_password(SERVICE_NAME, USPTO_KEY_NAME, api_key)
        return True
    except Exception as e:
        print(f"Error storing API key: {e}")
        return False


def get_api_key() -> str:
    """
    Retrieve the USPTO API key from Windows Credential Manager.
    Returns the API key or None if not found.
    """
    try:
        return keyring.get_password(SERVICE_NAME, USPTO_KEY_NAME)
    except Exception as e:
        print(f"Error retrieving API key: {e}")
        return None


def delete_api_key() -> bool:
    """
    Delete the USPTO API key from Windows Credential Manager.
    Returns True on success, False on failure.
    """
    try:
        keyring.delete_password(SERVICE_NAME, USPTO_KEY_NAME)
        return True
    except keyring.errors.PasswordDeleteError:
        # Key doesn't exist
        return True
    except Exception as e:
        print(f"Error deleting API key: {e}")
        return False


def has_api_key() -> bool:
    """Check if an API key is stored."""
    return get_api_key() is not None
