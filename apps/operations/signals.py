
"""
运营数据信号处理
-------------
处理运营数据相关的信号
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.operations.models import DeviceData, ManualOperationData
from django.utils import timezone


@receiver(post_save, sender=DeviceData)
def handle_device_data_created(sender, instance, created, **kwargs):
    """
    处理设备数据创建信号
    """
    if created:
        # 这里可以添加数据处理逻辑
        # 例如触发数据分析、发送通知等
        pass


@receiver(post_save, sender=ManualOperationData)
def handle_manual_data_created(sender, instance, created, **kwargs):
    """
    处理手动数据创建信号
    """
    if created:
        # 这里可以添加数据处理逻辑
        # 例如触发数据分析、发送通知等
        pass
