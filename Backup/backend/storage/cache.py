# backend/storage/cache.py
"""
本地数据缓存（成绩、排名）及数据目录管理
"""
import json
import os
import sys
from pathlib import Path

# ---------- 数据存储目录 ----------
APP_NAME = "GradeMonitor"

if sys.platform == "darwin":
    _default_appdata = os.path.join(
        os.path.expanduser("~"), "Library", "Application Support", APP_NAME
    )
else:
    _default_appdata = os.path.join(os.environ.get("APPDATA", ""), APP_NAME)

# 沙箱/权限受限时回退到 /tmp
def _resolve_data_dir() -> str:
    """选择可写入的数据目录，优先 ~/Library/Application Support，回退 /tmp"""
    try:
        os.makedirs(_default_appdata, exist_ok=True)
        # 测试写入权限
        test_file = os.path.join(_default_appdata, ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return _default_appdata
    except (PermissionError, OSError):
        fallback = os.path.join("/tmp", APP_NAME)
        os.makedirs(fallback, exist_ok=True)
        return fallback

APPDATA_DIR = _resolve_data_dir()


def ensure_data_dir() -> None:
    """确保数据目录存在"""
    if not os.path.exists(APPDATA_DIR):
        os.makedirs(APPDATA_DIR)


def get_data_file_path(filename: str) -> str:
    """获取数据文件的完整路径（自动确保目录存在）"""
    ensure_data_dir()
    return os.path.join(APPDATA_DIR, filename)


def get_data_dir() -> str:
    """获取数据存储目录路径"""
    ensure_data_dir()
    return APPDATA_DIR


# ---------- 缓存文件路径 ----------
LOCAL_GRADES_FILE = get_data_file_path("local_grades.json")
LOCAL_RANKS_FILE = get_data_file_path("local_ranks.json")
LOG_FILE = get_data_file_path("app.log")
STATS_FILE = get_data_file_path("stats.json")


# ---------- 成绩缓存 ----------
def load_local_grades() -> dict:
    """加载缓存的成绩数据"""
    if os.path.exists(LOCAL_GRADES_FILE):
        try:
            with open(LOCAL_GRADES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_local_grades(grades_dict: dict) -> None:
    """保存成绩数据到本地缓存"""
    with open(LOCAL_GRADES_FILE, "w", encoding="utf-8") as f:
        json.dump(grades_dict, f, ensure_ascii=False, indent=2)


# ---------- 排名缓存 ----------
def load_local_ranks() -> dict:
    """加载缓存的排名数据"""
    if os.path.exists(LOCAL_RANKS_FILE):
        try:
            with open(LOCAL_RANKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_local_ranks(ranks_dict: dict) -> None:
    """保存排名数据到本地缓存"""
    with open(LOCAL_RANKS_FILE, "w", encoding="utf-8") as f:
        json.dump(ranks_dict, f, ensure_ascii=False, indent=2)


# ---------- 统计缓存（查询次数持久化）----------
def load_total_query_count() -> int:
    """加载累计查询次数"""
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return int(data.get("total_queries", 0))
        except Exception:
            return 0
    return 0


def increment_query_count() -> int:
    """查询次数 +1 并持久化，返回新值"""
    current = load_total_query_count()
    current += 1
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump({"total_queries": current}, f, ensure_ascii=False, indent=2)
    return current


def reset_query_count() -> None:
    """重置查询计数"""
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump({"total_queries": 0}, f, ensure_ascii=False, indent=2)
