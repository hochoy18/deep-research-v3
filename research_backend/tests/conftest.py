"""pytest 全局 fixture：事件循环 + 异步 client 配置。"""
from __future__ import annotations

import asyncio
import os

import pytest

# 避免在 import 期就强制连接外部服务
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/postgres")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("LANGFUSE_HOST", "http://localhost:3001")
os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "pk-test")
os.environ.setdefault("LANGFUSE_SECRET_KEY", "sk-test")


@pytest.fixture(scope="session")
def event_loop():
    """asyncio mode=auto 下的会话级事件循环（pytest-asyncio 0.23+ 需要）。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
