"""Profile completion and safe onboarding destinations shared by auth and pages."""
import re
from urllib.parse import urlsplit

from .db import get_db

MIN_AGE = 18
MAX_AGE = 120
HOUSING_LABELS = {
    'needs_housing': 'I need housing',
    'has_housing': 'I already have housing',
}


def profile_for_user(user_id):
    return get_db().execute('SELECT * FROM profiles WHERE user_id = ?', (user_id,)).fetchone()


def is_complete(profile):
    if profile is None:
        return False
    return (isinstance(profile['name'], str) and 0 < len(profile['name'].strip()) <= 60
            and isinstance(profile['age'], int) and not isinstance(profile['age'], bool)
            and MIN_AGE <= profile['age'] <= MAX_AGE
            and isinstance(profile['preferred_location'], str)
            and 0 < len(profile['preferred_location'].strip()) <= 100
            and profile['housing_status'] in HOUSING_LABELS)


def safe_destination(value):
    if not isinstance(value, str) or len(value) > 2048 or '\\' in value or any(ord(c) < 32 for c in value):
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if parsed.scheme or parsed.netloc or parsed.fragment or not value.startswith('/'):
        return None
    if parsed.query and parsed.path != '/find-roommates':
        return None
    if parsed.path in {'/', '/profile', '/profile/edit', '/preferences', '/find-roommates', '/my-matches'} or re.fullmatch(r'/roommate/[0-9]+', parsed.path):
        return value
    # Never return to login, register, setup, a mutation API, or an external URL.
    return None
