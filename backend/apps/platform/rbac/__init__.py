"""RBAC: capabilities, roles, grants, enforcement (B.6).

Phase 1: app skeleton only — concrete Capability, Role, RoleCapability,
MembershipRoleAssignment, MembershipCapabilityGrant land in M1, and
``seed_v1`` (I.6.3) lands as ``0002_seed_v1`` in this app.
"""

default_app_config = "apps.platform.rbac.apps.RbacConfig"
