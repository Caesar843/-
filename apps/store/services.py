import logging
import hashlib
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone
from datetime import date, datetime, timedelta

from apps.core.exceptions import (
    BusinessValidationError,
    ResourceNotFoundException,
    StateConflictException
)
# 暂时注释掉OperationLog导入，因为apps.core.models不存在
# from apps.core.models import OperationLog
from apps.store.models import (
    Shop,
    Contract,
    ContractItem,
    ContractAttachment,
    ContractSignature,
    ContractNumberSequence,
    ApprovalFlowConfig,
    ApprovalTask,
)
from apps.store.dtos import (
    ShopCreateDTO,
    ContractCreateDTO,
    ContractActivateDTO
)
from apps.audit.services import log_audit_action
from apps.audit.utils import serialize_instance

logger = logging.getLogger(__name__)

SHOP_AUDIT_FIELDS = [
    "id",
    "name",
    "business_type",
    "area",
    "rent",
    "contact_person",
    "contact_phone",
    "entry_date",
    "description",
    "is_deleted",
]

CONTRACT_AUDIT_FIELDS = [
    "id",
    "shop_id",
    "contract_no",
    "start_date",
    "end_date",
    "monthly_rent",
    "deposit",
    "payment_cycle",
    "status",
    "reviewed_by_id",
    "reviewed_at",
    "review_comment",
    "is_archived",
    "archived_at",
    "archived_by_id",
]

APPROVAL_TASK_AUDIT_FIELDS = [
    "id",
    "tenant_id",
    "contract_id",
    "flow_config_id",
    "round_no",
    "order_no",
    "node_name",
    "approver_role",
    "assigned_to_id",
    "acted_by_id",
    "status",
    "comment",
    "sla_due_at",
    "acted_at",
]

CONTRACT_ITEM_AUDIT_FIELDS = [
    "id",
    "tenant_id",
    "contract_id",
    "item_type",
    "calc_type",
    "amount",
    "rate",
    "tax_rate",
    "currency",
    "period_start",
    "period_end",
    "payment_cycle",
    "free_rent_from",
    "free_rent_to",
    "sequence",
    "status",
]

CONTRACT_ATTACHMENT_AUDIT_FIELDS = [
    "id",
    "tenant_id",
    "contract_id",
    "attachment_type",
    "file",
    "original_name",
    "mime_type",
    "file_size",
    "file_hash",
    "version_no",
    "is_current",
    "remark",
    "uploaded_by_id",
]

CONTRACT_SIGNATURE_AUDIT_FIELDS = [
    "id",
    "tenant_id",
    "contract_id",
    "party_type",
    "signer_name",
    "signer_title",
    "sign_method",
    "signed_at",
    "attachment_id",
    "evidence_hash",
    "comment",
    "created_by_id",
]

"""
Service Layer Architecture & Engineering Constraints
----------------------------------------------------
[架构声明]
1. 事务与并发：
   - 本项目严格依赖数据库事务隔离级别（Read Committed）与行级锁（Row-Level Lock）。
   - 所有并发写操作必须通过 transaction.atomic + select_for_update 完成。
2. 异常边界：
   - Service 层仅允许主动抛出 apps.core.exceptions 中定义的业务异常。
   - 禁止捕获 ORM 或 Python 原生异常。
3. 数据来源：
   - 严禁直接访问 HTTP Request。
   - 所有业务数据必须来自 DTO。
"""


