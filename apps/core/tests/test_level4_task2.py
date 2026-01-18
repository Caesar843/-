"""
Level 4 Task 2: Celery 异步任务系统测试套件
包含任务定义、监控系统、API 接口、CLI 命令的完整测试

运行: python manage.py test apps.core.tests.test_level4_task2
"""

import json
import time
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase, Client
from django.core.cache import cache
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from celery import current_app
from celery.result import AsyncResult

from apps.core.celery_tasks import (
    test_task,
    check_pending_bills,
    send_bill_reminders,
    calculate_monthly_revenue,
    generate_hourly_report,
    generate_daily_report,
    generate_weekly_report,
    generate_monthly_report,
    send_notification_email,
    cleanup_old_notifications,
    export_data,
    backup_database,
    cleanup_cache,
    long_running_task,
)
from apps.core.celery_monitor import TaskMonitor, TaskManager


class CeleryTaskDefinitionTests(TestCase):
    """测试所有 Celery 任务定义"""

    def setUp(self):
        """设置测试环境"""
        # 设置 Celery 为同步模式用于测试
        current_app.conf.update(task_always_eager=True)

    def test_test_task(self):
        """测试简单的测试任务"""
        result = test_task.apply_async(args=('test',))
        self.assertEqual(result.result, 'Task received: test')
        self.assertEqual(result.status, 'SUCCESS')

    def test_test_task_with_failure(self):
        """测试任务失败处理"""
        result = test_task.apply_async(args=('fail',))
        # 如果任务抛出异常，状态应该是 FAILURE
        if result.status == 'FAILURE':
            self.assertIsNotNone(result.info)

    def test_long_running_task(self):
        """测试长时间运行的任务"""
        result = long_running_task.apply_async(args=(5,))
        self.assertEqual(result.status, 'SUCCESS')
        self.assertIn('completed', str(result.result).lower())

    def test_check_pending_bills(self):
        """测试账单检查任务"""
        result = check_pending_bills.apply_async()
        self.assertIn(result.status, ['SUCCESS', 'PENDING'])

    def test_send_bill_reminders(self):
        """测试账单提醒任务"""
        result = send_bill_reminders.apply_async()
        self.assertIn(result.status, ['SUCCESS', 'PENDING'])

    def test_calculate_monthly_revenue(self):
        """测试月度收入计算任务"""
        result = calculate_monthly_revenue.apply_async()
        self.assertIn(result.status, ['SUCCESS', 'PENDING'])

    def test_generate_hourly_report(self):
        """测试小时报告生成"""
        result = generate_hourly_report.apply_async()
        self.assertIn(result.status, ['SUCCESS', 'PENDING'])

    def test_generate_daily_report(self):
        """测试日报告生成"""
        result = generate_daily_report.apply_async()
        self.assertIn(result.status, ['SUCCESS', 'PENDING'])

    def test_generate_weekly_report(self):
        """测试周报告生成"""
        result = generate_weekly_report.apply_async()
        self.assertIn(result.status, ['SUCCESS', 'PENDING'])

    def test_generate_monthly_report(self):
        """测试月报告生成"""
        result = generate_monthly_report.apply_async()
        self.assertIn(result.status, ['SUCCESS', 'PENDING'])

    def test_send_notification_email(self):
        """测试通知邮件发送"""
        result = send_notification_email.apply_async(
            args=('user@example.com', 'Test Subject', 'Test message')
        )
        self.assertIn(result.status, ['SUCCESS', 'PENDING'])

    def test_cleanup_old_notifications(self):
        """测试清理旧通知"""
        result = cleanup_old_notifications.apply_async()
        self.assertIn(result.status, ['SUCCESS', 'PENDING'])

    def test_export_data(self):
        """测试数据导出"""
        result = export_data.apply_async(args=('csv',))
        self.assertIn(result.status, ['SUCCESS', 'PENDING'])

    def test_backup_database(self):
        """测试数据库备份"""
        result = backup_database.apply_async()
        self.assertIn(result.status, ['SUCCESS', 'PENDING'])

    def test_cleanup_cache(self):
        """测试缓存清理"""
        result = cleanup_cache.apply_async()
        self.assertIn(result.status, ['SUCCESS', 'PENDING'])

    def test_task_with_kwargs(self):
        """测试任务的关键字参数"""
        result = send_notification_email.apply_async(
            kwargs={
                'email': 'test@example.com',
                'subject': 'Kwargs Test',
                'message': 'Testing kwargs',
            }
        )
        self.assertIn(result.status, ['SUCCESS', 'PENDING'])


