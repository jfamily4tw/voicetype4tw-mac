import logging

log = logging.getLogger("voicetype")

def check_accessibility() -> bool:
    """Windows: Accessibility is always granted."""
    return True

def check_microphone() -> bool:
    """Windows: Microphone permission is managed by system settings."""
    return True

def request_microphone_permission():
    """Windows: No-op (handled by system)."""
    pass

def ensure_all_permissions():
    """Windows: No-op (all permissions auto-granted)."""
    pass
