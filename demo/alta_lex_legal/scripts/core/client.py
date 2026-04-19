"""
Alta Lex AI 基础 HTTP 客户端
============================
提供认证、请求、响应处理和 Session 过期自动重试。
认证方式: Authorization Header (Redis Session ID)

Session 缓存策略:
    同一设备 30 分钟内已登录则 Session 有效，重复调 login 接口会报错。
    因此采用 "缓存优先" 策略:
    1. 读取本地缓存的 Session ID → 验证是否仍有效
    2. 有效则直接复用，不调 login
    3. 无效(过期/不存在)才调 login，并缓存新 Session
"""

import json as _json
import os
import time
import requests
from typing import Optional


class AltaLexError(Exception):
    """基础异常。"""
    pass


class AuthenticationError(AltaLexError):
    """认证失败（用户名/密码错误或权限不足）。"""
    pass


class SessionExpiredError(AltaLexError):
    """Session 过期，需重新登录。"""
    pass


class APIError(AltaLexError):
    """API 调用异常。"""
    pass


class BaseClient:
    """
    Alta Lex AI 平台基础 HTTP 客户端。

    认证: Authorization Header 传递 Session ID
    Base URL: https://test.alta-lex.ai/api (可通过环境变量 ALTA_LEX_BASE_URL 覆盖)
    """

    DEFAULT_BASE_URL = "https://test.alta-lex.ai/api"
    SESSION_CACHE_FILE = os.path.join(
        os.path.expanduser("~"), ".openclaw", "skills", "alta_lex_legal", ".session_cache"
    )
    SESSION_TTL = 25 * 60  # 25 分钟 (服务端 30 分钟，留 5 分钟余量)

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (
            base_url
            or os.environ.get("ALTA_LEX_BASE_URL")
            or self.DEFAULT_BASE_URL
        ).rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        self._username: Optional[str] = None
        self._password: Optional[str] = None

    # ── 认证 ─────────────────────────────────────────────

    def set_auth(self, session_id: str):
        """直接设置 Authorization Header。"""
        self.session.headers["Authorization"] = session_id

    def login(self, username: str, password: str) -> dict:
        """
        登录获取 Session ID 并注入 Authorization Header。

        使用 /altalex/api/v1/web/public/auth/login/username/password 端点。
        警告: 同设备 30 分钟内已登录，重复调用此接口会报错。
        请优先使用 authenticate() 方法，它会自动处理 Session 缓存。

        Returns:
            用户信息 dict。
        """
        self._username = username
        self._password = password
        # 认证端点独立于 /api 路径，需要从 base_url 推导出站点根 URL
        # e.g. https://test.alta-lex.ai/api -> https://test.alta-lex.ai
        site_url = self.base_url.rsplit("/api", 1)[0]
        login_url = f"{site_url}/altalex/api/v1/web/public/auth/login/username/password"
        resp = self.session.post(
            login_url,
            json={"username": username, "password": password, "agree_terms": True},
            timeout=30,
        )
        data = self._handle_response(resp)
        # 从响应 Set-Cookie 或 data.token 中提取 session_id
        session_id = None
        for cookie in resp.cookies:
            if cookie.name in ("auth", "auth_test"):
                session_id = cookie.value
                break
        if not session_id:
            user_data = data.get("data", {})
            if isinstance(user_data, dict):
                session_id = user_data.get("token")
        if session_id:
            self.set_auth(session_id)
            self._save_session_cache(session_id)
        return data.get("data", data)

    def authenticate(self, username: str, password: str) -> dict:
        """
        智能认证: 优先复用缓存 Session，仅在失效时才调 login。

        流程:
        1. 读取本地缓存的 Session ID (带 TTL 检查) → 验证有效性
        2. 若 TTL 过期，尝试无 TTL 的 raw 缓存 (处理 25-30 分钟窗口期)
        3. 缓存均失效 → 调 login 获取新 Session 并缓存
        4. 若 login 报 "already logged in" → 自动 logout 旧 Session 再重试

        Returns:
            用户信息 dict。
        """
        self._username = username
        self._password = password

        # 1. 尝试从缓存恢复 Session (带 TTL 检查)
        cached_sid = self._load_session_cache()
        if cached_sid:
            self.set_auth(cached_sid)
            if self._verify_session():
                return {"status": "cached_session"}

        # 2. TTL 过期但服务端可能仍有效 (25-30 分钟窗口)
        raw_sid = self._load_session_cache_raw()
        if raw_sid and raw_sid != cached_sid:
            self.set_auth(raw_sid)
            if self._verify_session():
                self._save_session_cache(raw_sid)  # 刷新本地 TTL
                return {"status": "cached_session"}

        # 3. 缓存均失效，执行 login
        try:
            return self.login(username, password)
        except (APIError, AuthenticationError) as e:
            err_msg = str(e).lower()
            if "already logged" in err_msg or "logout" in err_msg:
                # 4. "already logged in" → 强制 logout 旧 Session 后重试
                self.logout(raw_sid)
                return self.login(username, password)
            raise

    def _verify_session(self) -> bool:
        """通过轻量 API 调用验证当前 Session 是否有效。"""
        try:
            self._get("/getAnalysisSessionList")
            return True
        except (SessionExpiredError, AuthenticationError):
            return False
        except AltaLexError:
            # 其他错误 (网络等) 不代表 Session 失效，保守认为有效
            return True

    def _auto_relogin(self) -> bool:
        """Session 过期时自动重新登录，返回是否成功。"""
        if not self._username or not self._password:
            return False
        try:
            self._clear_session_cache()
            self.login(self._username, self._password)
            return True
        except (APIError, AuthenticationError) as e:
            err_msg = str(e).lower()
            if "already logged" in err_msg or "logout" in err_msg:
                raw_sid = self._load_session_cache_raw()
                self.logout(raw_sid)
                try:
                    self.login(self._username, self._password)
                    return True
                except AltaLexError:
                    return False
            return False
        except AltaLexError:
            return False

    def get_user_info(self) -> dict:
        """通过获取会话列表验证当前认证是否有效。"""
        return self._get("/getAnalysisSessionList")

    # ── Session 缓存 ────────────────────────────────────

    def _save_session_cache(self, session_id: str):
        """将 Session ID 和时间戳写入本地缓存文件。"""
        try:
            cache_dir = os.path.dirname(self.SESSION_CACHE_FILE)
            os.makedirs(cache_dir, exist_ok=True)
            cache_data = {
                "session_id": session_id,
                "timestamp": time.time(),
                "base_url": self.base_url,
            }
            with open(self.SESSION_CACHE_FILE, "w") as f:
                _json.dump(cache_data, f)
        except OSError:
            pass  # 缓存写入失败不影响主流程

    def _load_session_cache(self) -> Optional[str]:
        """
        读取缓存的 Session ID，检查 TTL 和 base_url 匹配。
        返回有效的 session_id 或 None。
        """
        try:
            if not os.path.exists(self.SESSION_CACHE_FILE):
                return None
            with open(self.SESSION_CACHE_FILE, "r") as f:
                cache_data = _json.load(f)
            # TTL 检查: 超过 25 分钟视为过期
            elapsed = time.time() - cache_data.get("timestamp", 0)
            if elapsed > self.SESSION_TTL:
                return None
            # base_url 必须匹配 (防止测试/生产环境混用)
            if cache_data.get("base_url") != self.base_url:
                return None
            return cache_data.get("session_id")
        except (OSError, ValueError, KeyError):
            return None

    def _load_session_cache_raw(self) -> Optional[str]:
        """
        读取缓存的 Session ID，不做 TTL 检查。
        用于 logout / "already logged in" 恢复场景。
        """
        try:
            if not os.path.exists(self.SESSION_CACHE_FILE):
                return None
            with open(self.SESSION_CACHE_FILE, "r") as f:
                cache_data = _json.load(f)
            if cache_data.get("base_url") != self.base_url:
                return None
            return cache_data.get("session_id")
        except (OSError, ValueError, KeyError):
            return None

    def _clear_session_cache(self):
        """清除本地 Session 缓存。"""
        try:
            if os.path.exists(self.SESSION_CACHE_FILE):
                os.remove(self.SESSION_CACHE_FILE)
        except OSError:
            pass

    # ── Logout ─────────────────────────────────────────────

    def logout(self, session_id: Optional[str] = None) -> bool:
        """
        调用 logout API 注销指定 Session。

        Args:
            session_id: 要注销的 Session ID，默认使用当前 Authorization Header。

        Returns:
            是否成功注销。
        """
        site_url = self.base_url.rsplit("/api", 1)[0]
        logout_url = f"{site_url}/altalex/api/v1/web/public/auth/login/private/logout"
        sid = session_id or self.session.headers.get("Authorization")
        headers = dict(self.session.headers)
        if sid:
            headers["Authorization"] = sid
        try:
            resp = requests.post(logout_url, headers=headers, timeout=15)
            self._clear_session_cache()
            return resp.status_code < 400
        except Exception:
            self._clear_session_cache()
            return False

    # ── HTTP 方法 ────────────────────────────────────────

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, params=params, timeout=30)
        return self._handle_response(resp)

    def _post(self, path: str, json_data: Optional[dict] = None) -> dict:
        url = f"{self.base_url}{path}"
        resp = self.session.post(url, json=json_data or {}, timeout=30)
        return self._handle_response(resp)

    def _get_with_retry(self, path: str, params: Optional[dict] = None) -> dict:
        """GET 请求，Session 过期自动重登一次。"""
        try:
            return self._get(path, params)
        except SessionExpiredError:
            if self._auto_relogin():
                return self._get(path, params)
            raise

    def _post_with_retry(self, path: str, json_data: Optional[dict] = None) -> dict:
        """POST 请求，Session 过期自动重登一次。"""
        try:
            return self._post(path, json_data)
        except SessionExpiredError:
            if self._auto_relogin():
                return self._post(path, json_data)
            raise

    def _sse_get(self, path: str, params: Optional[dict] = None) -> requests.Response:
        """发起 GET SSE 流请求，返回原始 Response 对象 (stream=True)。"""
        url = f"{self.base_url}{path}"
        resp = self.session.get(
            url, params=params, stream=True, timeout=(10, 600),
            headers={**self.session.headers, "Accept": "text/event-stream"},
        )
        resp.raise_for_status()
        return resp

    def _sse_post(self, path: str, json_data: Optional[dict] = None) -> requests.Response:
        """发起 POST SSE 流请求，返回原始 Response 对象 (stream=True)。"""
        url = f"{self.base_url}{path}"
        resp = self.session.post(
            url, json=json_data or {}, stream=True, timeout=(10, 600),
            headers={**self.session.headers, "Accept": "text/event-stream"},
        )
        resp.raise_for_status()
        return resp

    # ── 响应处理 ─────────────────────────────────────────

    def _handle_response(self, resp: requests.Response):
        """统一处理 API 响应。支持 dict 和 list 类型 JSON 响应。"""
        try:
            data = resp.json()
        except ValueError:
            resp.raise_for_status()
            raise APIError(f"Non-JSON response (HTTP {resp.status_code}): {resp.text[:500]}")

        # list 类型响应 (如 /listFiles) 直接返回
        if isinstance(data, list):
            resp.raise_for_status()
            return data

        if resp.status_code >= 400:
            self._raise_from_error(data, resp.status_code)

        if data.get("status") == "error":
            self._raise_from_error(data, resp.status_code)

        return data

    @staticmethod
    def _raise_from_error(data: dict, status_code: int):
        """从错误响应中提取信息并抛出异常。"""
        error_info = data.get("error", {})
        if isinstance(error_info, dict):
            code = error_info.get("code", "UNKNOWN")
            message = error_info.get("message", data.get("message", "Unknown error"))
        else:
            code = "UNKNOWN"
            message = data.get("message", str(error_info))

        if code == "A01001" or status_code == 401:
            raise SessionExpiredError(message)
        if code == "A01007" or status_code == 403:
            raise AuthenticationError(message)
        raise APIError(f"[{code}] {message}")
