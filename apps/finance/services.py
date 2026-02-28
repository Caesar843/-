import logging

from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.data_governance.models import IdempotencyKey
from apps.data_governance.utils import hash_payload
from apps.finance.dtos import FinanceGenerateDTO, FinancePayDTO, FinanceRecordCreateDTO
from apps.finance.models import FinanceRecord, BillingSchedule
from apps.audit.services import log_audit_action
from apps.audit.utils import serialize_instance
from apps.core.exceptions import BusinessValidationError, StateConflictException, ResourceNotFoundException
from apps.store.models import Contract, ContractItem

logger = logging.getLogger(__name__)


class FinanceService:
    """
    财务服务类
    提供财务记录的生成、支付等核心业务逻辑
    """

    FINANCE_AUDIT_FIELDS = [
        "id",
        "contract_id",
        "amount",
        "fee_type",
        "billing_period_start",
        "billing_period_end",
        "status",
        "payment_method",
        "transaction_id",
        "paid_at",
        "reminder_sent",
    ]

    BILLING_SCHEDULE_AUDIT_FIELDS = [
        "id",
        "contract_id",
        "contract_item_id",
        "period_start",
        "period_end",
        "due_date",
        "amount",
        "status",
        "source_version",
        "finance_record_id",
    ]

    @staticmethod
    def _assert_tenant_access(
        *,
        target_model: str,
        target_id: int,
        actual_tenant_id: int,
        expected_tenant_id: int | None,
        actor_id: int | None,
        service_action: str,
        object_type: str,
    ) -> None:
        if expected_tenant_id is None:
            return
        if int(actual_tenant_id) == int(expected_tenant_id):
            return

        logger.warning(
            "Cross-tenant access blocked: %s id=%s actor=%s expected_tenant=%s actual_tenant=%s action=%s",
            target_model,
            target_id,
            actor_id,
            expected_tenant_id,
            actual_tenant_id,
            service_action,
        )
        log_audit_action(
            action="cross_tenant_access_blocked",
            module="finance",
            object_type=object_type,
            object_id=str(target_id),
            actor_id=actor_id,
            before_data={"actual_tenant_id": actual_tenant_id},
            after_data={
                "expected_tenant_id": expected_tenant_id,
                "service_action": service_action,
            },
        )
        raise ResourceNotFoundException(
            message=f"{target_model} with id {target_id} not found",
            override_error_code="RESOURCE_NOT_FOUND",
            data={"target_model": target_model, "target_id": target_id},
        )

    @staticmethod
    def _cycle_to_months(payment_cycle: str) -> int:
        cycle_month_map = {
            Contract.PaymentCycle.MONTHLY: 1,
            Contract.PaymentCycle.QUARTERLY: 3,
            Contract.PaymentCycle.SEMIANNUALLY: 6,
            Contract.PaymentCycle.ANNUALLY: 12,
            ContractItem.PaymentCycle.MONTHLY: 1,
            ContractItem.PaymentCycle.QUARTERLY: 3,
            ContractItem.PaymentCycle.SEMIANNUALLY: 6,
            ContractItem.PaymentCycle.ANNUALLY: 12,
        }
        return cycle_month_map.get(payment_cycle, 1)

    @staticmethod
    def _add_months(base: date, months: int) -> date:
        month_index = base.month - 1 + months
        target_year = base.year + month_index // 12
        target_month = month_index % 12 + 1
        target_day = min(base.day, monthrange(target_year, target_month)[1])
        return date(target_year, target_month, target_day)

    @staticmethod
    def _iter_periods(period_start: date, period_end: date, payment_cycle: str):
        current = period_start
        cycle_months = FinanceService._cycle_to_months(payment_cycle)
        while current <= period_end:
            next_date = FinanceService._add_months(current, cycle_months)
            current_period_end = min(next_date - timedelta(days=1), period_end)
            yield current, current_period_end
            current = next_date

    @staticmethod
    def _overlap_days(a_start: date, a_end: date, b_start: date, b_end: date) -> int:
        start = max(a_start, b_start)
        end = min(a_end, b_end)
        if end < start:
            return 0
        return (end - start).days + 1

    @staticmethod
    def _map_item_type_to_fee_type(item_type: str) -> str:
        if item_type == ContractItem.ItemType.RENT:
            return FinanceRecord.FeeType.RENT
        if item_type == ContractItem.ItemType.PROPERTY_FEE:
            return FinanceRecord.FeeType.PROPERTY_FEE
        return FinanceRecord.FeeType.OTHER

    @staticmethod
    def _calculate_item_amount(item: ContractItem, period_start: date, period_end: date) -> Decimal:
        amount = Decimal(item.amount or 0)

        if item.calc_type == ContractItem.CalcType.ESCALATION and item.rate:
            base_date = item.period_start or item.contract.start_date
            elapsed_months = (period_start.year - base_date.year) * 12 + (period_start.month - base_date.month)
            if period_start.day < base_date.day:
                elapsed_months -= 1
            elapsed_years = max(0, elapsed_months // 12)
            factor = (Decimal("1") + Decimal(item.rate)) ** elapsed_years
            amount = amount * factor

        total_days = (period_end - period_start).days + 1
        if (
            total_days > 0
            and item.free_rent_from
            and item.free_rent_to
            and item.item_type in {ContractItem.ItemType.RENT, ContractItem.ItemType.PROPERTY_FEE}
        ):
            free_days = FinanceService._overlap_days(
                period_start,
                period_end,
                item.free_rent_from,
                item.free_rent_to,
            )
            chargeable_days = max(total_days - free_days, 0)
            amount = amount * Decimal(chargeable_days) / Decimal(total_days)

        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    @transaction.atomic
    def generate_records_for_contract(
        contract_id: int,
        tenant_id: int | None = None,
        operator_id: int | None = None,
    ) -> List[FinanceRecord]:
        """
        为合同生成财务记录
        仅允许对 ACTIVE 合同生成，自动按月生成账单

        Args:
            contract_id: 合同ID

        Returns:
            生成的财务记录列表

        Raises:
            ResourceNotFoundException: 合同不存在
            BusinessValidationError: 合同状态不是 ACTIVE
        """
        try:
            contract = Contract.objects.get(id=contract_id)
            FinanceService._assert_tenant_access(
                target_model="Contract",
                target_id=contract.id,
                actual_tenant_id=contract.tenant_id,
                expected_tenant_id=tenant_id,
                actor_id=operator_id,
                service_action="generate_records_for_contract",
                object_type="store.contract",
            )
        except Contract.DoesNotExist:
            raise ResourceNotFoundException(f"Contract with id {contract_id} not found")

        if contract.status != Contract.Status.ACTIVE:
            raise BusinessValidationError(
                f"Contract must be in ACTIVE status, current status: {contract.status}",
                data={"field": "contract_status"},
            )

        generated_records: List[FinanceRecord] = []
        contract_items = list(
            ContractItem.objects.filter(
                contract=contract,
                status=ContractItem.Status.ACTIVE,
            ).order_by("sequence", "id")
        )

        if not contract_items:
            contract_items = [
                ContractItem(
                    contract=contract,
                    tenant_id=contract.tenant_id,
                    item_type=ContractItem.ItemType.RENT,
                    calc_type=ContractItem.CalcType.FIXED,
                    amount=contract.monthly_rent,
                    payment_cycle=contract.payment_cycle,
                    period_start=contract.start_date,
                    period_end=contract.end_date,
                )
            ]
            if contract.deposit and contract.deposit > 0:
                contract_items.append(
                    ContractItem(
                        contract=contract,
                        tenant_id=contract.tenant_id,
                        item_type=ContractItem.ItemType.DEPOSIT,
                        calc_type=ContractItem.CalcType.FIXED,
                        amount=contract.deposit,
                        payment_cycle=ContractItem.PaymentCycle.ONE_TIME,
                        period_start=contract.start_date,
                        period_end=contract.start_date,
                    )
                )

        for item in contract_items:
            item_period_start = item.period_start or contract.start_date
            item_period_end = item.period_end or contract.end_date
            effective_start = max(contract.start_date, item_period_start)
            effective_end = min(contract.end_date, item_period_end)
            if effective_end < effective_start:
                continue

            if item.item_type == ContractItem.ItemType.DEPOSIT or item.payment_cycle == ContractItem.PaymentCycle.ONE_TIME:
                periods = [(effective_start, effective_start)]
            else:
                periods = list(
                    FinanceService._iter_periods(
                        effective_start,
                        effective_end,
                        item.payment_cycle or contract.payment_cycle,
                    )
                )

            for period_start, period_end in periods:
                amount = FinanceService._calculate_item_amount(item, period_start, period_end)
                due_date = period_start
                bound_item = item if item.id else None

                schedule, created = BillingSchedule.objects.get_or_create(
                    contract=contract,
                    contract_item=bound_item,
                    period_start=period_start,
                    period_end=period_end,
                    source_version=1,
                    defaults={
                        "tenant_id": contract.tenant_id,
                        "due_date": due_date,
                        "amount": amount,
                        "status": BillingSchedule.Status.PLANNED if amount > 0 else BillingSchedule.Status.VOID,
                    },
                )

                if not created:
                    before_schedule = serialize_instance(schedule, FinanceService.BILLING_SCHEDULE_AUDIT_FIELDS)
                    schedule.due_date = due_date
                    schedule.amount = amount
                    if schedule.finance_record_id:
                        schedule.status = (
                            BillingSchedule.Status.PAID
                            if schedule.finance_record.status == FinanceRecord.Status.PAID
                            else BillingSchedule.Status.ISSUED
                        )
                    else:
                        schedule.status = BillingSchedule.Status.PLANNED if amount > 0 else BillingSchedule.Status.VOID
                    schedule.save(update_fields=["due_date", "amount", "status", "updated_at"])
                    log_audit_action(
                        action="update_billing_schedule",
                        module="finance",
                        instance=schedule,
                        actor_id=operator_id,
                        before_data=before_schedule,
                        after_data=serialize_instance(schedule, FinanceService.BILLING_SCHEDULE_AUDIT_FIELDS),
                    )
                else:
                    log_audit_action(
                        action="create_billing_schedule",
                        module="finance",
                        instance=schedule,
                        actor_id=operator_id,
                        before_data=None,
                        after_data=serialize_instance(schedule, FinanceService.BILLING_SCHEDULE_AUDIT_FIELDS),
                    )

                if amount <= 0 or schedule.finance_record_id:
                    continue

                fee_type = FinanceService._map_item_type_to_fee_type(item.item_type)
                record_period_end = period_end if period_end > period_start else (period_start + timedelta(days=1))
                existing_record = FinanceRecord.objects.filter(
                    contract=contract,
                    fee_type=fee_type,
                    billing_period_start=period_start,
                    billing_period_end=record_period_end,
                ).first()
                if existing_record:
                    schedule.finance_record = existing_record
                    schedule.status = (
                        BillingSchedule.Status.PAID
                        if existing_record.status == FinanceRecord.Status.PAID
                        else BillingSchedule.Status.ISSUED
                    )
                    schedule.save(update_fields=["finance_record", "status", "updated_at"])
                    continue

                record = FinanceRecord.objects.create(
                    contract=contract,
                    amount=amount,
                    fee_type=fee_type,
                    billing_period_start=period_start,
                    billing_period_end=record_period_end,
                    status=FinanceRecord.Status.UNPAID,
                )
                schedule.finance_record = record
                schedule.status = BillingSchedule.Status.ISSUED
                schedule.save(update_fields=["finance_record", "status", "updated_at"])

                log_audit_action(
                    action="generate_finance_record",
                    module="finance",
                    instance=record,
                    actor_id=operator_id,
                    before_data=None,
                    after_data=serialize_instance(record, FinanceService.FINANCE_AUDIT_FIELDS),
                )
                generated_records.append(record)

        return generated_records

    @staticmethod
    @transaction.atomic
    def generate_fee_record(
        dto: FinanceRecordCreateDTO,
        operator_id: int,
        tenant_id: int | None = None,
    ) -> FinanceRecord:
        """
        生成指定类型的费用记录

        Args:
            dto: 财务记录创建数据传输对象
            operator_id: 操作人ID

        Returns:
            生成的财务记录

        Raises:
            ResourceNotFoundException: 合同不存在
            BusinessValidationError: 合同状态不是 ACTIVE
        """
        # 查找合同
        try:
            contract = Contract.objects.get(id=dto.contract_id)
            FinanceService._assert_tenant_access(
                target_model="Contract",
                target_id=contract.id,
                actual_tenant_id=contract.tenant_id,
                expected_tenant_id=tenant_id,
                actor_id=operator_id,
                service_action="generate_fee_record",
                object_type="store.contract",
            )
        except Contract.DoesNotExist:
            raise ResourceNotFoundException(f"Contract with id {dto.contract_id} not found")

        # 检查合同状态
        if contract.status != Contract.Status.ACTIVE:
            raise BusinessValidationError(
                f"Contract must be in ACTIVE status, current status: {contract.status}",
                data={"field": "contract_status"}
            )

        # 解析日期
        try:
            billing_period_start = datetime.strptime(dto.billing_period_start, "%Y-%m-%d").date()
            billing_period_end = datetime.strptime(dto.billing_period_end, "%Y-%m-%d").date()
        except ValueError as e:
            raise BusinessValidationError(f"Invalid date format: {str(e)}", data={"field": "billing_period"})

        # 验证日期范围
        if billing_period_end <= billing_period_start:
            raise BusinessValidationError("End date must be after start date", data={"field": "billing_period_end"})

        # 创建财务记录
        record = FinanceRecord.objects.create(
            contract=contract,
            amount=dto.amount,
            fee_type=dto.fee_type,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end,
            status=FinanceRecord.Status.UNPAID
        )

        after_data = serialize_instance(record, FinanceService.FINANCE_AUDIT_FIELDS)
        log_audit_action(
            action="create_finance_record",
            module="finance",
            instance=record,
            actor_id=operator_id,
            before_data=None,
            after_data=after_data,
        )

        return record

    @staticmethod
    @transaction.atomic
    def mark_as_paid(
        dto: FinancePayDTO,
        operator_id: int,
        idempotency_key: Optional[str] = None,
        tenant_id: int | None = None,
    ) -> FinanceRecord:
        """
        标记财务记录为已支付
        状态流转：UNPAID → PAID
        幂等性检查：如果已经是 PAID 状态，直接返回

        Args:
            dto: 支付数据传输对象
            operator_id: 操作人ID

        Returns:
            更新后的财务记录

        Raises:
            ResourceNotFoundException: 财务记录不存在
            StateConflictException: 财务记录状态不是 UNPAID
        """
        payload = {
            "record_id": dto.record_id,
            "payment_method": dto.payment_method,
            "transaction_id": dto.transaction_id,
        }

        if getattr(settings, "ENABLE_IDEMPOTENCY", False):
            if not idempotency_key:
                raise BusinessValidationError(
                    "Idempotency key is required for payment operations",
                    data={"field": "idempotency_key"},
                )

            normalized_key = idempotency_key.strip()
            if not normalized_key:
                raise BusinessValidationError(
                    "Idempotency key must be a non-empty string",
                    data={"field": "idempotency_key"},
                )

            request_hash = hash_payload(payload)
            try:
                IdempotencyKey.objects.create(
                    key=normalized_key,
                    scope="finance.mark_as_paid",
                    request_hash=request_hash,
                    object_type="FinanceRecordPayment",
                    object_id=str(dto.record_id),
                )
            except IntegrityError:
                logger.info(
                    "Idempotent replay detected for FinanceRecord %s (key=%s)",
                    dto.record_id,
                    normalized_key,
                )
                try:
                    existing_record = FinanceRecord.objects.get(id=dto.record_id)
                    FinanceService._assert_tenant_access(
                        target_model="FinanceRecord",
                        target_id=existing_record.id,
                        actual_tenant_id=existing_record.tenant_id,
                        expected_tenant_id=tenant_id,
                        actor_id=operator_id,
                        service_action="mark_as_paid",
                        object_type="finance.financerecord",
                    )
                except FinanceRecord.DoesNotExist:
                    raise ResourceNotFoundException(
                        f"Finance record with id {dto.record_id} not found"
                    )

                if existing_record.status == FinanceRecord.Status.PAID:
                    return existing_record

                raise BusinessValidationError(
                    "Payment is already being processed, please wait",
                    data={"field": "idempotency_key"},
                )

        try:
            record = FinanceRecord.objects.select_for_update().get(id=dto.record_id)
            FinanceService._assert_tenant_access(
                target_model="FinanceRecord",
                target_id=record.id,
                actual_tenant_id=record.tenant_id,
                expected_tenant_id=tenant_id,
                actor_id=operator_id,
                service_action="mark_as_paid",
                object_type="finance.financerecord",
            )
        except FinanceRecord.DoesNotExist:
            raise ResourceNotFoundException(f"Finance record with id {dto.record_id} not found")

        if record.status == FinanceRecord.Status.PAID:
            return record

        if record.status != FinanceRecord.Status.UNPAID:
            raise StateConflictException(
                f"Finance record must be in UNPAID status to mark as paid, current status: {record.status}"
            )

        before_data = serialize_instance(record, FinanceService.FINANCE_AUDIT_FIELDS)
        record.status = FinanceRecord.Status.PAID
        record.payment_method = dto.payment_method
        record.transaction_id = dto.transaction_id
        record.paid_at = timezone.now()
        record.save(update_fields=['status', 'payment_method', 'transaction_id', 'paid_at', 'updated_at'])
        BillingSchedule.objects.filter(finance_record=record).update(
            status=BillingSchedule.Status.PAID,
            updated_at=timezone.now(),
        )

        after_data = serialize_instance(record, FinanceService.FINANCE_AUDIT_FIELDS)
        log_audit_action(
            action="mark_finance_paid",
            module="finance",
            instance=record,
            actor_id=operator_id,
            before_data=before_data,
            after_data=after_data,
        )

        return record

    @staticmethod
    def get_pending_payments(contract_id: Optional[int] = None, tenant_id: int | None = None) -> List[FinanceRecord]:
        """
        获取待支付的财务记录

        Args:
            contract_id: 可选的合同ID，用于过滤特定合同的待支付记录

        Returns:
            待支付的财务记录列表
        """
        if contract_id and tenant_id is not None:
            try:
                contract = Contract.objects.get(id=contract_id)
                FinanceService._assert_tenant_access(
                    target_model="Contract",
                    target_id=contract.id,
                    actual_tenant_id=contract.tenant_id,
                    expected_tenant_id=tenant_id,
                    actor_id=None,
                    service_action="get_pending_payments",
                    object_type="store.contract",
                )
            except Contract.DoesNotExist:
                raise ResourceNotFoundException(f"Contract with id {contract_id} not found")

        queryset = FinanceRecord.objects.filter(status=FinanceRecord.Status.UNPAID)
        if tenant_id is not None:
            queryset = queryset.filter(tenant_id=tenant_id)
        
        if contract_id:
            queryset = queryset.filter(contract_id=contract_id)
            
        return list(queryset)

    @staticmethod
    def get_payment_history(
        contract_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        tenant_id: int | None = None,
    ) -> List[FinanceRecord]:
        """
        获取支付历史记录

        Args:
            contract_id: 可选的合同ID，用于过滤特定合同的支付记录
            start_date: 可选的开始日期
            end_date: 可选的结束日期

        Returns:
            已支付的财务记录列表
        """
        if contract_id and tenant_id is not None:
            try:
                contract = Contract.objects.get(id=contract_id)
                FinanceService._assert_tenant_access(
                    target_model="Contract",
                    target_id=contract.id,
                    actual_tenant_id=contract.tenant_id,
                    expected_tenant_id=tenant_id,
                    actor_id=None,
                    service_action="get_payment_history",
                    object_type="store.contract",
                )
            except Contract.DoesNotExist:
                raise ResourceNotFoundException(f"Contract with id {contract_id} not found")

        queryset = FinanceRecord.objects.filter(status=FinanceRecord.Status.PAID)
        if tenant_id is not None:
            queryset = queryset.filter(tenant_id=tenant_id)
        
        if contract_id:
            queryset = queryset.filter(contract_id=contract_id)
            
        if start_date:
            queryset = queryset.filter(paid_at__gte=start_date)
            
        if end_date:
            queryset = queryset.filter(paid_at__lte=end_date)
            
        return list(queryset.order_by('-paid_at'))

    @staticmethod
    def generate_payment_reminders(days_ahead: int = 7, tenant_id: int | None = None) -> List[FinanceRecord]:
        """
        生成缴费提醒

        Args:
            days_ahead: 提前提醒的天数

        Returns:
            需要提醒的财务记录列表，每个记录包含days_until_due属性
        """
        today = date.today()
        reminder_date = today + timedelta(days=days_ahead)
        
        # 查找在提醒日期范围内到期的未支付账单
        records = FinanceRecord.objects.filter(
            status=FinanceRecord.Status.UNPAID,
            billing_period_end__lte=reminder_date,
            billing_period_end__gte=today
        )
        if tenant_id is not None:
            records = records.filter(tenant_id=tenant_id)
        
        # 为每个记录添加剩余天数属性
        result = []
        for record in records:
            days_until_due = (record.billing_period_end - today).days
            # 为记录对象添加动态属性
            record.days_until_due = days_until_due
            result.append(record)
        
        return result

    @staticmethod
    def send_payment_reminder_notifications(days_ahead: int = 3, tenant_id: int | None = None) -> dict:
        """
        发送缴费提醒通知（系统消息和短信）
        
        业务流程：
        1. 查询即将到期的未支付账单
        2. 获取相关店铺的联系人和管理员
        3. 通过通知服务发送消息和短信
        4. 记录已发送的提醒，避免重复
        
        参数：
        - days_ahead: 提前多少天发送提醒（默认3天）
        
        返回：
        - 包含发送统计信息的字典
        """
        from apps.notification.services import NotificationService
        import logging
        
        logger = logging.getLogger(__name__)
        
        today = date.today()
        reminder_date = today + timedelta(days=days_ahead)
        
        # 查询待提醒的账单
        reminder_records = FinanceRecord.objects.filter(
            status=FinanceRecord.Status.UNPAID,
            billing_period_end__exact=reminder_date,
            reminder_sent=False  # 只发送未提醒过的
        ).select_related('contract', 'contract__shop')
        if tenant_id is not None:
            reminder_records = reminder_records.filter(tenant_id=tenant_id)
        
        result = {
            'total': 0,
            'notification_sent': 0,
            'sms_sent': 0,
            'failed': 0,
            'errors': []
        }
        
        for finance_record in reminder_records:
            result['total'] += 1
            
            try:
                # 获取店铺管理员或联系人信息
                shop = finance_record.contract.shop
                
                # 尝试获取店铺联系人对应的用户账户
                # 这里假设有一个关联的用户，实际可能需要根据联系人电话查询
                recipient_users = shop.user_set.all() if hasattr(shop, 'user_set') else []
                
                # 如果没有关联用户，使用第一个管理员
                if not recipient_users:
                    from django.contrib.auth.models import User
                    recipient_users = User.objects.filter(is_staff=True)
                    if tenant_id is not None:
                        recipient_users = recipient_users.filter(profile__tenant_id=tenant_id)
                    recipient_users = recipient_users[:1]
                
                for recipient in recipient_users:
                    # 计算剩余天数
                    days_until_due = (finance_record.billing_period_end - today).days
                    
                    try:
                        # 发送系统通知和短信
                        notification, sms_record = NotificationService.send_payment_reminder(
                            finance_record=finance_record,
                            recipient_id=recipient.id,
                            days_until_due=days_until_due
                        )
                        
                        result['notification_sent'] += 1
                        if sms_record:
                            result['sms_sent'] += 1
                        
                        logger.info(f"Payment reminder sent for FinanceRecord {finance_record.id}")
                        
                    except Exception as e:
                        result['failed'] += 1
                        error_msg = f"Failed to send reminder for FinanceRecord {finance_record.id}: {str(e)}"
                        result['errors'].append(error_msg)
                        logger.error(error_msg)
                
                # 标记已提醒
                finance_record.reminder_sent = True
                finance_record.save(update_fields=['reminder_sent'])
                
            except Exception as e:
                result['failed'] += 1
                error_msg = f"Error processing FinanceRecord {finance_record.id}: {str(e)}"
                result['errors'].append(error_msg)
                logger.error(error_msg)
        
        logger.info(f"Payment reminder batch completed: {result}")
        return result

    @staticmethod
    def send_overdue_payment_alert(days_overdue: int = 0, tenant_id: int | None = None) -> dict:
        """
        发送逾期支付告警通知
        
        业务流程：
        1. 查询已逾期的未支付账单
        2. 通过通知服务发送高优先级告警
        3. 记录告警日期和次数
        
        参数：
        - days_overdue: 查询多少天前开始逾期的账单（默认0表示任何逾期）
        
        返回：
        - 包含发送统计信息的字典
        """
        from apps.notification.services import NotificationService
        import logging
        
        logger = logging.getLogger(__name__)
        
        today = date.today()
        cutoff_date = today - timedelta(days=days_overdue)
        
        # 查询逾期账单
        overdue_records = FinanceRecord.objects.filter(
            status=FinanceRecord.Status.UNPAID,
            billing_period_end__lt=cutoff_date
        ).select_related('contract', 'contract__shop')
        if tenant_id is not None:
            overdue_records = overdue_records.filter(tenant_id=tenant_id)
        
        result = {
            'total': 0,
            'alert_sent': 0,
            'failed': 0,
            'errors': []
        }
        
        for finance_record in overdue_records:
            result['total'] += 1
            
            try:
                # 获取店铺管理员
                from django.contrib.auth.models import User
                admins = User.objects.filter(is_staff=True, is_superuser=True)
                if tenant_id is not None:
                    admins = admins.filter(profile__tenant_id=tenant_id)
                
                for admin in admins:
                    try:
                        days_overdue_count = (today - finance_record.billing_period_end).days
                        
                        # 发送告警通知
                        notification = NotificationService.create_notification(
                            recipient_id=admin.id,
                            notification_type='PAYMENT_OVERDUE',
                            title=f'【紧急】账单逾期提醒',
                            content=f'店铺"{finance_record.contract.shop.name}"的 {finance_record.get_fee_type_display()} 账单已逾期 {days_overdue_count} 天，'
                                   f'金额：¥{finance_record.amount}，应缴日期：{finance_record.billing_period_end}。请立即处理！',
                            related_model='FinanceRecord',
                            related_id=finance_record.id
                        )
                        result['alert_sent'] += 1
                        logger.warning(f"Overdue payment alert sent for FinanceRecord {finance_record.id}")
                        
                    except Exception as e:
                        result['failed'] += 1
                        error_msg = f"Failed to send overdue alert: {str(e)}"
                        result['errors'].append(error_msg)
                        logger.error(error_msg)
                        
            except Exception as e:
                result['failed'] += 1
                error_msg = f"Error processing overdue record {finance_record.id}: {str(e)}"
                result['errors'].append(error_msg)
                logger.error(error_msg)
        
        logger.info(f"Overdue payment alert batch completed: {result}")
        return result

    @staticmethod
    def generate_payment_receipt_pdf(
        finance_record_id: int,
        tenant_id: int | None = None,
        operator_id: int | None = None,
    ) -> bytes:
        """
        生成支付凭证PDF
        
        功能：
        1. 查询财务记录详情
        2. 加载收据模板（HTML/CSS）
        3. 渲染动态数据
        4. 转换为PDF格式
        5. 返回PDF二进制数据
        
        参数：
        - finance_record_id: 财务记录ID
        
        返回：
        - PDF文件的二进制内容
        
        异常：
        - ResourceNotFoundException: 记录不存在
        - Exception: PDF生成失败
        """
        import logging
        from django.template.loader import render_to_string
        from io import BytesIO
        
        logger = logging.getLogger(__name__)
        
        try:
            finance_record = FinanceRecord.objects.get(id=finance_record_id)
            FinanceService._assert_tenant_access(
                target_model="FinanceRecord",
                target_id=finance_record.id,
                actual_tenant_id=finance_record.tenant_id,
                expected_tenant_id=tenant_id,
                actor_id=operator_id,
                service_action="generate_payment_receipt_pdf",
                object_type="finance.financerecord",
            )
        except FinanceRecord.DoesNotExist:
            raise ResourceNotFoundException(
                message=f"财务记录 ID {finance_record_id} 不存在",
                override_error_code="RESOURCE_NOT_FOUND",
                data={"target_model": "FinanceRecord", "target_id": finance_record_id}
            )
        
        try:
            # 准备PDF内容的上下文数据
            context = {
                'finance_record': finance_record,
                'contract': finance_record.contract,
                'shop': finance_record.contract.shop,
                'generated_at': timezone.now(),
                'company_name': '商场管理公司',  # 可配置
                'company_phone': '400-XXX-XXXX',  # 可配置
                'company_address': '城市中心商场',  # 可配置
            }
            
            # 渲染HTML模板
            html_content = render_to_string(
                'finance/receipt_template.html',
                context
            )
            
            # 尝试使用 WeasyPrint 或 ReportLab 生成PDF
            try:
                from weasyprint import HTML, CSS
                
                # 使用 WeasyPrint 从HTML生成PDF
                pdf_file = BytesIO()
                HTML(string=html_content).write_pdf(pdf_file)
                pdf_file.seek(0)
                
                logger.info(f"PDF receipt generated for finance record {finance_record_id} using WeasyPrint")
                return pdf_file.getvalue()
                
            except ImportError:
                # 如果WeasyPrint不可用，使用reportlab
                logger.warning("WeasyPrint not available, attempting to use ReportLab")
                return FinanceService._generate_pdf_with_reportlab(context, finance_record)
        
        except Exception as e:
            logger.error(f"Error generating PDF receipt: {str(e)}")
            raise
    
    @staticmethod
    def _generate_pdf_with_reportlab(context: dict, finance_record: FinanceRecord) -> bytes:
        """
        使用 ReportLab 生成PDF凭证
        
        这是一个备选方案，当WeasyPrint不可用时使用
        """
        from io import BytesIO
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch, cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # 创建PDF缓冲区
            pdf_buffer = BytesIO()
            
            # 创建PDF文档（A4纸张）
            doc = SimpleDocTemplate(
                pdf_buffer,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            # 获取样式
            styles = getSampleStyleSheet()
            
            # 自定义样式
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#333333'),
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#666666'),
                spaceAfter=12,
                fontName='Helvetica-Bold'
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=10,
                leading=14
            )
            
            # 构建PDF内容
            story = []
            
            # 1. 标题
            story.append(Paragraph('缴费凭证', title_style))
            story.append(Spacer(1, 0.3*inch))
            
            # 2. 基本信息表格
            info_data = [
                ['凭证编号：', str(finance_record.id)],
                ['店铺名称：', finance_record.contract.shop.name],
                ['费用类型：', finance_record.get_fee_type_display()],
                ['账单周期：', f"{finance_record.billing_period_start} 至 {finance_record.billing_period_end}"],
                ['应缴截止日期：', str(finance_record.billing_period_end)],
            ]
            
            info_table = Table(info_data, colWidths=[2*inch, 4*inch])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F5F5')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 0.3*inch))
            
            # 3. 金额信息
            story.append(Paragraph('缴费金额', heading_style))
            
            amount_data = [
                ['项目', '金额'],
                [finance_record.get_fee_type_display(), f'¥ {finance_record.amount}'],
            ]
            
            if finance_record.status == FinanceRecord.Status.PAID:
                amount_data.append(['已缴金额', f'¥ {finance_record.amount}'])
                amount_data.append(['缴费日期', str(finance_record.paid_at.date())])
                amount_data.append(['缴费方式', finance_record.get_payment_method_display() or '其他'])
            else:
                amount_data.append(['应缴金额', f'¥ {finance_record.amount}'])
            
            amount_table = Table(amount_data, colWidths=[3*inch, 3*inch])
            amount_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#666666')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFFFFF')),
            ]))
            
            story.append(amount_table)
            story.append(Spacer(1, 0.4*inch))
            
            # 4. 备注
            story.append(Paragraph('备注', heading_style))
            story.append(Paragraph(
                '此凭证为财务记录凭证，请妥善保管。如有疑问，请联系财务部门。',
                normal_style
            ))
            story.append(Spacer(1, 0.5*inch))
            
            # 5. 页脚
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.HexColor('#999999'),
                alignment=TA_CENTER
            )
            story.append(Paragraph(
                f"生成时间：{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}&nbsp;&nbsp;"
                f"系统自动生成，无需签字",
                footer_style
            ))
            
            # 构建PDF
            doc.build(story)
            
            pdf_data = pdf_buffer.getvalue()
            pdf_buffer.close()
            
            logger.info(f"PDF receipt generated for finance record {finance_record.id} using ReportLab")
            return pdf_data
            
        except Exception as e:
            logger.error(f"Error generating PDF with ReportLab: {str(e)}")
            raise
    
    @staticmethod
    def batch_generate_payment_receipts(
        finance_record_ids: List[int],
        tenant_id: int | None = None,
        operator_id: int | None = None,
    ) -> dict:
        """
        批量生成支付凭证PDF
        
        参数：
        - finance_record_ids: 财务记录ID列表
        
        返回：
        - 包含生成结果的字典
        """
        import logging
        logger = logging.getLogger(__name__)
        
        result = {
            'total': len(finance_record_ids),
            'success': 0,
            'failed': 0,
            'failed_ids': [],
            'generated_files': {}
        }
        
        for record_id in finance_record_ids:
            try:
                pdf_content = FinanceService.generate_payment_receipt_pdf(
                    record_id,
                    tenant_id=tenant_id,
                    operator_id=operator_id,
                )
                result['success'] += 1
                result['generated_files'][record_id] = pdf_content
                logger.info(f"Successfully generated PDF for finance record {record_id}")
                
            except Exception as e:
                result['failed'] += 1
                result['failed_ids'].append({
                    'record_id': record_id,
                    'error': str(e)
                })
                logger.error(f"Failed to generate PDF for finance record {record_id}: {str(e)}")
        
        return result
