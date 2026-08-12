# backend/service/grade_service.py
"""
成绩查询服务

使用已认证的 Session 请求教务系统成绩 API，返回结构化数据。
"""
import requests
from typing import Any

from backend.auth.login import login_and_bind_jw


def fetch_all_grades(session: requests.Session) -> dict[str, Any]:
    """
    使用已授权的 Session 获取全部成绩列表

    Args:
        session: 已经过 OAuth 认证的 requests.Session

    Returns:
        dict: API 原始响应 JSON，格式 { errorCode, errorMessage, data: [...] }
    """
    api_url = (
        "https://jw.ruc.edu.cn/resService/jwxtpt/v1/xsd/cjgl_xsxdsq/findKccjList"
        "?resourceCode=XSMH0526"
        "&apiCode=jw.xsd.xsdInfo.controller.CjglKccjckController.findKccjList"
    )

    # 1. 从已鉴权的 Cookie 中提取 JWT 凭证
    jwt_token = session.cookies.get("token", domain="jw.ruc.edu.cn")

    if not jwt_token:
        raise Exception(
            "[ERROR] Missing JWT token in session cookies. "
            "Authentication may have failed."
        )

    # 2. 将凭证注入到当前请求的 Headers 中
    session.headers.update({
        "Authorization": f"Bearer {jwt_token}",
        "token": jwt_token,
    })

    # 3. 构造请求载荷
    payload = {
        "pyfa007id": "1",
        "jczy013id": [],
        "fxjczy005id": "",
        "cjckflag": "xsdcjck",
        "kthList": [],
        "page": {
            "pageIndex": 1,
            "pageSize": 200,
            "orderBy": '[{"field":"jczy013id","sortType":"asc"}]',
        },
    }

    print("[INFO] Requesting grade data from API (with JWT Bearer)...")

    response = session.post(api_url, json=payload)

    if response.status_code != 200:
        raise Exception(
            f"[ERROR] API request failed with status: {response.status_code}. "
            f"Response: {response.text}"
        )

    response_json = response.json()

    # 4. 二次校验：防止 HTTP 200 但业务逻辑依然报错
    if response_json.get("errorMessage") == "security.httpstatu.401.1006":
        raise Exception(
            "[ERROR] API returned 401 Unauthorized inside HTTP 200 payload. "
            "Header key mismatch."
        )

    print("[INFO] Grade data fetched successfully.")
    return response_json


class GradeService:
    """
    成绩查询服务封装

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

    def fetch_latest_grades(self) -> dict[str, Any]:
        """
        获取最新成绩，返回按课程号 (kth) 索引的字典

        Returns:
            dict: { kth: course_dict, ... }
        """
        session = self._create_session()
        try:
            result = fetch_all_grades(session)
            if result.get("errorCode") != "success":
                raise Exception(
                    f"成绩 API 返回错误: {result.get('errorMessage')}"
                )
            course_list = result.get("data", [])
            grades_dict = {}
            for course in course_list:
                kth = course.get("kth")
                if kth:
                    grades_dict[kth] = course
            return grades_dict
        finally:
            session.close()

    def fetch_grade_json(self) -> dict[str, Any]:
        """获取原始成绩 JSON（用于 API 透传）"""
        session = self._create_session()
        try:
            result = fetch_all_grades(session)
            if result.get("errorCode") != "success":
                raise Exception(
                    f"成绩 API 返回错误: {result.get('errorMessage')}"
                )
            return result
        finally:
            session.close()
