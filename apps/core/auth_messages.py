AUTH_MESSAGES = {
    "LOGIN_MISSING": "请输入用户名和密码",
    "LOGIN_INVALID": "用户名或密码错误",
    "LOGIN_DISABLED": "用户名或密码错误",
    "LOGIN_SUCCESS": "登录成功",
    "REGISTER_SUCCESS": "注册成功，请使用新账号登录",
    "REGISTER_FAILED": "注册失败，请检查输入信息",
    "LOGOUT_SUCCESS": "已成功登出",
}


def auth_message(key, fallback="操作失败"):
    return AUTH_MESSAGES.get(key, fallback)
