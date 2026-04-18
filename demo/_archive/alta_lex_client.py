"""
Alta Lex AI API Client
======================
封装与 Alta Lex AI 平台交互的 Python 客户端。
支持登录认证（JWT Cookie）、会话管理和法律分析（SSE流式响应）。

认证机制:
    - JWT Token（HS256），通过 Cookie "auth" 传递
    - 支持两种认证方式：
      1. --token 直接传入 JWT（推荐，从浏览器 Cookie 获取）
      2. -u/-p 用户名密码登录（需要 /api/login 端点可用）
    - requests.Session 自动管理 Cookie 生命周期

使用方式:
    python alta_lex_client.py --token <JWT> -q "你的法律问题"
    python alta_lex_client.py --token <JWT> --list-sessions
    python alta_lex_client.py --token <JWT> --session-history <SESSION_ID>
"""

import argparse
import json
import os
import sys
import threading
from typing import Optional, Generator, Tuple

import requests


# ------------------------------------------------------------------
# 异常类
# ------------------------------------------------------------------

class AltaLexError(Exception):
    """Alta Lex 客户端基础异常。"""
    pass


class AuthenticationError(AltaLexError):
    """认证失败异常（用户名/密码错误）。"""
    pass


class SessionExpiredError(AltaLexError):
    """会话过期异常（JWT Token 已失效，需重新登录）。"""
    pass


class APIError(AltaLexError):
    """API 调用异常。"""
    pass


# ------------------------------------------------------------------
# SSE 事件数据类
# ------------------------------------------------------------------

class SSEEvent:
    """表示一个 SSE 数据事件。"""

    def __init__(self, message: str, is_finished: bool, raw: dict):
        self.message = message
        self.is_finished = is_finished
        self.raw = raw

    def __repr__(self):
        return f"SSEEvent(message={self.message!r}, is_finished={self.is_finished})"


# ------------------------------------------------------------------
# 客户端
# ------------------------------------------------------------------

