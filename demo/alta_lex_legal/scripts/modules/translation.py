"""
文档翻译模块 (Document Translation)
===================================
法律文档多语言翻译，支持会话模式和无状态快速翻译。
"""

from core.client import BaseClient
from core.sse import consume_sse_background, collect_sse_content


class TranslationModule:
    MODULE = "translation"

    def __init__(self, client: BaseClient):
        self.client = client

    def start(
        self,
        file_url: str,
        source_language: str = "English",
        target_language: str = "Chinese",
        contract_type: str = "",
        governing_law: str = "",
    ) -> dict:
        """创建翻译会话并触发 SSE 翻译。"""
        payload = {
            "sourceLanguage": source_language,
            "targetLanguage": target_language,
            "fileUrl": file_url,
        }
        if contract_type:
            payload["contractType"] = contract_type
        if governing_law:
            payload["gawLaw"] = governing_law

        resp = self.client._post_with_retry("/createTranslateSession", payload)
        session_id = resp.get("sessionId", "")

        # 触发 SSE 翻译
        sse_url = f"{self.client.base_url}/textTranslate"
        consume_sse_background(
            self.client.session, sse_url,
            method="POST", json_data={"sessionId": session_id},
        )

        return {
            "status": "started",
            "module": self.MODULE,
            "session_id": session_id,
        }

    def check(self, session_id: str) -> dict:
        """轮询翻译结果。"""
        resp = self.client._get_with_retry(
            "/getTranslateSessionHistory",
            params={"sessionId": session_id},
        )
        chats = resp.get("chats", [])
        if not chats:
            return {"status": "running", "module": self.MODULE,
                    "session_id": session_id, "content": ""}

        last_chat = chats[-1]
        answer = last_chat.get("answer", "")
        if answer:
            return {"status": "complete", "module": self.MODULE,
                    "session_id": session_id, "content": answer}
        return {"status": "running", "module": self.MODULE,
                "session_id": session_id, "content": ""}

    def quick_translate(
        self,
        query: str,
        source_language: str = "English",
        target_language: str = "Chinese",
        contract_type: str = "",
        governing_law: str = "",
    ) -> dict:
        """无状态快速翻译 (短文本)。"""
        payload = {
            "sourceLanguage": source_language,
            "targetLanguage": target_language,
            "query": query,
        }
        if contract_type:
            payload["contractType"] = contract_type
        if governing_law:
            payload["gawLaw"] = governing_law

        # genaralTranslate 可能是 SSE 也可能是同步，尝试 SSE
        try:
            resp = self.client._sse_post("/genaralTranslate", payload)
            content = collect_sse_content(resp)
            return {
                "status": "complete",
                "module": self.MODULE,
                "content": content,
            }
        except Exception:
            # 降级为同步调用
            resp = self.client._post_with_retry("/genaralTranslate", payload)
            content = resp.get("data", resp.get("message", ""))
            return {
                "status": "complete",
                "module": self.MODULE,
                "content": str(content),
            }

    def list_sessions(self) -> list:
        """获取翻译会话列表。"""
        resp = self.client._get_with_retry("/getTranslateSessionList")
        return resp.get("chats", [])

    def delete_session(self, session_id: str) -> dict:
        """删除翻译会话。"""
        return self.client._post_with_retry(
            "/removeTranslateSession", {"sessionId": session_id}
        )
