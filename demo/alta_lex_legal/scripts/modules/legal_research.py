"""
法律研究模块 (Legal Research)
============================
法律条文检索和深度分析，支持 Quick/Search 模式和多轮对话。
"""

from typing import Optional
from core.client import BaseClient
from core.sse import consume_sse_background


class LegalResearchModule:
    MODULE = "research"

    def __init__(self, client: BaseClient):
        self.client = client

    def start(
        self,
        query: str,
        research_type: str = "search",
        file_urls: Optional[list] = None,
    ) -> dict:
        """创建法律研究会话并触发 SSE 分析。"""
        create_payload = {
            "query": query,
            "researchType": research_type,
        }
        if file_urls:
            create_payload["fileUrls"] = file_urls

        resp = self.client._post_with_retry("/createAnalysisSession", create_payload)
        session_id = resp.get("sessionId", "")

        # Legal Research 使用 POST SSE
        sse_url = f"{self.client.base_url}/legalAnalysisSse"
        sse_payload = {
            "sessionId": session_id,
            "researchType": research_type,
        }
        consume_sse_background(
            self.client.session, sse_url,
            method="POST", json_data=sse_payload,
        )

        return {
            "status": "started",
            "module": self.MODULE,
            "session_id": session_id,
        }

    def check(self, session_id: str) -> dict:
        """轮询研究结果。"""
        resp = self.client._get_with_retry(
            "/getAnalysisSessionHistory", params={"sessionId": session_id}
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

    def followup(
        self,
        session_id: str,
        query: str,
        chat_id: str = "",
        research_type: str = "search",
        file_urls: Optional[list] = None,
    ) -> dict:
        """多轮追问 (Search 模式最多 10 轮)。"""
        sse_payload = {
            "sessionId": session_id,
            "query": query,
            "researchType": research_type,
        }
        if chat_id:
            sse_payload["chatId"] = chat_id
        if file_urls:
            sse_payload["fileUrls"] = file_urls

        sse_url = f"{self.client.base_url}/legalAnalysisSse"
        consume_sse_background(
            self.client.session, sse_url,
            method="POST", json_data=sse_payload,
        )

        return {
            "status": "started",
            "module": self.MODULE,
            "session_id": session_id,
        }

    def list_sessions(self) -> list:
        """获取会话列表。"""
        resp = self.client._get_with_retry("/getAnalysisSessionList")
        return resp.get("chats", [])

    def delete_session(self, session_id: str) -> dict:
        """删除会话。"""
        return self.client._post_with_retry(
            "/removeAnalysisSession", {"sessionId": session_id}
        )
