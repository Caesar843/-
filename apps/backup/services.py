"""
数据备份和恢复服务模块

[架构职责]
1. BackupService: 处理数据导出、压缩、加密等备份操作
2. RestoreService: 处理备份文件解析、验证、数据导入等恢复操作
3. 支持多种数据源（店铺、合约、运营、财务、日志）
4. 提供备份完整性验证和恢复预检

[设计模式]
- 服务层模式：将复杂业务逻辑从视图和模型中分离
- 工厂模式：支持不同数据导出器的创建和选择
"""

import os
import json
import gzip
import shutil
import hashlib
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from django.db import connection, connections
from django.core.management import call_command
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from io import StringIO

from apps.store.models import Shop, Contract
from apps.operations.models import OperationAnalysis, DeviceData, ManualOperationData
from apps.finance.models import FinanceRecord
from apps.core.exceptions import BusinessValidationError, StateConflictException


class BackupService:
    """
    数据备份服务
    
    功能：
    1. 导出指定类型的数据
    2. 压缩备份文件
    3. 计算文件哈希值
    4. 存储备份文件
    5. 记录备份元信息
    """
    
    # 备份文件配置
    BACKUP_DIR = getattr(settings, 'BACKUP_DIR', os.path.join(settings.BASE_DIR, 'backups'))
    BACKUP_COMPRESSION = getattr(settings, 'BACKUP_COMPRESSION', True)
    BACKUP_ENCRYPTION = getattr(settings, 'BACKUP_ENCRYPTION', False)
    
    def __init__(self):
        """初始化备份服务"""
        # 确保备份目录存在
        Path(self.BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, data_types=None, backup_type='FULL', user=None, 
                     description=''):
        """
        创建数据备份
        
        Args:
            data_types: 要备份的数据类型列表 ['SHOP', 'CONTRACT', 'OPERATION', 'FINANCE', 'LOG']
            backup_type: 备份类型 ('FULL' 或 'INCREMENTAL')
            user: 执行备份的用户
            description: 备份说明
            
        Returns:
            BackupRecord: 备份记录对象
        """
        from apps.backup.models import BackupRecord, BackupLog
        
        if not data_types:
            data_types = ['SHOP', 'CONTRACT', 'OPERATION', 'FINANCE', 'LOG']
        
        # 生成备份文件名
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_{backup_type.lower()}_{timestamp}"
        
        try:
            # 创建备份记录
            backup_record = BackupRecord.objects.create(
                backup_name=backup_name,
                backup_type=backup_type,
                status='RUNNING',
                data_types=data_types,
                file_path='',
                created_by=user,
                description=description,
                is_automatic=(user is None),
                backup_start_time=timezone.now()
            )
            
            # 执行备份
            backup_path = self._perform_backup(backup_record, data_types)
            
            # 更新备份记录
            backup_record.file_path = backup_path
            backup_record.file_size = os.path.getsize(backup_path)
            backup_record.file_hash = self._calculate_file_hash(backup_path)
            backup_record.status = 'SUCCESS'
            backup_record.backup_end_time = timezone.now()
            backup_record.save()
            
            # 记录日志
            BackupLog.objects.create(
                backup_record=backup_record,
                operation='BACKUP',
                log_level='SUCCESS',
                message=f'Backup {backup_type} created with {len(data_types)} data types',
                operated_by=user,
                details={
                    'data_types': data_types,
                    'file_size': backup_record.file_size,
                    'duration_seconds': (backup_record.backup_end_time - 
                                       backup_record.backup_start_time).total_seconds()
                }
            )
            
            return backup_record
            
        except Exception as e:
            # 更新失败状态
            backup_record.status = 'FAILED'
            backup_record.error_message = str(e)
            backup_record.backup_end_time = timezone.now()
            backup_record.save()
            
            # 记录错误日志
            BackupLog.objects.create(
                backup_record=backup_record,
                operation='BACKUP',
                log_level='ERROR',
                message=f'备份失败: {str(e)}',
                operated_by=user,
                details={'error': str(e)}
            )
            
            raise BusinessValidationError(f'备份创建失败: {str(e)}')
    
    def _perform_backup(self, backup_record, data_types):
        """
        执行实际的备份操作
        
        Returns:
            str: 备份文件路径
        """
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        
        try:
            backup_data = {}
            
            # 导出各种数据类型
            if 'SHOP' in data_types:
                backup_data['shops'] = self._export_shops()
            
            if 'CONTRACT' in data_types:
                backup_data['contracts'] = self._export_contracts()
            
            if 'OPERATION' in data_types:
                backup_data['operations'] = self._export_operations()
            
            if 'FINANCE' in data_types:
                backup_data['finance'] = self._export_finance()
            
            if 'LOG' in data_types:
                backup_data['logs'] = self._export_logs()
            
            # 添加元信息
            backup_data['metadata'] = {
                'backup_time': timezone.now().isoformat(),
                'backup_type': backup_record.backup_type,
                'data_types': data_types,
                'django_version': self._get_django_version(),
                'database': settings.DATABASES['default']['ENGINE']
            }
            
            # 写入JSON文件
            json_path = os.path.join(temp_dir, 'backup.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)
            
            # 压缩备份文件
            backup_path = self._compress_backup(temp_dir, backup_record.backup_name)
            
            return backup_path
            
        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _export_shops(self):
        """导出店铺数据"""
        shops = Shop.objects.all().values(
            'id', 'name', 'business_type', 'area', 'rent', 'contact_person',
            'contact_phone', 'entry_date', 'description', 'is_deleted',
            'created_at', 'updated_at'
        )
        return list(shops)
    
    def _export_contracts(self):
        """导出合约数据"""
        contracts = Contract.objects.all().values(
            'id', 'shop_id', 'start_date', 'end_date', 'monthly_rent',
            'deposit', 'payment_cycle', 'status', 'reviewed_by_id',
            'reviewed_at', 'review_comment', 'created_at', 'updated_at'
        )
        return list(contracts)
    
    def _export_operations(self):
        """导出运营数据"""
        operations = {
            'device_data': list(DeviceData.objects.all().values()),
            'manual_data': list(ManualOperationData.objects.all().values()),
            'analysis': list(OperationAnalysis.objects.all().values())
        }
        return operations
    
    def _export_finance(self):
        """导出财务数据"""
        finance = FinanceRecord.objects.all().values(
            'id', 'contract_id', 'amount', 'fee_type', 'status', 'payment_method',
            'billing_period_start', 'billing_period_end', 'paid_at',
            'transaction_id', 'reminder_sent', 'created_at', 'updated_at'
        )
        return list(finance)
    
    def _export_logs(self):
        """导出事务日志"""
        from django.contrib.admin.models import LogEntry
        logs = LogEntry.objects.all().values()
        return list(logs)
    
    def _compress_backup(self, source_dir, backup_name):
        """
        压缩备份文件
        
        Args:
            source_dir: 源目录
            backup_name: 备份名称
            
        Returns:
            str: 压缩文件路径
        """
        backup_path = os.path.join(self.BACKUP_DIR, f"{backup_name}.tar.gz")
        
        # 使用tar.gz格式压缩
        shutil.make_archive(
            backup_path.replace('.tar.gz', ''),
            'gztar',
            source_dir
        )
        
        return backup_path
    
    def _calculate_file_hash(self, file_path):
        """计算文件SHA256哈希值"""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    def _get_django_version(self):
        """获取Django版本"""
        import django
        return django.get_version()
    
    def delete_old_backups(self, days=30):
        """
        删除超过指定天数的旧备份
        
        Args:
            days: 保留天数
            
        Returns:
            int: 删除的备份数量
        """
        from apps.backup.models import BackupRecord, BackupLog
        
        cutoff_date = timezone.now() - timedelta(days=days)
        old_backups = BackupRecord.objects.filter(created_at__lt=cutoff_date)
        
        deleted_count = 0
        for backup in old_backups:
            try:
                # 删除物理文件
                if os.path.exists(backup.file_path):
                    os.remove(backup.file_path)
                
                # 记录删除日志
                BackupLog.objects.create(
                    backup_record=backup,
                    operation='DELETE',
                    log_level='SUCCESS',
                    message=f'已删除旧备份（超过{days}天）'
                )
                
                # 删除数据库记录
                backup.delete()
                deleted_count += 1
            except Exception as e:
                print(f"删除备份 {backup.backup_name} 失败: {str(e)}")
        
        return deleted_count


class RestoreService:
    """
    数据恢复服务
    
    功能：
    1. 解析备份文件
    2. 验证备份完整性
    3. 执行数据恢复
    4. 恢复前数据完整性检查
    """
    
    def __init__(self):
        """初始化恢复服务"""
        self.backup_dir = getattr(settings, 'BACKUP_DIR', 
                                 os.path.join(settings.BASE_DIR, 'backups'))
    
    def restore_from_backup(self, backup_record, user=None):
        """
        从备份文件恢复数据
        
        Args:
            backup_record: BackupRecord 对象
            user: 执行恢复的用户
            
        Returns:
            dict: 恢复结果统计
        """
        from apps.backup.models import BackupLog
        
        if not os.path.exists(backup_record.file_path):
            raise FileNotFoundError(f'备份文件不存在: {backup_record.file_path}')
        
        # 验证文件哈希值
        file_hash = hashlib.sha256()
        with open(backup_record.file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                file_hash.update(byte_block)
        
        if file_hash.hexdigest() != backup_record.file_hash:
            raise StateConflictException('备份文件完整性检查失败，文件可能已损坏')
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 解压备份文件
            self._extract_backup(backup_record.file_path, temp_dir)
            
            # 读取备份数据
            json_path = os.path.join(temp_dir, 'backup.json')
            with open(json_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # 恢复各类型数据
            restore_stats = {}
            
            if 'shops' in backup_data:
                restore_stats['shops'] = self._restore_shops(backup_data['shops'])
            
            if 'contracts' in backup_data:
                restore_stats['contracts'] = self._restore_contracts(backup_data['contracts'])
            
            if 'operations' in backup_data:
                restore_stats['operations'] = self._restore_operations(backup_data['operations'])
            
            if 'finance' in backup_data:
                restore_stats['finance'] = self._restore_finance(backup_data['finance'])
            
            # 标记备份为已恢复
            backup_record.mark_as_recovering()
            
            # 记录恢复日志
            BackupLog.objects.create(
                backup_record=backup_record,
                operation='RESTORE',
                log_level='SUCCESS',
                message='成功从备份恢复数据',
                operated_by=user,
                details=restore_stats
            )
            
            return restore_stats
            
        except Exception as e:
            # 记录恢复失败日志
            BackupLog.objects.create(
                backup_record=backup_record,
                operation='RESTORE',
                log_level='ERROR',
                message=f'数据恢复失败: {str(e)}',
                operated_by=user,
                details={'error': str(e)}
            )
            raise BusinessValidationError(f'数据恢复失败: {str(e)}')
        
        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _extract_backup(self, backup_path, extract_dir):
        """解压备份文件"""
        shutil.unpack_archive(backup_path, extract_dir)
    
    def _restore_shops(self, shops_data):
        """恢复店铺数据"""
        from apps.store.models import Shop
        
        restored = 0
        for shop_data in shops_data:
            shop_id = shop_data.pop('id')
            Shop.objects.update_or_create(id=shop_id, defaults=shop_data)
            restored += 1
        
        return restored
    
    def _restore_contracts(self, contracts_data):
        """恢复合约数据"""
        from apps.store.models import Contract
        
        restored = 0
        for contract_data in contracts_data:
            contract_id = contract_data.pop('id')
            Contract.objects.update_or_create(id=contract_id, defaults=contract_data)
            restored += 1
        
        return restored
    
    def _restore_operations(self, operations_data):
        """恢复运营数据"""
        from apps.operations.models import DeviceData, ManualOperationData, OperationAnalysis
        
        restored = {
            'device_data': 0,
            'manual_data': 0,
            'analysis': 0
        }
        
        for device_data in operations_data.get('device_data', []):
            device_id = device_data.pop('id', None)
            if device_id:
                DeviceData.objects.update_or_create(id=device_id, defaults=device_data)
            restored['device_data'] += 1
        
        for manual_data in operations_data.get('manual_data', []):
            manual_id = manual_data.pop('id', None)
            if manual_id:
                ManualOperationData.objects.update_or_create(id=manual_id, defaults=manual_data)
            restored['manual_data'] += 1
        
        for analysis in operations_data.get('analysis', []):
            analysis_id = analysis.pop('id', None)
            if analysis_id:
                OperationAnalysis.objects.update_or_create(id=analysis_id, defaults=analysis)
            restored['analysis'] += 1
        
        return restored
    
    def _restore_finance(self, finance_data):
        """恢复财务数据"""
        from apps.finance.models import FinanceRecord
        
        restored = 0
        for record_data in finance_data:
            record_id = record_data.pop('id')
            FinanceRecord.objects.update_or_create(id=record_id, defaults=record_data)
            restored += 1
        
        return restored
