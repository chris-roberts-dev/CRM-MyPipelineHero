# M1 D6 Retro — Cross-Subdomain Auth Handoff

**Days completed:** D6 / D7 of M1.
**Phases:** 1 (signing keys) → 2 (token issue/consume) → 3 (per-host
sessions) → 4A (host URL routing + MFA signals) → 4B (org picker +
handoff issue + tenant consume + tenant landing) → 5 (logout + token
revocation) → 6 (integration tests + retro).
**Test count:** start of D6 ≈ 280; end of D6 ≈ 410.

## What landed

The cross-subdomain authentication handoff (B.4.12 — B.4.17) is
end-to-end functional. Users log in to the root domain, complete MFA,
pick an organization, and are transported to a tenant subdomain via a
signed, single-use JWT. Logout works on both ends with the correct
session-scope semantics. Handoff tokens are revoked on root logout.
The full flow is exercised by integration tests in
`apps/web/tenant_portal/tests/test_multi_host_integration.py`.

## Deviations from the guide

The following are deliberate departures we made during D6 that should
be folded back into G.5 / B.4 at the next guide update.

### Handoff secret encryption at the service layer, not the database

G.5.7 implies application-level field encryption via a custom field
class. We chose Fernet encryption at the service-layer boundary
instead (`apps/platform/accounts/handoff/encryption.py`). The model
field stores ciphertext bytes; `decrypt_handoff_secret(secret_bytes)`
unwraps at the only read site. Tradeoff: no `Model.objects.filter(
secret=...)` lookups (acceptable — we never look up by secret), but
plain bytea column type, no migration hazard, and the secret never
appears in a Django ORM tracing context. The key derivation function
remains as specified; only the storage mechanism changed.

### Zero-overlap emergency rotation

Routine rotation supports an overlap window where the previous primary
key remains active so in-flight tokens can verify. Emergency rotation
(`emergency_rotate_handoff_signing_key`) deliberately takes a
zero-overlap path: previous primary key is immediately retired and a
new primary is promoted in a single transaction. Outstanding tokens
become invalid. Audit emits
`HANDOFF_SIGNING_KEY_EMERGENCY_ROTATED`. The deviation is justified by
the operational scenario (suspected key compromise — minimizing
attack window matters more than user friction). Documented as a known
deviation from the standard rotation flow.

### GETDEL instead of pipelined GET+DELETE for single-use nonce

The guide describes single-use enforcement as a pipelined GET + DELETE
in a MULTI/EXEC block. Two concurrent consumes can both see the GET
result before either DELETE lands, both interpret it as "the token
existed," and both succeed. GETDEL (Redis 6.2+) is a single atomic
command that returns the value AND deletes; concurrent calls either
get the value (one wins) or None (everyone else). Strictly stronger
than pipelining. This is the design we should adopt in the guide for
B.4.12.

### Subpackage model discovery requires explicit import

Models under `apps/platform/accounts/oauth/models.py` and
`apps/platform/accounts/handoff/models.py` are NOT auto-discovered by
Django because they don't live in the app's top-level `models.py`.
`AccountsConfig.ready()` must explicitly import the subpackages'
`models` module to register the models with the app registry.
Skipping this causes `makemigrations` to generate spurious `DeleteModel`
migrations. Worth documenting in the architectural notes if other apps
adopt subpackage models later.

### Middleware audit emissions must go through `record_auth_event`

The audit service raises `AuditOutsideTransactionError` if
`audit_emit` is called without an open transaction. Middleware runs
outside the request-handling view's transaction. Calling `audit_emit`
directly from middleware crashes the request with a 500.

Fix established mid-D6: middleware emissions route through
`record_auth_event`, the service wrapper that opens its own
`transaction.atomic()` and catches non-programming errors. Three new
production-realism tests with `@pytest.mark.django_db(transaction=True)`
guard against regression. This pattern is now project-wide: any signal
handler, middleware, or non-service code path that emits audit events
goes through `record_auth_event`.

### Per-host URL routing with test opt-out

`HostUrlconfMiddleware` overrides `request.urlconf` based on host
classification (ROOT → `urls_root`, TENANT → `urls_tenant`, OTHER
falls through). The override breaks tests that use
`override_settings(ROOT_URLCONF=__name__)` to swap in a test-only
URLconf — the middleware's `request.urlconf` write wins over the
settings override.

Resolution: `MPH_HOST_URLCONF_ROUTING_ENABLED` setting (True in
production, False in `test.py`). Tests that DO want to exercise host
routing opt back in via an autouse fixture. The setting flag is the
established pattern for per-test middleware behavior toggles in this
project.

### Defensive request-host extraction in the logout signal

The `user_logged_out` signal handler initially called
`request.get_host()` directly. This crashed in:

1. Existing tests using `client.logout()` where the underlying
   request has no `HTTP_HOST` or `SERVER_NAME` (KeyError on
   `META["SERVER_NAME"]`).
2. Signal-send tests that pass a `MagicMock` as the request
   (TypeError on string operations).
3. Real production requests with `DisallowedHost`.

Final implementation: `_safe_request_host(request)` wraps
`request.get_host()` in a broad except for `(AttributeError, KeyError,
DisallowedHost, TypeError, ValueError)`, falling back to a configured
host name or `testserver`. Classification failures default to
root-style behavior (revoke), biasing toward safety.

### `@override_settings` doesn't work as a class decorator on pytest classes

