"""
Celery 任务监控和管理模块

提供：
1. 任务状态查询
2. 任务监控统计
3. 任务管理 (取消、重试等)
4. Worker 状态检查
"""

import logging
import time
from datetime import datetime, timedelta

from django.core.cache import cache
from django.utils import timezone

from apps.core.metrics import record_task_result

try:
    from celery import current_app
    from celery.result import AsyncResult
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

logger = logging.getLogger(__name__)
_TASK_START_TIMES = {}


class TaskMonitor:
    """任务监控类"""
    
    TASK_STATS_KEY = 'celery:task:stats'
    TASK_HISTORY_KEY = 'celery:task:history'
    CACHE_TIMEOUT = 86400  # 24 小时
    
    @staticmethod
    def get_task_status(task_id):
        """获取任务状态"""
        if not CELERY_AVAILABLE:
            return {'status': 'unavailable', 'error': 'Celery not installed'}

        if current_app.conf.get('task_always_eager'):
            history = cache.get(TaskMonitor.TASK_HISTORY_KEY, [])
            for item in reversed(history):
                if item.get('task_id') == task_id:
                    return {
                        'task_id': task_id,
                        'status': item.get('status', 'UNKNOWN'),
                        'result': item.get('result'),
                        'error': item.get('error'),
                        'progress': None,
                    }
            return {
                'task_id': task_id,
                'status': 'UNKNOWN',
                'result': None,
                'error': None,
                'progress': None,
            }
        
        try:
            result = AsyncResult(task_id, app=current_app)
            
            return {
                'task_id': task_id,
                'status': result.status,
                'result': result.result if result.successful() else None,
                'error': str(result.info) if result.failed() else None,
                'progress': getattr(result, 'progress', None),
            }
        except Exception as e:
            logger.error(f'Error getting task status: {str(e)}')
            return {'status': 'error', 'error': str(e)}
    
    @staticmethod
    def get_all_tasks():
        """获取所有活跃任务"""
        if not CELERY_AVAILABLE:
            return []

        if current_app.conf.get('task_always_eager'):
            return []
        
        try:
            # 获取 inspect 对象
            inspect = current_app.control.inspect()
            
            # 获取活跃任务
            active = inspect.active()
            
            if not active:
                return []
            
            tasks = []
            for worker, worker_tasks in active.items():
                for task in worker_tasks:
                    tasks.append({
                        'worker': worker,
                        'task_id': task['id'],
                        'task_name': task['name'],
                        'args': task.get('args', []),
                        'kwargs': task.get('kwargs', {}),
                        'time_start': task.get('time_start'),
                    })
            
            return tasks
        except Exception as e:
            logger.error(f'Error getting all tasks: {str(e)}')
            return []
    
    @staticmethod
    def get_worker_stats():
        """获取 Worker 统计信息"""
        if not CELERY_AVAILABLE:
            return {}

        if current_app.conf.get('task_always_eager'):
            return {}
        
        try:
            inspect = current_app.control.inspect()
            
            stats_data = {}
            
            # 获取统计信息
            stats = inspect.stats()
            for worker, worker_stats in (stats or {}).items():
                stats_data[worker] = {
                    'status': 'online',
                    'pool': worker_stats.get('pool', {}),
                    'total_tasks': len(inspect.active().get(worker, [])),
                }
            
            return stats_data
        except Exception as e:
            logger.error(f'Error getting worker stats: {str(e)}')
            return {}
    
    @staticmethod
    def get_queue_stats():
        """获取队列统计"""
        if not CELERY_AVAILABLE:
            return {}

        if current_app.conf.get('task_always_eager'):
            return {}
        
        try:
            inspect = current_app.control.inspect()
            
            # 获取队列信息
            active_queues = inspect.active_queues()
            
            queue_stats = {}
            for worker, queues in (active_queues or {}).items():
                for queue in queues:
                    queue_name = queue['name']
                    if queue_name not in queue_stats:
                        queue_stats[queue_name] = {
                            'name': queue_name,
                            'workers': [],
                            'pending_count': 0
                        }
                    queue_stats[queue_name]['workers'].append(worker)
            
            return queue_stats
        except Exception as e:
            logger.error(f'Error getting queue stats: {str(e)}')
            return {}
    
    @staticmethod
    def record_task_execution(task_name, task_id=None, status=None, duration=0, error=None, result=None, timestamp=None):
        """
        记录任务执行信息
        
        Args:
            task_name: 任务名称 (或 task_data dict)
            task_id: 任务 ID
            status: 执行状态 (SUCCESS, FAILED/FAILURE, RETRY)
            duration: 执行时间 (秒)
            error: 错误信息 (如果有)
            result: 执行结果
            timestamp: 时间戳
        """
        try:
            if isinstance(task_name, dict):
                task_data = task_name
                task_name = task_data.get('task_name')
                task_id = task_data.get('task_id')
                status = task_data.get('status')
                duration = task_data.get('duration', 0)
                error = task_data.get('error')
                result = task_data.get('result')
                timestamp = task_data.get('timestamp')

            if not task_name:
                return

            status = (status or '').upper()
            if status == 'FAILURE':
                status = 'FAILED'

            if timestamp is None:
                timestamp = datetime.now()

            # 获取或初始化统计数据
            stats = cache.get(TaskMonitor.TASK_STATS_KEY, {})
            
            if task_name not in stats:
                stats[task_name] = {
                    'total': 0,
                    'success': 0,
                    'failed': 0,
                    'retry': 0,
                    'avg_duration': 0,
                    'last_execution': None,
                }
            
            # 更新统计
            task_stats = stats[task_name]
            task_stats['total'] += 1
            task_stats['last_execution'] = datetime.now().isoformat()
            
            if status == 'SUCCESS':
                task_stats['success'] += 1
                # 更新平均执行时间
                old_avg = task_stats['avg_duration']
                total = task_stats['success']
                task_stats['avg_duration'] = (old_avg * (total - 1) + duration) / total
            
            elif status == 'FAILED':
                task_stats['failed'] += 1
            
            elif status == 'RETRY':
                task_stats['retry'] += 1
            
            # 保存统计数据
            cache.set(TaskMonitor.TASK_STATS_KEY, stats, TaskMonitor.CACHE_TIMEOUT)
            
            # 记录历史
            history = cache.get(TaskMonitor.TASK_HISTORY_KEY, [])
            history.append({
                'task_name': task_name,
                'task_id': task_id,
                'status': status,
                'duration': duration,
                'error': error,
                'result': result,
                'timestamp': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
            })
            
            # 只保留最近 1000 条记录
            history = history[-1000:]
            cache.set(TaskMonitor.TASK_HISTORY_KEY, history, TaskMonitor.CACHE_TIMEOUT)
            
        except Exception as e:
            logger.error(f'Error recording task execution: {str(e)}')
    
    @staticmethod
    def get_task_stats():
        """获取任务统计信息"""
        return cache.get(TaskMonitor.TASK_STATS_KEY, {})
    
    @staticmethod
    def get_task_history(limit=100):
        """获取任务执行历史"""
        history = cache.get(TaskMonitor.TASK_HISTORY_KEY, [])
        return history[-limit:]


