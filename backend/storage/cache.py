# backend/storage/cache.py
"""
本地数据缓存（成绩、排名）及数据目录管理
"""
import json
import os
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
def load_local_grades() -> dict:
    """加载缓存的成绩数据"""
    if os.path.exists(LOCAL_GRADES_FILE):
        try:
            with open(LOCAL_GRADES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info(f"读取成绩缓存: {LOCAL_GRADES_FILE}  ({len(data)} 门)")
                return data
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败（可能手动编辑格式错误）: {LOCAL_GRADES_FILE} - {e}")
            return {}
        except Exception as e:
            logger.error(f"Failed to load cached grades: {e}")
            return {}
    logger.info(f"成绩缓存文件不存在: {LOCAL_GRADES_FILE}")
    return {}


def save_local_grades(grades_dict: dict) -> None:
    """保存成绩数据到本地缓存"""
    with open(LOCAL_GRADES_FILE, "w", encoding="utf-8") as f:
        json.dump(grades_dict, f, ensure_ascii=False, indent=2)
    logger.info(f"写入成绩缓存: {LOCAL_GRADES_FILE}  ({len(grades_dict)} 门)")


def diff_grades(old_grades: dict, new_grades: dict) -> tuple:
    """
    对比新旧成绩，返回 (new_courses, changed_courses)
    - new_courses: old 中不存在的课程（用户手动删掉后重新出现）
    - changed_courses: 平时成绩/绩点/加权成绩有变化的课程
    """

    def _safe_str(val) -> str:
        """将值转为字符串，None 转为空字符串，避免 str(None) → 'None'"""
        if val is None:
            return ""
        return str(val)

    new_courses = []
    changed_courses = []
    for kth, course in new_grades.items():
        if kth not in old_grades:
            new_courses.append(course)
            logger.info(f"[Diff] 新增课程: {course.get('kcname', '未知')} (kth={kth})")
        else:
            old = old_grades[kth]

            cjxm1_old = _safe_str(old.get("cjxm1"))
            cjxm1_new = _safe_str(course.get("cjxm1"))
            cjxm1_changed = cjxm1_new != cjxm1_old

            jd_old = _safe_str(old.get("jd"))
            jd_new = _safe_str(course.get("jd"))
            jd_changed = jd_new != jd_old

            zcj_old = _safe_str(old.get("zcj"))
            zcj_new = _safe_str(course.get("zcj"))
            zcj_changed = zcj_new != zcj_old

            if cjxm1_changed or jd_changed or zcj_changed:
                changed_courses.append(course)
                course_name = course.get("kcname", "未知")
                details = []
                if cjxm1_changed:
                    details.append(f"平时成绩: {cjxm1_old or '(空)'} -> {cjxm1_new or '(空)'}")
                if jd_changed:
                    details.append(f"绩点: {jd_old or '(空)'} -> {jd_new or '(空)'}")
                if zcj_changed:
                    details.append(f"加权成绩: {zcj_old or '(空)'} -> {zcj_new or '(空)'}")
                logger.info(f"[Diff] {course_name} (kth={kth}) 变动: {'; '.join(details)}")

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
