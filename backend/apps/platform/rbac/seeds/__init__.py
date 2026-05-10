"""V1 capability and default-role seed sources.

These modules are pure Python data — no Django model imports. They are
read by the ``seed_v1`` data migration (I.6.3) which itself uses
``apps.get_model(...)`` to obtain the historical model classes.

Editing capability codes here is a breaking change. Adding new
capabilities is additive and should be done in a successor seed
migration (I.6.5), NOT by editing this file.
"""
