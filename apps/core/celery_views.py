"""
Celery 任务管理 API 视图

提供：
1. 任务状态查询
2. 任务发送
3. 任务撤销
4. Worker 和队列状态
5. 任务统计
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import BasicAuthentication, SessionAuthentication

from apps.core.celery_monitor import TaskMonitor, TaskManager

logger = logging.getLogger(__name__)


class TaskViewSet(viewsets.ViewSet):
    """
    Celery 任务管理视图集
    
    端点：
    - GET /api/core/tasks/ - 列出所有活跃任务
    - GET /api/core/tasks/<task_id>/ - 获取任务状态
    - POST /api/core/tasks/ - 发送新任务
    - POST /api/core/tasks/<task_id>/revoke/ - 撤销任务
    - GET /api/core/tasks/stats/ - 获取任务统计
    """
    
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """列出所有活跃任务"""
        try:
            tasks = TaskMonitor.get_all_tasks()
            return Response({
                'tasks': tasks,
                'count': len(tasks)
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def retrieve(self, request, pk=None):
        """获取任务状态"""
        task_id = pk
        
        try:
            task_status = TaskMonitor.get_task_status(task_id)
            return Response(task_status)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def create(self, request):
        """发送新任务"""
        try:
            task_name = request.data.get('task_name')
            args = request.data.get('args', [])
            kwargs = request.data.get('kwargs', {})
            delay = request.data.get('delay', 0)
            queue = request.data.get('queue', 'default')
            
            if not task_name:
                return Response(
                    {'error': 'task_name is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            task_id = TaskManager.send_task(
                task_name,
                args=args,
                kwargs=kwargs,
                delay=delay,
                queue=queue
            )
            
            if not task_id:
                return Response(
                    {'error': 'Failed to send task'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response({
                'task_id': task_id,
                'task_name': task_name,
                'status': 'PENDING'
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f'Error sending task: {str(e)}')
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """撤销任务"""
        if not request.user.is_staff:
            return Response(
                {'error': '只有工作人员可以撤销任务'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        task_id = pk
        terminate = request.data.get('terminate', False)
        
        try:
            success = TaskManager.revoke_task(task_id, terminate=terminate)
            
            if success:
                return Response({'message': f'Task {task_id} revoked'})
            else:
                return Response(
                    {'error': 'Failed to revoke task'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取任务统计"""
        try:
            task_stats = TaskMonitor.get_task_stats()
            return Response(task_stats)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """获取任务执行历史"""
        limit = request.query_params.get('limit', 100)
        
        try:
            history = TaskMonitor.get_task_history(int(limit))
            return Response({
                'history': history,
                'count': len(history)
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class WorkerViewSet(viewsets.ViewSet):
    """Worker 状态视图集"""
    
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """列出所有 Worker"""
        try:
            worker_stats = TaskMonitor.get_worker_stats()
            return Response({
                'workers': worker_stats,
                'count': len(worker_stats)
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def queues(self, request):
        """获取队列信息"""
        try:
            queue_stats = TaskMonitor.get_queue_stats()
            return Response(queue_stats)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


# ============================================================================
# 简单 API 视图
# ============================================================================

@api_view(['GET'])
def task_status_view(request, task_id):
    """获取单个任务状态"""
    try:
        status_info = TaskMonitor.get_task_status(task_id)
        return Response(status_info)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
def send_task_view(request):
    """发送任务"""
    if not request.user.is_staff:
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        task_name = request.data.get('task_name')
        
        if not task_name:
            return Response(
                {'error': 'task_name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task_id = TaskManager.send_task(task_name)
        
        return Response({
            'task_id': task_id,
            'status': 'PENDING'
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
def celery_stats_view(request):
    """获取 Celery 统计信息"""
    if not request.user.is_staff:
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        return Response({
            'workers': TaskMonitor.get_worker_stats(),
            'queues': TaskMonitor.get_queue_stats(),
            'task_stats': TaskMonitor.get_task_stats(),
            'active_tasks': TaskMonitor.get_all_tasks(),
        })
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
