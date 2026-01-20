from prometheus_client import Counter, Histogram


CELERY_TASK_TOTAL = Counter(
    'celery_task_total',
    'Celery task executions by status',
    ['task_name', 'status'],
)

CELERY_TASK_DURATION_SECONDS = Histogram(
    'celery_task_duration_seconds',
    'Celery task duration in seconds',
    ['task_name', 'status'],
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60, 120, 300),
)


def record_task_result(task_name, status, duration=None):
    status_label = (status or 'UNKNOWN').upper()
    CELERY_TASK_TOTAL.labels(task_name=task_name, status=status_label).inc()

    if duration is not None:
        CELERY_TASK_DURATION_SECONDS.labels(
            task_name=task_name,
            status=status_label,
        ).observe(duration)
