from django.core.management.base import BaseCommand, CommandError

from apps.audit.services import verify_audit_chains_batch


class Command(BaseCommand):
    help = "Batch verify audit chains in a recent time window."

    def add_arguments(self, parser):
        parser.add_argument("--hours", type=int, default=24, help="Time window in hours.")
        parser.add_argument("--limit", type=int, default=300, help="Max distinct objects to verify.")
        parser.add_argument(
            "--modules",
            nargs="+",
            default=["contract", "finance"],
            help="Modules to verify, e.g. contract finance",
        )
        parser.add_argument(
            "--object-type",
            dest="object_type",
            default=None,
            help="Optional object type, e.g. store.Contract",
        )
        parser.add_argument(
            "--skip-sequence-check",
            action="store_true",
            help="Skip contract action-sequence completeness check.",
        )
        parser.add_argument(
            "--fail-fast",
            action="store_true",
            help="Return non-zero when any verification fails.",
        )

    def handle(self, *args, **options):
        result = verify_audit_chains_batch(
            modules=options["modules"],
            hours=options["hours"],
            limit=options["limit"],
            object_type=options.get("object_type"),
            include_sequence_check=not options["skip_sequence_check"],
        )
        self.stdout.write(
            f"Checked={result['checked_objects']} "
            f"chain_failures={result['failure_count']} "
            f"sequence_failures={result['sequence_failure_count']}"
        )
        if result.get("ok"):
            self.stdout.write(self.style.SUCCESS("Audit chain batch verification OK"))
            return

        self.stdout.write(self.style.WARNING(f"Verification details: {result}"))
        if options["fail_fast"]:
            raise CommandError("Audit chain batch verification failed")
