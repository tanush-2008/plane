"""
Deployment-specific settings for VJ Startups, read from the environment.

Nothing here may be a value that differs between environments (hostnames, the
college email domain, where backend 2 lives) - those belong in one place so a
change of domain is a settings change, not a code change.
"""

import os

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import APIException

# The public marketing site. "www" is the host that actually resolves today;
# set VJ_PUBLIC_SITE_URL to change it (e.g. once the bare domain has DNS).
DEFAULT_PUBLIC_SITE_URL = "https://www.vjstartup.com"

# The one Plane workspace every startup, wing and member lives in. Set VJ_WORKSPACE_SLUG to the
# slug of the workspace you already use; otherwise a second, empty workspace with the default
# slug is created the first time a startup is provisioned.
DEFAULT_WORKSPACE_SLUG = "vj-startups"
DEFAULT_WORKSPACE_NAME = "VJ Startups"

# Email domain(s) whose owners are auto-onboarded into the global workspace.
DEFAULT_INSTITUTIONAL_EMAIL_DOMAINS = "vnrvjiet.in"

# Only ever used in local development (DEBUG on), where backend 2 runs beside the API.
LOCAL_MICROSERVICE_URL = "http://localhost:6220"

# Wings whose master is made an Admin of the whole workspace (not just of the wing's own
# project). "*" means every wing. It was a hardcoded "vision" check inside the onboarding
# service, which left the other wing masters as plain members.
DEFAULT_WORKSPACE_ADMIN_WINGS = "*"

# Plane roles, as stored on workspace and project members.
ROLE_MEMBER = 15
ROLE_ADMIN = 20


class MicroserviceNotConfigured(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "VJ_MICROSERVICE_URL is not set on the API, so it cannot reach the ecosystem service."
    default_code = "microservice_not_configured"


def public_site_url():
    """Base URL of the public site, without a trailing slash."""
    return (os.environ.get("VJ_PUBLIC_SITE_URL") or DEFAULT_PUBLIC_SITE_URL).strip().rstrip("/")


def workspace_slug():
    """Slug of the global VJ Startups workspace (VJ_WORKSPACE_SLUG, default 'vj-startups')."""
    # Strip before falling back: a setting of just spaces must mean "not set", not an empty slug.
    return (os.environ.get("VJ_WORKSPACE_SLUG", "").strip() or DEFAULT_WORKSPACE_SLUG).lower()


def workspace_name():
    """Display name used only if the workspace has to be created (VJ_WORKSPACE_NAME)."""
    return os.environ.get("VJ_WORKSPACE_NAME", "").strip() or DEFAULT_WORKSPACE_NAME


def institutional_email_domains():
    """Lower-case email domains (no '@') from VJ_INSTITUTIONAL_EMAIL_DOMAINS, comma separated."""
    raw = os.environ.get("VJ_INSTITUTIONAL_EMAIL_DOMAINS") or DEFAULT_INSTITUTIONAL_EMAIL_DOMAINS
    return [d.strip().lstrip("@").lower() for d in raw.split(",") if d.strip()]


def workspace_admin_wing_slugs():
    """Lower-case wing slugs from VJ_WORKSPACE_ADMIN_WINGS (comma separated; default '*' = all)."""
    raw = os.environ.get("VJ_WORKSPACE_ADMIN_WINGS")
    if raw is None:
        raw = DEFAULT_WORKSPACE_ADMIN_WINGS
    return [s.strip().lower() for s in raw.split(",") if s.strip()]


def workspace_role_for_wing(project_role, wing_slug):
    """
    Workspace role for someone joining a wing with the given project role. A wing's
    master (project role Admin) becomes a workspace Admin if that wing is listed in
    VJ_WORKSPACE_ADMIN_WINGS ("*", the default, means every wing); everyone else is a plain
    workspace Member. Set the variable to an empty string to make no wing master a
    workspace Admin.
    """
    if project_role < ROLE_ADMIN:
        return ROLE_MEMBER
    slugs = workspace_admin_wing_slugs()
    if "*" in slugs or (wing_slug or "").strip().lower() in slugs:
        return ROLE_ADMIN
    return ROLE_MEMBER


def plan_workspace_membership(current_role, is_active, requested_role):
    """
    What granting `requested_role` in a workspace should do, given the person's current
    membership (current_role is None when they have none). Returns (action, resulting_role):

    - "add":        not a member yet -> becomes a member with the requested role
    - "reactivate": was a member but deactivated -> active again, never below what they had
    - "raise":      active with a lower role -> raised to the requested role
    - "keep":       active with the same or a higher role -> left exactly as it is

    Roles only ever go up here; lowering one is done by hand in Plane.
    """
    if current_role is None:
        return "add", requested_role
    if not is_active:
        return "reactivate", max(current_role, requested_role)
    if current_role < requested_role:
        return "raise", requested_role
    return "keep", current_role


def is_institutional_email(email):
    email = (email or "").strip().lower()
    return any(email.endswith("@" + domain) for domain in institutional_email_domains())


def microservice_base_url():
    """
    Base URL of backend 2 (the ecosystem service), or None when it is not
    configured. It never silently falls back to localhost in production: a
    missing setting used to make the API call itself and fail confusingly.
    """
    url = os.environ.get("VJ_MICROSERVICE_URL") or os.environ.get("NEXT_PUBLIC_MICROSERVICE_URL")
    if url:
        return url.strip().rstrip("/")
    return LOCAL_MICROSERVICE_URL if settings.DEBUG else None


def require_microservice_base_url():
    """Like microservice_base_url() but raises a clear 503 when it is not configured."""
    url = microservice_base_url()
    if url is None:
        raise MicroserviceNotConfigured()
    return url
