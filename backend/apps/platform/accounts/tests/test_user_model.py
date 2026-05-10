"""Smoke tests for the custom User model (B.3.3, I.6.7)."""

from __future__ import annotations

import uuid

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError


def test_auth_user_model_setting() -> None:
    """The custom user model must be wired in from migration #1 (I.6.7)."""
    assert settings.AUTH_USER_MODEL == "platform_accounts.User"


def test_user_model_class_is_custom() -> None:
    User = get_user_model()
    assert User._meta.app_label == "platform_accounts"
    assert User._meta.model_name == "user"


@pytest.mark.django_db
def test_create_user_lowercases_email() -> None:
    User = get_user_model()
    user = User.objects.create_user(
        email="Person@Example.COM", password="t3st-Pa$$word-12345"
    )
    assert user.email == "person@example.com"
    assert user.is_active is True
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.is_system is False
    assert user.password_changed_at is not None


@pytest.mark.django_db
def test_user_id_is_uuid() -> None:
    User = get_user_model()
    user = User.objects.create_user(
        email="u@example.com", password="t3st-Pa$$word-12345"
    )
    assert isinstance(user.id, uuid.UUID)


@pytest.mark.django_db
def test_create_superuser_flags() -> None:
    User = get_user_model()
    user = User.objects.create_superuser(
        email="admin@example.com", password="t3st-Pa$$word-12345"
    )
    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.is_system is False


@pytest.mark.django_db
def test_email_uniqueness_is_enforced() -> None:
    User = get_user_model()
    User.objects.create_user(email="dup@example.com", password="t3st-Pa$$word-12345")
    with pytest.raises(IntegrityError):
        User.objects.create_user(
            email="dup@example.com", password="t3st-Pa$$word-12345"
        )
