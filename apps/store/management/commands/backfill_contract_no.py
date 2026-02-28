import logging
from typing import Dict, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.store.models import Contract, ContractNumberSequence


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Backfill contract_no for legacy contracts where contract_no is empty."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-code",
            dest="tenant_code",
            type=str,
            default="",
            help="Only backfill contracts under this tenant code.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview generated numbers without writing to database.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit number of contracts to process (0 means no limit).",
        )

    def handle(self, *args, **options):
        tenant_code_filter = (options.get("tenant_code") or "").strip()
        dry_run = bool(options.get("dry_run"))
        limit = int(options.get("limit") or 0)

        queryset = (
            Contract.objects.select_related("tenant")
            .filter(Q(contract_no__isnull=True) | Q(contract_no=""))
            .order_by("tenant_id", "start_date", "id")
        )
        if tenant_code_filter:
            queryset = queryset.filter(tenant__code=tenant_code_filter)
        if limit > 0:
            queryset = queryset[:limit]

        if dry_run:
            targets = list(queryset)
            updated, skipped = self._assign_contract_numbers(targets, dry_run=True)
        else:
            with transaction.atomic():
                targets = list(queryset.select_for_update())
                updated, skipped = self._assign_contract_numbers(targets, dry_run=False)

        total = len(targets)
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed: total={total}, updated={updated}, skipped={skipped}, dry_run={dry_run}"
            )
        )

    def _assign_contract_numbers(self, contracts, *, dry_run: bool) -> Tuple[int, int]:
        """
        Assign numbers in format CT-{TENANT}-{YYYY}-{NNNNNN}.
        """
        seq_cache: Dict[Tuple[int, int], Dict[str, object]] = {}
        updated = 0
        skipped = 0

        for contract in contracts:
            tenant = contract.tenant
            if tenant is None:
                skipped += 1
                logger.warning("Skip contract %s: missing tenant", contract.id)
                continue

            year = int(contract.start_date.year)
            tenant_code = (tenant.code or "default").upper()
            cache_key = (tenant.id, year)

            if cache_key not in seq_cache:
                seq_obj = None
                if dry_run:
                    seq_obj = ContractNumberSequence.objects.filter(
                        tenant_id=tenant.id,
                        year=year,
                    ).first()
                else:
                    seq_obj = (
                        ContractNumberSequence.objects.select_for_update()
                        .filter(tenant_id=tenant.id, year=year)
                        .first()
                    )
                    if seq_obj is None:
                        seq_obj = ContractNumberSequence.objects.create(
                            tenant_id=tenant.id,
                            year=year,
                            last_seq=0,
                        )

                max_existing = self._max_existing_sequence(tenant.id, tenant_code, year)
                current_seq = max(seq_obj.last_seq if seq_obj else 0, max_existing)
                seq_cache[cache_key] = {
                    "tenant_code": tenant_code,
                    "year": year,
                    "current_seq": current_seq,
                    "seq_obj": seq_obj,
                }

            state = seq_cache[cache_key]
            next_seq = int(state["current_seq"]) + 1
            contract_no = self._format_contract_no(
                tenant_code=state["tenant_code"],
                year=state["year"],
                seq=next_seq,
            )

            # Defensive loop for any existing manual collisions.
            while Contract.objects.filter(
                tenant_id=tenant.id,
                contract_no=contract_no,
            ).exclude(id=contract.id).exists():
                next_seq += 1
                contract_no = self._format_contract_no(
                    tenant_code=state["tenant_code"],
                    year=state["year"],
                    seq=next_seq,
                )

            state["current_seq"] = next_seq

            if dry_run:
                self.stdout.write(f"[DRY-RUN] contract_id={contract.id} -> {contract_no}")
            else:
                contract.contract_no = contract_no
                contract.save(update_fields=["contract_no", "updated_at"])
            updated += 1

        if not dry_run:
            for state in seq_cache.values():
                seq_obj = state["seq_obj"]
                current_seq = int(state["current_seq"])
                if seq_obj and seq_obj.last_seq != current_seq:
                    seq_obj.last_seq = current_seq
                    seq_obj.save(update_fields=["last_seq", "updated_at"])

        return updated, skipped

    @staticmethod
    def _format_contract_no(*, tenant_code: str, year: int, seq: int) -> str:
        return f"CT-{tenant_code}-{year}-{seq:06d}"

    @staticmethod
    def _extract_seq(contract_no: str, prefix: str) -> int:
        if not contract_no or not contract_no.startswith(prefix):
            return 0
        suffix = contract_no[len(prefix):]
        if not suffix.isdigit():
            return 0
        return int(suffix)

    def _max_existing_sequence(self, tenant_id: int, tenant_code: str, year: int) -> int:
        prefix = f"CT-{tenant_code}-{year}-"
        max_seq = 0
        existing_numbers = Contract.objects.filter(
            tenant_id=tenant_id,
            contract_no__startswith=prefix,
        ).values_list("contract_no", flat=True)

        for no in existing_numbers:
            value = self._extract_seq(no, prefix)
            if value > max_seq:
                max_seq = value
        return max_seq
