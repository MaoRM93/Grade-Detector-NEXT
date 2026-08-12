# backend/utils/startup.py
"""
macOS 开机自启动管理
使用 AppleScript / System Events 设置登录项，可在「系统设置 → 登录项」中查看和管��
"""
import os
import subprocess
import sys

APP_NAME = "GradeMonitor"


def _get_app_path() -> str:
    """获取当前 .app 包的完整路径（打包后）或脚本路径（开发模式）"""
    if getattr(sys, "frozen", False):
        exe_path = sys.executable
        if ".app" in exe_path:
            return exe_path.split(".app")[0] + ".app"
        return exe_path
    else:
        return os.path.abspath(sys.argv[0])


def is_startup_enabled() -> bool:
    """检查是否已设置开机自启动（通过 AppleScript 查询）"""
    if sys.platform != "darwin":
        return False

    app_path = _get_app_path()
    if not app_path.endswith(".app"):
        return False

    app_name = os.path.splitext(os.path.basename(app_path))[0]

    try:
        script = (
            f'tell application "System Events"\n'
            f"set loginItems to name of every login item\n"
            f'if loginItems contains "{app_name}" then\n'
            f'return "yes"\n'
            f"else\n"
            f'return "no"\n'
            f"end if\n"
            f"end tell"
        )
        result = subprocess.run(
            ["osascript", "-"],
            input=script,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() == "yes"
    except Exception:
        return False


def set_startup_enabled(enabled: bool) -> None:
    """设置开机自启动（使用 macOS 原生登录项）"""
    if sys.platform != "darwin":
        raise Exception("This function is only for macOS")

    app_path = _get_app_path()

    if not app_path.endswith(".app"):
        raise Exception("开机自启动功能仅在打包为 .app 后可用。请先导出应用。")

    if enabled:
        _add_login_item(app_path)
    else:
        _remove_login_item(app_path)


def _add_login_item(app_path: str) -> None:
    """通过 AppleScript 添加登录项"""
    app_name = os.path.splitext(os.path.basename(app_path))[0]

    # 先尝试删除旧的（避免重复）
    try:
        _remove_login_item(app_path)
    except Exception:
        pass

    script = (
        f'tell application "System Events"\n'
        f"make login item at end with properties "
        f'{{path:"{app_path}", name:"{app_name}", hidden:true}}\n'
        f"end tell"
    )
    result = subprocess.run(
        ["osascript", "-"],
        input=script,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        raise Exception(f"添���登录项失败: {result.stderr.strip()}")


def _remove_login_item(app_path: str) -> None:
    """通过 AppleScript 删除登录项"""
    app_name = os.path.splitext(os.path.basename(app_path))[0]

    script = (
        f'tell application "System Events"\n'
        f'delete (every login item whose name is "{app_name}")\n'
        f"end tell"
    )
    subprocess.run(
        ["osascript", "-"],
        input=script,
        capture_output=True,
        text=True,
        timeout=15,
    )
