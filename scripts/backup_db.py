#!/usr/bin/env python
"""
数据库备份脚本

支持 SQLite 和 PostgreSQL 数据库的自动备份。

使用方法:
    python scripts/backup_db.py                    # 执行备份
    python scripts/backup_db.py --restore latest   # 恢复最新备份
    python scripts/backup_db.py --list             # 列出所有备份
    python scripts/backup_db.py --cleanup 30       # 删除30天前的备份
"""

import os
import sys
import shutil
import subprocess
import argparse
import gzip
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 备份配置
BACKUP_DIR = BASE_DIR / 'backups'
BACKUP_DIR.mkdir(exist_ok=True)

# Django 设置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')


class DatabaseBackup:
    """数据库备份管理器"""
    
    def __init__(self):
        """初始化备份管理器"""
        import django
        django.setup()
        
        from django.conf import settings
        self.settings = settings
        self.db_config = settings.DATABASES['default']
        self.engine = self.db_config['ENGINE']
    
    def backup(self, compress: bool = True) -> Optional[Path]:
        """
        执行数据库备份
        
        Args:
            compress: 是否压缩备份文件
            
        Returns:
            备份文件路径，失败返回 None
        """
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
    
    def _backup_sqlite(self, compress: bool = True) -> Optional[Path]:
        """备份 SQLite 数据库"""
        try:
            db_path = BASE_DIR / self.db_config['NAME']
            
            if not db_path.exists():
                logger.error(f'数据库文件不存在: {db_path}')
                return None
            
            # 生成备份文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = BACKUP_DIR / f'db_backup_{timestamp}.sqlite3'
            
            # 复制数据库文件
            shutil.copy2(db_path, backup_file)
            logger.info(f'数据库备份完成: {backup_file}')
            
            # 压缩备份
            if compress:
                return self._compress_backup(backup_file)
            
            return backup_file
        
        except Exception as e:
            logger.error(f'SQLite 备份失败: {str(e)}')
            return None
    
    def _backup_postgresql(self, compress: bool = True) -> Optional[Path]:
        """备份 PostgreSQL 数据库"""
        try:
            # 获取数据库配置
            db_name = self.db_config['NAME']
            db_user = self.db_config.get('USER', 'postgres')
            db_host = self.db_config.get('HOST', 'localhost')
            db_port = self.db_config.get('PORT', 5432)
            db_password = self.db_config.get('PASSWORD')
            
            # 生成备份文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = BACKUP_DIR / f'db_backup_{timestamp}.sql'
            
            # 构建 pg_dump 命令
            env = os.environ.copy()
            if db_password:
                env['PGPASSWORD'] = db_password
            
            cmd = [
                'pg_dump',
                '-h', db_host,
                '-p', str(db_port),
                '-U', db_user,
                '-d', db_name,
                '-F', 'plain',
                '-f', str(backup_file)
            ]
            
            # 执行备份
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f'pg_dump 失败: {result.stderr}')
                return None
            
            logger.info(f'数据库备份完成: {backup_file}')
            
            # 压缩备份
            if compress:
                return self._compress_backup(backup_file)
            
            return backup_file
        
        except FileNotFoundError:
            logger.error('pg_dump 命令未找到，请确保已安装 PostgreSQL 客户端')
            return None
        except Exception as e:
            logger.error(f'PostgreSQL 备份失败: {str(e)}')
            return None
    
    def _compress_backup(self, backup_file: Path) -> Optional[Path]:
        """压缩备份文件"""
        try:
            compressed_file = Path(str(backup_file) + '.gz')
            
            with open(backup_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # 删除原始文件
            backup_file.unlink()
            logger.info(f'备份文件已压缩: {compressed_file}')
            
            return compressed_file
        
        except Exception as e:
            logger.error(f'压缩备份失败: {str(e)}')
            return backup_file
    
    def restore(self, backup_file: Path) -> bool:
        """
        恢复数据库备份
        
        Args:
            backup_file: 备份文件路径
            
        Returns:
            成功返回 True，失败返回 False
        """
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
        """恢复 SQLite 数据库"""
        try:
            db_path = BASE_DIR / self.db_config['NAME']
            
            # 处理压缩文件
            if backup_file.suffix == '.gz':
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite3') as tmp:
                    with gzip.open(backup_file, 'rb') as f_in:
                        shutil.copyfileobj(f_in, tmp)
                    source_file = tmp.name
            else:
                source_file = backup_file
            
            # 创建备份
            backup_current = db_path.with_suffix('.sqlite3.backup')
            if db_path.exists():
                shutil.copy2(db_path, backup_current)
                logger.info(f'当前数据库已备份: {backup_current}')
            
            # 恢复备份
            shutil.copy2(source_file, db_path)
            logger.info(f'数据库已恢复: {db_path}')
            
            return True
        
        except Exception as e:
            logger.error(f'SQLite 恢复失败: {str(e)}')
            return False
    
    def _restore_postgresql(self, backup_file: Path) -> bool:
        """恢复 PostgreSQL 数据库"""
        try:
            db_name = self.db_config['NAME']
            db_user = self.db_config.get('USER', 'postgres')
            db_host = self.db_config.get('HOST', 'localhost')
            db_port = self.db_config.get('PORT', 5432)
            db_password = self.db_config.get('PASSWORD')
            
            # 处理压缩文件
            if backup_file.suffix == '.gz':
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.sql') as tmp:
                    with gzip.open(backup_file, 'rb') as f_in:
                        shutil.copyfileobj(f_in, tmp)
                    source_file = tmp.name
            else:
                source_file = backup_file
            
            env = os.environ.copy()
            if db_password:
                env['PGPASSWORD'] = db_password
            
            # 恢复备份
            with open(source_file, 'r') as f:
                cmd = [
                    'psql',
                    '-h', db_host,
                    '-p', str(db_port),
                    '-U', db_user,
                    '-d', db_name,
                ]
                result = subprocess.run(cmd, stdin=f, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f'psql 失败: {result.stderr}')
                return False
            
            logger.info(f'数据库已恢复: {db_name}')
            return True
        
        except Exception as e:
            logger.error(f'PostgreSQL 恢复失败: {str(e)}')
            return False
    
    def list_backups(self) -> List[dict]:
        """列出所有备份文件"""
        backups = []
        
        for backup_file in sorted(BACKUP_DIR.glob('db_backup_*')):
            stat = backup_file.stat()
            backups.append({
                'file': backup_file.name,
                'path': backup_file,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'time': datetime.fromtimestamp(stat.st_mtime),
            })
        
        return sorted(backups, key=lambda x: x['time'], reverse=True)
    
    def cleanup(self, days: int = 30) -> int:
        """
        删除指定天数前的备份
        
        Args:
            days: 保留的天数
            
        Returns:
            删除的文件数
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        for backup_file in BACKUP_DIR.glob('db_backup_*'):
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


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Django 数据库备份和恢复工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 执行备份
  python scripts/backup_db.py
  
  # 恢复最新备份
  python scripts/backup_db.py --restore latest
  
  # 恢复指定备份
  python scripts/backup_db.py --restore db_backup_20260116_153000.sqlite3.gz
  
  # 列出所有备份
  python scripts/backup_db.py --list
  
  # 删除30天前的备份
  python scripts/backup_db.py --cleanup 30
        '''
    )
    
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
    
    args = parser.parse_args()
    
    try:
        backup = DatabaseBackup()
        
        if args.restore:
            logger.info(f'恢复备份: {args.restore}')
            
            if args.restore == 'latest':
                backups = backup.list_backups()
                if not backups:
                    logger.error('没有可用的备份文件')
                    return 1
                backup_file = backups[0]['path']
            else:
                backup_file = BACKUP_DIR / args.restore
            
            if backup.restore(backup_file):
                logger.info('✅ 数据库恢复成功')
                return 0
            else:
                logger.error('❌ 数据库恢复失败')
                return 1
        
        elif args.list:
            backups = backup.list_backups()
            if not backups:
                logger.info('没有备份文件')
                return 0
            
            logger.info('=' * 80)
            logger.info('备份文件列表')
            logger.info('=' * 80)
            for backup in backups:
                logger.info(
                    f"{backup['file']:<45} "
                    f"{backup['size_mb']:>8} MB  "
                    f"{backup['time'].strftime('%Y-%m-%d %H:%M:%S')}"
                )
            logger.info('=' * 80)
            return 0
        
        elif args.cleanup is not None:
            logger.info(f'清理 {args.cleanup} 天前的备份')
            deleted = backup.cleanup(args.cleanup)
            logger.info(f'✅ 清理完成，删除了 {deleted} 个文件')
            return 0
        
        else:
            # 默认执行备份
            logger.info('开始备份数据库...')
            backup_file = backup.backup(compress=not args.no_compress)
            
            if backup_file:
                logger.info(f'✅ 备份成功: {backup_file}')
                return 0
            else:
                logger.error('❌ 备份失败')
                return 1
    
    except Exception as e:
        logger.error(f'执行出错: {str(e)}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
