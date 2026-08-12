# backend/service/rank_service.py
"""
排名查询服务
"""
import requests
from typing import Any, Optional

from backend.auth.login import login_and_bind_jw


def fetch_rank(session: requests.Session) -> Optional[dict[str, Any]]:
    """
    调用排名接口，获取所有学期的专业排名和班级排名

    Args:
        session: 已经过 OAuth 认证的 requests.Session

    Returns:
        dict | None: 包含专业排名(pm)、班级排名(bjpm)、总人数(countnum)等
    """
    api_url = (
        "https://jw.ruc.edu.cn/resService/jwxtpt/v1/xsd/cjgl_xsxdsq/"
        "professionalRankingQuery"
        "?resourceCode=XSMH0527"
        "&apiCode=jw.xsd.xsdInfo.controller.CjglKccjckController"
        ".professionalRankingQuery"
    )

    # 从 session 中提取 token
    jwt_token = session.cookies.get("token", domain="jw.ruc.edu.cn")
    if not jwt_token:
        raise Exception(
            "[ERROR] Missing JWT token in session cookies. "
            "Authentication may have failed."
        )

    # 注入认证头
    session.headers.update({
        "Authorization": f"Bearer {jwt_token}",
        "token": jwt_token,
        "Content-Type": "application/json",
    })

    # 构造请求参数（查询所有学期）
    payload = {
        "jczy013id": (
            "2025-2026-2,2025-2026-1,"
            "2024-2025-4,2024-2025-2,2024-2025-1"
        ),
        "kclbcode": "",
        "jczy010id": [],
        "jczy013idList": [],
    }

    print("[INFO] Requesting rank data from API (with JWT Bearer)...")
    response = session.post(api_url, json=payload)

    if response.status_code != 200:
        raise Exception(
            f"[ERROR] Rank API request failed with status: "
            f"{response.status_code}. Response: {response.text}"
        )

    resp_json = response.json()
    if resp_json.get("errorCode") != "success":
        raise Exception(
            f"[ERROR] Rank API returned error: {resp_json.get('errorMessage')}"
        )

    data = resp_json.get("data", [])
    if not data:
        return None

    # 取第一条记录（通常只有一条，包含所有汇总信息）
    rank_info = data[0]
    return {
        "pm": rank_info.get("pm", "N/A"),
        "bjpm": rank_info.get("bjpm", "N/A"),
        "countnum": rank_info.get("countnum", "N/A"),
        "bjgms": rank_info.get("bjgms", "N/A"),
        "sdxf": rank_info.get("sdxf", "N/A"),          # 已取得总学分
        "zjd": rank_info.get("zjd", "N/A"),            # 总学分绩点
        "pjxfjd": rank_info.get("pjxfjd", "N/A"),       # 平均学分绩点
        "ndzy_name": rank_info.get("ndzy_name", "未知专业"),
        "xs_name": rank_info.get("xs_name", "未知姓名"),
        "xh": rank_info.get("xh", "未知学号"),
        "xnxq": rank_info.get("xnxq", "全部学年"),
    }


class RankService:
    """
    排名查询服务封装

    管理 Session 生命周期，提供高层查询接口。
    """

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    def _create_session(self) -> requests.Session:
        """创建并认证一个新的 Session"""
        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        login_and_bind_jw(session, self.username, self.password)
        return session

    def fetch_latest_rank(self) -> Optional[dict[str, Any]]:
        """获取最新排名信息"""
        session = self._create_session()
        try:
            return fetch_rank(session)
        finally:
            session.close()
