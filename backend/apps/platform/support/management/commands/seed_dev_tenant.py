"""Dev-only standalone management command: seed_dev_tenant (I.6.2).

Creates a fully-functional sample tenant so an engineer can sign in and
walk through ``/platform/`` with real organization data.

This command MUST NOT run in non-dev environments. It refuses to execute
unless ``DJANGO_DEBUG`` is true OR the active settings module is
``config.settings.dev`` / ``config.settings.test``.

After M1 D2: the creation path delegates to
:func:`apps.platform.organizations.services.create_organization` and
:func:`apps.platform.organizations.services.assign_owner_membership`.
The ``--reset`` path retains direct ORM writes because it is a
destructive dev-only tool with no service-layer analogue.

Exempt from the service-layer discipline AST check (A.4.5) because
management commands are explicitly listed in the exemption set, same as
admin/migrations/tests.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.platform.organizations.models import (
    Membership,
    Organization,
)
from apps.platform.organizations.services import (
    assign_owner_membership,
    create_organization,
)
from apps.platform.rbac.models import (
    Capability,
    MembershipRole,
    Role,
)

DEV_SAFE_SETTINGS_MODULES = {
    "config.settings.dev",
    "config.settings.test",
}


class Command(BaseCommand):
    """Seed a demo tenant for local development."""

    help = (
        "Create a demo Organization, admin User, default per-tenant Roles, "
        "and Membership with the Owner role assigned. Idempotent on slug. "
        "Use --reset to drop and recreate."
    )

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--slug",
            default="demo",
            help="Organization slug. Default: 'demo'.",
        )
        parser.add_argument(
            "--name",
            default="Demo Organization",
            help="Organization display name.",
        )
        parser.add_argument(
            "--admin-email",
            default="admin@mph.local",
            help="Email for the bootstrap admin user.",
        )
        parser.add_argument(
            "--admin-password",
            default="mph-demo-password!",
            help=(
                "Password for the bootstrap admin user. The default "
                "satisfies the v1 password validators."
            ),
        )
        parser.add_argument(
            "--contact-email",
            default="contact@demo.mph.local",
            help="Primary contact email on the Organization.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Delete the demo tenant first, then recreate. Removes "
                "the org, its memberships, its per-tenant roles, and "
                "the admin user if the admin has no other memberships."
            ),
        )

    # ---------------------------------------------------------------- guard

    def _refuse_in_production(self) -> None:
        active = getattr(settings, "SETTINGS_MODULE", "") or ""
        debug = bool(getattr(settings, "DEBUG", False))
        if active in DEV_SAFE_SETTINGS_MODULES:
            return
        if debug:
            return
        raise CommandError(
            "seed_dev_tenant refuses to run outside dev/test settings. "
            f"DJANGO_SETTINGS_MODULE={active!r}, DEBUG={debug}. "
            "Use the M1 services.create_organization path for non-dev "
            "tenant provisioning."
        )

    # ---------------------------------------------------------------- handle

    def handle(self, *args: Any, **options: Any) -> None:
        self._refuse_in_production()

        slug: str = options["slug"]
        name: str = options["name"]
        admin_email: str = options["admin_email"].lower()
        admin_password: str = options["admin_password"]
        contact_email: str = options["contact_email"]
        reset: bool = options["reset"]

        # Pre-flight: seed_v1 must have run.
        template_count = Role.objects.filter(
            organization__isnull=True, is_default=True
        ).count()
        if template_count != 11:
            raise CommandError(
                f"Expected 11 default role templates from seed_v1; found "
                f"{template_count}. Run `python manage.py migrate` first."
            )

        if reset:
            self._reset_tenant(slug=slug, admin_email=admin_email)

        # Idempotency check: if the org already exists, treat the run as
        # a no-op for the create path. The service itself is strict
        # (raises on existing slug) per A.4.4 — this idempotency is the
        # dev convenience layer that wraps it.
        existing_org = Organization.objects.filter(slug=slug).first()
        existing_user = self._existing_admin_user(admin_email)

        # System User is the actor for all bootstrap operations. C.2
        # says system-triggered transitions attribute the actor to the
        # System User.
        system_actor_id = self._system_user_id()

        if existing_org is None:
            org = create_organization(
                slug=slug,
                name=name,
                primary_contact_email=contact_email,
                primary_contact_name="Demo Owner",
                timezone="America/Chicago",
                base_currency_code="USD",
                actor_id=system_actor_id,
            )
            org_created = True
        else:
            org = existing_org
            org_created = False

        user, user_created = self._upsert_admin_user(
            email=admin_email, password=admin_password
        )

        existing_membership = Membership.objects.filter(
            user=user, organization=org
        ).first()

        if existing_membership is None:
            membership = assign_owner_membership(
                organization_id=org.id,
                user_id=user.id,
                actor_id=system_actor_id,
                first_name="Demo",
                last_name="Owner",
            )
            membership_created = True
            assignment_created = True
        else:
            membership = existing_membership
            membership_created = False
            # Was the Owner role already assigned?
            owner_role = Role.objects.get(organization=org, code="owner")
            assignment_created = not MembershipRole.objects.filter(
                membership=membership, role=owner_role
            ).exists()
            if assignment_created:
                # Edge case: membership exists but Owner not yet
                # assigned. Wrap in a transaction so the create is
                # consistent. (Audit emission for the late assignment
                # would normally come from assign_owner_membership,
                # but the membership already exists so we'd violate
                # that service's MembershipAlreadyExistsError guard;
                # an inline create here is the right level of nuance
                # for this dev-only path.)
                with transaction.atomic():
                    MembershipRole.objects.create(
                        membership=membership,
                        role=owner_role,
                        assigned_by=user,
                    )

        self._print_summary(
            org=org,
            org_created=org_created,
            user=user,
            user_created=user_created,
            admin_password=admin_password,
            membership_created=membership_created,
            assignment_created=assignment_created,
        )

    # ---------------------------------------------------------------- reset

    def _reset_tenant(self, *, slug: str, admin_email: str) -> None:
        """Delete the demo tenant and its associated rows.

        Order matters because of FK protection:
          MembershipRole → Membership → Role (per-tenant) → Organization.
        Capability rows are platform-level and are never touched here.
        """
        try:
            org = Organization.objects.get(slug=slug)
        except Organization.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(
                    f"--reset: no Organization with slug={slug!r}; nothing to do."
                )
            )
            org = None

        if org is not None:
            with transaction.atomic():
                MembershipRole.objects.filter(membership__organization=org).delete()
                Membership.objects.filter(organization=org).delete()
                Role.objects.filter(organization=org).delete()
                org.delete()
            self.stdout.write(
                self.style.WARNING(f"--reset: removed Organization slug={slug!r}.")
            )

        User = get_user_model()
        try:
            user = User.objects.get(email=admin_email)
        except User.DoesNotExist:
            return
        if user.is_system:
            return
        if Membership.objects.filter(user=user).exists():
            self.stdout.write(
                self.style.WARNING(
                    f"--reset: admin user {admin_email!r} retained "
                    "(still has memberships in other orgs)."
                )
            )
            return
        user.delete()
        self.stdout.write(
            self.style.WARNING(f"--reset: removed admin user {admin_email!r}.")
        )

    # ---------------------------------------------------------------- helpers

    def _system_user_id(self) -> Any:
        User = get_user_model()
        try:
            return User.objects.get(is_system=True).id
        except User.DoesNotExist as exc:
            raise CommandError(
                "System User missing. Run `python manage.py migrate` "
                "(which applies seed_v1) before invoking seed_dev_tenant."
            ) from exc

    def _existing_admin_user(self, email: str) -> Any | None:
        User = get_user_model()
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            return None

    def _upsert_admin_user(self, *, email: str, password: str) -> tuple[Any, bool]:
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
            return user, False
        except User.DoesNotExist:
            pass

        user = User(email=email, is_active=True, is_staff=False, is_superuser=False)
        user.set_password(password)
        user.save()
        return user, True

    # ---------------------------------------------------------------- summary

    def _print_summary(
        self,
        *,
        org: Organization,
        org_created: bool,
        user: Any,
        user_created: bool,
        admin_password: str,
        membership_created: bool,
        assignment_created: bool,
    ) -> None:
        cap_count = Capability.objects.count()
        tenant_role_count = Role.objects.filter(organization=org).count()
        members = Membership.objects.filter(organization=org).count()

        def fmt(label: str, created: bool) -> str:
            tag = (
                self.style.SUCCESS("created")
                if created
                else self.style.NOTICE("exists")
            )
            return f"{label:<22} {tag}"

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("seed_dev_tenant: summary"))
        self.stdout.write("-" * 60)
        self.stdout.write(fmt(f"Organization {org.slug!r}", org_created))
        self.stdout.write(fmt(f"User {user.email!r}", user_created))
        self.stdout.write(fmt("Membership", membership_created))
        self.stdout.write(fmt("Owner role assignment", assignment_created))
        self.stdout.write(f"Per-tenant roles      {tenant_role_count} on disk")
        self.stdout.write(f"Total capabilities    {cap_count}")
        self.stdout.write(f"Total memberships     {members}")
        self.stdout.write("-" * 60)
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Sign in:"))
        self.stdout.write("  URL:      http://mph.local/login/")
        self.stdout.write(f"  Email:    {user.email}")
        self.stdout.write(f"  Password: {admin_password}")
        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "Note: M0 ships the login page as a scaffold only. The full "
                "auth flow (allauth + MFA + impersonation) lands in M1."
            )
        )
