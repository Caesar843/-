from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class BackupRecord(models.Model):
    """
    数据备份记录模型
    
    [架构职责]
    1. 记录备份操作的元信息（时间、大小、类型、状态）
    2. 跟踪备份文件的存储位置和加密信息
    3. 支持备份查询和审计日志
    
    [字段说明]
    - backup_type: 备份类型（FULL 全量，INCREMENTAL 增量）
    - status: 备份状态（PENDING 待处理，RUNNING 进行中，SUCCESS 成功，FAILED 失败）
    - data_types: 备份的数据类型组合（店铺、合约、运营、财务、日志）
    """
    
    BACKUP_TYPE_CHOICES = [
        ('FULL', '全量备份'),
        ('INCREMENTAL', '增量备份'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', '待处理'),
        ('RUNNING', '进行中'),
        ('SUCCESS', '成功'),
        ('FAILED', '失败'),
    ]
    
    DATA_TYPE_CHOICES = [
        ('SHOP', '店铺信息'),
        ('CONTRACT', '合约数据'),
        ('OPERATION', '运营数据'),
        ('FINANCE', '财务记录'),
        ('LOG', '事务日志'),
    ]
    
    # 基本信息
    backup_name = models.CharField(max_length=255, help_text='备份文件名称')
    backup_type = models.CharField(max_length=20, choices=BACKUP_TYPE_CHOICES, default='FULL')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # 数据内容
    data_types = models.JSONField(default=list, help_text='备份包含的数据类型列表')
    
    # 文件信息
    file_path = models.CharField(max_length=500, help_text='备份文件存储路径')
    file_size = models.BigIntegerField(default=0, help_text='备份文件大小（字节）')
    file_hash = models.CharField(max_length=64, blank=True, help_text='备份文件SHA256哈希值')
    
    # 加密信息
    is_encrypted = models.BooleanField(default=False, help_text='是否加密存储')
    encryption_key_id = models.CharField(max_length=50, blank=True, help_text='加密密钥ID')
    
    # 时间信息
    created_at = models.DateTimeField(auto_now_add=True, help_text='备份创建时间')
    backup_start_time = models.DateTimeField(null=True, blank=True, help_text='备份开始时间')
    backup_end_time = models.DateTimeField(null=True, blank=True, help_text='备份结束时间')
    
    # 操作者信息
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, help_text='创建备份的管理员')
    is_automatic = models.BooleanField(default=True, help_text='是否自动备份')
    
    # 恢复相关
    recovery_records = models.IntegerField(default=0, help_text='已使用该备份恢复的次数')
    last_recovered_at = models.DateTimeField(null=True, blank=True, help_text='最后一次恢复时间')
    
    # 备份说明
    description = models.TextField(blank=True, help_text='备份说明或备注')
    error_message = models.TextField(blank=True, help_text='备份失败时的错误信息')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = '备份记录'
        verbose_name_plural = '备份记录'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['backup_type']),
        ]
    
    def __str__(self):
        return f"{self.backup_name} ({self.get_status_display()})"
    
    def is_old(self, days=30):
        """判断备份是否超过指定天数"""
        return (timezone.now() - self.created_at).days > days
    
    def mark_as_recovering(self):
        """标记为正在恢复"""
        self.recovery_records += 1
        self.last_recovered_at = timezone.now()
        self.save()


class BackupLog(models.Model):
    """
    备份操作日志模型
    
    [架构职责]
    1. 记录所有备份/恢复操作的详细日志
    2. 支持操作审计和问题诊断
    3. 跟踪操作进度和详细信息
    """
    
    OPERATION_CHOICES = [
        ('BACKUP', '执行备份'),
        ('RESTORE', '执行恢复'),
        ('VERIFY', '验证备份'),
        ('DELETE', '删除备份'),
        ('DOWNLOAD', '下载备份'),
    ]
    
    LOG_LEVEL_CHOICES = [
        ('INFO', '信息'),
        ('WARNING', '警告'),
        ('ERROR', '错误'),
        ('SUCCESS', '成功'),
    ]
    
    backup_record = models.ForeignKey(BackupRecord, on_delete=models.CASCADE, 
                                     related_name='logs', help_text='关联的备份记录')
    operation = models.CharField(max_length=20, choices=OPERATION_CHOICES, help_text='操作类型')
    log_level = models.CharField(max_length=20, choices=LOG_LEVEL_CHOICES, default='INFO')
    
    message = models.TextField(help_text='日志消息')
    details = models.JSONField(default=dict, blank=True, help_text='操作详细信息')
    
    operated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, help_text='操作者')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = '备份日志'
        verbose_name_plural = '备份日志'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['operation']),
        ]
    
    def __str__(self):
        return f"{self.get_operation_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
