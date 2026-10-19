"""
Public profile handles (the `<handle>` in /u/<handle>).

Kept free of database imports at module level so the rules are unit-testable.
Handles are always stored lower-case; uniqueness is enforced by the column's
unique constraint, `is_available` just gives a friendly answer before saving.
"""

import re

from django.utils.text import slugify

HANDLE_MIN_LENGTH = 3
HANDLE_MAX_LENGTH = 30
HANDLE_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")

# Words that would collide with routes on the public site or look official.
RESERVED_HANDLES = frozenset(
    {
        "admin", "administrator", "api", "about", "help", "support", "login", "logout", "signin", "signup",
        "register", "me", "u", "new", "settings", "profile", "profiles", "members", "member", "team", "startups",
        "startup", "wings", "wing", "leaderboard", "leaderboards", "events", "ideas", "problems", "vjos", "plane",
        "vjstartup", "vjstartups", "root", "null", "undefined", "static", "assets", "public", "www",
    }
)


class HandleError(ValueError):
    """The handle is not allowed; the message is safe to show to the user."""


def normalize_handle(raw):
    return (raw or "").strip().lower()


def validate_handle(raw):
    """Return the normalized handle, or raise HandleError saying why it cannot be used."""
    handle = normalize_handle(raw)
    if len(handle) < HANDLE_MIN_LENGTH:
        raise HandleError(f"Handle must be at least {HANDLE_MIN_LENGTH} characters.")
    if len(handle) > HANDLE_MAX_LENGTH:
        raise HandleError(f"Handle must be at most {HANDLE_MAX_LENGTH} characters.")
    if not HANDLE_PATTERN.match(handle):
        raise HandleError(
            "Use only lower-case letters, numbers and single hyphens, starting and ending with a letter or number."
        )
    if "--" in handle:
        raise HandleError("Handle cannot contain two hyphens in a row.")
    if handle in RESERVED_HANDLES:
        raise HandleError("That handle is reserved.")
    return handle


def is_available(handle, taken, exclude_profile_id=None):
    """`taken` is a callable (handle, exclude_profile_id) -> bool, so tests need no database."""
    return not taken(handle, exclude_profile_id)


def candidate_handles(first_name, last_name, email):
    """Yield sensible handle bases for a person, best first."""
    name = slugify(f"{first_name or ''} {last_name or ''}".strip())
    local = slugify((email or "").split("@")[0])
    # "member" would be a natural last resort, but it is a reserved handle, so use "user".
    for base in (name, local, "user"):
        base = base.strip("-")[:HANDLE_MAX_LENGTH].strip("-")
        if base:
            yield base


def suggest_handle(first_name, last_name, email, taken):
    """Pick the first free, valid handle for a person, adding a number if the name is taken."""
    for base in candidate_handles(first_name, last_name, email):
        for suffix in [""] + [str(n) for n in range(2, 100)]:
            candidate = f"{base[: HANDLE_MAX_LENGTH - len(suffix)].rstrip('-')}{suffix}"
            try:
                handle = validate_handle(candidate)
            except HandleError:
                continue
            if is_available(handle, taken):
                return handle
    raise HandleError("Could not find a free handle; please choose one yourself.")
