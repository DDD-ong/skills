"""
谈判策略模块 (Negotiation Playbook)
===================================
基于合同类型和业务场景生成谈判手册和策略建议。
"""

from core.client import BaseClient
from core.sse import consume_sse_background, read_sse_result


class NegotiationModule:
    MODULE = "negotiation"

    def __init__(self, client: BaseClient):
        self.client = client

    def start(
        self,
        industry: str,
        position: str,
        scenario: str,
        contract_type: str,
        language: str = "Chinese",
        title: str = "",
        customer_request: str = "",
        file_url: str = "",
    ) -> dict:
        """创建谈判手册会话并触发 SSE 生成。"""
        payload = {
            "title": title or f"{contract_type} Negotiation",
            "industry": industry,
            "position": position,
            "scenario": scenario,
            "contractType": contract_type,
            "language": language,
        }
        if customer_request:
            payload["customerRequest"] = customer_request
        if file_url:
            payload["fileUrl"] = file_url

        resp = self.client._post_with_retry("/createNegotiationPlaybook", payload)
        session_id = resp.get("sessionId", "")

        sse_url = f"{self.client.base_url}/commonGenerateSse/negotiationPlaybook"
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
        """轮询谈判手册结果：优先读本地 SSE 结果，回退到服务端 API。"""
        local = read_sse_result(session_id)
        if local and local.get("status") == "complete" and local.get("content"):
            return {"status": "complete", "module": self.MODULE,
                    "session_id": session_id, "content": local["content"]}
        if local and local.get("status") == "error" and local.get("error"):
            return {"status": "error", "module": self.MODULE,
                    "session_id": session_id, "content": "",
                    "error": local["error"]}

        resp = self.client._get_with_retry(
            "/getSessionHistory/negotiationPlaybook",
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
