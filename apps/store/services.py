import logging
from django.db import transaction
from django.utils import timezone
from datetime import date, datetime, timedelta

from apps.core.exceptions import (
    BusinessValidationError,
    ResourceNotFoundException,
    StateConflictException
)
# 暂时注释掉OperationLog导入，因为apps.core.models不存在
# from apps.core.models import OperationLog
from apps.store.models import Shop, Contract
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
    "start_date",
    "end_date",
    "monthly_rent",
    "deposit",
    "payment_cycle",
    "status",
    "reviewed_by_id",
    "reviewed_at",
    "review_comment",
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

    def delete_shop(self, shop_id: int, operator_id: int) -> None:
        """
        删除店铺（逻辑删除）
        """
        with transaction.atomic():
            # 1. 锁定并查询 Shop
            try:
                shop = Shop.objects.select_for_update().get(id=shop_id)
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

    def create_draft_contract(self, dto: ContractCreateDTO, operator_id: int) -> Contract:
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
            contract = Contract.objects.create(
                shop=shop,
                start_date=dto.start_date,
                end_date=dto.end_date,
                monthly_rent=dto.monthly_rent,
                deposit=dto.deposit,
                payment_cycle=dto.payment_cycle,
                status=Contract.Status.DRAFT
            )

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

    def activate_contract(self, dto: ContractActivateDTO, operator_id: int) -> None:
        """
        激活合同（状态流转：DRAFT -> ACTIVE）
        """
        with transaction.atomic():
            # 1. 锁定并查询 Contract
            # 必须在做任何时间重叠查询前锁定当前对象，保证基准数据一致性
            try:
                contract = Contract.objects.select_for_update().get(id=dto.contract_id)
            except Contract.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"合同 ID {dto.contract_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "Contract", "target_id": dto.contract_id}
                )

            # 2. 校验当前状态（幂等性与状态机检查）
            if contract.status == Contract.Status.ACTIVE:
                raise StateConflictException(
                    message="合同已处于生效状态，请勿重复激活",
                    override_error_code="CONTRACT_STATUS_CONFLICT",
                    data={
                        "target_model": "Contract",
                        "target_id": contract.id,
                        "current_status": str(contract.status)
                    }
                )

            # 显式禁止非法流转 (EXPIRED/TERMINATED -> ACTIVE)
            if contract.status != Contract.Status.DRAFT:
                raise StateConflictException(
                    message=f"合同当前状态为 {contract.get_status_display()}，仅草稿状态可激活",
                    override_error_code="CONTRACT_STATUS_CONFLICT",
                    data={
                        "target_model": "Contract",
                        "target_id": contract.id,
                        "current_status": str(contract.status)
                    }
                )

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

    def terminate_contract(self, contract_id: int, operator_id: int, reason: str = None) -> None:
        """
        终止合同（状态流转：ACTIVE -> TERMINATED）
        """
        with transaction.atomic():
            # 1. 锁定并查询 Contract
            try:
                contract = Contract.objects.select_for_update().get(id=contract_id)
            except Contract.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"合同 ID {contract_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "Contract", "target_id": contract_id}
                )

            # 2. 校验当前状态
            if contract.status != Contract.Status.ACTIVE:
                raise StateConflictException(
                    message=f"合同当前状态为 {contract.get_status_display()}，仅生效状态可终止",
                    override_error_code="CONTRACT_STATUS_CONFLICT",
                    data={
                        "target_model": "Contract",
                        "target_id": contract.id,
                        "current_status": str(contract.status)
                    }
                )

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

    def renew_contract(self, contract_id: int, new_end_date: date, operator_id: int) -> Contract:
        """
        续签合同
        创建新的合同记录，继承原合同的基本信息
        """
        with transaction.atomic():
            # 1. 锁定并查询原合同
            try:
                original_contract = Contract.objects.select_for_update().get(id=contract_id)
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
            new_contract = Contract.objects.create(
                shop=original_contract.shop,
                start_date=original_contract.end_date + timedelta(days=1),
                end_date=new_end_date,
                monthly_rent=original_contract.monthly_rent,
                deposit=original_contract.deposit,
                payment_cycle=original_contract.payment_cycle,
                status=Contract.Status.DRAFT
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

    def expire_contract(self, contract_id: int, operator_id: int) -> None:
        """
        标记合同为过期（状态流转：ACTIVE -> EXPIRED）
        """
        with transaction.atomic():
            # 1. 锁定并查询 Contract
            try:
                contract = Contract.objects.select_for_update().get(id=contract_id)
            except Contract.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"合同 ID {contract_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "Contract", "target_id": contract_id}
                )

            # 2. 校验当前状态
            if contract.status != Contract.Status.ACTIVE:
                raise StateConflictException(
                    message=f"合同当前状态为 {contract.get_status_display()}，仅生效状态可标记为过期",
                    override_error_code="CONTRACT_STATUS_CONFLICT",
                    data={
                        "target_model": "Contract",
                        "target_id": contract.id,
                        "current_status": str(contract.status)
                    }
                )

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

    def submit_for_review(self, contract_id: int) -> Contract:
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
            except Contract.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"合同 ID {contract_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "Contract", "target_id": contract_id}
                )

            # 2. 校验当前状态
            if contract.status != Contract.Status.DRAFT:
                raise StateConflictException(
                    message=f"合同当前状态为 {contract.get_status_display()}，仅草稿状态可提交审核",
                    override_error_code="CONTRACT_STATUS_CONFLICT",
                    data={
                        "target_model": "Contract",
                        "target_id": contract.id,
                        "current_status": str(contract.status)
                    }
                )

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
            contract.save(update_fields=['status', 'updated_at'])

            after_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            log_audit_action(
                action="submit_contract_review",
                module="contract",
                instance=contract,
                before_data=before_data,
                after_data=after_data,
            )

            logger.info(f"Contract {contract.id} submitted for review")
            return contract

    def approve_contract(self, contract_id: int, reviewer_id: int, comment: str = '') -> Contract:
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
            # 1. 锁定并查询 Contract
            try:
                contract = Contract.objects.select_for_update().get(id=contract_id)
            except Contract.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"合同 ID {contract_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "Contract", "target_id": contract_id}
                )

            # 2. 校验当前状态
            if contract.status != Contract.Status.PENDING_REVIEW:
                raise StateConflictException(
                    message=f"合同当前状态为 {contract.get_status_display()}，仅待审核状态可批准",
                    override_error_code="CONTRACT_STATUS_CONFLICT",
                    data={
                        "target_model": "Contract",
                        "target_id": contract.id,
                        "current_status": str(contract.status)
                    }
                )

            # 3. 校验审核员存在
            try:
                reviewer = User.objects.get(id=reviewer_id)
            except User.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"审核员 ID {reviewer_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "User", "target_id": reviewer_id}
                )

            # 4. 更新合同审核信息
            before_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            contract.status = Contract.Status.APPROVED
            contract.reviewed_by = reviewer
            contract.reviewed_at = timezone.now()
            contract.review_comment = comment
            contract.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_comment', 'updated_at'])

            after_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            log_audit_action(
                action="reject_contract",
                module="contract",
                instance=contract,
                actor_id=reviewer_id,
                before_data=before_data,
                after_data=after_data,
            )

            after_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            log_audit_action(
                action="approve_contract",
                module="contract",
                instance=contract,
                actor_id=reviewer_id,
                before_data=before_data,
                after_data=after_data,
            )

            # 5. 后续业务流程：激活合同并生成初始账单
            # 注：此处可集成后续业务流程，如：
            # - 生成首月账单 (FinanceService.generate_records_for_contract)
            # - 发送合同激活通知
            # - 更新店铺状态等

            logger.info(f"Contract {contract.id} approved by reviewer {reviewer_id}")
            return contract

    def reject_contract(self, contract_id: int, reviewer_id: int, reason: str) -> Contract:
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
            # 1. 锁定并查询 Contract
            try:
                contract = Contract.objects.select_for_update().get(id=contract_id)
            except Contract.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"合同 ID {contract_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "Contract", "target_id": contract_id}
                )

            # 2. 校验当前状态
            if contract.status != Contract.Status.PENDING_REVIEW:
                raise StateConflictException(
                    message=f"合同当前状态为 {contract.get_status_display()}，仅待审核状态可拒绝",
                    override_error_code="CONTRACT_STATUS_CONFLICT",
                    data={
                        "target_model": "Contract",
                        "target_id": contract.id,
                        "current_status": str(contract.status)
                    }
                )

            # 3. 校验拒绝原因不为空
            if not reason or not reason.strip():
                raise BusinessValidationError(
                    message="拒绝原因不能为空",
                    override_error_code="REJECTION_REASON_EMPTY",
                    data={"target_model": "Contract", "target_id": contract.id}
                )

            # 4. 校验审核员存在
            try:
                reviewer = User.objects.get(id=reviewer_id)
            except User.DoesNotExist:
                raise ResourceNotFoundException(
                    message=f"审核员 ID {reviewer_id} 不存在",
                    override_error_code="RESOURCE_NOT_FOUND",
                    data={"target_model": "User", "target_id": reviewer_id}
                )

            # 5. 更新合同审核信息
            before_data = serialize_instance(contract, CONTRACT_AUDIT_FIELDS)
            contract.status = Contract.Status.REJECTED
            contract.reviewed_by = reviewer
            contract.reviewed_at = timezone.now()
            contract.review_comment = reason  # 拒绝原因存储在 review_comment 字段
            contract.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_comment', 'updated_at'])

            logger.info(f"Contract {contract.id} rejected by reviewer {reviewer_id}. Reason: {reason}")
            return contract
