# backend/storage/cache.py
"""
本地数据缓存（成绩、排名）及数据目录管理
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from backend.utils.logger import get_logger

logger = get_logger(__name__)

# ---------- 数据存储目录 ----------
APP_NAME = "GradeMonitor"

if sys.platform == "darwin":
    _default_appdata = os.path.join(
        os.path.expanduser("~"), "Library", "Application Support", APP_NAME
    )
else:
    _default_appdata = os.path.join(os.environ.get("APPDATA", ""), APP_NAME)


def _resolve_data_dir() -> str:
    """选择可写入的数据目录。
    优先级: ~/Library/Application Support/GradeMonitor → ~/.grademonitor → /tmp/GradeMonitor
    """
    # 1. 标准 macOS 应用数据目录（跨重启持久）
    try:
        os.makedirs(_default_appdata, exist_ok=True)
        test_file = os.path.join(_default_appdata, ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        logger.info(f"数据目录: {_default_appdata}")
        return _default_appdata
    except (PermissionError, OSError) as e:
        logger.warning(f"主数据目录不可用 ({e}), 尝试备选...")

    # 2. 用户主目录下的隐藏文件夹（持久，不易被清理）
    try:
        home_fallback = os.path.join(os.path.expanduser("~"), ".grademonitor")
        os.makedirs(home_fallback, exist_ok=True)
        test_file = os.path.join(home_fallback, ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        logger.warning(f"数据目录（home fallback）: {home_fallback}")
        return home_fallback
    except (PermissionError, OSError) as e:
        logger.error(f"备选 home 目录也不可用 ({e}), 回退到 /tmp（重启后数据将丢失！）")

    # 3. 最终回退（仅 /tmp，重启后清空）
    fallback = os.path.join("/tmp", APP_NAME)
    os.makedirs(fallback, exist_ok=True)
    logger.error(f"数据目录（/tmp fallback - 非持久！）: {fallback}")
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
STATS_FILE = get_data_file_path("stats.json")


# ---------- 成绩缓存 ----------
# 课程对象的字段全为标量（无嵌套 dict/list），`\{[^{}]*\}` 能精确框出每个
# 完整课程块，完全不依赖外层括号配对——即使文件因手动编辑出现残留括号、
# 多余逗号或截断，每个本身完整的课程对象仍能被独立提取
_COURSE_BLOCK_RE = re.compile(r"\{[^{}]*\}")


def _extract_courses(raw: str) -> dict | None:
    """从损坏的 JSON 文本中逐块抢救课程对象。

    只认携带非空字符串 kth 字段的对象为课程，其余噪声块丢弃。
    一个课程都提取不到时返回 None（区别于空 dict {}）。
    """
    courses: dict = {}
    for m in _COURSE_BLOCK_RE.finditer(raw):
        block = m.group(0)
        try:
            obj = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            kth = obj.get("kth")
            if isinstance(kth, str) and kth:
                courses[kth] = obj
    return courses if courses else None


def load_local_grades() -> dict | None:
    """加载缓存的成绩数据。

    返回值语义：
    - dict（可为空 {}）：合法基准；{} 表示首次运行/无缓存（合法状态）
    - None：文件损坏且无法修复的哨兵信号，调用方必须跳过本轮对比（绝不误报）
    """
    if os.path.exists(LOCAL_GRADES_FILE):
        try:
            with open(LOCAL_GRADES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    logger.error(
                        f"成绩缓存顶层结构不是 dict（{type(data).__name__}），"
                        f"视为损坏: {LOCAL_GRADES_FILE}"
                    )
                    return None
                logger.info(f"读取成绩缓存: {LOCAL_GRADES_FILE}  ({len(data)} 门)")
                return data
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败（可能手动编辑格式错误）: {LOCAL_GRADES_FILE} - {e}")
            # 二级策略：正则逐块抢救课程对象
            try:
                with open(LOCAL_GRADES_FILE, "r", encoding="utf-8") as f:
                    raw = f.read()
                repaired = _extract_courses(raw)
                if repaired is not None:
                    logger.warning(
                        f"JSON 损坏，已逐个课程修复（恢复 {len(repaired)} 门），回写缓存文件"
                    )
                    save_local_grades(repaired)  # 回写修复结果，下次直接正常解析
                    return repaired
                # 三级策略：彻底无法恢复 → None 哨兵，调用方跳过本轮对比
                logger.error(
                    "JSON 彻底损坏且无法提取任何课程，返回 None（跳过本轮成绩对比，零误报）"
                )
                return None
            except Exception as e2:
                logger.error(f"JSON 损坏修复流程失败: {e2}")
                return None
        except Exception as e:
            logger.error(f"Failed to load cached grades: {e}")
            return None
    logger.info(f"成绩缓存文件不存在: {LOCAL_GRADES_FILE}")
    return {}


def save_local_grades(grades_dict: dict) -> None:
    """保存成绩数据到本地缓存"""
    with open(LOCAL_GRADES_FILE, "w", encoding="utf-8") as f:
        json.dump(grades_dict, f, ensure_ascii=False, indent=2)
    logger.info(f"写入成绩缓存: {LOCAL_GRADES_FILE}  ({len(grades_dict)} 门)")


def _normalize_value(val):
    """字段值归一化：消除"等价但类型不同"的假变动。

    - None 保持 None；bool 必须在 int 判断之前（bool 是 int 子类）
    - 整数值的 float（7.0 → 7），消除 int 7 vs float 7.0 抖动
    - 字符串去首尾空白
    - list/dict 转规范化 JSON 字符串再比较
    """
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, float):
        return int(val) if val.is_integer() else val
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, (list, dict)):
        return json.dumps(val, ensure_ascii=False, sort_keys=True)
    return val


def diff_grades(old_grades: dict, new_grades: dict) -> tuple:
    """
    对比新旧成绩，返回 (new_courses, changed_courses)
    - new_courses: 基准中不存在的课程（服务器新增，或用户手动删掉后重新出现）
    - changed_courses: 任一字段归一化后不等的课程

    不变量：严格按课程号 kth 做 dict 键值对比，绝不按顺序/索引——
    删除中间一门课只会使该门课被判为"新增"，绝不连带其他课程误报。
    """
    new_courses = []
    changed_courses = []
    for kth, course in new_grades.items():
        if kth not in old_grades:
            new_courses.append(course)
            logger.info(f"[Diff] 新增课程: {course.get('kcname', '未知')} (kth={kth})")
            continue

        old = old_grades[kth]
        changed_fields = [
            f for f in set(old) | set(course)
            if _normalize_value(old.get(f)) != _normalize_value(course.get(f))
        ]
        if changed_fields:
            changed_courses.append(course)
            logger.info(
                f"[Diff] {course.get('kcname', '未知')} (kth={kth}) 变动字段: "
                f"{', '.join(sorted(changed_fields))}"
            )

    return new_courses, changed_courses


# ---------- 排名缓存 ----------
def load_local_ranks() -> dict:
    """加载缓存的排名数据"""
    if os.path.exists(LOCAL_RANKS_FILE):
        try:
            with open(LOCAL_RANKS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.debug("Loaded cached ranks")
                return data
        except Exception as e:
            logger.error(f"Failed to load cached ranks: {e}")
            return {}
    return {}


def save_local_ranks(ranks_dict: dict) -> None:
    """保存排名数据到本地缓存"""
    with open(LOCAL_RANKS_FILE, "w", encoding="utf-8") as f:
        json.dump(ranks_dict, f, ensure_ascii=False, indent=2)
    logger.debug("Saved ranks to cache")


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
