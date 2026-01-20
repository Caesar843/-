from django.apps import AppConfig


class TenantsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tenants"

    def ready(self):
        # Attach a lightweight tenant property to User for convenience.
        from django.contrib.auth.models import User

        if not hasattr(User, "tenant"):
            def _tenant(user):
                return getattr(getattr(user, "profile", None), "tenant", None)

            User.tenant = property(_tenant)