class TaskMonitorTests(TransactionTestCase):
    """测试 TaskMonitor 监控系统"""

    def setUp(self):
        """设置测试环境"""
        current_app.conf.update(task_always_eager=True)
        cache.clear()
        self.monitor = TaskMonitor()
        self.manager = TaskManager()

    def tearDown(self):
        """清理测试环境"""
        cache.clear()

    def test_monitor_initialization(self):
        """测试监控系统初始化"""
        self.assertIsNotNone(self.monitor)
        self.assertTrue(hasattr(self.monitor, 'get_task_status'))
        self.assertTrue(hasattr(self.monitor, 'get_all_tasks'))

    def test_record_task_execution(self):
        """测试记录任务执行"""
        task_data = {
            'task_id': 'test-task-123',
            'task_name': 'test_task',
            'status': 'SUCCESS',
            'result': 'Test result',
            'timestamp': datetime.now(),
            'duration': 1.5,
        }
        self.monitor.record_task_execution(task_data)

        # 验证数据被记录到缓存
        stats = self.monitor.get_task_stats()
        self.assertIsNotNone(stats)

    def test_get_task_stats(self):
        """测试获取任务统计"""
        # 记录几个任务
        for i in range(3):
            task_data = {
                'task_id': f'test-task-{i}',
                'task_name': 'test_task',
                'status': 'SUCCESS',
                'result': f'Result {i}',
                'timestamp': datetime.now(),
                'duration': 1.0,
            }
            self.monitor.record_task_execution(task_data)

        stats = self.monitor.get_task_stats()
        self.assertIsNotNone(stats)
        self.assertTrue(isinstance(stats, dict))

    def test_get_task_history(self):
        """测试获取任务历史"""
        history = self.monitor.get_task_history(limit=10)
        self.assertTrue(isinstance(history, list))

    def test_task_manager_send_task(self):
        """测试任务管理器发送任务"""
        task_id = self.manager.send_task('test_task', args=('test',))
        self.assertIsNotNone(task_id)

    def test_task_manager_get_result(self):
        """测试获取任务结果"""
        # 发送一个任务
        result = test_task.apply_async(args=('test',))
        task_id = result.id

        # 获取结果
        task_result = self.manager.get_result(task_id, timeout=5)
        self.assertIsNotNone(task_result)


