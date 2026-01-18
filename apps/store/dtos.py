from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from apps.core.exceptions import BusinessValidationError

"""
DTO (Data Transfer Object) Layer Definition
-------------------------------------------
本模块定义了 Service 层的唯一输入契约。

边界契约声明：
1. 纯粹性：DTO 仅负责数据结构定义与基础类型/格式校验，绝不包含业务逻辑或数据库操作。
2. 可信性：DTO 实例一旦成功构造，即代表数据在类型（Type）与基础约束（Constraint）上是合法的。
   Service 层无需再进行 isinstance 或非空检查，可直接信任 DTO 数据。
3. 异常契约：所有校验失败均抛出 BusinessValidationError，明确指名字段（field）与原因（message）。
"""


@dataclass(frozen=True)
class ShopCreateDTO:
    """
    店铺创建数据传输对象。

    使用场景：StoreService.create_shop 入参
    """
    name: str
    business_type: str
    area: Decimal
    rent: Decimal
    contact_person: str = None
    contact_phone: str = None
    entry_date: date = None
    description: str = None

    def __post_init__(self):
        # Field: name
        if not isinstance(self.name, str):
            raise BusinessValidationError("Type mismatch: expected str", field="name")
        if not self.name.strip():
            raise BusinessValidationError("Value cannot be empty or whitespace only", field="name")

        # Field: business_type
        if not isinstance(self.business_type, str):
            raise BusinessValidationError("Type mismatch: expected str", field="business_type")
        if not self.business_type.strip():
            raise BusinessValidationError("Value cannot be empty or whitespace only", field="business_type")

        # Field: area
        if not isinstance(self.area, Decimal):
            raise BusinessValidationError("Type mismatch: expected Decimal", field="area")
        if self.area <= 0:
            raise BusinessValidationError("Value must be greater than 0", field="area")

        # Field: rent
        if not isinstance(self.rent, Decimal):
            raise BusinessValidationError("Type mismatch: expected Decimal", field="rent")
        if self.rent <= 0:
            raise BusinessValidationError("Value must be greater than 0", field="rent")

        # Field: contact_person (optional)
        if self.contact_person is not None and not isinstance(self.contact_person, str):
            raise BusinessValidationError("Type mismatch: expected str", field="contact_person")

        # Field: contact_phone (optional)
        if self.contact_phone is not None and not isinstance(self.contact_phone, str):
            raise BusinessValidationError("Type mismatch: expected str", field="contact_phone")

        # Field: entry_date (optional)
        if self.entry_date is not None and not isinstance(self.entry_date, date):
            raise BusinessValidationError("Type mismatch: expected date", field="entry_date")

        # Field: description (optional)
        if self.description is not None and not isinstance(self.description, str):
            raise BusinessValidationError("Type mismatch: expected str", field="description")


@dataclass(frozen=True)
class ContractCreateDTO:
    """
    合同创建数据传输对象。

    使用场景：ContractService.create_draft_contract 入参
    """
    shop_id: int
    start_date: date
    end_date: date
    monthly_rent: Decimal
    deposit: Decimal
    payment_cycle: str = 'MONTHLY'

    def __post_init__(self):
        # Field: shop_id
        if not isinstance(self.shop_id, int) or isinstance(self.shop_id, bool):
            raise BusinessValidationError("Type mismatch: expected int", field="shop_id")
        if self.shop_id <= 0:
            raise BusinessValidationError("Value must be greater than 0", field="shop_id")

        # Field: start_date
        if not isinstance(self.start_date, date):
            raise BusinessValidationError("Type mismatch: expected date", field="start_date")

        # Field: end_date
        if not isinstance(self.end_date, date):
            raise BusinessValidationError("Type mismatch: expected date", field="end_date")

        # Field: monthly_rent
        if not isinstance(self.monthly_rent, Decimal):
            raise BusinessValidationError("Type mismatch: expected Decimal", field="monthly_rent")
        if self.monthly_rent <= 0:
            raise BusinessValidationError("Value must be greater than 0", field="monthly_rent")

        # Field: deposit
        if not isinstance(self.deposit, Decimal):
            raise BusinessValidationError("Type mismatch: expected Decimal", field="deposit")
        if self.deposit < 0:
            raise BusinessValidationError("Value must be greater than or equal to 0", field="deposit")

        # Field: payment_cycle
        if not isinstance(self.payment_cycle, str):
            raise BusinessValidationError("Type mismatch: expected str", field="payment_cycle")
        valid_cycles = ['MONTHLY', 'QUARTERLY', 'SEMIANNUALLY', 'ANNUALLY']
        if self.payment_cycle not in valid_cycles:
            raise BusinessValidationError(f"Value must be one of: {', '.join(valid_cycles)}", field="payment_cycle")

        # Cross-field validation
        if self.end_date <= self.start_date:
            raise BusinessValidationError("Logic error: end_date must be later than start_date", field="end_date")


@dataclass(frozen=True)
class ContractActivateDTO:
    """
    合同激活数据传输对象。

    使用场景：ContractService.activate_contract 入参
    """
    contract_id: int

    def __post_init__(self):
        # Field: contract_id
        if not isinstance(self.contract_id, int) or isinstance(self.contract_id, bool):
            raise BusinessValidationError("Type mismatch: expected int", field="contract_id")
        if self.contract_id <= 0:
            raise BusinessValidationError("Value must be greater than 0", field="contract_id")