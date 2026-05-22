"""Redis client factory for handoff nonce storage (M1 D6 Phase 2).

Centralizes the choice of Redis backend so tests can swap in
fakeredis. The choice is made via the ``MPH_HANDOFF_USE_FAKEREDIS``
setting (True in test.py, False everywhere else); the URL is
``MPH_HANDOFF_REDIS_URL`` for the real-Redis case.

We deliberately open a fresh client per call rather than caching a
module-level singleton. Reasons:

* Test isolation: each test gets its own fakeredis instance.
* Connection pooling is already handled by redis-py's per-URL
  default pool.
* Avoids "module-level singleton holds stale connection after Redis
  restart" failure mode in production.

Future optimization (M2+): cache per-process clients keyed by URL
with a connection-health check on retrieval.
"""

from __future__ import annotations

import logging
from typing import Any

import redis
from django.conf import settings

logger = logging.getLogger(__name__)


def get_handoff_redis_client() -> Any:
    """Return a redis-compatible client for handoff nonce storage.

    Returns a real ``redis.Redis`` instance in production / dev /
    staging, and a ``fakeredis.FakeRedis`` instance when
    ``MPH_HANDOFF_USE_FAKEREDIS`` is True (test settings).

    The returned client supports all commands the handoff services
    use: ``set``, ``setex``, ``get``, ``delete``, ``getdel``,
    ``pipeline``, ``exists``.
    """
    use_fake = getattr(settings, "MPH_HANDOFF_USE_FAKEREDIS", False)
    if use_fake:
        # Lazy import — fakeredis is a test-only dep, not in base.txt.

        return _shared_fakeredis_client()

    url = getattr(settings, "MPH_HANDOFF_REDIS_URL", None)
    if not url:
        raise RuntimeError(
            "MPH_HANDOFF_REDIS_URL is not configured. Set it in your "
            "environment or settings module."
        )
    return redis.Redis.from_url(url, decode_responses=False)


# ---------------------------------------------------------------------------
# Test fakeredis sharing
# ---------------------------------------------------------------------------
#
# Multiple service calls within a single test must hit the SAME
# fakeredis instance — otherwise issuing a token in test setup and
# consuming it later see different data stores. We expose a module-
# level singleton for the fakeredis case ONLY; tests reset it via
# the ``reset_handoff_fakeredis`` helper (called from a conftest
# autouse fixture).

_fake_client: Any | None = None


def _shared_fakeredis_client() -> Any:
    """Return the process-wide fakeredis instance, creating it if needed."""
    global _fake_client
    if _fake_client is None:
        import fakeredis

        _fake_client = fakeredis.FakeRedis(decode_responses=False)
    return _fake_client


def reset_handoff_fakeredis() -> None:
    """Test helper: flush + recreate the fakeredis singleton.

    Called from an autouse pytest fixture to give each test a fresh
    in-memory Redis. Never call from production code.
    """
    global _fake_client
    if _fake_client is not None:
        try:
            _fake_client.flushall()
        except Exception:
            # If the previous instance is in a bad state, drop it
            # and rebuild on next access.
            logger.debug("flushall failed on fakeredis; rebuilding instance.")
    _fake_client = None