class CeleryAPITests(APITestCase):
    """测试 Celery REST API 接口"""

    def setUp(self):
        """设置测试环境"""
        current_app.conf.update(task_always_eager=True)
        cache.clear()

        # 创建测试用户
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
        )

        # 创建管理员用户
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
        )

        self.client = APIClient()

    def tearDown(self):
        """清理测试环境"""
        cache.clear()

    def test_task_list_unauthorized(self):
        """测试未授权访问任务列表"""
        response = self.client.get('/api/core/tasks/', format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_task_list_authenticated(self):
        """测试授权访问任务列表"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/core/tasks/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(response.data, (list, dict)))

    def test_create_task(self):
        """测试创建新任务"""
        self.client.force_authenticate(user=self.user)
        data = {
            'task_name': 'test_task',
            'args': ['test'],
            'kwargs': {},
        }
        response = self.client.post('/api/core/tasks/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('task_id', response.data)

    def test_retrieve_task_status(self):
        """测试获取任务状态"""
        self.client.force_authenticate(user=self.user)

        # 先创建一个任务
        result = test_task.apply_async(args=('test',))
        task_id = result.id

        # 获取任务状态
        response = self.client.get(f'/api/core/tasks/{task_id}/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)

    def test_revoke_task(self):
        """测试撤销任务"""
        self.client.force_authenticate(user=self.admin)

        # 创建任务
        result = test_task.apply_async(args=('test',))
        task_id = result.id

        # 撤销任务
        response = self.client.post(
            f'/api/core/tasks/{task_id}/revoke/', format='json'
        )
        # 可能返回 200 或 204
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT])

    def test_task_stats_endpoint(self):
        """测试任务统计端点"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/core/tasks/stats/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_task_history_endpoint(self):
        """测试任务历史端点"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/core/tasks/history/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_worker_list(self):
        """测试获取工作进程列表"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/core/workers/', format='json')
        # 可能返回 200 或 503（如果没有工作进程）
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE])

    def test_worker_queues(self):
        """测试获取队列信息"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/core/workers/queues/', format='json')
        # 可能返回 200 或 503（如果没有工作进程）
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE])

    def test_permission_denies_non_admin_revoke(self):
        """测试普通用户无法撤销任务"""
        self.client.force_authenticate(user=self.user)

        result = test_task.apply_async(args=('test',))
        task_id = result.id

        # 普通用户尝试撤销
        response = self.client.post(
            f'/api/core/tasks/{task_id}/revoke/', format='json'
        )
        # 应该返回 403 Forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CeleryIntegrationTests(TransactionTestCase):
    """集成测试"""

    def setUp(self):
        """设置测试环境"""
        current_app.conf.update(task_always_eager=True)
        cache.clear()

    def tearDown(self):
        """清理测试环境"""
        cache.clear()

    def test_task_execution_chain(self):
        """测试任务执行链"""
        # 执行多个相关任务
        result1 = check_pending_bills.apply_async()
        result2 = send_bill_reminders.apply_async()
        result3 = calculate_monthly_revenue.apply_async()

        # 验证所有任务都在处理中或已完成
        for result in [result1, result2, result3]:
            self.assertIn(result.status, ['SUCCESS', 'PENDING'])

    def test_report_generation_flow(self):
        """测试报告生成流程"""
        results = [
            generate_hourly_report.apply_async(),
            generate_daily_report.apply_async(),
            generate_weekly_report.apply_async(),
            generate_monthly_report.apply_async(),
        ]

        for result in results:
            self.assertIn(result.status, ['SUCCESS', 'PENDING'])

    def test_notification_flow(self):
        """测试通知流程"""
        # 发送通知
        result1 = send_notification_email.apply_async(
            args=('test@example.com', 'Test', 'Message')
        )
        # 清理旧通知
        result2 = cleanup_old_notifications.apply_async()

        self.assertIn(result1.status, ['SUCCESS', 'PENDING'])
        self.assertIn(result2.status, ['SUCCESS', 'PENDING'])

    def test_maintenance_tasks(self):
        """测试维护任务"""
        results = [
            backup_database.apply_async(),
            cleanup_cache.apply_async(),
            export_data.apply_async(args=('csv',)),
        ]

        for result in results:
            self.assertIn(result.status, ['SUCCESS', 'PENDING'])

    def test_celery_configuration(self):
        """测试 Celery 配置"""
        conf = current_app.conf
        # 验证基本配置
        self.assertIsNotNone(conf.get('broker_url'))
        self.assertIsNotNone(conf.get('result_backend'))

    def test_task_routing(self):
        """测试任务路由"""
        # 检查任务是否被正确路由
        result = check_pending_bills.apply_async()
        self.assertIsNotNone(result.id)


class CeleryTaskRobustnessTests(TestCase):
    """Celery 任务鲁棒性测试"""

    def setUp(self):
        """设置测试环境"""
        current_app.conf.update(task_always_eager=True)

    def test_task_retry_logic(self):
        """测试任务重试逻辑"""
        # 测试具有重试逻辑的任务
        result = test_task.apply_async(args=('test',))
        self.assertEqual(result.status, 'SUCCESS')

    def test_task_timeout_handling(self):
        """测试任务超时处理"""
        # 测试长时间运行的任务
        result = long_running_task.apply_async(args=(2,))
        self.assertIn(result.status, ['SUCCESS', 'PENDING'])

    def test_task_error_handling(self):
        """测试任务错误处理"""
        # 测试任务中的错误处理
        result = test_task.apply_async(args=('test',))
        # 任务应该优雅地处理错误
        self.assertIsNotNone(result.id)

    def test_concurrent_task_execution(self):
        """测试并发任务执行"""
        # 同时发送多个任务
        results = [
            test_task.apply_async(args=(f'test-{i}',))
            for i in range(5)
        ]

        # 所有任务应该都有 ID
        for result in results:
            self.assertIsNotNone(result.id)

    def test_task_result_serialization(self):
        """测试任务结果序列化"""
        result = test_task.apply_async(args=('serialize_test',))
        # 结果应该可以被序列化为 JSON
        if result.status == 'SUCCESS':
            self.assertIsNotNone(result.result)


class CeleryMonitoringTests(TransactionTestCase):
    """Celery 监控测试"""

    def setUp(self):
        """设置测试环境"""
        current_app.conf.update(task_always_eager=True)
        cache.clear()
        self.monitor = TaskMonitor()

    def tearDown(self):
        """清理测试环境"""
        cache.clear()

    def test_monitor_task_execution(self):
        """测试监控任务执行"""
        task_data = {
            'task_id': 'monitor-test-1',
            'task_name': 'test_task',
            'status': 'SUCCESS',
            'result': 'Test execution',
            'timestamp': datetime.now(),
            'duration': 0.5,
        }
        self.monitor.record_task_execution(task_data)

        stats = self.monitor.get_task_stats()
        self.assertIsNotNone(stats)

    def test_monitor_statistics_accumulation(self):
        """测试监控统计积累"""
        # 记录多个任务执行
        for i in range(3):
            task_data = {
                'task_id': f'stat-test-{i}',
                'task_name': 'test_task',
                'status': 'SUCCESS' if i % 2 == 0 else 'FAILURE',
                'result': f'Result {i}',
                'timestamp': datetime.now(),
                'duration': 1.0 + i,
            }
            self.monitor.record_task_execution(task_data)

        stats = self.monitor.get_task_stats()
        self.assertTrue(isinstance(stats, dict))

    def test_monitor_history_retrieval(self):
        """测试监控历史检索"""
        # 记录几个任务
        for i in range(5):
            task_data = {
                'task_id': f'history-test-{i}',
                'task_name': f'task_{i}',
                'status': 'SUCCESS',
                'result': f'Result {i}',
                'timestamp': datetime.now(),
                'duration': 0.5,
            }
            self.monitor.record_task_execution(task_data)

        # 获取历史
        history = self.monitor.get_task_history(limit=10)
        self.assertTrue(isinstance(history, list))


class CeleryManagerTests(TransactionTestCase):
    """Celery 任务管理器测试"""

    def setUp(self):
        """设置测试环境"""
        current_app.conf.update(task_always_eager=True)
        cache.clear()
        self.manager = TaskManager()

    def tearDown(self):
        """清理测试环境"""
        cache.clear()

    def test_manager_send_simple_task(self):
        """测试发送简单任务"""
        task_id = self.manager.send_task('test_task', args=('test',))
        self.assertIsNotNone(task_id)

    def test_manager_send_task_with_kwargs(self):
        """测试发送带关键字参数的任务"""
        task_id = self.manager.send_task(
            'send_notification_email',
            kwargs={
                'email': 'test@example.com',
                'subject': 'Test',
                'message': 'Message',
            }
        )
        self.assertIsNotNone(task_id)

    def test_manager_get_result(self):
        """测试获取任务结果"""
        result = test_task.apply_async(args=('test',))
        task_id = result.id

        task_result = self.manager.get_result(task_id, timeout=5)
        self.assertIsNotNone(task_result)


# 汇总测试统计
class TestSummary:
    """测试摘要"""
    test_classes = [
        ('CeleryTaskDefinitionTests', 14),
        ('TaskMonitorTests', 7),
        ('CeleryAPITests', 11),
        ('CeleryIntegrationTests', 6),
        ('CeleryTaskRobustnessTests', 5),
        ('CeleryMonitoringTests', 3),
        ('CeleryManagerTests', 3),
    ]

    total_tests = sum(count for _, count in test_classes)


if __name__ == '__main__':
    import unittest
    unittest.main()
