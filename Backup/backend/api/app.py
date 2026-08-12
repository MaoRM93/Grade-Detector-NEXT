# backend/api/app.py
"""
GradeMonitor Backend API - FastAPI 应用入口

启动方式: uvicorn backend.api.app:app --host 127.0.0.1 --port 18923

API 端点:
  POST /api/login         用户登录
  POST /api/logout        登出
  GET  /api/grades        获取成绩列表
  GET  /api/rank          获取排名信息
  GET  /api/settings      获取设置
  POST /api/settings      更新设置
  GET  /api/monitor/status  监控状态
  WS   /ws/events         实时事件推送（监控变化通知）
"""

import shutil
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any

from backend.auth.login import login_and_bind_jw
from backend.service.grade_service import GradeService
from backend.service.rank_service import RankService
from backend.service.monitor_service import monitor
from backend.service.notification_service import send_test_notification
from backend.storage.settings import load_settings, save_settings, DEFAULT_SETTINGS
from backend.storage.cache import get_data_dir, get_data_file_path, load_total_query_count, increment_query_count, reset_query_count

# ---------- 应用初始化 ----------
app = FastAPI(
    title="GradeMonitor API",
    description="自动查成绩后台服务",
    version="3.0.0",
)

# 允许本地 Flutter 应用跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- 请求 / 响应模型 ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str = ""


class SettingsUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    remember_me: Optional[bool] = None
    notify_mode: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    interval_seconds: Optional[int] = None
    auto_start: Optional[bool] = None
    auto_monitor_enabled: Optional[bool] = None
    rank_monitor_enabled: Optional[bool] = None
    show_menubar_icon: Optional[bool] = None
    no_auto_query: Optional[bool] = None


# ---------- API 端点 ----------


@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "service": "GradeMonitor Backend"}


@app.post("/api/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """用户登录（验证凭据 + 建立 OAuth Session）"""
    import requests as req_lib

    session = req_lib.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })

    try:
        login_and_bind_jw(session, req.username, req.password)
        return LoginResponse(success=True, message="登录成功")
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
    finally:
        session.close()


@app.get("/api/grades")
async def get_grades():
    """获取成绩列表"""
    settings = load_settings()
    username = settings.get("username", "")
    password = settings.get("password", "")

    if not username or not password:
        raise HTTPException(
            status_code=400,
            detail="请先登录并保存凭据",
        )

    try:
        service = GradeService(username, password)
        result = service.fetch_grade_json()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rank")
async def get_rank():
    """获取排名信息"""
    settings = load_settings()
    username = settings.get("username", "")
    password = settings.get("password", "")

    if not username or not password:
        raise HTTPException(
            status_code=400,
            detail="请先登录并保存凭据",
        )

    try:
        service = RankService(username, password)
        rank_data = service.fetch_latest_rank()
        if rank_data is None:
            return {"data": None, "message": "暂无排名数据"}
        return {"data": rank_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/settings")
async def get_settings():
    """获取当前设置"""
    return load_settings()


@app.post("/api/settings")
async def update_settings(update: SettingsUpdate):
    """更新设置（部分更新）"""
    current = load_settings()
    for key, val in update.dict(exclude_none=True).items():
        if val is not None:
            current[key] = val
    save_settings(current)
    return {"success": True, "settings": current}


@app.get("/api/monitor/status")
async def get_monitor_status():
    """获取监控状态"""
    settings = load_settings()
    last_q = monitor.last_query_at
    return {
        "auto_monitor_enabled": settings.get("auto_monitor_enabled", False),
        "rank_monitor_enabled": settings.get("rank_monitor_enabled", False),
        "interval_seconds": settings.get("interval_seconds", 300),
        "start_time": settings.get("start_time", "08:00"),
        "end_time": settings.get("end_time", "22:00"),
        "is_running": monitor.is_running,
        "last_query_at": last_q.isoformat() if last_q else None,
        "total_queries": load_total_query_count(),
    }


@app.post("/api/monitor/start")
async def start_monitor():
    """启动监控服务"""
    try:
        await monitor.start()
        return {"success": True, "message": "监控已启动"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/monitor/stop")
async def stop_monitor():
    """停止监控服务"""
    try:
        await monitor.stop()
        return {"success": True, "message": "监控已停止"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/monitor/restart")
async def restart_monitor():
    """重启监控服务（设置变更后使用）"""
    try:
        await monitor.restart()
        return {"success": True, "message": "监控已重启"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notification/test")
async def test_notification():
    """发送测试通知"""
    try:
        send_test_notification()
        return {"success": True, "message": "测试通知已发送"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 开发者工具 ----------

@app.post("/api/dev/query-once")
async def query_once():
    """立即查询一次成绩和排名（不等待定时器）"""
    settings = load_settings()
    username = settings.get("username", "")
    password = settings.get("password", "")
    if not username or not password:
        raise HTTPException(status_code=400, detail="请先登录并保存凭据")
    results = {}
    try:
        gs = GradeService(username, password)
        results["grades"] = gs.fetch_grade_json()
    except Exception as e:
        results["grades_error"] = str(e)
    try:
        rs = RankService(username, password)
        rank_data = rs.fetch_latest_rank()
        results["rank"] = rank_data
    except Exception as e:
        results["rank_error"] = str(e)
    # 手动查询也计入统计
    increment_query_count()
    return {"success": True, "results": results}


@app.post("/api/dev/clear-cache")
async def clear_cache():
    """清理所有本地缓存（成绩/排名缓存文件）"""
    data_dir = get_data_dir()
    cleaned = []
    for fname in ["local_grades.json", "local_ranks.json", "stats.json"]:
        fp = get_data_file_path(fname)
        if fp.exists():
            fp.unlink()
            cleaned.append(fname)
    return {"success": True, "cleaned": cleaned, "message": f"已清理 {len(cleaned)} 个缓存文件"}


@app.post("/api/dev/clear-all-data")
async def clear_all_data():
    """清理所有数据（缓存 + 设置不变）"""
    data_dir = get_data_dir()
    cleaned = []
    for fname in ["local_grades.json", "local_ranks.json", "settings.json", "stats.json"]:
        fp = get_data_file_path(fname)
        if fp.exists():
            fp.unlink()
            cleaned.append(fname)
    return {"success": True, "cleaned": cleaned, "message": f"已清理 {len(cleaned)} 个数据文件"}


@app.get("/api/dev/open-log-dir")
async def open_log_dir():
    """打开日志/数据目录"""
    data_dir = str(get_data_dir())
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", data_dir])
        elif sys.platform == "win32":
            subprocess.run(["explorer", data_dir])
        else:
            subprocess.run(["xdg-open", data_dir])
        return {"success": True, "path": data_dir}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dev/data-dir")
async def get_data_dir_info():
    """获取数据目录路径"""
    return {"path": str(get_data_dir()), "exists": get_data_dir().exists()}


# ---------- WebSocket 事件推送 ----------


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """
    实时事件推送（监控变化通知）

    Flutter 端连接此 WebSocket 后，监控检测到变化时自动推送事件。
    """
    await websocket.accept()
    await websocket.send_json({"type": "connected", "message": "已连接"})

    async def send_event(event: dict) -> None:
        """将监控事件转发给 Flutter 客户端"""
        try:
            await websocket.send_json(event)
        except Exception:
            pass

    monitor.add_listener(send_event)

    try:
        while True:
            data = await websocket.receive_text()
            # 心跳保持
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        monitor.remove_listener(send_event)
