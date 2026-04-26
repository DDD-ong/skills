"""
合同起草模块 (Contract Draft)
============================
基于业务参数和可选模板生成合同文档，SSE 流式响应。
"""

from typing import Optional
from core.client import BaseClient
from core.sse import collect_sse_content


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
        sync_sse: bool = False,
    ) -> dict:
        """创建起草会话并触发 SSE 生成。

        Args:
            sync_sse: True 时同步消费 SSE 流并直接返回内容 (用于 --wait 模式)。
                      False 时在后台线程消费 (用于 cron 轮询模式)。
        """
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

        if sync_sse:
            sse_resp = self.client._sse_get(
                "/commonGenerateSse", params={"sessionId": session_id}
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
        """轮询起草结果：直接查询服务端 API。"""
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
