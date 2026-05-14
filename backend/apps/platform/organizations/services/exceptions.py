"""Exceptions raised by the organization services.

These are typed for the service-layer caller. Callers should NEVER
``except IntegrityError`` to detect a slug collision — that's an
implementation detail. They catch :exc:`OrganizationSlugInUseError`.
"""

from __future__ import annotations

from uuid import UUID


class OrganizationSlugInUseError(ValueError):
    """Raised when create_organization sees an existing slug.

    The slug uniqueness constraint is the only realistic source of
    IntegrityError on the Organization insert, so the service catches
    that case explicitly and re-raises with a typed exception so
    callers can branch cleanly without parsing exception strings.

    Attributes:
        slug: the slug that already exists.
    """

    def __init__(self, slug: str) -> None:
        super().__init__(f"Organization slug {slug!r} is already in use.")
        self.slug = slug


class OrganizationNotFoundError(LookupError):
    """Raised when a service lookup by organization_id returns nothing."""

    def __init__(self, organization_id: UUID) -> None:
        super().__init__(f"Organization {organization_id} not found.")
        self.organization_id = organization_id


class UserNotFoundError(LookupError):
    """Raised when a service lookup by user_id returns nothing."""

    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"User {user_id} not found.")
        self.user_id = user_id


class MembershipAlreadyExistsError(ValueError):
    """Raised when assign_owner_membership is called for a (user, org) pair
    that already has a Membership row.

    This is a service-layer protection: the M0 D2 partial unique index
    enforces "at most one Membership per (user, organization)" at the
    DB level. Catching the existence check in Python first lets callers
    branch on a typed exception instead of an IntegrityError.

    Attributes:
        user_id: the user that already has a membership.
        organization_id: the organization the user is already a member of.
    """

    def __init__(self, *, user_id: UUID, organization_id: UUID) -> None:
        super().__init__(
            f"User {user_id} already has a Membership in organization {organization_id}."
        )
        self.user_id = user_id
        self.organization_id = organization_id
