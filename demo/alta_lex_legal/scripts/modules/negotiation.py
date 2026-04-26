"""
谈判策略模块 (Negotiation Playbook)
===================================
基于合同类型和业务场景生成谈判手册和策略建议。
"""

from core.client import BaseClient
from core.sse import collect_sse_content


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
        sync_sse: bool = False,
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

        if sync_sse:
            sse_resp = self.client._sse_get(
                "/commonGenerateSse/negotiationPlaybook",
                params={"sessionId": session_id},
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

        return {
            "status": "started",
            "module": self.MODULE,
            "session_id": session_id,
        }

    def check(self, session_id: str) -> dict:
        """轮询谈判手册结果：直接查询服务端 API。"""
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
