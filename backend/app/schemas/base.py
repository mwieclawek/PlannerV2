_SLUG_RE = r'^[a-z0-9][a-z0-9-]{1,62}$'
_EMAIL_RE = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'


def _validate_password_strength(v: str) -> str:
    """Shared password strength validation (min 8 chars, >= 1 uppercase, >= 1 digit)."""
    if len(v) < 8:
        raise ValueError('Password must be at least 8 characters')
    if not any(c.isupper() for c in v):
        raise ValueError('Password must contain at least one uppercase letter')
    if not any(c.isdigit() for c in v):
        raise ValueError('Password must contain at least one digit')
    return v
