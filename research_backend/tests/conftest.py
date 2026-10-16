"""pytest 全局 fixture：env 默认值 + DB mock 工具。"""
from __future__ import annotations

import os

# 必须在 import app.* 之前
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/postgres")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("LANGFUSE_HOST", "http://localhost:3001")
os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "pk-test")
os.environ.setdefault("LANGFUSE_SECRET_KEY", "sk-test")
