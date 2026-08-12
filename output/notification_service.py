# backend/service/notification_service.py
"""
系统通知服务
macOS 使用 osascript display notification，Windows 使用 win_toast。
"""
import subprocess
import sys

from backend.utils.logger import get_logger

logger = get_logger(__name__)


def send_startup_notification(auto_monitor_enabled: bool,
                               start_time: str = "08:00",
                               end_time: str = "22:00",
                               interval: int = 300) -> None:
    if auto_monitor_enabled:
        message = f"程序将在后台自动按设置监测成绩和排名（监测时段：{start_time}-{end_time}，间隔：{interval}秒）"
    else:
        message = "程序已启动，将按照您的设置进行后台监测"
    _show("自动查成绩小工具", message)


def send_grades_notification(new_count: int, changed_count: int,
                              course_details: list = None,
                              rank_pm: str = "N/A", rank_countnum: str = "N/A",
                              rank_bjpm: str = "N/A", rank_bjgms: str = "N/A",
                              is_simple: bool = False) -> None:
    """
    成绩变化通知

    详细模式:
      标题：课程名字+成绩有更新
      正文第一行：平均学分绩点：xxx；加权分数：xxx
      第二行：平时成绩：xx；期末成绩：xx
      第三行：班级排名：xxx，专业排名：xxx

    简洁模式:
      标题：您有成绩或排名变动
      内容：请进入程序查看
    """
    if is_simple:
        _show("您有成绩或排名变动", "请进入程序查看")
        return

    # 详细模式
    course_name = "未知课程"
    pjxfjd = "N/A"
    zcj = "N/A"
    cjxm1 = "N/A"
    cjxm3 = "N/A"

    if course_details:
        first = course_details[0]
        course_name = first.get("kcname", "未知课程")
        # 计算平均学分绩点
        jd_val = float(first.get("jd", 0) or 0)
        xf_val = float(first.get("xf", 1) or 1)
        pjxfjd = f"{jd_val / xf_val:.1f}" if xf_val > 0 else "N/A"
        zcj = first.get("zcj", "N/A")
        cjxm1 = first.get("cjxm1", "N/A")
        cjxm3 = first.get("cjxm3", "N/A")

    # 未传入排名数据时，尝试从缓存读取
    if rank_pm == "N/A" or rank_bjpm == "N/A":
        try:
            from backend.storage.cache import load_local_ranks
            rank = load_local_ranks()
            if rank:
                if rank_pm == "N/A":
                    rank_pm = str(rank.get("pm", "N/A"))
                if rank_bjpm == "N/A":
                    rank_bjpm = str(rank.get("bjpm", "N/A"))
        except Exception:
            pass

    title = f"{course_name} 成绩有更新"
    lines = [
        f"平均学分绩点：{pjxfjd}；加权分数：{zcj}",
        f"平时成绩：{cjxm1}；期末成绩：{cjxm3}",
        f"班级排名：{rank_bjpm}，专业排名：{rank_pm}",
    ]

    message = "\n".join(lines)
    _show(title, message)


def send_rank_notification(rank_data: dict, change_msgs: list = None,
                            is_simple: bool = False) -> None:
    if is_simple:
        _show("您有成绩或排名变动", "请进入程序查看")
        return

    pm = rank_data.get("pm", "N/A")
    bjpm = rank_data.get("bjpm", "N/A")
    pjxfjd = rank_data.get("pjxfjd", "N/A")
    title = "排名已更新"
    lines = [
        f"平均学分绩点：{pjxfjd}",
        f"当前总排名：{pm}，班级排名：{bjpm}",
    ]
    if change_msgs:
        lines.append("--- 变化 ---")
        lines.extend(change_msgs[:3])
    _show(title, "\n".join(lines))


def send_test_notification(is_simple: bool = False,
                            course_details: list = None) -> None:
    """测试通知：展示详细或简洁模式的实际通知内容"""
    if is_simple:
        _show("您有成绩或排名变动", "请进入程序查看")
        return

    # 构造模拟数据展示格式
    course_name = "高等数学"
    if course_details:
        course_name = course_details[0].get("kcname", "高等数学")

    title = f"{course_name} 成绩有更新"
    message = (
        "平均学分绩点：3.7、加权分数：85.5\n"
        "平时成绩：90；期末成绩：82\n"
        "当前总排名：15，班级排名：3"
    )
    _show(title, message)


def send_notification_preview(is_simple: bool) -> str:
    """返回通知预览文本（供前端展示）"""
    if is_simple:
        return "标题：您有成绩或排名变动\n内容：请进入程序查看"

    return (
        "标题：高等数学 成绩有更新\n"
        "正文：\n"
        "  平均学分绩点：3.7、加权分数：85.5\n"
        "  平时成绩：90；期末成绩：82\n"
        "  当前总排名：15，班级排名：3"
    )


def _show(title: str, message: str) -> None:
    try:
        if sys.platform == "darwin":
            escaped_title = title.replace('"', '\\"').replace("'", "\\'")
            escaped_message = message.replace('"', '\\"').replace("'", "\\'")
            script = (
                f'tell application "System Events"\n'
                f'display notification "{escaped_message}"'
                f' with title "{escaped_title}"\n'
                f'end tell'
            )
            subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
            logger.debug(f"Notification sent: {title}")
        elif sys.platform == "win32":
            try:
                from win10toast import ToastNotifier
                ToastNotifier().show_toast(title, message, duration=5)
                logger.debug(f"Notification sent: {title}")
            except ImportError:
                logger.warning("win10toast not installed")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
