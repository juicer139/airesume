"""Celery 应用实例。

两个角色分工：
- broker（Redis）：任务消息队列，FastAPI 把任务"寄"到这里
- backend（Redis）：任务返回值存储，本项目结果直接写 MySQL，backend 只用于调试

include 显式声明任务模块：Worker 启动时会 import 它们完成任务注册，
否则 Worker 收到消息也不知道该执行哪个函数。
"""
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "airesume",
    broker=settings.REDIS_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.analysis_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    # 任务执行完才向队列确认：Worker 半路崩溃，消息会重新派发，任务不丢
    task_acks_late=True,
    # AI 任务耗时几十秒，Worker 一次只预取 1 个任务，
    # 防止某个 Worker 攥着一堆任务让后面的用户干等
    worker_prefetch_multiplier=1,
)
