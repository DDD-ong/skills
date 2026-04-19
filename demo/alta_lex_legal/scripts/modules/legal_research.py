"""
法律研究模块 (Legal Research)
============================
法律条文检索和深度分析，支持 Quick/Search 模式和多轮对话。
"""

from typing import Optional
from core.client import BaseClient
from core.sse import consume_sse_background, collect_sse_content, read_sse_result


class LegalResearchModule:
    MODULE = "research"

    def __init__(self, client: BaseClient):
        self.client = client

    def start(
        self,
        query: str,
        research_type: str = "search",
        file_urls: Optional[list] = None,
        sync_sse: bool = False,
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

        sse_payload = {
            "sessionId": session_id,
            "researchType": research_type,
        }

        if sync_sse:
            sse_resp = self.client._sse_post(
                "/legalAnalysisSse", json_data=sse_payload
            )
            content = collect_sse_content(sse_resp)
            if content:
                return {
                    "status": "complete",
                    "module": self.MODULE,
                    "session_id": session_id,
                    "content": content,
                }
            return {
                "status": "error",
                "module": self.MODULE,
                "session_id": session_id,
                "content": "",
                "error": "SSE stream completed but no content received",
            }

        sse_url = f"{self.client.base_url}/legalAnalysisSse"
        consume_sse_background(
            self.client.session, sse_url,
            method="POST", json_data=sse_payload,
            session_id=session_id,
        )

        return {
            "status": "started",
            "module": self.MODULE,
            "session_id": session_id,
        }

    def check(self, session_id: str) -> dict:
        """轮询研究结果：优先读本地 SSE 结果，回退到服务端 API。"""
        local = read_sse_result(session_id)
        if local and local.get("status") == "complete" and local.get("content"):
            return {"status": "complete", "module": self.MODULE,
                    "session_id": session_id, "content": local["content"]}
        if local and local.get("status") == "error" and local.get("error"):
            return {"status": "error", "module": self.MODULE,
                    "session_id": session_id, "content": "",
                    "error": local["error"]}

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
        sync_sse: bool = False,
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

        if sync_sse:
            sse_resp = self.client._sse_post(
                "/legalAnalysisSse", json_data=sse_payload
            )
            content = collect_sse_content(sse_resp)
            if content:
                return {
                    "status": "complete",
                    "module": self.MODULE,
                    "session_id": session_id,
                    "content": content,
                }
            return {
                "status": "error",
                "module": self.MODULE,
                "session_id": session_id,
                "content": "",
                "error": "SSE stream completed but no content received",
            }

        sse_url = f"{self.client.base_url}/legalAnalysisSse"
        consume_sse_background(
            self.client.session, sse_url,
            method="POST", json_data=sse_payload,
            session_id=session_id,
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
