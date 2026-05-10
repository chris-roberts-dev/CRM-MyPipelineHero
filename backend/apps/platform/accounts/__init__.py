"""Platform identity — the canonical User model (B.3).

The ``User`` model in this app is the value of ``AUTH_USER_MODEL``
(``platform_accounts.User``) and is migrated in this app's
``0001_initial`` migration. Retrofitting AUTH_USER_MODEL after
deployment is prohibited (I.6.7).
"""

default_app_config = "apps.platform.accounts.apps.AccountsConfig"
