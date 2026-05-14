"""Dev-only standalone management command: seed_dev_tenant (I.6.2).

Creates a fully-functional sample tenant so an engineer can sign in and
walk through ``/platform/`` with real organization data.

This command MUST NOT run in non-dev environments. It refuses to execute
unless ``DJANGO_DEBUG`` is true OR the active settings module is
``config.settings.dev``. The seed migration (``seed_v1``) is the only
seed code that runs in production.

The command is the v1 dev-tenant bootstrap. The production tenant
provisioning path (``apps.platform.organizations.services.create_organization``)
lands in M1 and is the authoritative path for non-dev environments.
This command performs the equivalent steps inline because no service
layer exists in M0.

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
    MembershipStatus,
    Organization,
    OrganizationStatus,
)
from apps.platform.rbac.models import (
    Capability,
    MembershipRole,
    Role,
    RoleCapability,
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

        with transaction.atomic():
            org, org_created = self._upsert_organization(
                slug=slug, name=name, contact_email=contact_email
            )
            user, user_created = self._upsert_admin_user(
                email=admin_email, password=admin_password
            )
            tenant_roles, roles_created = self._clone_role_templates(org=org)
            membership, membership_created = self._upsert_membership(
                user=user, organization=org
            )
            owner_role = tenant_roles["owner"]
            assignment, assignment_created = self._ensure_owner_assignment(
                membership=membership, owner_role=owner_role
            )

        self._print_summary(
            org=org,
            org_created=org_created,
            user=user,
            user_created=user_created,
            admin_password=admin_password,
            roles_created=roles_created,
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
                # 1) MembershipRole (M2M between Membership and Role)
                MembershipRole.objects.filter(membership__organization=org).delete()
                # 2) Memberships
                Membership.objects.filter(organization=org).delete()
                # 3) Per-tenant RoleCapability + Role (cascade via CASCADE on Role)
                Role.objects.filter(organization=org).delete()
                # 4) The Organization itself
                org.delete()
            self.stdout.write(
                self.style.WARNING(f"--reset: removed Organization slug={slug!r}.")
            )

        # If the admin user has no remaining memberships, drop the user too.
        User = get_user_model()
        try:
            user = User.objects.get(email=admin_email)
        except User.DoesNotExist:
            return
        if user.is_system:
            # Belt-and-suspenders: never delete the System User row.
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

    # ---------------------------------------------------------------- upserts

    def _upsert_organization(
        self, *, slug: str, name: str, contact_email: str
    ) -> tuple[Organization, bool]:
        org, created = Organization.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "status": OrganizationStatus.ACTIVE,
                "primary_contact_email": contact_email,
                "primary_contact_name": "Demo Owner",
                "timezone": "America/Chicago",
                "base_currency_code": "USD",
            },
        )
        return org, created

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

    def _clone_role_templates(
        self, *, org: Organization
    ) -> tuple[dict[str, Role], int]:
        """Clone the 11 default role templates as per-tenant Role rows.

        Each clone:
          - Has organization=org (so the row is tenant-scoped).
          - Has is_default=False, is_locked=False (templates are locked;
            tenant copies can be modified by Org Admin from M1 onward).
          - Has the same is_scoped_role flag as the template.
          - Has RoleCapability rows pointing at the same Capability
            objects as the template.

        Idempotent: if the tenant already has a role with the same code,
        we keep the existing row and don't touch its RoleCapability rows.
        Use --reset to force a clean rebuild.
        """
        created_count = 0
        result: dict[str, Role] = {}

        templates = Role.objects.filter(
            organization__isnull=True, is_default=True
        ).prefetch_related("role_capabilities__capability")

        for template in templates:
            tenant_role, created = Role.objects.get_or_create(
                organization=org,
                code=template.code,
                defaults={
                    "name": template.name,
                    "description": template.description,
                    "is_default": False,
                    "is_scoped_role": template.is_scoped_role,
                    "is_locked": False,
                },
            )
            result[template.code] = tenant_role
            if not created:
                continue
            created_count += 1
            # Replicate the capability set.
            cap_links = [
                RoleCapability(role=tenant_role, capability=rc.capability)
                for rc in template.role_capabilities.all()
            ]
            RoleCapability.objects.bulk_create(cap_links)

        return result, created_count

    def _upsert_membership(
        self, *, user: Any, organization: Organization
    ) -> tuple[Membership, bool]:
        membership, created = Membership.objects.get_or_create(
            user=user,
            organization=organization,
            defaults={
                "status": MembershipStatus.ACTIVE,
                "first_name": "Demo",
                "last_name": "Owner",
                "is_default_for_user": True,
            },
        )
        return membership, created

    def _ensure_owner_assignment(
        self, *, membership: Membership, owner_role: Role
    ) -> tuple[MembershipRole, bool]:
        assignment, created = MembershipRole.objects.get_or_create(
            membership=membership,
            role=owner_role,
        )
        return assignment, created

    # ---------------------------------------------------------------- summary

    def _print_summary(
        self,
        *,
        org: Organization,
        org_created: bool,
        user: Any,
        user_created: bool,
        admin_password: str,
        roles_created: int,
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
        self.stdout.write(
            f"Per-tenant roles      {tenant_role_count} on disk "
            f"({roles_created} created this run)"
        )
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