class AltaLexClient:
    """
    Alta Lex AI 平台 API 客户端。

    认证方式: JWT Token（通过 Cookie 自动管理）
    API 基础路径: /api/
    响应格式: JSON {"status": "success"|"error", "data": ..., "traceId": ...}
    """

    BASE_URL = "https://test.alta-lex.ai"

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        self.user_info: Optional[dict] = None

    # ------------------------------------------------------------------
    # 认证相关
    # ------------------------------------------------------------------

    def set_token(self, token: str, cookie_name: Optional[str] = None):
        """
        直接设置认证 Token（无需调用 login）。

        适用于从浏览器 Cookie 中提取 auth Token 后直接使用的场景。
        Token 会被注入到 requests.Session 的 Cookie 中。

        Args:
            token: Token 字符串（从浏览器 Cookie 获取）。
            cookie_name: Cookie 名称。默认自动推断：
                         test.alta-lex.ai → "auth_test"
                         其他 → "auth"
        """
        if cookie_name is None:
            cookie_name = "auth_test" if "test." in self.base_url else "auth"
        domain = self.base_url.split("//")[-1].split("/")[0]
        self.session.cookies.set(cookie_name, token, domain=domain)

    def login(self, username: str, password: str) -> dict:
        """
        登录并获取 JWT Token。

        注意: 此端点可能在某些环境中不可用（返回 404）。
        如果不可用，请使用 set_token() 直接设置 JWT Token。

        Returns:
            用户信息 dict。
        Raises:
            AuthenticationError: 用户名或密码错误。
            APIError: 端点不可用。
        """
        resp = self._post("/api/login", json_data={
            "username": username,
            "password": password,
        })
        self.user_info = resp.get("data", {})
        return self.user_info

    def logout(self) -> dict:
        """登出并清除 JWT Cookie。"""
        resp = self._post("/api/logout")
        self.user_info = None
        self.session.cookies.clear()
        return resp

    def is_authenticated(self) -> bool:
        """通过获取会话列表来检查当前 Token 是否仍然有效。"""
        try:
            self.get_analysis_session_list()
            return True
        except (SessionExpiredError, APIError):
            return False

    def get_auth_token(self) -> Optional[str]:
        """获取当前 JWT Token（如果存在）。"""
        return self.session.cookies.get("auth")

    # ------------------------------------------------------------------
    # 法律研究 (Legal Research) — 核心功能
    # ------------------------------------------------------------------

    def create_analysis_session(self, query: str) -> str:
        """
        创建法律分析会话。

        Args:
            query: 查询描述（会作为会话标题）。
        Returns:
            新创建的 sessionId (UUID)。
        """
        resp = self._post("/api/createAnalysisSession", json_data={
            "query": query,
        })
        # sessionId 在顶层，不在 data 内
        session_id = resp.get("sessionId")
        if not session_id:
            # 兼容可能的格式变化
            data = resp.get("data")
            if isinstance(data, dict):
                session_id = data.get("sessionId")
        if not session_id:
            raise APIError(f"未获取到 sessionId，响应: {resp}")
        return session_id

    def legal_analysis_sse(
        self,
        session_id: str,
        query: str,
        practice_area: str = "",
        jurisdiction: str = "",
        output_language: str = "English",
        background: str = "",
        legal_research_pro: bool = False,
    ) -> Generator[SSEEvent, None, None]:
        """
        发送法律分析请求，通过 SSE (Server-Sent Events) 流式接收分析结果。

        SSE 数据格式:
            `: init\\n\\n`                                  — 初始化信号
            `: heartbeat N\\n\\n`                           — 心跳保活
            `data: {"message": "<text>", "is_finished": false}\\n\\n` — 文本片段
            `data: {"message": "<text>", "is_finished": true}\\n\\n`  — 最后一个片段

        Args:
            session_id: 会话 ID（由 create_analysis_session 返回）。
            query: 法律问题。
            practice_area: 法律领域，如 "Contract Law"。
            jurisdiction: 司法管辖区，如 "Hong Kong"。
            output_language: 输出语言（默认 English）。
            background: 额外背景信息。
            legal_research_pro: 是否启用高级研究模式。

        Yields:
            SSEEvent 对象，包含 message（文本片段）和 is_finished 标志。
        """
        payload = {
            "sessionId": session_id,
            "query": query,
            "practiceArea": practice_area,
            "jurisdiction": jurisdiction,
            "outputLanguage": output_language,
            "background": background,
            "legalResearchPro": legal_research_pro,
        }
        url = f"{self.base_url}/api/legalAnalysisSse"
        resp = self.session.post(
            url,
            json=payload,
            stream=True,
            timeout=(10, 600),
        )
        resp.raise_for_status()
        yield from self._parse_sse_stream(resp)

    def legal_analysis(
        self,
        query: str,
        practice_area: str = "",
        jurisdiction: str = "",
        output_language: str = "English",
        background: str = "",
        legal_research_pro: bool = False,
    ) -> Tuple[str, str]:
        """
        便捷方法：创建会话 + 发送查询 + 收集完整响应。

        Returns:
            (session_id, full_text) 元组。
        """
        session_id = self.create_analysis_session(query)
        parts = []
        for event in self.legal_analysis_sse(
            session_id=session_id,
            query=query,
            practice_area=practice_area,
            jurisdiction=jurisdiction,
            output_language=output_language,
            background=background,
            legal_research_pro=legal_research_pro,
        ):
            parts.append(event.message)
            if event.is_finished:
                break
        return session_id, "".join(parts)

    def get_analysis_session_list(self) -> list:
        """获取所有分析会话列表。"""
        resp = self._get("/api/getAnalysisSessionList")
        return resp.get("chats", resp.get("data", []))

    def get_analysis_session_history(self, session_id: str) -> dict:
        """
        获取指定会话的聊天历史。

        Returns:
            dict，包含 chats 列表（每项含 chatId, query, answer, status）和 researchType。
        """
        resp = self._get("/api/getAnalysisSessionHistory", params={
            "sessionId": session_id,
        })
        return resp

    # ------------------------------------------------------------------
    # 草稿 (Drafting)
    # ------------------------------------------------------------------

    def get_draft_session_list(self) -> list:
        """获取草稿会话列表。"""
        resp = self._get("/api/getDraftSessionList")
        return resp.get("chats", resp.get("data", []))

    def create_draft_session(
        self,
        scenario: str,
        position: str,
        industry: str,
        contract_type: str,
        governing_law: str,
        language: str = "English",
    ) -> str:
        """创建草稿会话并返回 sessionId。"""
        resp = self._post("/api/createDraftSession", json_data={
            "scenario": scenario,
            "position": position,
            "industry": industry,
            "contractType": contract_type,
            "governingLaw": governing_law,
            "language": language,
        })
        return resp.get("sessionId") or (resp.get("data") or {}).get("sessionId", "")

    # ------------------------------------------------------------------
    # 翻译 (Translate)
    # ------------------------------------------------------------------

    def get_translate_session_list(self) -> list:
        """获取翻译会话列表。"""
        resp = self._get("/api/getTranslateSessionList")
        return resp.get("chats", resp.get("data", []))

    # ------------------------------------------------------------------
    # 快速启动 & 状态检查（OpenClaw 集成）
    # ------------------------------------------------------------------

    def quick_start_analysis(
        self,
        query: str,
        practice_area: str = "",
        jurisdiction: str = "",
        output_language: str = "English",
        background: str = "",
        legal_research_pro: bool = False,
    ) -> str:
        """
        快速启动法律分析：创建会话并发起 SSE 请求（后台消费流），立即返回 session_id。

        用于 OpenClaw 异步工作流：启动分析 -> 返回 session_id -> cron 轮询检查结果。
        """
        session_id = self.create_analysis_session(query)
        payload = {
            "sessionId": session_id,
            "query": query,
            "practiceArea": practice_area,
            "jurisdiction": jurisdiction,
            "outputLanguage": output_language,
            "background": background,
            "legalResearchPro": legal_research_pro,
        }
        url = f"{self.base_url}/api/legalAnalysisSse"

        def _consume_sse():
            try:
                resp = self.session.post(url, json=payload, stream=True, timeout=(10, 600))
                resp.raise_for_status()
                for _ in resp.iter_content(chunk_size=4096):
                    pass
            except Exception:
                pass

        t = threading.Thread(target=_consume_sse, daemon=True)
        t.start()
        return session_id

    def check_session_complete(self, session_id: str) -> dict:
        """
        检查分析会话是否完成。

        Returns:
            dict: {"status": "running"|"complete"|"error", "session_id": "...",
                   "content": "...", "error": "..."}
        """
        try:
            history = self.get_analysis_session_history(session_id)
            chats = history.get("chats", [])
            if not chats:
                return {"status": "running", "session_id": session_id,
                        "content": "", "error": ""}
            last_chat = chats[-1]
            answer = last_chat.get("answer", "")
            if answer:
                return {"status": "complete", "session_id": session_id,
                        "content": answer, "error": ""}
            return {"status": "running", "session_id": session_id,
                    "content": "", "error": ""}
        except SessionExpiredError as e:
            return {"status": "error", "session_id": session_id,
                    "content": "", "error": f"Session expired: {e}"}
        except AltaLexError as e:
            return {"status": "error", "session_id": session_id,
                    "content": "", "error": str(e)}

    # ------------------------------------------------------------------
    # 文件管理
    # ------------------------------------------------------------------

    def list_files(self, file_type: str = "review") -> list:
        """列出指定类型的文件。"""
        resp = self._post("/api/listFiles", json_data={"type": file_type})
        return resp.get("data", [])

    # ------------------------------------------------------------------
    # 内部工具方法
    # ------------------------------------------------------------------

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, params=params, timeout=30)
        return self._handle_response(resp)

    def _post(self, path: str, json_data: Optional[dict] = None) -> dict:
        url = f"{self.base_url}{path}"
        resp = self.session.post(url, json=json_data or {}, timeout=30)
        return self._handle_response(resp)

    def _handle_response(self, resp: requests.Response) -> dict:
        """统一处理 API 响应，提取错误信息并抛出对应异常。"""
        try:
            data = resp.json()
        except ValueError:
            resp.raise_for_status()
            raise APIError(f"非 JSON 响应 (HTTP {resp.status_code}): {resp.text[:500]}")

        # HTTP 错误
        if resp.status_code >= 400:
            self._raise_from_error(data, resp.status_code)

        # 业务逻辑错误
        if data.get("status") == "error":
            self._raise_from_error(data, resp.status_code)

        return data

    @staticmethod
    def _raise_from_error(data: dict, status_code: int):
        """从错误响应中提取信息并抛出异常。"""
        error_info = data.get("error", {})
        if isinstance(error_info, dict):
            code = error_info.get("code", "UNKNOWN")
            message = error_info.get("message", data.get("message", "未知错误"))
        else:
            code = "UNKNOWN"
            message = data.get("message", str(error_info))

        if code == "A01001" or status_code == 401:
            raise SessionExpiredError(message)
        if status_code == 403:
            raise AuthenticationError(message)
        raise APIError(f"[{code}] {message}")

    @staticmethod
    def _parse_sse_stream(resp: requests.Response) -> Generator[SSEEvent, None, None]:
        """
        解析 Server-Sent Events 流。

        Alta Lex SSE 格式:
            `: init`          — SSE 注释（初始化信号，忽略）
            `: heartbeat N`   — SSE 注释（心跳保活，忽略）
            `data: {"message": "...", "is_finished": false}`  — 数据事件
        """
        buffer = ""
        for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
            if not chunk:
                continue
            buffer += chunk
            while "\n\n" in buffer:
                event_text, buffer = buffer.split("\n\n", 1)
                for line in event_text.split("\n"):
                    line = line.strip()
                    if not line or line.startswith(":"):
                        # SSE 注释行（: init, : heartbeat N），跳过
                        continue
                    if line.startswith("data:"):
                        payload = line[len("data:"):].strip()
                        if not payload or payload == "[DONE]":
                            continue
                        try:
                            obj = json.loads(payload)
                            yield SSEEvent(
                                message=obj.get("message", ""),
                                is_finished=obj.get("is_finished", False),
                                raw=obj,
                            )
                        except json.JSONDecodeError:
                            # 非 JSON 格式的 data 行
                            yield SSEEvent(message=payload, is_finished=False, raw={})
        # 处理缓冲区中剩余数据
        if buffer.strip():
            for line in buffer.strip().split("\n"):
                line = line.strip()
                if not line or line.startswith(":"):
                    continue
                if line.startswith("data:"):
                    payload = line[len("data:"):].strip()
                    if not payload or payload == "[DONE]":
                        continue
                    try:
                        obj = json.loads(payload)
                        yield SSEEvent(
                            message=obj.get("message", ""),
                            is_finished=obj.get("is_finished", False),
                            raw=obj,
                        )
                    except json.JSONDecodeError:
                        yield SSEEvent(message=payload, is_finished=False, raw={})


