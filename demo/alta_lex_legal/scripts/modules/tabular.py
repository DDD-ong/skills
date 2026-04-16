"""
表格处理模块 (Tabular Analysis)
==============================
从文档中提取表格数据并进行结构化分析。
"""

import json
from typing import Optional
from core.client import BaseClient
from core.sse import consume_sse_background, collect_sse_content


class TabularModule:
    MODULE = "tabular"

    def __init__(self, client: BaseClient):
        self.client = client

    def generate_checklist(
        self,
        document_type: str,
        position: str,
        industry: str,
        jurisdiction: str = "PRC",
        language: str = "Chinese",
        customer_request: str = "",
    ) -> dict:
        """生成表格检查清单 (SSE)。"""
        payload = {
            "documentType": document_type,
            "position": position,
            "industry": industry,
            "jurisdiction": jurisdiction,
            "language": language,
        }
        if customer_request:
            payload["customerRequest"] = customer_request

        resp = self.client._sse_post("/generateTabularChecklist", payload)
        content = collect_sse_content(resp)

        return {
            "status": "complete",
            "module": self.MODULE,
            "content": content,
        }

    def start(
        self,
        file_urls: list,
        document_type: str = "",
        position: str = "",
        industry: str = "",
        jurisdiction: str = "PRC",
        language: str = "Chinese",
        title: str = "",
        customer_request: str = "",
        checklist: Optional[list] = None,
        checklist_file: str = "",
    ) -> dict:
        """启动表格分析任务。"""
        payload = {
            "fileUrls": file_urls,
        }
        if document_type:
            payload["documentType"] = document_type
        if position:
            payload["position"] = position
        if industry:
            payload["industry"] = industry
        if jurisdiction:
            payload["jurisdiction"] = jurisdiction
        if language:
            payload["language"] = language
        if title:
            payload["title"] = title
        if customer_request:
            payload["customerRequest"] = customer_request
        if checklist:
            payload["checklist"] = checklist
        elif checklist_file:
            payload["checklistFile"] = checklist_file

        resp = self.client._post_with_retry("/startTabularAnalysis", payload)

        return {
            "status": "started",
            "module": self.MODULE,
            "session_id": resp.get("sessionId", ""),
            "chat_id": resp.get("chatId", ""),
        }

    def check(self, session_id: str, chat_id: str) -> dict:
        """轮询表格分析结果。"""
        resp = self.client._get_with_retry(
            "/getTabularTaskResult",
            params={"sessionId": session_id, "chatId": chat_id},
        )

        status = resp.get("status", "")

        if status == "completed":
            result = resp.get("result", {})
            content = json.dumps(result, ensure_ascii=False) if result else ""
            return {
                "status": "complete",
                "module": self.MODULE,
                "session_id": session_id,
                "chat_id": chat_id,
                "content": content,
            }

        if status in ("error", "failed"):
            return {
                "status": "error",
                "module": self.MODULE,
                "session_id": session_id,
                "chat_id": chat_id,
                "content": "",
                "error": resp.get("message", "Tabular analysis failed"),
            }

        return {"status": "running", "module": self.MODULE,
                "session_id": session_id, "chat_id": chat_id, "content": ""}
