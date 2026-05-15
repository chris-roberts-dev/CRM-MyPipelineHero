"""App config for apps.operations.locations."""

from __future__ import annotations

from django.apps import AppConfig


class LocationsConfig(AppConfig):
    name = "apps.operations.locations"
    label = "operations_locations"
    verbose_name = "Operating scope: Region / Market / Location"
