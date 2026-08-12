# backend/utils/logger.py
"""
统一日志模块

- 同时输出到控制台和文件
- 日志文件输出到项目根目录 /logs/ 文件夹
- 按天自动轮转，保留最近 30 天
- 支持模块级 logger 获取
"""
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

# ---------- 日志目录 ----------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_LOG_DIR = _PROJECT_ROOT / "logs"

os.makedirs(_LOG_DIR, exist_ok=True)

LOG_FILE = _LOG_DIR / "backend.log"

# ---------- 日志格式 ----------
_LOG_FORMAT = logging.Formatter(
    fmt="%(asctime)s.%(msecs)03d | %(levelname)-5s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ---------- 全局日志级别 ----------
# 可通过环境变量 LOG_LEVEL 控制（默认 INFO）
_LOG_LEVEL_NAME = os.environ.get("LOG_LEVEL", "INFO").upper()
_LOG_LEVEL = getattr(logging, _LOG_LEVEL_NAME, logging.INFO)

# ---------- 根 Logger 配置 ----------
_root_logger = logging.getLogger("grademonitor")
_root_logger.setLevel(_LOG_LEVEL)

# 避免重复添加 handler
if not _root_logger.handlers:
    # 文件 handler：按天轮转，保留 30 天
    file_handler = TimedRotatingFileHandler(
        filename=str(LOG_FILE),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_LOG_FORMAT)
    _root_logger.addHandler(file_handler)

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(_LOG_LEVEL)
    console_handler.setFormatter(_LOG_FORMAT)
    _root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    获取指定模块的 logger

    用法:
        from backend.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("something happened")
    """
    return _root_logger.getChild(name)


# ---------- 便捷函数 ----------
def debug(msg: str, *args):
    _root_logger.debug(msg, *args)


def info(msg: str, *args):
    _root_logger.info(msg, *args)


def warning(msg: str, *args):
    _root_logger.warning(msg, *args)


def error(msg: str, *args):
    _root_logger.error(msg, *args)


def exception(msg: str, *args):
    _root_logger.exception(msg, *args)
