# backend/auth/login.py
"""
RUC 统一认证（OAuth2）登录流程
"""
import requests
from bs4 import BeautifulSoup
from backend.auth.oauth import AUTH_LOGIN_URL, LOGIN_URL, AUTHORIZE_URL
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def get_csrf_token(session: requests.Session) -> str:
    """从认证页面提取 CSRF Token"""
    resp = session.get(AUTH_LOGIN_URL)
    soup = BeautifulSoup(resp.text, "html.parser")
    token = soup.find("input", {"id": "csrftoken"})
    if not token:
        raise Exception("[ERROR] csrftoken not found in the authentication page.")
    return token["value"]


def login_and_bind_jw(session: requests.Session, username: str, password: str):
    """
    完整认证闭环（无需验证码）

    Args:
        session: requests.Session 实例
        username: 学号
        password: 密码

    Returns:
        requests.Response: 教务系统回调的最终响应
    """
    csrf = get_csrf_token(session)
    logger.info(f"CSRF Token: {csrf[:10]}...")

    # 验证码字段置空（服务端可能忽略）
    data = {
        "username": f"ruc:{username}",
        "password": password,
        "code": "",
        "remember_me": "false",
        "redirect_uri": AUTHORIZE_URL,
        "token": csrf,
        "captcha_id": "",
        "twofactor_password": "",
        "twofactor_recovery": "",
    }

    resp = session.post(LOGIN_URL, json=data, allow_redirects=False)

    if resp.status_code != 302:
        logger.error(f"Unexpected status code: {resp.status_code}")
        logger.error(f"Server response body: {resp.text[:500]}")
        try:
            soup = BeautifulSoup(resp.text, "html.parser")
            error_msg = soup.find(class_="error-msg").text.strip()
        except Exception:
            error_msg = "Please check the logs for response body."
        raise Exception(
            f"Login authentication failed (HTTP {resp.status_code}). "
            f"Reason: {error_msg}"
        )

    oauth_authorize_url = resp.headers.get("Location")
    if oauth_authorize_url and oauth_authorize_url.startswith("/"):
        oauth_authorize_url = f"https://v.ruc.edu.cn{oauth_authorize_url}"

    logger.info(f"Authentication successful. Redirecting to OAuth2: {oauth_authorize_url}")

    resp_oauth = session.get(oauth_authorize_url, allow_redirects=False)
    if resp_oauth.status_code != 302:
        raise Exception(f"OAuth2 authorization failed (HTTP {resp_oauth.status_code})")

    jw_callback_url = resp_oauth.headers.get("Location")
    if jw_callback_url and jw_callback_url.startswith("/"):
        jw_callback_url = f"https://jw.ruc.edu.cn{jw_callback_url}"

    logger.info(f"OAuth2 Code obtained. Establishing Session: {jw_callback_url.split('?')[0]}...")

    final_resp = session.get(jw_callback_url, allow_redirects=True)

    jw_cookies = session.cookies.get_dict(domain="jw.ruc.edu.cn")
    if jw_cookies:
        logger.info(f"Session successfully established for jw.ruc.edu.cn (cookies: {list(jw_cookies.keys())})")
        return final_resp
    else:
        raise Exception(
            "Process completed, but no valid Cookie found for jw.ruc.edu.cn."
        )