# ------------------------------------------------------------------
# CLI 入口
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Alta Lex AI API Client - 法律研究助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用 JWT Token 认证（推荐，从浏览器 Cookie 获取）
  python alta_lex_client.py --token <JWT_TOKEN> -q "What is contract law?"
  python alta_lex_client.py --token <JWT_TOKEN> --list-sessions

  # 使用环境变量传递 Token
  export ALTA_LEX_TOKEN=<JWT_TOKEN>
  python alta_lex_client.py --list-sessions

  # 使用用户名密码登录（需要 /api/login 端点可用）
  python alta_lex_client.py -u Mplus -p 'PPD689#' -q "What is contract law?"

  # 指定法律领域和管辖区
  python alta_lex_client.py --token <JWT> \\
      -q "What are the requirements for a valid contract?" \\
      --practice-area "Contract Law" \\
      --jurisdiction "Hong Kong"

  # 查看指定会话的聊天历史
  python alta_lex_client.py --token <JWT> --session-history <SESSION_ID>

  # OpenClaw 集成：快速启动
  python alta_lex_client.py --token <JWT> --quick-start -q "Legal question"

  # OpenClaw 集成：轮询检查
  python alta_lex_client.py --token <JWT> --check-session <SESSION_ID>
        """,
    )
    auth_group = parser.add_argument_group("认证方式（二选一）")
    auth_group.add_argument("--token", default=None,
                            help="JWT Token（从浏览器 auth Cookie 获取，或设置 ALTA_LEX_TOKEN 环境变量）")
    auth_group.add_argument("-u", "--username", default=None, help="登录用户名")
    auth_group.add_argument("-p", "--password", default=None, help="登录密码")

    parser.add_argument("-q", "--query", help="法律查询问题")
    parser.add_argument("--practice-area", default="", help="法律领域 (如: Contract Law)")
    parser.add_argument("--jurisdiction", default="", help="司法管辖区 (如: Hong Kong)")
    parser.add_argument("--output-language", default="English", help="输出语言 (默认: English)")
    parser.add_argument("--background", default="", help="背景信息")
    parser.add_argument("--pro", action="store_true", help="启用 Legal Research Pro 模式")
    parser.add_argument("--list-sessions", action="store_true", help="列出所有分析会话")
    parser.add_argument("--session-history", metavar="SESSION_ID", help="查看指定会话的历史")
    parser.add_argument("--quick-start", action="store_true",
                        help="快速启动分析（立即返回 session_id JSON，用于 OpenClaw 集成）")
    parser.add_argument("--check-session", metavar="SESSION_ID",
                        help="检查分析会话状态（输出 JSON，用于 OpenClaw cron 轮询）")
    parser.add_argument("--base-url", default=None, help="API 基础 URL")

    args = parser.parse_args()
    client = AltaLexClient(base_url=args.base_url)

    # JSON 输出模式（用于 OpenClaw 集成）
    json_mode = args.quick_start or args.check_session

    # 1. 认证：优先 --token / ALTA_LEX_TOKEN，其次 -u/-p 登录
    token = args.token or os.environ.get("ALTA_LEX_TOKEN")
    if token:
        client.set_token(token)
        if not json_mode:
            print("[+] 使用 JWT Token 认证")
    elif args.username and args.password:
        try:
            if not json_mode:
                print(f"[*] 正在登录 ({args.username})...")
            user = client.login(args.username, args.password)
            if not json_mode:
                print(f"[+] 登录成功! 用户: {user.get('username')}, 角色: {user.get('role')}")
        except AltaLexError as e:
            if json_mode:
                print(json.dumps({"status": "error", "session_id": "",
                                  "content": "", "error": f"Login failed: {e}"}))
            else:
                print(f"[-] 登录失败: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        msg = "需要认证：使用 --token <JWT> 或 -u <用户名> -p <密码>，或设置 ALTA_LEX_TOKEN 环境变量"
        if json_mode:
            print(json.dumps({"status": "error", "session_id": "",
                              "content": "", "error": msg}))
        else:
            print(f"[-] {msg}", file=sys.stderr)
        sys.exit(1)

    # -- OpenClaw 集成：快速启动分析 --
    if args.quick_start:
        if not args.query:
            print(json.dumps({"status": "error", "session_id": "",
                              "content": "", "error": "Missing --query (-q)"}))
            sys.exit(1)
        try:
            session_id = client.quick_start_analysis(
                query=args.query,
                practice_area=args.practice_area,
                jurisdiction=args.jurisdiction,
                output_language=args.output_language,
                background=args.background,
                legal_research_pro=args.pro,
            )
            print(json.dumps({"status": "started", "session_id": session_id,
                              "content": "", "error": ""}))
        except AltaLexError as e:
            print(json.dumps({"status": "error", "session_id": "",
                              "content": "", "error": str(e)}))
            sys.exit(1)
        return

    # -- OpenClaw 集成：检查会话状态 --
    if args.check_session:
        result = client.check_session_complete(args.check_session)
        print(json.dumps(result))
        sys.exit(0 if result["status"] in ("complete", "running") else 1)

    # 2. 列出会话
    if args.list_sessions:
        try:
            sessions = client.get_analysis_session_list()
            print(f"\n[*] 共有 {len(sessions)} 个分析会话:")
            for s in sessions:
                sid = s.get("sessionId", "N/A")
                name = s.get("sessionName") or s.get("title", "无标题")
                # 截断过长的名称
                if len(name) > 80:
                    name = name[:80] + "..."
                print(f"    - {sid}: {name}")
        except AltaLexError as e:
            print(f"[-] 获取会话列表失败: {e}")
        if not args.query and not args.session_history:
            return

    # 3. 查看会话历史
    if args.session_history:
        try:
            history = client.get_analysis_session_history(args.session_history)
            chats = history.get("chats", [])
            print(f"\n[*] 会话历史 ({args.session_history}), 共 {len(chats)} 条记录:")
            for chat in chats:
                query_text = chat.get("query") or ""
                print(f"\n  Q: {query_text[:200]}")
                answer = chat.get("answer") or ""
                print(f"  A: {answer[:500]}{'...' if len(answer) > 500 else ''}")
        except AltaLexError as e:
            print(f"[-] 获取会话历史失败: {e}")
        if not args.query:
            return

    # 4. 执行法律分析
    if args.query:
        try:
            print(f"\n[*] 创建新分析会话...")
            session_id = client.create_analysis_session(args.query)
            print(f"[+] 会话ID: {session_id}")
            print(f"[*] 正在分析 (SSE 流式接收，可能需要 5-8 分钟)...\n")
            print("=" * 60)

            full_response = []
            for event in client.legal_analysis_sse(
                session_id=session_id,
                query=args.query,
                practice_area=args.practice_area,
                jurisdiction=args.jurisdiction,
                output_language=args.output_language,
                background=args.background,
                legal_research_pro=args.pro,
            ):
                print(event.message, end="", flush=True)
                full_response.append(event.message)
                if event.is_finished:
                    break

            print("\n" + "=" * 60)
            print(f"\n[+] 分析完成! 会话ID: {session_id}")
            print(f"[*] 响应总长度: {len(''.join(full_response))} 字符")

        except AltaLexError as e:
            print(f"\n[-] 分析失败: {e}", file=sys.stderr)
            sys.exit(1)

    elif not args.list_sessions and not args.session_history:
        print("\n[!] 未指定操作。使用 -q 进行查询, --list-sessions 列出会话, "
              "或 --session-history <ID> 查看历史。")


if __name__ == "__main__":
    main()
