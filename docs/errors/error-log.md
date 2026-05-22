# Per-Tenant Session Middleware Test Debugging Notes

## Summary

A group of tests for `PerTenantSessionMiddleware` were failing because the tests expected Django to write a host-specific session cookie during a `GET /accounts/login/` request. In the current application behavior, that request only wrote a CSRF cookie and did not modify the Django session.

The middleware itself was not proven broken by the original failures. The issue was that the tests depended on a brittle assumption about allauth's login page behavior.

The fix was to replace the `/accounts/login/` dependency with a deterministic test-only view that explicitly writes to `request.session`. After this change, the tests passed.

---

## Original Symptom

Running the test suite produced six failures in `apps/common/sessions/tests/test_middleware.py`.

The tests expected cookies such as:

```text
mph_root_session
tenant_session_acme
```

But the actual cookies were only:

```text
mph_csrftoken
```

Representative failure:

```text
AssertionError: Expected tenant_session_acme cookie, got ['mph_csrftoken']
```

This meant the request completed and CSRF behavior ran, but Django did not persist a session cookie.

---

## Original Test Assumption

The original test file used this path:

```python
_SESSION_TOUCHING_PATH = "/accounts/login/"
```

The comments in the test assumed that allauth's login page would touch the session during a `GET` request:

```python
# Path that's reliably session-touching: allauth's login GET writes
# CSRF + form state to the session, so the middleware's
# process_response writes a cookie even without authentication.
_SESSION_TOUCHING_PATH = "/accounts/login/"
```

That assumption was no longer true in the current application behavior.

---

## Verification Step

This command verified what `/accounts/login/` actually did:

```bash
docker compose -f backend/compose.yaml --project-directory backend exec -T web python manage.py shell -c "
from django.test import Client
c = Client(HTTP_HOST='acme.mph.local')
r = c.get('/accounts/login/')
print('Status:', r.status_code)
print('Cookies:', list(c.cookies))
"
```

Output:

```text
Status: 200
Cookies: ['mph_csrftoken']
```

That confirmed `/accounts/login/` rendered successfully, but only created a CSRF cookie. It did not modify `request.session`, so Django did not write a session cookie.

---

## Why No Session Cookie Was Written

Django generally writes a session cookie only when the session is created or modified.

For example, this modifies the session and should cause a session cookie to be written:

```python
request.session["touched"] = True
```

But rendering a page that only uses CSRF may only create a CSRF cookie, not a session cookie.

That is why the client only contained:

```text
mph_csrftoken
```

and not:

```text
tenant_session_acme
```

---

## Extra Debugging Issue: `Apps aren't loaded yet`

An initial debug command used plain Python:

```bash
python -c "..."
```

That produced:

```text
django.core.exceptions.AppRegistryNotReady: Apps aren't loaded yet.
```

This happened because Django was not initialized before using `django.test.Client`.

The corrected approach was to use:

```bash
python manage.py shell -c "..."
```

or, if using plain Python, explicitly configure Django with `DJANGO_SETTINGS_MODULE` and `django.setup()` before importing and using Django test utilities.

---

## Extra Debugging Issue: Temporary URLConf Using `__name__`

A later manual test attempted:

```python
with override_settings(ROOT_URLCONF=__name__):
```

Inside `manage.py shell -c`, `__name__` resolved to:

```text
django.core.management.commands.shell
```

That caused this error:

```text
django.core.exceptions.ImproperlyConfigured: The included URLconf 'django.core.management.commands.shell' does not appear to have any patterns in it.
```

The fix for the manual shell test was to create an in-memory module and point `ROOT_URLCONF` to that module name.

Working manual verification:

```bash
docker compose -f backend/compose.yaml --project-directory backend exec -T web python manage.py shell -c "
import sys
import types

from django.http import HttpResponse
from django.test import Client, override_settings
from django.urls import path, clear_url_caches

def touch_session_view(request):
    request.session['touched'] = True
    return HttpResponse('ok')

debug_urls = types.ModuleType('debug_urls')
debug_urls.urlpatterns = [
    path('__test__/touch-session/', touch_session_view),
]
sys.modules['debug_urls'] = debug_urls

clear_url_caches()

with override_settings(ROOT_URLCONF='debug_urls'):
    clear_url_caches()
    c = Client(HTTP_HOST='acme.mph.local')
    r = c.get('/__test__/touch-session/')
    print('Status:', r.status_code)
    print('Cookies:', list(c.cookies))

clear_url_caches()
"
```

Output:

```text
Status: 200
Cookies: ['tenant_session_acme']
```

This confirmed the middleware correctly wrote the tenant-specific session cookie when the request actually modified the session.

---

## Final Fix

The tests were rewritten to use a deterministic test-only view instead of `/accounts/login/`.

### Test-only session-touching view

```python
def touch_session_view(request: HttpRequest) -> HttpResponse:
    """Force Django to create/write a session cookie."""
    request.session["touched"] = True
    return HttpResponse("ok")
```

### Test-only URLConf

```python
urlpatterns = [
    path("__test__/touch-session/", touch_session_view),
]

_SESSION_TOUCHING_PATH = "/__test__/touch-session/"
```

### Autouse fixture

```python
@pytest.fixture(autouse=True)
def use_test_urlconf(settings):
    """Point these tests at the test-only URLConf in this module."""
    settings.ROOT_URLCONF = __name__
    clear_url_caches()
    yield
    clear_url_caches()
```

This works inside the pytest module because `__name__` refers to the actual test module, not Django's shell command module.

---

## Why the Fix Works

The rewritten tests directly create the condition needed to exercise the middleware:

1. A real Django test client request is issued.
2. The request includes a host such as `mph.local` or `acme.mph.local`.
3. The test-only view modifies `request.session`.
4. Django's session machinery writes a session cookie.
5. `PerTenantSessionMiddleware` can apply the correct host-specific cookie name and domain behavior.

This makes the tests deterministic and focused on the middleware behavior.

---

## What the Tests Now Validate

The updated tests validate three behaviors.

### 1. Cookie name by host

Root host requests should produce:

```text
mph_root_session
```

Tenant host requests should produce:

```text
tenant_session_acme
```

### 2. Cookie domain scoping

Root session cookies should not set a broad parent-domain attribute.

Tenant session cookies should scope to the exact tenant host:

```text
acme.mph.local
```

### 3. Session isolation between hosts

A root-domain client and a tenant-domain client should receive different session keys.

This confirms that root and tenant sessions do not bleed into each other through a shared cookie.

---

## Key Takeaway

The original failures looked like middleware failures, but the actual issue was a brittle test dependency.

The tests expected `/accounts/login/` to touch the session, but that path only created a CSRF cookie in the current app configuration. By replacing that dependency with a test-only view that explicitly writes to `request.session`, the tests became deterministic and the middleware behavior could be tested directly.