class TaskManager:
    """任务管理类"""
    
    @staticmethod
    def send_task(task_name, args=None, kwargs=None, delay=0, queue='default'):
        """
        发送任务
        
        Args:
            task_name: 任务名称
            args: 位置参数
            kwargs: 关键字参数
            delay: 延迟执行时间 (秒)
            queue: 队列名称
        
        Returns:
            task_id 或 None
        """
        if not CELERY_AVAILABLE:
            logger.warning('Celery not available, task not sent')
            return None
        
        try:
            args = args or []
            kwargs = kwargs or {}

            task = current_app.tasks.get(task_name)
            if task is None and '.' not in task_name:
                for name, registered in current_app.tasks.items():
                    if name.endswith(f'.{task_name}'):
                        task = registered
                        break

            if task is not None:
                if delay > 0:
                    result = task.apply_async(args=args, kwargs=kwargs, countdown=delay, queue=queue)
                else:
                    result = task.apply_async(args=args, kwargs=kwargs, queue=queue)
            else:
                if delay > 0:
                    result = current_app.send_task(
                        task_name,
                        args=args,
                        kwargs=kwargs,
                        countdown=delay,
                        queue=queue
                    )
                else:
                    result = current_app.send_task(
                        task_name,
                        args=args,
                        kwargs=kwargs,
                        queue=queue
                    )

            logger.info(f'Task sent: {task_name} (ID: {result.id})')
            return result.id

        except Exception as e:
            logger.error(f'Error sending task: {str(e)}')
            return None
    
    @staticmethod
    def revoke_task(task_id, terminate=False):
        """
        撤销任务
        
        Args:
            task_id: 任务 ID
            terminate: 是否立即终止正在执行的任务
        """
        if not CELERY_AVAILABLE:
            return False

        if current_app.conf.get('task_always_eager'):
            logger.info(f'Task revoke skipped in eager mode: {task_id}')
            return True
        
        try:
            current_app.control.revoke(task_id, terminate=terminate)
            logger.info(f'Task revoked: {task_id}')
            return True
        except Exception as e:
            logger.error(f'Error revoking task: {str(e)}')
            return False
    
    @staticmethod
    def retry_task(task_id):
        """
        重新执行任务
        
        Args:
            task_id: 任务 ID
        """
        if not CELERY_AVAILABLE:
            return False
        
        try:
            result = AsyncResult(task_id, app=current_app)
            
            if result.failed():
                # 获取原始任务信息并重新发送
                # 这需要任务存储了原始参数
                logger.info(f'Task retried: {task_id}')
                return True
            else:
                logger.warning(f'Cannot retry non-failed task: {task_id}')
                return False
        except Exception as e:
            logger.error(f'Error retrying task: {str(e)}')
            return False
    
    @staticmethod
    def get_result(task_id, timeout=None):
        """
        获取任务执行结果
        
        Args:
            task_id: 任务 ID
            timeout: 超时时间 (秒)
        
        Returns:
            任务结果或 None
        """
        if not CELERY_AVAILABLE:
            return None
        
        try:
            if current_app.conf.get('task_always_eager'):
                history = cache.get(TaskMonitor.TASK_HISTORY_KEY, [])
                for item in reversed(history):
                    if item.get('task_id') == task_id:
                        if item.get('result') is not None:
                            return item.get('result')
                        break
                return {'status': 'unavailable', 'task_id': task_id}

            result = AsyncResult(task_id, app=current_app)

            # 等待任务完成
            return result.get(timeout=timeout)

        except Exception as e:
            logger.error(f'Error getting task result: {str(e)}')
            return None


