# backend/auth/oauth.py
"""
OAuth 认证相关 URL 配置
"""

# 获取验证码（预留）
CAPTCHA_URL = "https://v.ruc.edu.cn/auth/captcha"

# 登录接口
LOGIN_URL = "https://v.ruc.edu.cn/auth/login"

# OAuth 授权 URL（redirect_uri 指向教务系统回调）
AUTHORIZE_URL = (
    "https://v.ruc.edu.cn/oauth2/authorize"
    "?response_type=code"
    "&scope=all"
    "&state=yourstate"
    "&client_id=5d25ae5b90f4d14aa601ede8.ruc"
    "&redirect_uri=https://jw.ruc.edu.cn/secService/oauthlogin"
)

# 认证登录页面 URL（proxy 模式）
AUTH_LOGIN_URL = (
    "https://v.ruc.edu.cn/auth/login"
    "?proxy=true"
    "&redirect_uri=https://v.ruc.edu.cn/oauth2/authorize"
    "?response_type=code"
    "&scope=all"
    "&state=yourstate"
    "&client_id=5d25ae5b90f4d14aa601ede8.ruc"
    "&redirect_uri=https://jw.ruc.edu.cn/secService/oauthlogin"
)
