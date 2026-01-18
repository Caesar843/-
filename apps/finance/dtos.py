from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from apps.core.exceptions import BusinessValidationError


@dataclass(frozen=True)
class FinanceGenerateDTO:
    """
    财务记录生成数据传输对象。

    使用场景：FinanceService.generate_records_for_contract 入参
    """
    contract_id: int

    def __post_init__(self):
        # Field: contract_id
        if not isinstance(self.contract_id, int):
            raise BusinessValidationError("Type mismatch: expected int", field="contract_id")
        if self.contract_id <= 0:
            raise BusinessValidationError("Value must be greater than 0", field="contract_id")


@dataclass(frozen=True)
class FinancePayDTO:
    """
    财务记录支付数据传输对象。

    使用场景：FinanceService.mark_as_paid 入参
    """
    record_id: int
    payment_method: str
    transaction_id: Optional[str] = None

    def __post_init__(self):
        # Field: record_id
        if not isinstance(self.record_id, int):
            raise BusinessValidationError("Type mismatch: expected int", field="record_id")
        if self.record_id <= 0:
            raise BusinessValidationError("Value must be greater than 0", field="record_id")
        
        # Field: payment_method
        if not isinstance(self.payment_method, str):
            raise BusinessValidationError("Type mismatch: expected str", field="payment_method")
        valid_methods = ['WECHAT', 'ALIPAY', 'BANK_TRANSFER', 'CASH']
        if self.payment_method not in valid_methods:
            raise BusinessValidationError(f"Value must be one of: {', '.join(valid_methods)}", field="payment_method")
        
        # Field: transaction_id (optional)
        if self.transaction_id is not None and not isinstance(self.transaction_id, str):
            raise BusinessValidationError("Type mismatch: expected str", field="transaction_id")


@dataclass(frozen=True)
class FinanceRecordCreateDTO:
    """
    财务记录创建数据传输对象。

    使用场景：手动创建财务记录
    """
    contract_id: int
    amount: Decimal
    fee_type: str
    billing_period_start: str
    billing_period_end: str

    def __post_init__(self):
        # Field: contract_id
        if not isinstance(self.contract_id, int):
            raise BusinessValidationError("Type mismatch: expected int", field="contract_id")
        if self.contract_id <= 0:
            raise BusinessValidationError("Value must be greater than 0", field="contract_id")
        
        # Field: amount
        if not isinstance(self.amount, Decimal):
            raise BusinessValidationError("Type mismatch: expected Decimal", field="amount")
        if self.amount < 0:
            raise BusinessValidationError("Value must be greater than or equal to 0", field="amount")
        
        # Field: fee_type
        if not isinstance(self.fee_type, str):
            raise BusinessValidationError("Type mismatch: expected str", field="fee_type")
        valid_fee_types = ['RENT', 'PROPERTY_FEE', 'UTILITY_FEE', 'OTHER']
        if self.fee_type not in valid_fee_types:
            raise BusinessValidationError(f"Value must be one of: {', '.join(valid_fee_types)}", field="fee_type")
        
        # Field: billing_period_start
        if not isinstance(self.billing_period_start, str):
            raise BusinessValidationError("Type mismatch: expected str", field="billing_period_start")
        
        # Field: billing_period_end
        if not isinstance(self.billing_period_end, str):
            raise BusinessValidationError("Type mismatch: expected str", field="billing_period_end")
