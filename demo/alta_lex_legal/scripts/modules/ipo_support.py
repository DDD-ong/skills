"""
IPO 支持模块 (IPO Support)
==========================
针对香港联交所 IPO 流程生成检查清单和合规审核。
"""

from core.client import BaseClient
from core.sse import consume_sse_background, collect_sse_content, read_sse_result


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

        sse_url = f"{self.client.base_url}/commonGenerateSse/ipoCheckList"
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
        """轮询检查清单结果：优先读本地 SSE 结果，回退到服务端 API。"""
        local = read_sse_result(session_id)
        if local and local.get("status") == "complete" and local.get("content"):
            return {"status": "complete", "module": self.MODULE,
                    "session_id": session_id, "content": local["content"]}
        if local and local.get("status") == "error" and local.get("error"):
            return {"status": "error", "module": self.MODULE,
                    "session_id": session_id, "content": "",
                    "error": local["error"]}

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
