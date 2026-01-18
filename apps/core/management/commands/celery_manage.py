"""
Celery 任务管理命令

使用方式：
    python manage.py celery_manage --list-tasks
    python manage.py celery_manage --send-task apps.finance.tasks.check_pending_bills
    python manage.py celery_manage --task-status <task_id>
    python manage.py celery_manage --revoke-task <task_id>
    python manage.py celery_manage --worker-stats
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from io import StringIO

from apps.core.celery_monitor import TaskMonitor, TaskManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Celery 管理命令"""
    
    help = '管理 Celery 异步任务'
    
    def add_arguments(self, parser):
        """添加命令参数"""
        
        # 列出任务
        parser.add_argument(
            '--list-tasks',
            action='store_true',
            help='列出所有活跃任务'
        )
        
        # 发送任务
        parser.add_argument(
            '--send-task',
            metavar='TASK_NAME',
            help='发送任务 (e.g., apps.finance.tasks.check_pending_bills)'
        )
        
        # 任务参数
        parser.add_argument(
            '--args',
            metavar='ARGS',
            help='任务位置参数 (JSON 格式)'
        )
        
        parser.add_argument(
            '--kwargs',
            metavar='KWARGS',
            help='任务关键字参数 (JSON 格式)'
        )
        
        # 查看任务状态
        parser.add_argument(
            '--task-status',
            metavar='TASK_ID',
            help='查看任务状态'
        )
        
        # 撤销任务
        parser.add_argument(
            '--revoke-task',
            metavar='TASK_ID',
            help='撤销任务'
        )
        
        # Worker 信息
        parser.add_argument(
            '--worker-stats',
            action='store_true',
            help='显示 Worker 统计信息'
        )
        
        # 队列信息
        parser.add_argument(
            '--queue-stats',
            action='store_true',
            help='显示队列信息'
        )
        
        # 任务统计
        parser.add_argument(
            '--task-stats',
            action='store_true',
            help='显示任务执行统计'
        )
        
        # 任务历史
        parser.add_argument(
            '--history',
            action='store_true',
            help='显示任务执行历史'
        )
        
        # 测试任务
        parser.add_argument(
            '--test-task',
            action='store_true',
            help='发送测试任务'
        )
    
    def handle(self, *args, **options):
        """处理命令"""
        
        # 列出任务
        if options['list_tasks']:
            self.list_tasks()
        
        # 发送任务
        elif options['send_task']:
            self.send_task(
                options['send_task'],
                options.get('args'),
                options.get('kwargs')
            )
        
        # 查看任务状态
        elif options['task_status']:
            self.task_status(options['task_status'])
        
        # 撤销任务
        elif options['revoke_task']:
            self.revoke_task(options['revoke_task'])
        
        # Worker 信息
        elif options['worker_stats']:
            self.worker_stats()
        
        # 队列信息
        elif options['queue_stats']:
            self.queue_stats()
        
        # 任务统计
        elif options['task_stats']:
            self.task_stats()
        
        # 任务历史
        elif options['history']:
            self.task_history()
        
        # 测试任务
        elif options['test_task']:
            self.test_task()
        
        else:
            self.stdout.write(self.style.WARNING('请指定一个操作'))
            self.print_help('manage.py', 'celery_manage')
    
    def list_tasks(self):
        """列出所有活跃任务"""
        self.stdout.write(self.style.SUCCESS('\n=== 活跃任务 ===\n'))
        
        tasks = TaskMonitor.get_all_tasks()
        
        if not tasks:
            self.stdout.write('没有活跃任务')
            return
        
        self.stdout.write(f'{'任务ID':<36} {'任务名称':<40} {'Worker':<20}')
        self.stdout.write('-' * 96)
        
        for task in tasks:
            self.stdout.write(
                f"{task['task_id']:<36} "
                f"{task['task_name']:<40} "
                f"{task['worker']:<20}"
            )
        
        self.stdout.write(f'\n总计: {len(tasks)} 个任务\n')
    
    def send_task(self, task_name, args_str=None, kwargs_str=None):
        """发送任务"""
        import json
        
        try:
            args = []
            kwargs = {}
            
            if args_str:
                args = json.loads(args_str)
            
            if kwargs_str:
                kwargs = json.loads(kwargs_str)
            
            task_id = TaskManager.send_task(task_name, args=args, kwargs=kwargs)
            
            if task_id:
                self.stdout.write(self.style.SUCCESS(
                    f'✓ 任务已发送\n'
                    f'  任务: {task_name}\n'
                    f'  ID: {task_id}\n'
                ))
            else:
                raise CommandError('发送任务失败')
        
        except json.JSONDecodeError as e:
            raise CommandError(f'JSON 格式错误: {str(e)}')
        except Exception as e:
            raise CommandError(f'发送任务失败: {str(e)}')
    
    def task_status(self, task_id):
        """查看任务状态"""
        self.stdout.write(self.style.SUCCESS('\n=== 任务状态 ===\n'))
        
        status_info = TaskMonitor.get_task_status(task_id)
        
        self.stdout.write(f'任务 ID: {task_id}')
        self.stdout.write(f'状态: {status_info["status"]}')
        
        if status_info.get('result'):
            self.stdout.write(f'结果: {status_info["result"]}')
        
        if status_info.get('error'):
            self.stdout.write(f'错误: {status_info["error"]}')
        
        self.stdout.write()
    
    def revoke_task(self, task_id):
        """撤销任务"""
        try:
            success = TaskManager.revoke_task(task_id, terminate=True)
            
            if success:
                self.stdout.write(self.style.SUCCESS(
                    f'✓ 任务已撤销: {task_id}\n'
                ))
            else:
                raise CommandError(f'撤销任务失败: {task_id}')
        
        except Exception as e:
            raise CommandError(f'撤销任务失败: {str(e)}')
    
    def worker_stats(self):
        """显示 Worker 统计信息"""
        self.stdout.write(self.style.SUCCESS('\n=== Worker 信息 ===\n'))
        
        workers = TaskMonitor.get_worker_stats()
        
        if not workers:
            self.stdout.write('没有在线 Worker')
            return
        
        for worker_name, worker_info in workers.items():
            self.stdout.write(f'\nWorker: {worker_name}')
            self.stdout.write(f'  状态: {worker_info["status"]}')
            self.stdout.write(f'  活跃任务: {worker_info["total_tasks"]}')
        
        self.stdout.write(f'\n总计: {len(workers)} 个 Worker\n')
    
    def queue_stats(self):
        """显示队列信息"""
        self.stdout.write(self.style.SUCCESS('\n=== 队列信息 ===\n'))
        
        queues = TaskMonitor.get_queue_stats()
        
        if not queues:
            self.stdout.write('没有队列信息')
            return
        
        for queue_name, queue_info in queues.items():
            self.stdout.write(f'\n队列: {queue_name}')
            self.stdout.write(f'  Workers: {", ".join(queue_info["workers"])}')
            self.stdout.write(f'  待处理: {queue_info["pending_count"]}')
        
        self.stdout.write(f'\n总计: {len(queues)} 个队列\n')
    
    def task_stats(self):
        """显示任务执行统计"""
        self.stdout.write(self.style.SUCCESS('\n=== 任务执行统计 ===\n'))
        
        stats = TaskMonitor.get_task_stats()
        
        if not stats:
            self.stdout.write('没有任务统计数据')
            return
        
        self.stdout.write(f'{'任务名称':<40} {'总数':<8} {'成功':<8} {'失败':<8} {'重试':<8}')
        self.stdout.write('-' * 72)
        
        for task_name, task_stats in stats.items():
            self.stdout.write(
                f'{task_name:<40} '
                f'{task_stats["total"]:<8} '
                f'{task_stats["success"]:<8} '
                f'{task_stats["failed"]:<8} '
                f'{task_stats["retry"]:<8}'
            )
        
        self.stdout.write()
    
    def task_history(self):
        """显示任务执行历史"""
        self.stdout.write(self.style.SUCCESS('\n=== 任务执行历史 ===\n'))
        
        history = TaskMonitor.get_task_history(limit=20)
        
        if not history:
            self.stdout.write('没有执行历史')
            return
        
        self.stdout.write(f'{'任务名称':<40} {'状态':<10} {'时间':<20}')
        self.stdout.write('-' * 70)
        
        for record in reversed(history):
            self.stdout.write(
                f'{record["task_name"]:<40} '
                f'{record["status"]:<10} '
                f'{record["timestamp"]:<20}'
            )
        
        self.stdout.write(f'\n总计: {len(history)} 条记录\n')
    
    def test_task(self):
        """发送测试任务"""
        try:
            task_id = TaskManager.send_task(
                'apps.core.celery_tasks.test_task',
                args=['test_value']
            )
            
            self.stdout.write(self.style.SUCCESS(
                f'✓ 测试任务已发送\n'
                f'  任务 ID: {task_id}\n'
                f'  查询状态: python manage.py celery_manage --task-status {task_id}\n'
            ))
        
        except Exception as e:
            raise CommandError(f'发送测试任务失败: {str(e)}')
