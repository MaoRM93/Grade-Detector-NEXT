# backend/service/notification_service.py
"""
系统通知服务

规则与旧 Qt 版本完全一致，仅改变 UI 层。
macOS 使用 osascript display notification，Windows 使用 win_toast。
"""
import subprocess
import sys


def send_startup_notification(auto_monitor_enabled: bool,
                               start_time: str = "08:00",
                               end_time: str = "22:00",
                               interval: int = 300) -> None:
    """程序启动时发送的通知"""
    if auto_monitor_enabled:
        message = (
            f"程序将在后台自动按设置监测成绩和排名"
            f"（监测时段：{start_time}-{end_time}，间隔：{interval}秒）"
        )
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

    - 简洁模式 (is_simple=True): "成绩更新：N 门课程"
    - 详细模式 (is_simple=False): 列出前 5 门课程名+绩点 + 排名信息
    """
    title = "您有成绩或排名更新"
    if is_simple:
        message = f"成绩更新：{new_count + changed_count} 门课程"
    else:
        lines = []
        if course_details:
            for course in course_details[:5]:
                name = course.get("kcname", "未知课程")
                jd = course.get("jd", 0)
                xf = course.get("xf", 1)
                gpa = round(jd / xf, 1) if xf > 0 else 0
                lines.append(f"{name} 绩点:{gpa}")
        total = new_count + changed_count
        if total > 5:
            lines.append(f"... 等 {total} 门")
        if rank_pm != "N/A":
            lines.append(f"年名: {rank_pm}/{rank_countnum} 班名: {rank_bjpm}/{rank_bjgms}")
        elif course_details:
            # 没有排名时给出提示
            pass
        message = "\n".join(lines) if lines else f"成绩更新：{total} 门课程"
    _show(title, message)


def send_rank_notification(rank_data: dict, change_msgs: list = None,
                            is_simple: bool = False) -> None:
    """
    排名变化通知

    - 简洁模式: "排名已更新"
    - 详细模式: 专业 / 年名 / 班名 / 平均绩点 / 变化文字
    """
    title = "您有成绩或排名更新"
    if is_simple:
        message = "排名已更新"
    else:
        pm = rank_data.get("pm", "N/A")
        bjpm = rank_data.get("bjpm", "N/A")
        countnum = rank_data.get("countnum", "N/A")
        bjgms = rank_data.get("bjgms", "N/A")
        ndzy_name = rank_data.get("ndzy_name", "未知专业")
        pjxfjd = rank_data.get("pjxfjd", "N/A")
        lines = [
            f"专业：{ndzy_name}",
            f"年名：{pm}/{countnum}",
            f"班名：{bjpm}/{bjgms}",
            f"平均绩点：{pjxfjd}",
        ]
        if change_msgs:
            lines.append("--- 变化 ---")
            lines.extend(change_msgs[:3])
        message = "\n".join(lines)
    _show(title, message)


def send_test_notification() -> None:
    """测试通知"""
    _show("自动查成绩小工具", "您的通知已正确开启")


def _show(title: str, message: str) -> None:
    """底层通知发送"""
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
            subprocess.run(
                ["osascript", "-e", script],
                check=True, capture_output=True,
            )
        elif sys.platform == "win32":
            # Windows: 使用 win_toast（需要安装 win10toast 或类似库）
            try:
                from win10toast import ToastNotifier
                ToastNotifier().show_toast(title, message, duration=5)
            except ImportError:
                pass
    except Exception:
        pass
