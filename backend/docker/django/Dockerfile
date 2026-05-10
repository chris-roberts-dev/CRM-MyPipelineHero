# syntax=docker/dockerfile:1.7
# MyPipelineHero Django image.
# Multi-stage so dev images include pytest/ruff/mypy and prod images don't.

ARG PYTHON_IMAGE=python:3.14-slim

# ---------------------------------------------------------------------------
# base — shared OS layer
# ---------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

# Build deps are kept in case a transitive wheel isn't yet available for cp314.
# We install runtime libs first, then optionally install build chain in dev.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      curl \
      ca-certificates \
      libpq5 \
      libjpeg62-turbo \
      tini \
 && rm -rf /var/lib/apt/lists/*

# Non-root runtime user (I.4.2).
RUN groupadd --system --gid 1001 mph \
 && useradd  --system --uid 1001 --gid 1001 --create-home --home-dir /home/mph mph

WORKDIR /app

# ---------------------------------------------------------------------------
# build-deps — install heavy compilers only where needed
# ---------------------------------------------------------------------------
FROM base AS build-deps
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential \
      libpq-dev \
      libjpeg-dev \
      zlib1g-dev \
      pkg-config \
 && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# dev — local development image
# ---------------------------------------------------------------------------
FROM build-deps AS dev

COPY requirements/base.txt requirements/dev.txt requirements/
RUN pip install -r requirements/dev.txt

# Copy the source code in (overlaid by the bind mount in compose for HMR).
COPY . .

# manage.py lives at /app/manage.py.
RUN chown -R mph:mph /app
USER mph

EXPOSE 8000

# Tini for proper signal handling.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---------------------------------------------------------------------------
# builder — used to produce a runtime-only prod image
# ---------------------------------------------------------------------------
FROM build-deps AS builder

COPY requirements/base.txt requirements/prod.txt requirements/
RUN pip install --prefix=/install -r requirements/prod.txt

# ---------------------------------------------------------------------------
# prod — production runtime image
# ---------------------------------------------------------------------------
FROM base AS prod

# Copy installed wheels-in-prefix from the builder.
COPY --from=builder /install /usr/local

COPY --chown=mph:mph . /app

USER mph

# Healthcheck — uses /healthz/ liveness route (G.4.8). Kept inside the image
# so external orchestrators don't need to know our routes.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:8000/healthz || exit 1

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "config.wsgi:application"]