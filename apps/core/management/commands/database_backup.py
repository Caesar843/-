"""
Django 管理命令：database_backup

用于备份数据库的 Django 管理命令，可与 Celery Beat 结合使用自动备份。

使用方法:
    python manage.py database_backup                    # 执行备份
    python manage.py database_backup --restore latest   # 恢复最新备份
    python manage.py database_backup --list             # 列出所有备份
    python manage.py database_backup --cleanup 30       # 删除30天前的备份
"""

import os
import sys
import shutil
import subprocess
import gzip
import logging
from pathlib import Path
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """数据库备份管理命令"""
    
    help = '数据库备份和恢复工具'
    
    def add_arguments(self, parser):
        """添加命令行参数"""
        parser.add_argument(
            '--restore',
            metavar='FILE',
            help='恢复备份文件 (latest 表示最新)'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='列出所有备份文件'
        )
        parser.add_argument(
            '--cleanup',
            type=int,
            metavar='DAYS',
            help='删除指定天数前的备份文件'
        )
        parser.add_argument(
            '--no-compress',
            action='store_true',
            help='不压缩备份文件'
        )
    
    def handle(self, *args, **options):
        """命令处理器"""
        try:
            backup_manager = BackupManager()
            
            if options['restore']:
                return self._handle_restore(backup_manager, options['restore'])
            elif options['list']:
                return self._handle_list(backup_manager)
            elif options['cleanup'] is not None:
                return self._handle_cleanup(backup_manager, options['cleanup'])
            else:
                return self._handle_backup(backup_manager, options['no_compress'])
        
        except Exception as e:
            raise CommandError(f'执行出错: {str(e)}')
    
    def _handle_backup(self, backup_manager, no_compress):
        """处理备份"""
        self.stdout.write('开始备份数据库...')
        backup_file = backup_manager.backup(compress=not no_compress)
        
        if backup_file:
            self.stdout.write(
                self.style.SUCCESS(f'✅ 备份成功: {backup_file}')
            )
            return 0
        else:
            self.stdout.write(
                self.style.ERROR('❌ 备份失败')
            )
            return 1
    
    def _handle_restore(self, backup_manager, backup_name):
        """处理恢复"""
        if backup_name == 'latest':
            backups = backup_manager.list_backups()
            if not backups:
                raise CommandError('没有可用的备份文件')
            backup_file = backups[0]['path']
            self.stdout.write(f'恢复最新备份: {backups[0]["file"]}')
        else:
            backup_file = backup_manager.backup_dir / backup_name
        
        if backup_manager.restore(backup_file):
            self.stdout.write(
                self.style.SUCCESS('✅ 数据库恢复成功')
            )
            return 0
        else:
            self.stdout.write(
                self.style.ERROR('❌ 数据库恢复失败')
            )
            return 1
    
    def _handle_list(self, backup_manager):
        """处理列表显示"""
        backups = backup_manager.list_backups()
        
        if not backups:
            self.stdout.write('没有备份文件')
            return 0
        
        self.stdout.write('=' * 100)
        self.stdout.write(f"{'文件名':<45} {'大小':>10} {'创建时间':<25}")
        self.stdout.write('=' * 100)
        
        for backup in backups:
            self.stdout.write(
                f"{backup['file']:<45} "
                f"{backup['size_mb']:>8.2f} MB  "
                f"{backup['time'].strftime('%Y-%m-%d %H:%M:%S'):<25}"
            )
        
        self.stdout.write('=' * 100)
        return 0
    
    def _handle_cleanup(self, backup_manager, days):
        """处理清理"""
        self.stdout.write(f'清理 {days} 天前的备份...')
        deleted = backup_manager.cleanup(days)
        self.stdout.write(
            self.style.SUCCESS(f'✅ 清理完成，删除了 {deleted} 个文件')
        )
        return 0


