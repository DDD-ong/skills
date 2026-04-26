"""
IPO 支持模块 (IPO Support)
==========================
针对香港联交所 IPO 流程生成检查清单和合规审核。
"""

from core.client import BaseClient
from core.sse import collect_sse_content


class IPOSupportModule:
    MODULE = "ipo"

    def __init__(self, client: BaseClient):
        self.client = client

    def start(
        self,
        title: str = "IPO Check",
        connected_person: str = "",
        connect_transact_class: str = "Share Transfer",
        transaction_classification: str = "Connected Transaction",
        involves_guarantees: bool = True,
        shareholder_approval: bool = True,
        circular_requirements: bool = True,
        other_relevant_facts: str = "",
        file_url: str = "",
        sync_sse: bool = False,
    ) -> dict:
        """创建 IPO 检查清单会话并触发 SSE 生成。"""
        payload = {
            "title": title,
            "connectedPerson": connected_person,
            "connectTransactClass": connect_transact_class,
            "transactionClassification": transaction_classification,
            "involvesGuaranteesSecurity": involves_guarantees,
            "shareholderApproval": shareholder_approval,
            "circularRequirements": circular_requirements,
            "otherRelevantFacts": other_relevant_facts,
            "fileUrl": file_url,
        }

        resp = self.client._post_with_retry("/createIpoCheckListSession", payload)
        session_id = resp.get("sessionId", "")

        if sync_sse:
            sse_resp = self.client._sse_get(
                "/commonGenerateSse/ipoCheckList",
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
        """轮询检查清单结果：直接查询服务端 API。"""
        resp = self.client._get_with_retry(
            "/getSessionHistory/ipoCheckList", params={"sessionId": session_id}
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