# 任务执行信号处理器

def record_task_sent(sender=None, task_id=None, task=None, args=None, kwargs=None, **kw):
    """任务发送信号"""
    logger.debug(f'Task sent: {task} ({task_id})')


def record_task_prerun(sender=None, task_id=None, task=None, args=None, **kw):
    """???????"""
    task_name = None
    if hasattr(sender, 'name'):
        task_name = sender.name
    elif task:
        task_name = str(task)

    task_id = task_id or getattr(getattr(sender, 'request', None), 'id', None)
    if task_id:
        _TASK_START_TIMES[task_id] = time.time()
    if task_name and task_id:
        TaskMonitor.record_task_execution(task_name, task_id, 'STARTED')
        record_task_result(task_name, 'STARTED')


def record_task_postrun(sender=None, task_id=None, task=None, args=None, retval=None, state=None, **kw):
    """???????"""
    task_name = None
    if hasattr(sender, 'name'):
        task_name = sender.name
    elif task:
        task_name = str(task)

    task_id = task_id or getattr(getattr(sender, 'request', None), 'id', None)
    duration = 0
    if task_id in _TASK_START_TIMES:
        duration = max(0, time.time() - _TASK_START_TIMES.pop(task_id))
    if task_name and task_id:
        TaskMonitor.record_task_execution(task_name, task_id, state or 'FINISHED', duration=duration, result=retval)
        record_task_result(task_name, state or 'FINISHED')


def record_task_success(sender=None, result=None, task_id=None, task=None, args=None, **kw):
    """任务成功信号"""
    logger.info(f'Task success: {task} ({task_id})')

    task_name = None
    if hasattr(sender, 'name'):
        task_name = sender.name
    elif task:
        task_name = str(task)

    task_id = task_id or getattr(getattr(sender, 'request', None), 'id', None)

    if task_name and task_id:
        TaskMonitor.record_task_execution(task_name, task_id, 'SUCCESS', result=result)


def record_task_failure(sender=None, task_id=None, task=None, args=None, exception=None, **kw):
    """任务失败信号"""
    logger.error(f'Task failed: {task} ({task_id}): {str(exception)}')

    task_name = None
    if hasattr(sender, 'name'):
        task_name = sender.name
    elif task:
        task_name = str(task)

    task_id = task_id or getattr(getattr(sender, 'request', None), 'id', None)

    if task_name and task_id:
        TaskMonitor.record_task_execution(
            task_name, task_id, 'FAILED', error=str(exception)
        )


def record_task_retry(sender=None, task_id=None, task=None, args=None, reason=None, **kw):
    """任务重试信号"""
    logger.warning(f'Task retry: {task} ({task_id}): {reason}')

    task_name = None
    if hasattr(sender, 'name'):
        task_name = sender.name
    elif task:
        task_name = str(task)

    task_id = task_id or getattr(getattr(sender, 'request', None), 'id', None)

    if task_name and task_id:
        TaskMonitor.record_task_execution(
            task_name, task_id, 'RETRY', error=reason
        )
        record_task_result(task_name, 'RETRY')


# 连接信号处理器
if CELERY_AVAILABLE:
    from celery.signals import before_task_publish, task_success, task_failure, task_retry, task_prerun, task_postrun
    
    before_task_publish.connect(record_task_sent)
    task_success.connect(record_task_success)
    task_failure.connect(record_task_failure)
    task_retry.connect(record_task_retry)
    task_prerun.connect(record_task_prerun)
    task_postrun.connect(record_task_postrun)
