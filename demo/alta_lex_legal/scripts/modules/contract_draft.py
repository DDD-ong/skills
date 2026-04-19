"""
合同起草模块 (Contract Draft)
============================
基于业务参数和可选模板生成合同文档，SSE 流式响应。
"""

from typing import Optional
from core.client import BaseClient
from core.sse import consume_sse_background, read_sse_result


class ContractDraftModule:
    MODULE = "draft"

    def __init__(self, client: BaseClient):
        self.client = client

    def start(
        self,
        industry: str,
        position: str,
        scenario: str,
        contract_type: str,
        governing_law: str,
        language: str = "Chinese",
        template_url: str = "",
        customer_request: str = "",
    ) -> dict:
        """创建起草会话并触发 SSE 生成。"""
        payload = {
            "industry": industry,
            "position": position,
            "scenario": scenario,
            "contractType": contract_type,
            "governingLaw": governing_law,
            "language": language,
        }
        if template_url:
            payload["templateFileUrl"] = template_url
        if customer_request:
            payload["customerRequest"] = customer_request

        resp = self.client._post_with_retry("/createDraftSession", payload)
        session_id = resp.get("sessionId", "")

        # 后台触发 SSE 流（捕获内容到本地文件）
        sse_url = f"{self.client.base_url}/commonGenerateSse"
        consume_sse_background(
            self.client.session, sse_url,
            method="GET", params={"sessionId": session_id},
            session_id=session_id,
        )

        return {
            "status": "started",
            "module": self.MODULE,
            "session_id": session_id,
        }

    def check(self, session_id: str) -> dict:
        """轮询起草结果：优先读本地 SSE 结果，回退到服务端 API。"""
        # 1. 先检查本地 SSE 结果文件
        local = read_sse_result(session_id)
        if local and local.get("status") == "complete" and local.get("content"):
            return {"status": "complete", "module": self.MODULE,
                    "session_id": session_id, "content": local["content"]}
        if local and local.get("status") == "error" and local.get("error"):
            return {"status": "error", "module": self.MODULE,
                    "session_id": session_id, "content": "",
                    "error": local["error"]}

        # 2. 回退到服务端 API
        resp = self.client._get_with_retry(
            "/getDraftSessionHistory", params={"sessionId": session_id}
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

    def list_sessions(self) -> list:
        """获取会话列表。"""
        resp = self.client._get_with_retry("/getDraftSessionList")
        return resp.get("chats", [])

    def delete_session(self, session_id: str) -> dict:
        """删除会话。"""
        return self.client._post_with_retry(
            "/removeDraftSession", {"sessionId": session_id}
        )