class StoreService:
    """
    店铺业务服务层
    """

    def create_shop(self, dto: ShopCreateDTO, operator_id: int) -> Shop:
        """
        创建新店铺
        """
        # 1. 业务规则校验（同名检查）
        if Shop.objects.filter(name=dto.name, is_deleted=False).exists():
            raise BusinessValidationError(
                message=f"店铺名称 '{dto.name}' 已存在",
                override_error_code="SHOP_NAME_CONFLICT",
                data={
                    "field": "name",
                    "target_model": "Shop",
                    "value": dto.name
                }
            )

        with transaction.atomic():
            # 2. 执行数据库 Insert
            shop = Shop.objects.create(
                name=dto.name,
                business_type=dto.business_type,
                area=dto.area,
                rent=dto.rent,
                contact_person=dto.contact_person,
                contact_phone=dto.contact_phone,
                entry_date=dto.entry_date,
                description=dto.description,
                is_deleted=False
            )

            # 3. 写入审计日志
            # 暂时注释掉OperationLog创建，因为apps.core.models不存在
            # OperationLog.objects.create(
            #     operator_id=operator_id,
            #     target_model='Shop',
            #     target_id=str(shop.id),
            #     action_type='CREATE',
            #     details={
            #         "name": shop.name,
            #         "area": str(shop.area),
            #         "is_deleted": False
            #     }
            # )

            after_data = serialize_instance(shop, SHOP_AUDIT_FIELDS)
            log_audit_action(
                action="create_shop",
                module="store",
                instance=shop,
                actor_id=operator_id,
                before_data=None,
                after_data=after_data,
            )

            logger.info(f"Shop {shop.id} created by operator {operator_id}")
            return shop

    def delete_shop(self, shop_id: int, operator_id: int, tenant_id: int | None = None) -> None:
        """
        删除店铺（逻辑删除）
        """
        with transaction.atomic():
            # 1. 锁定并查询 Shop
            try:
                shop = Shop.objects.select_for_update().get(id=shop_id)
                if tenant_id is not None and int(shop.tenant_id) != int(tenant_id):
                    logger.warning(
                        "Cross-tenant access blocked: Shop id=%s actor=%s expected_tenant=%s actual_tenant=%s action=delete_shop",
                        shop_id,
                        operator_id,
                        tenant_id,
                        shop.tenant_id,
                    )
                    log_audit_action(
                        action="cross_tenant_access_blocked",
                        module="store",
                        object_type="store.shop",
                        object_id=str(shop_id),
                        actor_id=operator_id,
                        before_data={"actual_tenant_id": shop.tenant_id},
                        after_data={
                            "expected_tenant_id": tenant_id,
                            "service_action": "delete_shop",
                        },
                    )
                    raise ResourceNotFoundException(
                        message=f"Shop ID {shop_id} not found",
                        override_error_code="RESOURCE_NOT_FOUND",
                        data={"target_model": "Shop", "target_id": shop_id},
                    )
            except Shop.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"店铺 ID {shop_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "Shop", "target_id": shop_id}
                )

            # 2. 检查店铺是否已被删除
            if shop.is_deleted:
                raise BusinessValidationError(
                    message=f"店铺 ID {shop_id} 已删除",
                    override_error_code="SHOP_ALREADY_DELETED",
                    data={"target_model": "Shop", "target_id": shop_id}
                )

            # 3. 检查店铺是否有关联的活跃合同
            from apps.store.models import Contract
            active_contracts = shop.contracts.filter(
                status__in=[Contract.Status.DRAFT, Contract.Status.ACTIVE]
            )
            if active_contracts.exists():
                raise BusinessValidationError(
                    message="该店铺有关联的活跃合同，无法删除",
                    override_error_code="SHOP_HAS_ACTIVE_CONTRACTS",
                    data={"target_model": "Shop", "target_id": shop_id}
                )

            # 4. 执行逻辑删除
            before_data = serialize_instance(shop, SHOP_AUDIT_FIELDS)
            shop.is_deleted = True
            shop.save(update_fields=['is_deleted', 'updated_at'])

            # 5. 写入审计日志
            # 暂时注释掉OperationLog创建，因为apps.core.models不存在
            # OperationLog.objects.create(
            #     operator_id=operator_id,
            #     target_model='Shop',
            #     target_id=str(shop.id),
            #     action_type='DELETE',
            #     details={
            #         "shop_id": shop.id,
            #         "shop_name": shop.name,
            #         "is_deleted": True
            #     }
            # )

            after_data = serialize_instance(shop, SHOP_AUDIT_FIELDS)
            log_audit_action(
                action="delete_shop",
                module="store",
                instance=shop,
                actor_id=operator_id,
                before_data=before_data,
                after_data=after_data,
            )

            logger.info(f"Shop {shop.id} deleted by operator {operator_id}")
            return None

    def export_shops(self, format: str = 'csv') -> str:
        """
        导出店铺信息
        """
        import csv
        from io import StringIO
        
        # 获取所有未删除的店铺
        shops = Shop.objects.filter(is_deleted=False)
        
        # 创建CSV文件
        output = StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow(['店铺ID', '店铺名称', '业态类型', '经营面积', '租金', '联系人', '联系方式', '入驻日期', '描述', '创建时间', '更新时间'])
        
        # 写入数据
        for shop in shops:
            writer.writerow([
                shop.id,
                shop.name,
                shop.get_business_type_display(),
                shop.area,
                shop.rent,
                shop.contact_person or '',
                shop.contact_phone or '',
                shop.entry_date.strftime('%Y-%m-%d') if shop.entry_date else '',
                shop.description or '',
                shop.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                shop.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return output.getvalue()
    
    def import_shops(self, file_content: str, operator_id: int) -> dict:
        """
        批量导入店铺信息
        """
        import csv
        from io import StringIO
        from decimal import Decimal
        from datetime import datetime

        def _sanitize_csv_cell(value: str) -> str:
            if not value:
                return value
            trimmed = value.strip()
            if trimmed and trimmed[0] in ('=', '+', '-', '@'):
                return "'" + trimmed
            return value

        
        # 初始化导入结果
        result = {
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }
        
        # 解析CSV文件
        reader = csv.DictReader(StringIO(file_content))
        
        # 验证表头
        required_fields = ['店铺名称', '业态类型', '经营面积', '租金']
        header_fields = reader.fieldnames
        
        for field in required_fields:
            if field not in header_fields:
                raise BusinessValidationError(
                    message=f'CSV文件缺少必要字段: {field}',
                    override_error_code='MISSING_REQUIRED_FIELD',
                    data={'field': field}
                )
        
        # 处理每一行数据
        for row_num, row in enumerate(reader, start=2):  # 行号从2开始（跳过表头）
            row = {k: _sanitize_csv_cell(v) if isinstance(v, str) else v for k, v in row.items()}
            try:
                # 提取数据
                name = row.get('店铺名称', '').strip()
                business_type = row.get('业态类型', '').strip()
                area_str = row.get('经营面积', '').strip()
                rent_str = row.get('租金', '').strip()
                contact_person = row.get('联系人', '').strip() or None
                contact_phone = row.get('联系方式', '').strip() or None
                entry_date_str = row.get('入驻日期', '').strip()
                description = row.get('描述', '').strip() or None
                
                # 验证必填字段
                if not name:
                    raise BusinessValidationError(message='店铺名称不能为空', data={'field': 'name'})
                if not business_type:
                    raise BusinessValidationError(message='业态类型不能为空', data={'field': 'business_type'})
                if not area_str:
                    raise BusinessValidationError(message='经营面积不能为空', data={'field': 'area'})
                if not rent_str:
                    raise BusinessValidationError(message='租金不能为空', data={'field': 'rent'})
                
                # 转换数据类型
                area = Decimal(area_str)
                rent = Decimal(rent_str)
                
                # 验证数值
                if area <= 0:
                    raise BusinessValidationError(message='经营面积必须大于0', data={'field': 'area'})
                if rent <= 0:
                    raise BusinessValidationError(message='租金必须大于0', data={'field': 'rent'})
                
                # 处理入驻日期
                entry_date = None
                if entry_date_str:
                    try:
                        entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()
                    except ValueError:
                        raise BusinessValidationError(message='入驻日期格式错误，应为YYYY-MM-DD', data={'field': 'entry_date'})
                
                # 检查店铺名称是否已存在
                if Shop.objects.filter(name=name, is_deleted=False).exists():
                    raise BusinessValidationError(message=f'店铺名称 "{name}" 已存在', data={'field': 'name'})
                
                # 处理业态类型映射
                business_type_map = {
                    '零售': 'RETAIL',
                    '餐饮': 'FOOD',
                    '娱乐': 'ENTERTAINMENT',
                    '服务': 'SERVICE',
                    '其他': 'OTHER'
                }
                
                if business_type in business_type_map:
                    business_type_code = business_type_map[business_type]
                else:
                    # 如果不是标准类型，使用OTHER
                    business_type_code = 'OTHER'
                
                # 创建店铺
                shop = Shop.objects.create(
                    name=name,
                    business_type=business_type_code,
                    area=area,
                    rent=rent,
                    contact_person=contact_person,
                    contact_phone=contact_phone,
                    entry_date=entry_date,
                    description=description,
                    is_deleted=False
                )
                
                result['success_count'] += 1
                
            except Exception as e:
                result['error_count'] += 1
                result['errors'].append(f'第 {row_num} 行: {str(e)}')
        
        return result


class ContractService:
    """
    合同业务服务层
    """

    ALLOWED_STATUS_TRANSITIONS = {
        Contract.Status.DRAFT: {Contract.Status.PENDING_REVIEW},
        Contract.Status.PENDING_REVIEW: {Contract.Status.APPROVED, Contract.Status.REJECTED},
        Contract.Status.APPROVED: {Contract.Status.ACTIVE},
        Contract.Status.ACTIVE: {Contract.Status.EXPIRED, Contract.Status.TERMINATED},
        Contract.Status.REJECTED: {Contract.Status.DRAFT},
        Contract.Status.EXPIRED: set(),
        Contract.Status.TERMINATED: set(),
    }

    def _ensure_contract_status_transition(self, contract: Contract, target_status: str) -> None:
        """
        Validate contract status transition using a unified state-machine map.
        """
        current_status = contract.status
        allowed_next_statuses = self.ALLOWED_STATUS_TRANSITIONS.get(current_status, set())

        if target_status in allowed_next_statuses:
            return

        if current_status == target_status:
            message = f"Contract is already in status {target_status}"
        else:
            message = f"Invalid contract status transition: {current_status} -> {target_status}"

        raise StateConflictException(
            message=message,
            override_error_code="CONTRACT_STATUS_CONFLICT",
            data={
                "target_model": "Contract",
                "target_id": contract.id,
                "current_status": str(current_status),
                "target_status": str(target_status),
                "allowed_next_statuses": sorted([str(item) for item in allowed_next_statuses]),
            },
        )

    def _assert_tenant_access(
        self,
        *,
        target_model: str,
        target_id: int,
        actual_tenant_id: int,
        expected_tenant_id: int | None,
        actor_id: int | None,
        module: str,
        object_type: str,
        service_action: str,
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
            module=module,
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
            message=f"{target_model} ID {target_id} not found",
            override_error_code="RESOURCE_NOT_FOUND",
            data={
                "target_model": target_model,
                "target_id": target_id,
            },
        )

    def _get_latest_approval_round(self, contract_id: int) -> int:
        latest = (
            ApprovalTask.objects.filter(contract_id=contract_id)
            .order_by("-round_no")
            .values_list("round_no", flat=True)
            .first()
        )
        return int(latest or 0)

    def _build_approval_tasks_for_contract(self, contract: Contract, operator_id: int | None = None) -> int:
        flow_nodes = list(
            ApprovalFlowConfig.objects.filter(
                tenant_id=contract.tenant_id,
                target_type=ApprovalFlowConfig.TargetType.CONTRACT,
                is_active=True,
            ).order_by("order_no", "id")
        )
        if not flow_nodes:
            raise BusinessValidationError(
                message="审批流程未配置，请先在后台配置审批节点",
                override_error_code="APPROVAL_FLOW_NOT_CONFIGURED",
                data={
                    "target_model": "ApprovalFlowConfig",
                    "tenant_id": contract.tenant_id,
                },
            )

        round_no = self._get_latest_approval_round(contract.id) + 1
        for node in flow_nodes:
            due_at = None
            if node.sla_hours:
                due_at = timezone.now() + timedelta(hours=int(node.sla_hours))

            task = ApprovalTask.objects.create(
                tenant_id=contract.tenant_id,
                contract=contract,
                flow_config=node,
                round_no=round_no,
                order_no=node.order_no,
                node_name=node.node_name,
                approver_role=node.approver_role,
                assigned_to=node.approver,
                status=ApprovalTask.Status.PENDING,
                sla_due_at=due_at,
            )
            after_data = serialize_instance(task, APPROVAL_TASK_AUDIT_FIELDS)
            log_audit_action(
                action="create_approval_task",
                module="contract",
                instance=contract,
                actor_id=operator_id,
                before_data=None,
                after_data=after_data,
            )
        return round_no

    def _get_current_pending_task(self, contract_id: int) -> ApprovalTask:
        latest_round = self._get_latest_approval_round(contract_id)
        task = (
            ApprovalTask.objects.select_for_update()
            .filter(
                contract_id=contract_id,
                round_no=latest_round,
                status=ApprovalTask.Status.PENDING,
            )
            .order_by("order_no", "id")
            .first()
        )
        if not task:
            raise StateConflictException(
                message="当前合同没有待处理的审批节点",
                override_error_code="APPROVAL_TASK_NOT_FOUND",
                data={
                    "target_model": "ApprovalTask",
                    "contract_id": contract_id,
                    "round_no": latest_round,
                },
            )
        return task

    @staticmethod
    def _resolve_reviewer_role_type(reviewer) -> str | None:
        return getattr(getattr(getattr(reviewer, "profile", None), "role", None), "role_type", None)

    def _assert_task_reviewer_permission(self, task: ApprovalTask, reviewer) -> None:
        if reviewer.is_superuser:
            return

        if task.assigned_to_id and reviewer.id != task.assigned_to_id:
            log_audit_action(
                action="approval_task_permission_denied",
                module="contract",
                instance=task.contract,
                actor_id=reviewer.id,
                before_data={
                    "task_id": task.id,
                    "assigned_to_id": task.assigned_to_id,
                },
                after_data={
                    "reviewer_id": reviewer.id,
                    "reason": "assigned_reviewer_mismatch",
                },
            )
            raise BusinessValidationError(
                message="当前审批节点已指定审批人，您无权处理",
                override_error_code="APPROVAL_TASK_PERMISSION_DENIED",
                data={
                    "target_model": "ApprovalTask",
                    "target_id": task.id,
                    "assigned_to_id": task.assigned_to_id,
                    "reviewer_id": reviewer.id,
                },
            )

        role_type = self._resolve_reviewer_role_type(reviewer)
        if task.approver_role and role_type != task.approver_role:
            log_audit_action(
                action="approval_task_role_mismatch",
                module="contract",
                instance=task.contract,
                actor_id=reviewer.id,
                before_data={
                    "task_id": task.id,
                    "required_role": task.approver_role,
                },
                after_data={
                    "reviewer_id": reviewer.id,
                    "actual_role": role_type,
                    "reason": "role_mismatch",
                },
            )
            raise BusinessValidationError(
                message=f"当前节点需 {task.approver_role} 角色审批",
                override_error_code="APPROVAL_TASK_ROLE_MISMATCH",
                data={
                    "target_model": "ApprovalTask",
                    "target_id": task.id,
                    "required_role": task.approver_role,
                    "actual_role": role_type,
                },
            )

    def _next_contract_sequence(self, tenant, year: int) -> int:
        """
        Reserve and return the next per-tenant annual sequence number.
        """
        sequence = (
            ContractNumberSequence.objects.select_for_update()
            .filter(tenant=tenant, year=year)
            .first()
        )
        if sequence is None:
            try:
                sequence = ContractNumberSequence.objects.create(
                    tenant=tenant,
                    year=year,
                    last_seq=0,
                )
            except IntegrityError:
                sequence = (
                    ContractNumberSequence.objects.select_for_update()
                    .get(tenant=tenant, year=year)
                )
        sequence.last_seq += 1
        sequence.save(update_fields=["last_seq", "updated_at"])
        return sequence.last_seq

    def _generate_contract_no(self, tenant, start_date: date) -> str:
        """
        Generate contract number using tenant code + year + sequence.
        Format: CT-{TENANT}-{YYYY}-{NNNNNN}
        """
        year = int(start_date.year)
        sequence = self._next_contract_sequence(tenant, year)
        tenant_code = (getattr(tenant, "code", "") or "default").upper()
        return f"CT-{tenant_code}-{year}-{sequence:06d}"

    def _create_contract_item(
        self,
        *,
        contract: Contract,
        item_type: str,
        calc_type: str,
        amount,
        payment_cycle: str,
        sequence: int,
        operator_id: int | None,
        period_start: date | None = None,
        period_end: date | None = None,
        rate=None,
        free_rent_from: date | None = None,
        free_rent_to: date | None = None,
    ) -> ContractItem:
        item = ContractItem.objects.create(
            tenant_id=contract.tenant_id,
            contract=contract,
            item_type=item_type,
            calc_type=calc_type,
            amount=amount,
            rate=rate,
            payment_cycle=payment_cycle,
            period_start=period_start,
            period_end=period_end,
            free_rent_from=free_rent_from,
            free_rent_to=free_rent_to,
            sequence=sequence,
            status=ContractItem.Status.ACTIVE,
        )
        log_audit_action(
            action="create_contract_item",
            module="contract",
            instance=contract,
            actor_id=operator_id,
            before_data=None,
            after_data=serialize_instance(item, CONTRACT_ITEM_AUDIT_FIELDS),
        )
        return item

    def _ensure_default_contract_items(self, contract: Contract, operator_id: int | None = None) -> None:
        if ContractItem.objects.filter(contract=contract).exists():
            return

        self._create_contract_item(
            contract=contract,
            item_type=ContractItem.ItemType.RENT,
            calc_type=ContractItem.CalcType.FIXED,
            amount=contract.monthly_rent,
            payment_cycle=contract.payment_cycle,
            period_start=contract.start_date,
            period_end=contract.end_date,
            sequence=1,
            operator_id=operator_id,
        )
        if contract.deposit and contract.deposit > 0:
            self._create_contract_item(
                contract=contract,
                item_type=ContractItem.ItemType.DEPOSIT,
                calc_type=ContractItem.CalcType.FIXED,
                amount=contract.deposit,
                payment_cycle=ContractItem.PaymentCycle.ONE_TIME,
                period_start=contract.start_date,
                period_end=contract.start_date,
                sequence=2,
                operator_id=operator_id,
            )

    def _clone_contract_items(
        self,
        *,
        source_contract: Contract,
        target_contract: Contract,
        operator_id: int | None = None,
    ) -> None:
        source_items = list(
            ContractItem.objects.filter(contract=source_contract).order_by("sequence", "id")
        )
        if not source_items:
            self._ensure_default_contract_items(target_contract, operator_id=operator_id)
            return

        for source_item in source_items:
            if source_item.item_type == ContractItem.ItemType.DEPOSIT:
                period_start = target_contract.start_date
                period_end = target_contract.start_date
                payment_cycle = ContractItem.PaymentCycle.ONE_TIME
            else:
                period_start = target_contract.start_date
                period_end = target_contract.end_date
                payment_cycle = source_item.payment_cycle

            self._create_contract_item(
                contract=target_contract,
                item_type=source_item.item_type,
                calc_type=source_item.calc_type,
                amount=source_item.amount,
                payment_cycle=payment_cycle,
                period_start=period_start,
                period_end=period_end,
                sequence=source_item.sequence,
                rate=source_item.rate,
                free_rent_from=source_item.free_rent_from,
                free_rent_to=source_item.free_rent_to,
                operator_id=operator_id,
            )

    @staticmethod
    def _compute_file_sha256(uploaded_file) -> str:
        digest = hashlib.sha256()
        for chunk in uploaded_file.chunks():
            digest.update(chunk)
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        return digest.hexdigest()

    def add_contract_attachment(
        self,
        *,
        contract_id: int,
        operator_id: int,
        attachment_type: str,
        uploaded_file,
        remark: str = "",
        tenant_id: int | None = None,
    ) -> ContractAttachment:
        from django.contrib.auth.models import User

        with transaction.atomic():
            try:
                contract = Contract.objects.select_for_update().get(id=contract_id)
                self._assert_tenant_access(
                    target_model="Contract",
                    target_id=contract.id,
                    actual_tenant_id=contract.tenant_id,
                    expected_tenant_id=tenant_id,
                    actor_id=operator_id,
                    module="contract",
                    object_type="store.contract",
                    service_action="add_contract_attachment",
                )
            except Contract.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"合同 ID {contract_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "Contract", "target_id": contract_id},
                )

            valid_attachment_types = {choice[0] for choice in ContractAttachment.AttachmentType.choices}
            if attachment_type not in valid_attachment_types:
                raise BusinessValidationError(
                    message="不支持的附件类型",
                    override_error_code="CONTRACT_ATTACHMENT_TYPE_INVALID",
                    data={"attachment_type": attachment_type},
                )
            if not uploaded_file:
                raise BusinessValidationError(
                    message="请上传附件文件",
                    override_error_code="CONTRACT_ATTACHMENT_FILE_REQUIRED",
                    data={"target_model": "ContractAttachment"},
                )

            try:
                operator = User.objects.get(id=operator_id)
            except User.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"用户 ID {operator_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "User", "target_id": operator_id},
                )

            current_items = ContractAttachment.objects.select_for_update().filter(
                contract=contract,
                attachment_type=attachment_type,
            )
            latest_version = current_items.aggregate(max_version=Max("version_no")).get("max_version") or 0
            current_items.filter(is_current=True).update(is_current=False, updated_at=timezone.now())

            file_hash = self._compute_file_sha256(uploaded_file)
            attachment = ContractAttachment.objects.create(
                tenant_id=contract.tenant_id,
                contract=contract,
                attachment_type=attachment_type,
                file=uploaded_file,
                original_name=getattr(uploaded_file, "name", "") or "attachment",
                mime_type=getattr(uploaded_file, "content_type", "") or "",
                file_size=getattr(uploaded_file, "size", 0) or 0,
                file_hash=file_hash,
                version_no=int(latest_version) + 1,
                is_current=True,
                remark=(remark or "").strip() or None,
                uploaded_by=operator,
            )
            log_audit_action(
                action="upload_contract_attachment",
                module="contract",
                instance=contract,
                actor_id=operator_id,
                before_data=None,
                after_data=serialize_instance(attachment, CONTRACT_ATTACHMENT_AUDIT_FIELDS),
            )
            return attachment

    def add_contract_signature(
        self,
        *,
        contract_id: int,
        operator_id: int,
        party_type: str,
        signer_name: str,
        sign_method: str,
        signed_at,
        attachment_id: int | None = None,
        evidence_hash: str = "",
        comment: str = "",
        signer_title: str = "",
        tenant_id: int | None = None,
    ) -> ContractSignature:
        from django.contrib.auth.models import User

        with transaction.atomic():
            try:
                contract = Contract.objects.select_for_update().get(id=contract_id)
                self._assert_tenant_access(
                    target_model="Contract",
                    target_id=contract.id,
                    actual_tenant_id=contract.tenant_id,
                    expected_tenant_id=tenant_id,
                    actor_id=operator_id,
                    module="contract",
                    object_type="store.contract",
                    service_action="add_contract_signature",
                )
            except Contract.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"合同 ID {contract_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "Contract", "target_id": contract_id},
                )

            if not signer_name or not signer_name.strip():
                raise BusinessValidationError(
                    message="签署人不能为空",
                    override_error_code="CONTRACT_SIGNATURE_SIGNER_REQUIRED",
                    data={"target_model": "ContractSignature"},
                )
            valid_party_types = {choice[0] for choice in ContractSignature.PartyType.choices}
            if party_type not in valid_party_types:
                raise BusinessValidationError(
                    message="不支持的签署方类型",
                    override_error_code="CONTRACT_SIGNATURE_PARTY_INVALID",
                    data={"party_type": party_type},
                )
            valid_sign_methods = {choice[0] for choice in ContractSignature.SignMethod.choices}
            if sign_method not in valid_sign_methods:
                raise BusinessValidationError(
                    message="不支持的签署方式",
                    override_error_code="CONTRACT_SIGNATURE_METHOD_INVALID",
                    data={"sign_method": sign_method},
                )
            if evidence_hash and len(evidence_hash.strip()) != 64:
                raise BusinessValidationError(
                    message="签署证据哈希长度必须为 64 位",
                    override_error_code="CONTRACT_SIGNATURE_HASH_INVALID",
                    data={"evidence_hash": evidence_hash},
                )

            try:
                operator = User.objects.get(id=operator_id)
            except User.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"用户 ID {operator_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "User", "target_id": operator_id},
                )

            attachment = None
            if attachment_id:
                try:
                    attachment = ContractAttachment.objects.select_for_update().get(
                        id=attachment_id,
                        contract_id=contract.id,
                    )
                except ContractAttachment.DoesNotExist:
                    raise ResourceNotFoundException(
                        message=f"附件 ID {attachment_id} 不存在",
                        override_error_code="RESOURCE_NOT_FOUND",
                        data={"target_model": "ContractAttachment", "target_id": attachment_id},
                    )

            signature = ContractSignature.objects.create(
                tenant_id=contract.tenant_id,
                contract=contract,
                party_type=party_type,
                signer_name=signer_name.strip(),
                signer_title=(signer_title or "").strip() or None,
                sign_method=sign_method,
                signed_at=signed_at or timezone.now(),
                attachment=attachment,
                evidence_hash=((evidence_hash or "").strip() or (attachment.file_hash if attachment else None)),
                comment=(comment or "").strip() or None,
                created_by=operator,
            )
            log_audit_action(
                action="create_contract_signature",
                module="contract",
                instance=contract,
                actor_id=operator_id,
                before_data=None,
                after_data=serialize_instance(signature, CONTRACT_SIGNATURE_AUDIT_FIELDS),
            )
            return signature

    def create_draft_contract(self, dto: ContractCreateDTO, operator_id: int, tenant_id: int | None = None) -> Contract:
        """
        创建合同草稿
        """
        # 1. 边界条件校验
        if dto.start_date >= dto.end_date:
            raise BusinessValidationError(
                message="合同结束日期必须晚于开始日期",
                override_error_code="INVALID_DATE_RANGE",
                data={
                    "target_model": "Contract",
                    "start_date": str(dto.start_date),
                    "end_date": str(dto.end_date)
                }
            )

        with transaction.atomic():
            # 2. 锁定并查询 Shop（防止并发删除）
            try:
                shop = Shop.objects.select_for_update().get(id=dto.shop_id)
                self._assert_tenant_access(
                    target_model="Shop",
                    target_id=shop.id,
                    actual_tenant_id=shop.tenant_id,
                    expected_tenant_id=tenant_id,
                    actor_id=operator_id,
                    module="store",
                    object_type="store.shop",
                    service_action="create_draft_contract",
                )
            except Shop.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"店铺 ID {dto.shop_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "Shop", "target_id": dto.shop_id}
                )

            # 3. 校验 Shop 状态
            if shop.is_deleted:
                raise ResourceNotFoundException(
                    message=f"店铺 ID {dto.shop_id} 已删除，无法创建合同",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "Shop", "target_id": dto.shop_id}
                )

            # 4. 执行 Contract Insert
            contract_no = self._generate_contract_no(shop.tenant, dto.start_date)
            contract = Contract.objects.create(
                shop=shop,
                contract_no=contract_no,
                start_date=dto.start_date,
                end_date=dto.end_date,
                monthly_rent=dto.monthly_rent,
                deposit=dto.deposit,
                payment_cycle=dto.payment_cycle,
                status=Contract.Status.DRAFT
            )
            self._ensure_default_contract_items(contract, operator_id=operator_id)

            # 5. 写入审计日志
            # 暂时注释掉OperationLog创建，因为apps.core.models不存在
            # OperationLog.objects.create(
            #     operator_id=operator_id,
            #     target_model='Contract',
            #     target_id=str(contract.id),
            #     action_type='CREATE_DRAFT',
            #     details={
            #         "shop_id": shop.id,
            #         "start_date": str(contract.start_date),
            #         "end_date": str(contract.end_date),
            #         "monthly_rent": str(contract.monthly_rent),
            #         "deposit": str(contract.deposit),
            #         "status": "DRAFT"
            #     }
            # )

            after_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            log_audit_action(
                action="create_contract",
                module="contract",
                instance=contract,
                actor_id=operator_id,
                before_data=None,
                after_data=after_data,
            )

            logger.info(f"Draft Contract {contract.id} created for Shop {shop.id}")
            return contract

    def activate_contract(self, dto: ContractActivateDTO, operator_id: int, tenant_id: int | None = None) -> None:
        """
        激活合同（状态流转：APPROVED -> ACTIVE）
        """
        with transaction.atomic():
            # 1. 锁定并查询 Contract
            # 必须在做任何时间重叠查询前锁定当前对象，保证基准数据一致性
            try:
                contract = Contract.objects.select_for_update().get(id=dto.contract_id)
                self._assert_tenant_access(
                    target_model="Contract",
                    target_id=contract.id,
                    actual_tenant_id=contract.tenant_id,
                    expected_tenant_id=tenant_id,
                    actor_id=operator_id,
                    module="contract",
                    object_type="store.contract",
                    service_action="activate_contract",
                )
            except Contract.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"合同 ID {dto.contract_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "Contract", "target_id": dto.contract_id}
                )

            # 2. 校验当前状态（幂等性与状态机检查）
            self._ensure_contract_status_transition(contract, Contract.Status.ACTIVE)

            # 3. 边界条件校验：禁止激活已过期的合同
            # 这是一个状态冲突问题（时间状态不满足），而非输入参数错误
            today = timezone.now().date()
            if contract.end_date <= today:
                raise StateConflictException(
                    message="无法激活已过期的合同",
                    override_error_code="CONTRACT_EXPIRED_CONFLICT",
                    data={
                        "target_model": "Contract",
                        "target_id": contract.id,
                        "current_status": str(contract.status),
                        "end_date": str(contract.end_date),
                        "today": str(today)
                    }
                )

            # 4. 校验业务规则（排他性 Check）
            # 规则：同一店铺在 [start_date, end_date) 区间内不能有其他 ACTIVE 合同
            # 逻辑：查找 (StartA < EndB) and (EndA > StartB) 的记录
            overlap_contract = Contract.objects.filter(
                shop_id=contract.shop_id,
                status=Contract.Status.ACTIVE,
                start_date__lt=contract.end_date,
                end_date__gt=contract.start_date
            ).exclude(id=contract.id).first()

            if overlap_contract:
                raise StateConflictException(
                    message="该店铺在当前时间段内已存在生效合同（时间重叠）",
                    override_error_code="CONTRACT_TIME_OVERLAP",
                    data={
                        "target_model": "Contract",
                        "target_id": contract.id,
                        "shop_id": contract.shop_id,
                        "conflict_contract_id": overlap_contract.id,
                        "conflict_range": {
                            "start_date": str(overlap_contract.start_date),
                            "end_date": str(overlap_contract.end_date)
                        }
                    }
                )

            # 5. 执行状态 Update
            before_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            old_status = str(contract.status)
            contract.status = Contract.Status.ACTIVE
            contract.save(update_fields=['status', 'updated_at'])

            # 6. 写入审计日志
            # 暂时注释掉OperationLog创建，因为apps.core.models不存在
            # current_time_str = str(timezone.now())
            # OperationLog.objects.create(
            #     operator_id=operator_id,
            #     target_model='Contract',
            #     target_id=str(contract.id),
            #     action_type='ACTIVATE',
            #     details={
            #         "contract_id": contract.id,
            #         "shop_id": contract.shop_id,
            #         "from_status": old_status,
            #         "to_status": "ACTIVE",
            #         "activated_at": current_time_str
            #     }
            # )

            after_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            log_audit_action(
                action="activate_contract",
                module="contract",
                instance=contract,
                actor_id=operator_id,
                before_data=before_data,
                after_data=after_data,
            )

            logger.info(f"Contract {contract.id} activated by operator {operator_id}")
            return None

    def terminate_contract(self, contract_id: int, operator_id: int, reason: str = None, tenant_id: int | None = None) -> None:
        """
        终止合同（状态流转：ACTIVE -> TERMINATED）
        """
        with transaction.atomic():
            # 1. 锁定并查询 Contract
            try:
                contract = Contract.objects.select_for_update().get(id=contract_id)
                self._assert_tenant_access(
                    target_model="Contract",
                    target_id=contract.id,
                    actual_tenant_id=contract.tenant_id,
                    expected_tenant_id=tenant_id,
                    actor_id=operator_id,
                    module="contract",
                    object_type="store.contract",
                    service_action="terminate_contract",
                )
            except Contract.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"合同 ID {contract_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "Contract", "target_id": contract_id}
                )

            # 2. 校验当前状态
            self._ensure_contract_status_transition(contract, Contract.Status.TERMINATED)

            # 3. 执行状态 Update
            before_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            old_status = str(contract.status)
            contract.status = Contract.Status.TERMINATED
            contract.save(update_fields=['status', 'updated_at'])

            after_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            log_audit_action(
                action="terminate_contract",
                module="contract",
                instance=contract,
                actor_id=operator_id,
                before_data=before_data,
                after_data=after_data,
            )

            logger.info(f"Contract {contract.id} terminated by operator {operator_id}")
            return None

    def archive_contract(self, contract_id: int, operator_id: int, tenant_id: int | None = None) -> None:
        """
        合同归档（软删除）：仅允许终止/过期合同归档，且不删除财务记录。
        """
        from django.contrib.auth.models import User

        with transaction.atomic():
            try:
                contract = Contract.objects.select_for_update().get(id=contract_id)
                self._assert_tenant_access(
                    target_model="Contract",
                    target_id=contract.id,
                    actual_tenant_id=contract.tenant_id,
                    expected_tenant_id=tenant_id,
                    actor_id=operator_id,
                    module="contract",
                    object_type="store.contract",
                    service_action="archive_contract",
                )
            except Contract.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"合同 ID {contract_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "Contract", "target_id": contract_id}
                )

            if contract.is_archived:
                log_audit_action(
                    action="archive_contract_blocked",
                    module="contract",
                    instance=contract,
                    actor_id=operator_id,
                    before_data={"is_archived": contract.is_archived},
                    after_data={"reason": "already_archived"},
                )
                raise StateConflictException(
                    message="合同已归档，请勿重复操作",
                    override_error_code="CONTRACT_ARCHIVE_CONFLICT",
                    data={
                        "target_model": "Contract",
                        "target_id": contract.id,
                        "is_archived": True,
                    }
                )

            if contract.status not in [Contract.Status.TERMINATED, Contract.Status.EXPIRED]:
                log_audit_action(
                    action="archive_contract_blocked",
                    module="contract",
                    instance=contract,
                    actor_id=operator_id,
                    before_data={"current_status": str(contract.status)},
                    after_data={"reason": "invalid_status_for_archive"},
                )
                raise StateConflictException(
                    message=f"合同当前状态为 {contract.get_status_display()}，仅终止或过期合同可归档",
                    override_error_code="CONTRACT_STATUS_CONFLICT",
                    data={
                        "target_model": "Contract",
                        "target_id": contract.id,
                        "current_status": str(contract.status),
                    }
                )

            try:
                operator = User.objects.get(id=operator_id)
            except User.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"用户 ID {operator_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "User", "target_id": operator_id}
                )

            before_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            contract.is_archived = True
            contract.archived_at = timezone.now()
            contract.archived_by = operator
            contract.save(update_fields=["is_archived", "archived_at", "archived_by", "updated_at"])

            after_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            log_audit_action(
                action="archive_contract",
                module="contract",
                instance=contract,
                actor_id=operator_id,
                before_data=before_data,
                after_data=after_data,
            )

            logger.info(f"Contract {contract.id} archived by operator {operator_id}")
            return None

    def renew_contract(self, contract_id: int, new_end_date: date, operator_id: int, tenant_id: int | None = None) -> Contract:
        """
        续签合同
        创建新的合同记录，继承原合同的基本信息
        """
        with transaction.atomic():
            # 1. 锁定并查询原合同
            try:
                original_contract = Contract.objects.select_for_update().get(id=contract_id)
                self._assert_tenant_access(
                    target_model="Contract",
                    target_id=original_contract.id,
                    actual_tenant_id=original_contract.tenant_id,
                    expected_tenant_id=tenant_id,
                    actor_id=operator_id,
                    module="contract",
                    object_type="store.contract",
                    service_action="renew_contract",
                )
            except Contract.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"合同 ID {contract_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "Contract", "target_id": contract_id}
                )

            # 2. 校验原合同状态
            if original_contract.status not in [Contract.Status.ACTIVE, Contract.Status.EXPIRED]:
                raise StateConflictException(
                    message=f"合同当前状态为 {original_contract.get_status_display()}，仅生效或已过期状态可续签",
                    override_error_code="CONTRACT_STATUS_CONFLICT",
                    data={
                        "target_model": "Contract",
                        "target_id": original_contract.id,
                        "current_status": str(original_contract.status)
                    }
                )

            # 3. 校验新的结束日期
            if new_end_date <= original_contract.end_date:
                raise BusinessValidationError(
                    message="新的合同结束日期必须晚于原合同结束日期",
                    override_error_code="INVALID_RENEWAL_DATE",
                    data={
                        "target_model": "Contract",
                        "original_end_date": str(original_contract.end_date),
                        "new_end_date": str(new_end_date)
                    }
                )

            # 4. 创建新的续签合同
            new_start_date = original_contract.end_date + timedelta(days=1)
            contract_no = self._generate_contract_no(original_contract.tenant, new_start_date)
            new_contract = Contract.objects.create(
                shop=original_contract.shop,
                contract_no=contract_no,
                start_date=new_start_date,
                end_date=new_end_date,
                monthly_rent=original_contract.monthly_rent,
                deposit=original_contract.deposit,
                payment_cycle=original_contract.payment_cycle,
                status=Contract.Status.DRAFT
            )
            self._clone_contract_items(
                source_contract=original_contract,
                target_contract=new_contract,
                operator_id=operator_id,
            )

            after_data = serialize_instance(new_contract, CONTRACT_AUDIT_FIELDS)
            before_data = {
                "original_contract_id": original_contract.id,
                "original_status": str(original_contract.status),
                "original_end_date": str(original_contract.end_date),
            }
            log_audit_action(
                action="renew_contract",
                module="contract",
                instance=new_contract,
                actor_id=operator_id,
                before_data=before_data,
                after_data=after_data,
            )

            logger.info(f"Renewal Contract {new_contract.id} created for Shop {original_contract.shop.id}")
            return new_contract

    def expire_contract(self, contract_id: int, operator_id: int, tenant_id: int | None = None) -> None:
        """
        标记合同为过期（状态流转：ACTIVE -> EXPIRED）
        """
        with transaction.atomic():
            # 1. 锁定并查询 Contract
            try:
                contract = Contract.objects.select_for_update().get(id=contract_id)
                self._assert_tenant_access(
                    target_model="Contract",
                    target_id=contract.id,
                    actual_tenant_id=contract.tenant_id,
                    expected_tenant_id=tenant_id,
                    actor_id=operator_id,
                    module="contract",
                    object_type="store.contract",
                    service_action="expire_contract",
                )
            except Contract.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"合同 ID {contract_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "Contract", "target_id": contract_id}
                )

            # 2. 校验当前状态
            self._ensure_contract_status_transition(contract, Contract.Status.EXPIRED)

            # 3. 校验是否真的过期
            today = timezone.now().date()
            if contract.end_date >= today:
                raise BusinessValidationError(
                    message="合同尚未过期，无法标记为过期状态",
                    override_error_code="CONTRACT_NOT_EXPIRED",
                    data={
                        "target_model": "Contract",
                        "target_id": contract.id,
                        "end_date": str(contract.end_date),
                        "today": str(today)
                    }
                )

            # 4. 执行状态 Update
            before_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            old_status = str(contract.status)
            contract.status = Contract.Status.EXPIRED
            contract.save(update_fields=['status', 'updated_at'])

            after_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            log_audit_action(
                action="expire_contract",
                module="contract",
                instance=contract,
                actor_id=operator_id,
                before_data=before_data,
                after_data=after_data,
            )

            logger.info(f"Contract {contract.id} marked as expired by operator {operator_id}")
            return None

    def submit_for_review(self, contract_id: int, operator_id: int = None, tenant_id: int | None = None) -> Contract:
        """
        提交合同进行审核（状态流转：DRAFT -> PENDING_REVIEW）
        
        业务逻辑：
        1. 验证合同存在且处于DRAFT状态
        2. 校验必填信息完整性（店铺、金额、周期等）
        3. 执行状态转移到PENDING_REVIEW
        """
        with transaction.atomic():
            # 1. 锁定并查询 Contract
            try:
                contract = Contract.objects.select_for_update().get(id=contract_id)
                self._assert_tenant_access(
                    target_model="Contract",
                    target_id=contract.id,
                    actual_tenant_id=contract.tenant_id,
                    expected_tenant_id=tenant_id,
                    actor_id=operator_id,
                    module="contract",
                    object_type="store.contract",
                    service_action="submit_for_review",
                )
            except Contract.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"合同 ID {contract_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "Contract", "target_id": contract_id}
                )

            # 2. 校验当前状态
            self._ensure_contract_status_transition(contract, Contract.Status.PENDING_REVIEW)

            # 3. 校验必填信息完整性
            if not contract.shop_id:
                raise BusinessValidationError(
                    message="合同未绑定店铺，无法提交审核",
                    override_error_code="CONTRACT_SHOP_MISSING",
                    data={"target_model": "Contract", "target_id": contract.id}
                )
            
            if not contract.monthly_rent or contract.monthly_rent <= 0:
                raise BusinessValidationError(
                    message="合同月租金未设置或小于零，无法提交审核",
                    override_error_code="CONTRACT_RENT_INVALID",
                    data={"target_model": "Contract", "target_id": contract.id}
                )
            
            if not contract.start_date or not contract.end_date:
                raise BusinessValidationError(
                    message="合同起止日期未设置，无法提交审核",
                    override_error_code="CONTRACT_DATE_MISSING",
                    data={"target_model": "Contract", "target_id": contract.id}
                )
            
            if contract.start_date >= contract.end_date:
                raise BusinessValidationError(
                    message="合同起止日期不合法（起始日期必须早于结束日期），无法提交审核",
                    override_error_code="CONTRACT_DATE_INVALID",
                    data={
                        "target_model": "Contract",
                        "target_id": contract.id,
                        "start_date": str(contract.start_date),
                        "end_date": str(contract.end_date)
                    }
                )

            # 4. 执行状态转移
            before_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            contract.status = Contract.Status.PENDING_REVIEW
            contract.reviewed_by = None
            contract.reviewed_at = None
            contract.review_comment = None
            contract.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_comment', 'updated_at'])

            round_no = self._build_approval_tasks_for_contract(contract, operator_id=operator_id)

            after_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            log_audit_action(
                action="submit_contract_review",
                module="contract",
                instance=contract,
                actor_id=operator_id,
                before_data=before_data,
                after_data=after_data,
            )
            log_audit_action(
                action="start_approval_round",
                module="contract",
                instance=contract,
                actor_id=operator_id,
                before_data={"round_no": round_no - 1},
                after_data={"round_no": round_no},
            )

            logger.info(f"Contract {contract.id} submitted for review by operator {operator_id}, round {round_no}")
            return contract

    def approve_contract(
        self,
        contract_id: int,
        reviewer_id: int,
        comment: str = '',
        tenant_id: int | None = None,
    ) -> Contract:
        """
        批准合同（状态流转：PENDING_REVIEW -> APPROVED -> ACTIVE）
        
        业务逻辑：
        1. 验证合同处于PENDING_REVIEW状态
        2. 设置审核者、审核时间和评论
        3. 状态转移到APPROVED
        4. 触发后续业务流程（生成初始账单等）
        
        参数：
        - contract_id: 合同ID
        - reviewer_id: 审核员ID（auth.User的ID）
        - comment: 审核评论（可选）
        """
        from django.contrib.auth.models import User

        with transaction.atomic():
            try:
                contract = Contract.objects.select_for_update().get(id=contract_id)
                self._assert_tenant_access(
                    target_model="Contract",
                    target_id=contract.id,
                    actual_tenant_id=contract.tenant_id,
                    expected_tenant_id=tenant_id,
                    actor_id=reviewer_id,
                    module="contract",
                    object_type="store.contract",
                    service_action="approve_contract",
                )
            except Contract.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"合同 ID {contract_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "Contract", "target_id": contract_id},
                )

            self._ensure_contract_status_transition(contract, Contract.Status.APPROVED)

            try:
                reviewer = User.objects.get(id=reviewer_id)
            except User.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"审核员 ID {reviewer_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "User", "target_id": reviewer_id},
                )

            current_task = self._get_current_pending_task(contract.id)
            self._assert_task_reviewer_permission(current_task, reviewer)

            acted_at = timezone.now()
            task_before_data = serialize_instance(current_task, APPROVAL_TASK_AUDIT_FIELDS)
            current_task.status = ApprovalTask.Status.APPROVED
            current_task.acted_by = reviewer
            current_task.acted_at = acted_at
            current_task.comment = comment or None
            current_task.save(update_fields=["status", "acted_by", "acted_at", "comment", "updated_at"])
            task_after_data = serialize_instance(current_task, APPROVAL_TASK_AUDIT_FIELDS)
            log_audit_action(
                action="approve_approval_task",
                module="contract",
                instance=contract,
                actor_id=reviewer_id,
                before_data=task_before_data,
                after_data=task_after_data,
            )

            has_pending_next = ApprovalTask.objects.filter(
                contract_id=contract.id,
                round_no=current_task.round_no,
                status=ApprovalTask.Status.PENDING,
            ).exists()

            contract_before_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            contract.reviewed_by = reviewer
            contract.reviewed_at = acted_at
            contract.review_comment = comment or None
            update_fields = ["reviewed_by", "reviewed_at", "review_comment", "updated_at"]
            audit_action = "approve_contract_node"
            if not has_pending_next:
                contract.status = Contract.Status.APPROVED
                update_fields.insert(0, "status")
                audit_action = "approve_contract"
            contract.save(update_fields=update_fields)
            contract_after_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            log_audit_action(
                action=audit_action,
                module="contract",
                instance=contract,
                actor_id=reviewer_id,
                before_data=contract_before_data,
                after_data=contract_after_data,
            )

            logger.info(
                "Contract %s approved at node %s by reviewer %s; final_status=%s",
                contract.id,
                current_task.node_name,
                reviewer_id,
                contract.status,
            )
            return contract

    def reject_contract(self, contract_id: int, reviewer_id: int, reason: str, tenant_id: int | None = None) -> Contract:
        """
        拒绝合同（状态流转：PENDING_REVIEW -> REJECTED）
        
        业务逻辑：
        1. 验证合同处于PENDING_REVIEW状态
        2. 设置审核者、审核时间和拒绝原因
        3. 状态转移到REJECTED
        4. 记录拒绝信息供后续处理
        
        参数：
        - contract_id: 合同ID
        - reviewer_id: 审核员ID（auth.User的ID）
        - reason: 拒绝原因（必填）
        """
        from django.contrib.auth.models import User

        with transaction.atomic():
            try:
                contract = Contract.objects.select_for_update().get(id=contract_id)
                self._assert_tenant_access(
                    target_model="Contract",
                    target_id=contract.id,
                    actual_tenant_id=contract.tenant_id,
                    expected_tenant_id=tenant_id,
                    actor_id=reviewer_id,
                    module="contract",
                    object_type="store.contract",
                    service_action="reject_contract",
                )
            except Contract.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"合同 ID {contract_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "Contract", "target_id": contract_id},
                )

            self._ensure_contract_status_transition(contract, Contract.Status.REJECTED)

            if not reason or not reason.strip():
                log_audit_action(
                    action="reject_contract_blocked",
                    module="contract",
                    instance=contract,
                    actor_id=reviewer_id,
                    before_data={"status": str(contract.status)},
                    after_data={"reason": "empty_reject_reason"},
                )
                raise BusinessValidationError(
                    message="拒绝原因不能为空",
                    override_error_code="REJECTION_REASON_EMPTY",
                    data={"target_model": "Contract", "target_id": contract.id},
                )

            try:
                reviewer = User.objects.get(id=reviewer_id)
            except User.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"审核员 ID {reviewer_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "User", "target_id": reviewer_id},
                )

            current_task = self._get_current_pending_task(contract.id)
            self._assert_task_reviewer_permission(current_task, reviewer)
            acted_at = timezone.now()

            rejected_task_before_data = serialize_instance(current_task, APPROVAL_TASK_AUDIT_FIELDS)
            current_task.status = ApprovalTask.Status.REJECTED
            current_task.acted_by = reviewer
            current_task.acted_at = acted_at
            current_task.comment = reason
            current_task.save(update_fields=["status", "acted_by", "acted_at", "comment", "updated_at"])
            rejected_task_after_data = serialize_instance(current_task, APPROVAL_TASK_AUDIT_FIELDS)
            log_audit_action(
                action="reject_approval_task",
                module="contract",
                instance=contract,
                actor_id=reviewer_id,
                before_data=rejected_task_before_data,
                after_data=rejected_task_after_data,
            )

            pending_following_tasks = list(
                ApprovalTask.objects.select_for_update().filter(
                    contract_id=contract.id,
                    round_no=current_task.round_no,
                    status=ApprovalTask.Status.PENDING,
                )
            )
            for skipped_task in pending_following_tasks:
                skipped_before_data = serialize_instance(skipped_task, APPROVAL_TASK_AUDIT_FIELDS)
                skipped_task.status = ApprovalTask.Status.SKIPPED
                skipped_task.acted_by = reviewer
                skipped_task.acted_at = acted_at
                skipped_task.comment = "因前序节点驳回自动跳过"
                skipped_task.save(update_fields=["status", "acted_by", "acted_at", "comment", "updated_at"])
                skipped_after_data = serialize_instance(skipped_task, APPROVAL_TASK_AUDIT_FIELDS)
                log_audit_action(
                    action="skip_approval_task_after_reject",
                    module="contract",
                    instance=contract,
                    actor_id=reviewer_id,
                    before_data=skipped_before_data,
                    after_data=skipped_after_data,
                )

            contract_before_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            contract.status = Contract.Status.REJECTED
            contract.reviewed_by = reviewer
            contract.reviewed_at = acted_at
            contract.review_comment = reason
            contract.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_comment", "updated_at"])
            contract_after_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            log_audit_action(
                action="reject_contract",
                module="contract",
                instance=contract,
                actor_id=reviewer_id,
                before_data=contract_before_data,
                after_data=contract_after_data,
            )

            logger.info("Contract %s rejected by reviewer %s. Reason: %s", contract.id, reviewer_id, reason)
            return contract
