from django.core.management.base import BaseCommand
from django.urls import URLPattern, URLResolver, get_resolver
from django.contrib.auth.mixins import LoginRequiredMixin

try:
    from rest_framework.permissions import IsAuthenticated, IsAdminUser
except Exception:  # pragma: no cover - optional dependency
    IsAuthenticated = None
    IsAdminUser = None


PUBLIC_PATH_PREFIXES = (
    "core/login/",
    "core/register/",
    "core/health/",
    "health/",
    "api/schema/",
    "api/docs/",
    "api/redoc/",
    "metrics/",
)


def _iter_patterns(patterns, prefix=""):
    for entry in patterns:
        if isinstance(entry, URLPattern):
            yield prefix + str(entry.pattern), entry.callback
        elif isinstance(entry, URLResolver):
            yield from _iter_patterns(entry.url_patterns, prefix + str(entry.pattern))


def _has_login_mixin(view_class):
    try:
        return issubclass(view_class, LoginRequiredMixin)
    except Exception:
        return False


def _has_drf_auth(view_class):
    perms = getattr(view_class, "permission_classes", None)
    if not perms:
        return False
    if IsAuthenticated is None:
        return True
    for perm in perms:
        try:
            if issubclass(perm, (IsAuthenticated, IsAdminUser)):
                return True
        except Exception:
            continue
    return False


def _is_public(path):
    return path.startswith(PUBLIC_PATH_PREFIXES)


class Command(BaseCommand):
    help = "Audit URL auth coverage (heuristic). Lists routes without obvious auth protection."

    def handle(self, *args, **options):
        resolver = get_resolver()
        findings = []

        for path, callback in _iter_patterns(resolver.url_patterns):
            clean_path = path.lstrip("/")
            if _is_public(clean_path):
                continue

            view_class = getattr(callback, "view_class", None)
            if view_class:
                protected = _has_login_mixin(view_class) or _has_drf_auth(view_class)
            else:
                protected = hasattr(callback, "login_url")

            if not protected:
                findings.append((path, callback))

        if not findings:
            self.stdout.write(self.style.SUCCESS("✅ No obvious unauthenticated routes found."))
            return

        self.stdout.write(self.style.WARNING("⚠️  Potentially unprotected routes:"))
        for path, callback in findings:
            self.stdout.write(f"- {path} -> {callback}")
