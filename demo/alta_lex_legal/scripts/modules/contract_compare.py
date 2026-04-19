"""
合同比对模块 (Contract Compare)
==============================
对比两个合同版本的差异，生成变更分析。
"""

from core.client import BaseClient
from core.sse import consume_sse_background, read_sse_result


class ContractCompareModule:
    MODULE = "compare"

    def __init__(self, client: BaseClient):
        self.client = client

    def start(
        self,
        original_url: str,
        revised_url: str,
        industry: str = "General",
        position: str = "Reviewer",
        contract_type: str = "General Agreement",
        language: str = "Chinese",
        governing_law: str = "",
        title: str = "",
        customer_request: str = "",
    ) -> dict:
        """创建比对会话并触发 SSE 生成。"""
        payload = {
            "originalContractUrl": original_url,
            "revisedContractUrl": revised_url,
            "title": title or "Contract Comparison",
            "industry": industry,
            "position": position,
            "contractType": contract_type,
            "language": language,
            "governingLaw": governing_law,
            "customerRequest": customer_request,
        }

        resp = self.client._post_with_retry("/createContractCompare", payload)
        session_id = resp.get("sessionId", "")

        sse_url = f"{self.client.base_url}/commonGenerateSse/contractCompare"
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
        """轮询比对结果：优先读本地 SSE 结果，回退到服务端 API。"""
        local = read_sse_result(session_id)
        if local and local.get("status") == "complete" and local.get("content"):
            return {"status": "complete", "module": self.MODULE,
                    "session_id": session_id, "content": local["content"]}
        if local and local.get("status") == "error" and local.get("error"):
            return {"status": "error", "module": self.MODULE,
                    "session_id": session_id, "content": "",
                    "error": local["error"]}

        resp = self.client._get_with_retry(
            "/getSessionHistory/contractCompare", params={"sessionId": session_id}
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
