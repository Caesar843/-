from django.core.management.base import BaseCommand, CommandError

from apps.audit.services import verify_audit_chain


class Command(BaseCommand):
    help = "Verify audit chain integrity for a given object."

    def add_arguments(self, parser):
        parser.add_argument("object_type", help="App label and model name, e.g. store.Contract")
        parser.add_argument("object_id", help="Object ID")

    def handle(self, *args, **options):
        object_type = options["object_type"]
        object_id = options["object_id"]
        result = verify_audit_chain(object_type, object_id)
        if not result.get("ok"):
            raise CommandError(f"Audit chain verification failed: {result}")
        self.stdout.write(self.style.SUCCESS(f"Audit chain OK: {result}"))
