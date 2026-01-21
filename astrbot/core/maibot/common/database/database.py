import os
from peewee import SqliteDatabase
from rich.traceback import install

from astrbot.core.maibot.config.context import get_context

install(extra_lines=3)


# 全局变量，由外部初始化
_DB_FILE: str | None = None
db: SqliteDatabase | None = None


def initialize_database(db_path: str | None = None):
    """
    初始化数据库

    Args:
        db_path: 数据库文件完整路径，如果为 None 则从 InstanceContext 获取
    """
    global _DB_FILE, db

    # 如果未指定路径，从上下文中获取
    if db_path is None:
        context = get_context()
        db_path = context.get_database_path()

    _DB_FILE = db_path
    _DB_DIR = os.path.dirname(db_path)

    # 确保数据库目录存在
    os.makedirs(_DB_DIR, exist_ok=True)

    # 创建 Peewee SQLite 数据库实例
    db = SqliteDatabase(
        _DB_FILE,
        pragmas={
            "journal_mode": "wal",  # WAL模式提高并发性能
            "cache_size": -64 * 1000,  # 64MB缓存
            "foreign_keys": 1,
            "ignore_check_constraints": 0,
            "synchronous": 0,  # 异步写入提高性能
            "busy_timeout": 1000,  # 1秒超时而不是3秒
        },
    )

    return db


def get_database_path() -> str | None:
    """获取当前数据库文件路径"""
    return _DB_FILE

