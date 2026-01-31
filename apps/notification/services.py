import logging
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User
from typing import Optional, Dict, Any

from apps.core.exceptions import (
    BusinessValidationError,
    ResourceNotFoundException
)
from apps.notification.models import (
    Notification,
    NotificationTemplate,
    SMSRecord,
    NotificationPreference
)

logger = logging.getLogger(__name__)


class NotificationService:
    """
    通知服务层
    负责处理系统通知、短信通知等各类通知业务逻辑
    """

    # SMS 服务配置（可根据实际情况配置）
    SMS_CONFIG = {
        'enabled': getattr(settings, 'SMS_ENABLED', True),
        'provider': getattr(settings, 'SMS_PROVIDER', 'CUSTOM'),
        'timeout': getattr(settings, 'SMS_TIMEOUT', 10),
    }

    @staticmethod
    def get_or_create_preference(user: User) -> NotificationPreference:
        """
        获取或创建用户通知偏好
        """
        preference, _ = NotificationPreference.objects.get_or_create(user=user)
        return preference

    @staticmethod
    def create_notification(
        recipient_id: int,
        notification_type: str,
        title: str,
        content: str,
        related_model: Optional[str] = None,
        related_id: Optional[int] = None,
        template: Optional[NotificationTemplate] = None
    ) -> Notification:
        """
        创建系统通知消息
        
        参数：
        - recipient_id: 收件人ID（auth.User的ID）
        - notification_type: 通知类型（Notification.Type中的选项）
        - title: 通知标题
        - content: 通知内容
        - related_model: 关联的业务模型名称（可选）
        - related_id: 关联的业务对象ID（可选）
        - template: 使用的模板（可选）
        """
        try:
            recipient = User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            raise ResourceNotFoundException(
                message=f"用户 ID {recipient_id} 不存在",
                override_error_code="RESOURCE_NOT_FOUND",
                data={"target_model": "User", "target_id": recipient_id}
            )

        with transaction.atomic():
            notification = Notification.objects.create(
                recipient=recipient,
                notification_type=notification_type,
                title=title,
                content=content,
                related_model=related_model,
                related_id=related_id,
                template=template,
                status=Notification.Status.SENT  # 系统消息立即标记为已发送
            )
            notification.sent_at = timezone.now()
            notification.save(update_fields=['sent_at'])
            
            logger.info(f"Notification created for user {recipient_id}: {notification_type}")
            return notification

    @staticmethod
    def render_template(
        template: NotificationTemplate,
        variables: Dict[str, Any]
    ) -> tuple[str, str]:
        """
        使用变量渲染模板
        
        参数：
        - template: 通知模板
        - variables: 变量字典
        
        返回：
        - (title, content) 元组
        """
        title = template.title
        content = template.content

        # 简单的变量替换实现
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"  # {{variable_name}} 格式
            title = title.replace(placeholder, str(value))
            content = content.replace(placeholder, str(value))

        return title, content

    @staticmethod
    def send_notification_by_template(
        recipient_id: int,
        template_name: str,
        notification_type: str,
        variables: Optional[Dict[str, Any]] = None,
        related_model: Optional[str] = None,
        related_id: Optional[int] = None
    ) -> Notification:
        """
        使用模板发送通知
        
        参数：
        - recipient_id: 收件人ID
        - template_name: 模板名称
        - notification_type: 通知类型
        - variables: 模板变量字典
        - related_model: 关联业务模型
        - related_id: 关联业务对象ID
        """
        try:
            template = NotificationTemplate.objects.get(name=template_name, is_active=True)
        except NotificationTemplate.DoesNotExist:
            raise ResourceNotFoundException(
                message=f"通知模板 '{template_name}' 不存在或未启用",
                override_error_code="RESOURCE_NOT_FOUND",
                data={"target_model": "NotificationTemplate", "target_id": template_name}
            )

        variables = variables or {}
        title, content = NotificationService.render_template(template, variables)

        return NotificationService.create_notification(
            recipient_id=recipient_id,
            notification_type=notification_type,
            title=title,
            content=content,
            related_model=related_model,
            related_id=related_id,
            template=template
        )

    @staticmethod
    def send_sms(
        phone_number: str,
        content: str,
        related_model: Optional[str] = None,
        related_id: Optional[int] = None,
        notification: Optional[Notification] = None
    ) -> SMSRecord:
        """
        发送短信
        
        参数：
        - phone_number: 目标手机号
        - content: 短信内容
        - related_model: 关联业务模型
        - related_id: 关联业务对象ID
        - notification: 关联的通知对象
        """
        
        # 验证手机号格式
        if not phone_number or len(phone_number.replace('+', '')) < 11:
            raise BusinessValidationError(
                message=f"手机号 '{phone_number}' 不合法",
                override_error_code="INVALID_PHONE_NUMBER",
                data={"phone_number": phone_number}
            )

        # 验证内容长度
        if not content or len(content) == 0:
            raise BusinessValidationError(
                message="短信内容不能为空",
                override_error_code="EMPTY_SMS_CONTENT",
                data={"phone_number": phone_number}
            )

        with transaction.atomic():
            sms_record = SMSRecord.objects.create(
                phone_number=phone_number,
                content=content,
                related_model=related_model,
                related_id=related_id,
                notification=notification,
                status=SMSRecord.Status.PENDING
            )

            # 检查是否启用了短信功能
            if not NotificationService.SMS_CONFIG['enabled']:
                sms_record.status = SMSRecord.Status.FAILED
                sms_record.error_message = "短信功能未启用"
                sms_record.save(update_fields=['status', 'error_message'])
                logger.warning(f"SMS disabled, skipping SMS to {phone_number}")
                return sms_record

            # 调用短信服务发送
            try:
                provider = NotificationService.SMS_CONFIG['provider']
                
                if provider == 'ALIYUN':
                    success = NotificationService._send_via_aliyun(phone_number, content)
                elif provider == 'TENCENT':
                    success = NotificationService._send_via_tencent(phone_number, content)
                else:  # CUSTOM
                    # 这里可以集成自定义短信服务或日志记录
                    success = NotificationService._send_via_custom(phone_number, content)

                if not success and getattr(settings, 'DEBUG', False) and provider != 'CUSTOM':
                    logger.warning("SMS provider failed in DEBUG; falling back to CUSTOM stub")
                    success = NotificationService._send_via_custom(phone_number, content)

                if success:
                    sms_record.status = SMSRecord.Status.SENT
                    sms_record.sent_at = timezone.now()
                    logger.info(f"SMS sent successfully to {phone_number}")
                else:
                    sms_record.status = SMSRecord.Status.FAILED
                    sms_record.error_message = "短信服务返回失败"
                    logger.error(f"Failed to send SMS to {phone_number}")

            except Exception as e:
                sms_record.status = SMSRecord.Status.FAILED
                sms_record.error_message = str(e)
                logger.error(f"Exception when sending SMS to {phone_number}: {str(e)}")

            sms_record.save(update_fields=['status', 'sent_at', 'error_message'])
            return sms_record

    @staticmethod
    def _send_via_custom(phone_number: str, content: str) -> bool:
        """
        使用自定义短信服务发送（默认实现）
        可根据实际需求集成第三方短信平台
        """
        # TODO: integrate a real provider. In DEBUG, treat as a dev stub.
        logger.info(f"[SMS CUSTOM] Sending to {phone_number}: {content[:50]}...")
        return bool(getattr(settings, 'DEBUG', False))

    @staticmethod
    def _send_via_aliyun(phone_number: str, content: str) -> bool:
        """
        使用阿里云短信服务发送
        需要配置阿里云SDK
        """
        # TODO: 实现阿里云短信发送逻辑
        # from aliyunsdkcore.client import AcsClient
        # from aliyunsdkcore.auth.credentials import SigV4Credentials
        # from aliyunsdkdysmsapi.request.v20170525.SendSmsRequest import SendSmsRequest
        logger.warning("Aliyun SMS service not implemented")
        return False

    @staticmethod
    def _send_via_tencent(phone_number: str, content: str) -> bool:
        """
        使用腾讯云短信服务发送
        需要配置腾讯云SDK
        """
        # TODO: 实现腾讯云短信发送逻辑
        # from tencentcloud.common import credential
        # from tencentcloud.common.profile import client_profile, http_profile
        # from tencentcloud.sms.v20210111 import sms_client, models
        logger.warning("Tencent SMS service not implemented")
        return False

    @staticmethod
    def send_contract_notification(
        contract,
        event_type: str,
        recipient_id: int,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """
        发送合同相关通知
        
        参数：
        - contract: Contract 对象
        - event_type: 事件类型（submitted, approved, rejected等）
        - recipient_id: 收件人ID
        - extra_data: 额外数据字典
        """
        extra_data = extra_data or {}
        
        if event_type == 'submitted':
            title = '合同提交待审核'
            content = f'店铺"{contract.shop.name}"的合同（{contract.start_date} 至 {contract.end_date}）已提交待审核。'
            notification_type = Notification.Type.CONTRACT_SUBMITTED
            
        elif event_type == 'approved':
            title = '合同已批准'
            reviewer_name = extra_data.get('reviewer_name', '管理员')
            content = f'店铺"{contract.shop.name}"的合同已由{reviewer_name}批准并已生效。月租金：¥{contract.monthly_rent}。'
            notification_type = Notification.Type.CONTRACT_APPROVED
            
        elif event_type == 'rejected':
            title = '合同已拒绝'
            reviewer_name = extra_data.get('reviewer_name', '管理员')
            reason = extra_data.get('reason', '请重新提交')
            content = f'店铺"{contract.shop.name}"的合同已被{reviewer_name}拒绝。原因：{reason}'
            notification_type = Notification.Type.CONTRACT_REJECTED
            
        else:
            raise BusinessValidationError(
                message=f"未知的合同事件类型: {event_type}",
                override_error_code="UNKNOWN_EVENT_TYPE",
                data={"event_type": event_type}
            )

        return NotificationService.create_notification(
            recipient_id=recipient_id,
            notification_type=notification_type,
            title=title,
            content=content,
            related_model='Contract',
            related_id=contract.id
        )

    @staticmethod
    def send_payment_reminder(
        finance_record,
        recipient_id: int,
        days_until_due: int
    ) -> tuple[Notification, Optional[SMSRecord]]:
        """
        发送支付提醒通知和短信
        
        参数：
        - finance_record: FinanceRecord 对象
        - recipient_id: 收件人ID
        - days_until_due: 距离截止日期的天数
        
        返回：
        - (notification, sms_record) 元组
        """
        try:
            recipient = User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            raise ResourceNotFoundException(
                message=f"用户 ID {recipient_id} 不存在",
                override_error_code="RESOURCE_NOT_FOUND",
                data={"target_model": "User", "target_id": recipient_id}
            )

        # 创建系统通知
        title = f'支付提醒 (还有{days_until_due}天)'
        content = f'店铺"{finance_record.contract.shop.name}"的 {finance_record.get_fee_type_display()} 账单待缴，金额：¥{finance_record.amount}，截止日期：{finance_record.due_date}。'
        
        notification = NotificationService.create_notification(
            recipient_id=recipient_id,
            notification_type=Notification.Type.PAYMENT_REMINDER,
            title=title,
            content=content,
            related_model='FinanceRecord',
            related_id=finance_record.id
        )

        # 检查用户偏好并发送短信
        sms_record = None
        preference = NotificationService.get_or_create_preference(recipient)
        
        if preference.enable_sms_notification and hasattr(recipient, 'userprofile'):
            phone = recipient.userprofile.phone_number if hasattr(recipient.userprofile, 'phone_number') else None
            if phone:
                sms_content = f'【{finance_record.contract.shop.name}】{finance_record.get_fee_type_display()}账单待缴，金额¥{finance_record.amount}，截止{finance_record.due_date}，请及时缴费。'
                sms_record = NotificationService.send_sms(
                    phone_number=phone,
                    content=sms_content,
                    related_model='FinanceRecord',
                    related_id=finance_record.id,
                    notification=notification
                )

        return notification, sms_record

    @staticmethod
    def get_user_notifications(
        user_id: int,
        limit: int = 20,
        unread_only: bool = False
    ) -> list[Notification]:
        """
        获取用户的通知列表
        
        参数：
        - user_id: 用户ID
        - limit: 返回条数限制
        - unread_only: 是否仅返回未读通知
        """
        try:
            User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ResourceNotFoundException(
                message=f"用户 ID {user_id} 不存在",
                override_error_code="RESOURCE_NOT_FOUND",
                data={"target_model": "User", "target_id": user_id}
            )

        query = Notification.objects.filter(recipient_id=user_id)
        
        if unread_only:
            query = query.filter(is_read=False)
        
        return list(query[:limit])

    @staticmethod
    def mark_as_read(notification_id: int) -> Notification:
        """
        标记通知为已读
        """
        try:
            notification = Notification.objects.get(id=notification_id)
        except Notification.DoesNotExist:
            raise ResourceNotFoundException(
                message=f"通知 ID {notification_id} 不存在",
                override_error_code="RESOURCE_NOT_FOUND",
                data={"target_model": "Notification", "target_id": notification_id}
            )

        notification.mark_as_read()
        return notification

    @staticmethod
    def bulk_mark_as_read(notification_ids: list[int]) -> int:
        """
        批量标记通知为已读
        
        返回：标记数量
        """
        updated_count = Notification.objects.filter(
            id__in=notification_ids,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        return updated_count