Django's `@override_settings` can decorate `SimpleTestCase` subclasses
only. Plain pytest classes are not subclasses of `SimpleTestCase`.
Decorating a pytest class raises `ValueError("Only subclasses of
Django SimpleTestCase can be decorated with override_settings")` at
import time.

Resolution: use pytest-django's `settings` fixture inside an autouse
fixture at module or class level. The fixture writes the setting,
pytest-django reverts at teardown.

### Test client `session` is host-blind

Django's `client.session` reads the session cookie by
`settings.SESSION_COOKIE_NAME` — the SAME name for every request.
Our `PerTenantSessionMiddleware` writes a HOST-DERIVED cookie name
(`mph_root_session` on root, `tenant_session_{slug}` on tenant). The
test client's `session` property never sees the tenant cookie.

Resolution: `_load_session_for_host(client, host)` helper that calls
`resolve_session_scope(host)`, reads the appropriate cookie value, and
loads the session via `SessionStore(session_key=...).load()`. Used in
every tenant-session test.

### `client.force_login` writes the session cookie before host context exists

The Django test client's `force_login` synthesizes a session under
`settings.SESSION_COOKIE_NAME` BEFORE the test makes any HTTP request
that would carry a host. Tests that need tenant-host-cookie behavior
cannot use `force_login` — they need either:

1. A real `client.post('/accounts/login/', ...)` against the test host.
2. A test-only URLconf with a session-touching view, paired with
   `MPH_HOST_URLCONF_ROUTING_ENABLED=False` so the override doesn't fire.

Phase 3 used approach (2). Phase 4B/5 use a mix.

## Known limitations carried forward

### Race window: issue concurrent with logout

If `issue_handoff_token` and `revoke_all_handoff_tokens_for_user` run
concurrently for the same user:

1. Logout's SMEMBERS reads the index.
2. Issue's SADD runs (after the read, before the DEL).
3. Logout's DEL removes the index and known token nonces.
4. Issue's token survives logout until its own TTL expires (60s).

Mitigation: bounded by TTL. Net effect: short window where a
"recently issued" token survives a logout. Lua-script atomicity would
close it but adds operational complexity disproportionate to risk for
v1.

### Signal handler fallback chain doesn't match project setting

`signals_logout.py:_fallback_host` checks `ROOT_DOMAIN`,
`PUBLIC_ROOT_DOMAIN`, `BASE_DOMAIN`, `PRIMARY_DOMAIN` for a fallback
when `request.get_host()` raises. Our setting is `MPH_ROOT_DOMAIN`;
none of the checked names match. The function falls through to the
`testserver` default. Works correctly because `testserver` classifies
as OTHER → not TENANT → revoke path → correct outcome for tests.
Worth aligning the chain to `MPH_ROOT_DOMAIN` if we want production
fallback to use the project's real setting rather than `testserver`.

### Multi-tab interstitial (B.4.16)

The guide describes a UX where a user with multiple tabs on tenant
subdomains can log out from one tab and have the others detect it.
The mechanism described requires cross-subdomain cookie sharing,
which the architecture explicitly disallows. The spec is incomplete
on this point. Deferring until product confirms whether multi-tab
detection is worth a polling endpoint or another mechanism.

### Trusted-provider TOTP challenge bypass

M1 D5 deferred the case where a user authenticates via trusted-
provider OAuth AND has a local TOTP authenticator enrolled.
Currently the user gets the local TOTP challenge anyway. Tracked for
M1 D7 or M2.

## Lessons

1. **Request file contents before producing changes to files I haven't
   seen in this session.** Two large failure cascades in D6 (105
   failures from a stale `SelectOrgPlaceholderView` reference;
   smaller cascades from URL splits) came from snippet-paste
   instructions on files I lacked visibility into. The compaction
   notes flagged this twice; this milestone confirmed the cost.

2. **Audit-event registration is a serial bottleneck.** Every phase
   added codes to `_KNOWN_EVENT_TYPES`. Three phases registered codes
   in different places. Worth considering a registration helper or
   per-module event-code declaration to localize the changes.

3. **Per-host behavior is a cross-cutting concern.** Three middlewares
   now care about host scope (session cookies, URL routing, logout
   signal). All read `_mph_session_scope` set by
   `PerTenantSessionMiddleware`. Ordering is critical — the session
   middleware must run first. Worth a startup check that asserts this
   ordering in production settings.

4. **Signal handlers became a real architectural layer.** M1 D4
   handlers do audit emission. M1 D6 Phase 4A handlers do session-key
   writes. M1 D6 Phase 5 handler does Redis operations + audit.
   Pattern: signal handlers are now first-class extension points,
   not just hooks. Should be reflected in the architectural notes.

5. **Production-realism tests with `@pytest.mark.django_db(transaction=True)`
   are essential for transaction-boundary code.** The audit
   "must-be-in-transaction" requirement crashed only when the request
   wasn't already wrapped in a transaction-per-test test. Plain
   `@pytest.mark.django_db` masks the issue because pytest-django
   wraps each test in a transaction.

## Phase-by-phase test count progression

* Phase 1 (signing keys): +33 tests.
* Phase 2 (issue/consume): +21 tests.
* Phase 3 (per-host sessions): +27 tests.
* Phase 4A (host URL routing + MFA signals): +13 tests.
* Phase 4B (picker + issue + consume views): +9 tests (after fixing
  a 105-failure cascade from a stale `SelectOrgPlaceholderView`
  reference).
* Phase 5 (logout + revocation): +17 tests.
* Phase 6 (integration tests): +8 tests.

Total D6: ~128 new tests.
