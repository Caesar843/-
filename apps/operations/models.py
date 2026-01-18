
"""
运营数据模型
-------------
定义运营数据相关的数据模型，包括设备数据、手动上传数据和分析结果
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.store.models import Shop
from django.utils import timezone


class Device(models.Model):
    """
    智能设备模型
    -------------
    管理连接到系统的智能设备信息
    """
    
    class DeviceType(models.TextChoices):
        """设备类型枚举"""
        FOOT_TRAFFIC = 'FOOT_TRAFFIC', _('客流统计仪')
        POS_MACHINE = 'POS_MACHINE', _('POS机')
        ENVIRONMENT_SENSOR = 'ENVIRONMENT_SENSOR', _('环境传感器')
        OTHER = 'OTHER', _('其他设备')
    
    class DeviceStatus(models.TextChoices):
        """设备状态枚举"""
        ONLINE = 'ONLINE', _('在线')
        OFFLINE = 'OFFLINE', _('离线')
        MAINTENANCE = 'MAINTENANCE', _('维护中')
    
    # 设备基本信息
    device_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('设备ID'),
        help_text=_('设备的唯一标识符')
    )
    device_type = models.CharField(
        max_length=30,
        choices=DeviceType.choices,
        verbose_name=_('设备类型'),
        help_text=_('设备的类型')
    )
    device_name = models.CharField(
        max_length=100,
        verbose_name=_('设备名称'),
        help_text=_('设备的名称')
    )
    status = models.CharField(
        max_length=20,
        choices=DeviceStatus.choices,
        default=DeviceStatus.OFFLINE,
        verbose_name=_('设备状态'),
        help_text=_('设备的当前状态')
    )
    
    # 关联信息
    shop = models.ForeignKey(
        Shop,
        on_delete=models.PROTECT,
        related_name='devices',
        verbose_name=_('关联店铺'),
        help_text=_('设备所属的店铺')
    )
    
    # 网络信息
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name=_('IP地址'),
        help_text=_('设备的IP地址')
    )
    mac_address = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('MAC地址'),
        help_text=_('设备的MAC地址')
    )
    
    # 配置信息
    api_key = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_('API密钥'),
        help_text=_('设备调用API的密钥')
    )
    
    # 时间信息
    last_active_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('最后活跃时间'),
        help_text=_('设备最后一次活跃的时间')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('创建时间'),
        help_text=_('设备创建的时间')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('更新时间'),
        help_text=_('设备信息更新的时间')
    )
    
    class Meta:
        """元数据"""
        verbose_name = _('智能设备')
        verbose_name_plural = _('智能设备')
        ordering = ['-created_at']
    
    def __str__(self):
        """字符串表示"""
        return f"{self.device_name} ({self.device_id})"


class DeviceData(models.Model):
    """
    设备数据模型
    -------------
    存储从智能设备采集的原始数据
    """
    
    # 关联设备
    device = models.ForeignKey(
        Device,
        on_delete=models.PROTECT,
        related_name='device_data',
        verbose_name=_('关联设备'),
        help_text=_('数据来源的设备')
    )
    
    # 关联店铺
    shop = models.ForeignKey(
        Shop,
        on_delete=models.PROTECT,
        related_name='device_data',
        verbose_name=_('关联店铺'),
        help_text=_('数据所属的店铺')
    )
    
    # 数据类型
    data_type = models.CharField(
        max_length=50,
        verbose_name=_('数据类型'),
        help_text=_('数据的类型，如客流量、销售额等')
    )
    
    # 数据值
    value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('数据值'),
        help_text=_('数据的具体值')
    )
    
    # 数据时间
    data_time = models.DateTimeField(
        verbose_name=_('数据时间'),
        help_text=_('数据产生的时间')
    )
    
    # 采集时间
    collected_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('采集时间'),
        help_text=_('数据被系统采集的时间')
    )
    
    # 额外信息
    metadata = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_('额外信息'),
        help_text=_('与数据相关的额外信息')
    )
    
    class Meta:
        """元数据"""
        verbose_name = _('设备数据')
        verbose_name_plural = _('设备数据')
        ordering = ['-data_time']
        indexes = [
            models.Index(fields=['shop', 'data_type', 'data_time']),
            models.Index(fields=['device', 'data_time']),
        ]
    
    def __str__(self):
        """字符串表示"""
        return f"{self.shop.name} - {self.data_type}: {self.value} ({self.data_time})"


class ManualOperationData(models.Model):
    """
    手动上传运营数据模型
    -------------
    存储店铺手动上传的运营数据
    """
    
    # 关联店铺
    shop = models.ForeignKey(
        Shop,
        on_delete=models.PROTECT,
        related_name='manual_operation_data',
        verbose_name=_('关联店铺'),
        help_text=_('数据所属的店铺')
    )
    
    # 数据日期
    data_date = models.DateField(
        verbose_name=_('数据日期'),
        help_text=_('数据对应的日期')
    )
    
    # 客流量
    foot_traffic = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_('客流量'),
        help_text=_('店铺的客流量')
    )
    
    # 销售额
    sales_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name=_('销售额'),
        help_text=_('店铺的销售额')
    )
    
    # 交易笔数
    transaction_count = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_('交易笔数'),
        help_text=_('店铺的交易笔数')
    )
    
    # 客单价
    average_transaction_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name=_('客单价'),
        help_text=_('店铺的客单价')
    )
    
    # 其他数据
    other_data = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_('其他数据'),
        help_text=_('其他运营相关数据')
    )
    
    # 上传信息
    uploaded_by = models.CharField(
        max_length=100,
        verbose_name=_('上传人'),
        help_text=_('数据上传人')
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('上传时间'),
        help_text=_('数据上传的时间')
    )
    
    # 备注
    remarks = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('备注'),
        help_text=_('数据的备注信息')
    )
    
    class Meta:
        """元数据"""
        verbose_name = _('手动运营数据')
        verbose_name_plural = _('手动运营数据')
        ordering = ['-data_date']
        unique_together = ['shop', 'data_date']
    
    def __str__(self):
        """字符串表示"""
        return f"{self.shop.name} - {self.data_date}"
    
    def save(self, *args, **kwargs):
        """保存前计算客单价"""
        if self.sales_amount and self.transaction_count and self.transaction_count > 0:
            self.average_transaction_value = self.sales_amount / self.transaction_count
        super().save(*args, **kwargs)


class OperationAnalysis(models.Model):
    """
    运营分析结果模型
    -------------
    存储对运营数据的分析结果
    """
    
    # 关联店铺
    shop = models.ForeignKey(
        Shop,
        on_delete=models.PROTECT,
        related_name='operation_analyses',
        verbose_name=_('关联店铺'),
        help_text=_('分析结果所属的店铺')
    )
    
    # 分析周期
    analysis_period = models.CharField(
        max_length=20,
        verbose_name=_('分析周期'),
        help_text=_('分析的时间周期，如日、周、月等')
    )
    
    # 周期开始和结束时间
    period_start = models.DateTimeField(
        verbose_name=_('周期开始时间'),
        help_text=_('分析周期的开始时间')
    )
    period_end = models.DateTimeField(
        verbose_name=_('周期结束时间'),
        help_text=_('分析周期的结束时间')
    )
    
    # 客流量分析
    total_foot_traffic = models.IntegerField(
        verbose_name=_('总客流量'),
        help_text=_('分析周期内的总客流量')
    )
    average_daily_foot_traffic = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('日均客流量'),
        help_text=_('分析周期内的日均客流量')
    )
    
    # 销售额分析
    total_sales = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('总销售额'),
        help_text=_('分析周期内的总销售额')
    )
    average_daily_sales = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_('日均销售额'),
        help_text=_('分析周期内的日均销售额')
    )
    
    # 客单价分析
    average_transaction_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('客单价'),
        help_text=_('分析周期内的客单价')
    )
    
    # 转化率分析
    conversion_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        verbose_name=_('转化率'),
        help_text=_('分析周期内的转化率')
    )
    
    # 同比分析
    sales_growth_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        blank=True,
        null=True,
        verbose_name=_('销售额增长率'),
        help_text=_('与去年同期相比的销售额增长率')
    )
    foot_traffic_growth_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        blank=True,
        null=True,
        verbose_name=_('客流量增长率'),
        help_text=_('与去年同期相比的客流量增长率')
    )
    
    # 分析结果
    analysis_result = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_('分析结果'),
        help_text=_('详细的分析结果数据')
    )
    
    # 分析时间
    analyzed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('分析时间'),
        help_text=_('分析执行的时间')
    )
    
    class Meta:
        """元数据"""
        verbose_name = _('运营分析结果')
        verbose_name_plural = _('运营分析结果')
        ordering = ['-period_start']
        unique_together = ['shop', 'analysis_period', 'period_start']
    
    def __str__(self):
        """字符串表示"""
        return f"{self.shop.name} - {self.analysis_period} ({self.period_start.date()})"