class BackupManager:
    """备份管理器"""
    
    def __init__(self):
        """初始化"""
        self.backup_dir = Path(settings.BASE_DIR) / 'backups'
        self.backup_dir.mkdir(exist_ok=True)
        
        self.db_config = settings.DATABASES['default']
        self.engine = self.db_config['ENGINE']
    
    def backup(self, compress: bool = True):
        """执行备份"""
        try:
            if 'sqlite' in self.engine:
                return self._backup_sqlite(compress)
            elif 'postgresql' in self.engine:
                return self._backup_postgresql(compress)
            else:
                logger.error(f'不支持的数据库引擎: {self.engine}')
                return None
        except Exception as e:
            logger.error(f'备份失败: {str(e)}')
            return None
    
    def _backup_sqlite(self, compress: bool = True):
        """备份 SQLite"""
        try:
            db_path = Path(settings.BASE_DIR) / self.db_config['NAME']
            
            if not db_path.exists():
                logger.error(f'数据库文件不存在: {db_path}')
                return None
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.backup_dir / f'db_backup_{timestamp}.sqlite3'
            
            shutil.copy2(db_path, backup_file)
            logger.info(f'SQLite 备份完成: {backup_file}')
            
            if compress:
                return self._compress_file(backup_file)
            
            return backup_file
        
        except Exception as e:
            logger.error(f'SQLite 备份失败: {str(e)}')
            return None
    
    def _backup_postgresql(self, compress: bool = True):
        """备份 PostgreSQL"""
        try:
            db_name = self.db_config['NAME']
            db_user = self.db_config.get('USER', 'postgres')
            db_host = self.db_config.get('HOST', 'localhost')
            db_port = self.db_config.get('PORT', 5432)
            db_password = self.db_config.get('PASSWORD')
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.backup_dir / f'db_backup_{timestamp}.sql'
            
            env = os.environ.copy()
            if db_password:
                env['PGPASSWORD'] = db_password
            
            cmd = [
                'pg_dump',
                '-h', str(db_host),
                '-p', str(db_port),
                '-U', db_user,
                '-d', db_name,
                '-F', 'plain',
                '-f', str(backup_file)
            ]
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f'pg_dump 失败: {result.stderr}')
                return None
            
            logger.info(f'PostgreSQL 备份完成: {backup_file}')
            
            if compress:
                return self._compress_file(backup_file)
            
            return backup_file
        
        except Exception as e:
            logger.error(f'PostgreSQL 备份失败: {str(e)}')
            return None
    
    def _compress_file(self, backup_file: Path):
        """压缩文件"""
        try:
            compressed_file = Path(str(backup_file) + '.gz')
            
            with open(backup_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            backup_file.unlink()
            logger.info(f'备份已压缩: {compressed_file}')
            return compressed_file
        
        except Exception as e:
            logger.error(f'压缩失败: {str(e)}')
            return backup_file
    
    def restore(self, backup_file: Path) -> bool:
        """恢复备份"""
        try:
            if not backup_file.exists():
                logger.error(f'备份文件不存在: {backup_file}')
                return False
            
            if 'sqlite' in self.engine:
                return self._restore_sqlite(backup_file)
            elif 'postgresql' in self.engine:
                return self._restore_postgresql(backup_file)
            else:
                logger.error(f'不支持的数据库引擎: {self.engine}')
                return False
        
        except Exception as e:
            logger.error(f'恢复失败: {str(e)}')
            return False
    
    def _restore_sqlite(self, backup_file: Path) -> bool:
        """恢复 SQLite"""
        try:
            db_path = Path(settings.BASE_DIR) / self.db_config['NAME']
            
            if backup_file.suffix == '.gz':
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite3') as tmp:
                    with gzip.open(backup_file, 'rb') as f_in:
                        shutil.copyfileobj(f_in, tmp)
                    source_file = tmp.name
            else:
                source_file = str(backup_file)
            
            # 备份当前数据库
            backup_current = db_path.with_suffix('.sqlite3.backup')
            if db_path.exists():
                shutil.copy2(db_path, backup_current)
                logger.info(f'当前数据库已备份: {backup_current}')
            
            # 恢复
            shutil.copy2(source_file, db_path)
            logger.info(f'SQLite 已恢复: {db_path}')
            return True
        
        except Exception as e:
            logger.error(f'SQLite 恢复失败: {str(e)}')
            return False
    
    def _restore_postgresql(self, backup_file: Path) -> bool:
        """恢复 PostgreSQL"""
        try:
            db_name = self.db_config['NAME']
            db_user = self.db_config.get('USER', 'postgres')
            db_host = self.db_config.get('HOST', 'localhost')
            db_port = self.db_config.get('PORT', 5432)
            db_password = self.db_config.get('PASSWORD')
            
            if backup_file.suffix == '.gz':
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.sql') as tmp:
                    with gzip.open(backup_file, 'rb') as f_in:
                        shutil.copyfileobj(f_in, tmp)
                    source_file = tmp.name
            else:
                source_file = str(backup_file)
            
            env = os.environ.copy()
            if db_password:
                env['PGPASSWORD'] = db_password
            
            with open(source_file, 'r') as f:
                cmd = [
                    'psql',
                    '-h', str(db_host),
                    '-p', str(db_port),
                    '-U', db_user,
                    '-d', db_name,
                ]
                result = subprocess.run(cmd, stdin=f, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f'psql 失败: {result.stderr}')
                return False
            
            logger.info(f'PostgreSQL 已恢复: {db_name}')
            return True
        
        except Exception as e:
            logger.error(f'PostgreSQL 恢复失败: {str(e)}')
            return False
    
    def list_backups(self):
        """列出备份"""
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob('db_backup_*')):
            stat = backup_file.stat()
            backups.append({
                'file': backup_file.name,
                'path': backup_file,
                'size_mb': stat.st_size / (1024 * 1024),
                'time': datetime.fromtimestamp(stat.st_mtime),
            })
        
        return sorted(backups, key=lambda x: x['time'], reverse=True)
    
    def cleanup(self, days: int = 30) -> int:
        """清理旧备份"""
        cutoff_time = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        for backup_file in self.backup_dir.glob('db_backup_*'):
            file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
            
            if file_time < cutoff_time:
                try:
                    backup_file.unlink()
                    logger.info(f'已删除: {backup_file.name}')
                    deleted_count += 1
                except Exception as e:
                    logger.error(f'删除失败 {backup_file.name}: {str(e)}')
        
        logger.info(f'共删除 {deleted_count} 个备份文件')
        return deleted_count
