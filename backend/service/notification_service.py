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

    简洁模式:
      标题：您有成绩或排名更新
      正文：无

    详细模式:
      单门：标题=您有成绩或排名更新：{课程名}
            正文第一行：平时分：xx；期末分：xx；加权分：xx
            正文第二行：平均学分绩点：x.x；班名：xx；年名：xx
      多门：标题=您有成绩或排名更新：{首课程名} 等 N 门
            正文逐门列出：课程名：平时xx 期末xx 加权xx 绩点x.x
    """
    if is_simple:
        _show("您有成绩或排名更新", "")
        return

    total = len(course_details) if course_details else 0
    if total == 0:
        return

    # 加载排名数据（班名、年名）
    bjpm = "N/A"
    pm = "N/A"
    try:
        from backend.storage.cache import load_local_ranks
        rank = load_local_ranks()
        if rank:
            bjpm = str(rank.get("bjpm", "N/A"))
            pm = str(rank.get("pm", "N/A"))
    except Exception:
        pass

    def _format_course(course: dict) -> dict:
        """提取课程展示字段"""
        return {
            "name": course.get("kcname", "未知课程"),
            "cjxm1": course.get("cjxm1", "N/A"),
            "cjxm3": course.get("cjxm3", "N/A"),
            "zcj": course.get("zcj", "N/A"),
            "pjxfjd": _calc_pjxfjd(course),
        }

    def _calc_pjxfjd(course: dict) -> str:
        jd_val = float(course.get("jd", 0) or 0)
        xf_val = float(course.get("xf", 1) or 1)
        return f"{jd_val / xf_val:.1f}" if xf_val > 0 else "N/A"

    if total == 1:
        c = _format_course(course_details[0])
        title = f"您有成绩或排名更新：{c['name']}"
        lines = [
            f"平时分：{c['cjxm1']}；期末分：{c['cjxm3']}；加权分：{c['zcj']}",
            f"平均学分绩点：{c['pjxfjd']}；班名：{bjpm}；年名：{pm}",
        ]
        _show(title, "\n".join(lines))
    else:
        first_name = course_details[0].get("kcname", "未知课程")
        title = f"您有成绩或排名更新：{first_name} 等 {total} 门"
        lines = []
        for course in course_details:
            c = _format_course(course)
            lines.append(f"{c['name']}：平时{c['cjxm1']} 期末{c['cjxm3']} 加权{c['zcj']} 绩点{c['pjxfjd']}")
        _show(title, "\n".join(lines))


def send_rank_notification(rank_data: dict, change_msgs: list = None,
                            is_simple: bool = False) -> None:
    if is_simple:
        _show("您有成绩或排名更新", "")
        return

    pm = rank_data.get("pm", "N/A")
    bjpm = rank_data.get("bjpm", "N/A")
    pjxfjd = rank_data.get("pjxfjd", "N/A")
    title = "您有成绩或排名更新：排名"
    lines = [
        f"平均学分绩点：{pjxfjd}",
        f"年名：{pm}；班名：{bjpm}",
    ]
    if change_msgs:
        lines.append("--- 变化 ---")
        lines.extend(change_msgs[:3])
    _show(title, "\n".join(lines))


def send_test_notification(is_simple: bool = False,
                            course_details: list = None) -> None:
    """测试通知：展示详细或简洁模式的实际通知内容"""
    if is_simple:
        _show("您有成绩或排名更新", "")
        return

    # 构造模拟数据展示格式
    course_name = "高等数学"
    if course_details:
        course_name = course_details[0].get("kcname", "高等数学")

    title = f"您有成绩或排名更新：{course_name}"
    message = (
        "平时分：90；期末分：82；加权分：85.5\n"
        "平均学分绩点：3.7；班名：3；年名：15"
    )
    _show(title, message)


def send_notification_preview(is_simple: bool) -> str:
    """返回通知预览文本（供前端展示）"""
    if is_simple:
        return "标题：您有成绩或排名更新\n内容：（无正文）"

    return (
        "标题：您有成绩或排名更新：高等数学\n"
        "正文：\n"
        "  平时分：90；期末分：82；加权分：85.5\n"
        "  平均学分绩点：3.7；班名：3；年名：15"
    )


def _show(title: str, message: str) -> None:
    """发送 macOS/Windows 系统通知。
    注：WebSocket 辅助通道暂时关闭，优先保证稳定性。后续开启时取消 _try_send_via_websocket 注释即可。
    """
    try:
        if sys.platform == "darwin":
            escaped_title = title.replace('"', '\\"').replace("'", "\\'")
            escaped_message = message.replace('"', '\\"').replace("'", "\\'")
            script = (
                f'display notification "{escaped_message}"'
                f' with title "{escaped_title}"'
            )
            logger.info(f"Executing AppleScript: {script}")
            subprocess.run(["osascript", "-e", script], check=True)
            logger.info(f"Notification sent via osascript: {title}")
        elif sys.platform == "win32":
            try:
                from win10toast import ToastNotifier
                ToastNotifier().show_toast(title, message, duration=5)
                logger.info(f"Notification sent via win10toast: {title}")
            except ImportError:
                logger.warning("win10toast not installed")
    except subprocess.CalledProcessError as e:
        logger.error(
            f"osascript 执行失败 (exit code {e.returncode}):\n"
            f"  stdout: {e.stdout.decode('utf-8', errors='replace') if e.stdout else '(empty)'}\n"
            f"  stderr: {e.stderr.decode('utf-8', errors='replace') if e.stderr else '(empty)'}"
        )
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")


def _try_send_via_websocket(title: str, message: str) -> bool:
    """尝试通过 MonitorService 的 WebSocket 广播通知事件。
    返回 True 表示成功广播（有至少一个 Flutter 客户端连接），False 表示无可用通道。
    """
    try:
        from backend.service.monitor_service import monitor
        import asyncio

        # 获取运行中的 event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.debug("WebSocket 不可用（无运行中的 event loop），使用 fallback")
            return False

        # 检查是否有连接的 Flutter 客户端
        if not monitor._listeners:
            logger.debug("WebSocket 无连接客户端，使用 osascript fallback")
            return False

        # 广播通知事件
        loop.create_task(monitor._broadcast({
            "type": "show_notification",
            "title": title,
            "message": message,
        }))
        return True
    except Exception as e:
        logger.debug(f"WebSocket 广播失败，使用 fallback: {e}")
        return False
