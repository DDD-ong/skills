"""
尽职调查模块 (Due Diligence)
============================
系统化尽职调查分析，支持检查清单生成、单文件/批量分析。
"""

import json
from typing import Optional
from core.client import BaseClient
from core.sse import collect_sse_content


class DueDiligenceModule:
    MODULE = "duediligence"

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
        """生成尽职调查检查清单 (SSE)。"""
        payload = {
            "documentType": document_type,
            "position": position,
            "industry": industry,
            "jurisdiction": jurisdiction,
            "language": language,
        }
        if customer_request:
            payload["customerRequest"] = customer_request

        resp = self.client._sse_post("/generateDueDiligenceChecklist", payload)
        content = collect_sse_content(resp)

        return {
            "status": "complete",
            "module": self.MODULE,
            "content": content,
        }

    def edit_checklist(
        self,
        document_type: str,
        position: str,
        checklist: list,
        customer_request: str = "",
    ) -> dict:
        """编辑检查清单。"""
        payload = {
            "documentType": document_type,
            "position": position,
            "checklist": checklist,
        }
        if customer_request:
            payload["customerRequest"] = customer_request

        resp = self.client._sse_post("/editDueDiligenceChecklist", payload)
        content = collect_sse_content(resp)

        return {
            "status": "complete",
            "module": self.MODULE,
            "content": content,
        }

    def start(
        self,
        file_url: str = "",
        file_urls: Optional[list] = None,
        session_id: str = "",
        checklist: str = "",
    ) -> dict:
        """
        提交文件进行尽职调查分析。

        单文件: 使用 file_url
        批量: 使用 file_urls
        """
        if file_urls and len(file_urls) > 1:
            # 批量分析
            payload = {"fileUrls": file_urls}
            if session_id:
                payload["sessionId"] = session_id
            if checklist:
                payload["checklist"] = checklist

            resp = self.client._post_with_retry("/analyzeDocuments", payload)
            return {
                "status": "started",
                "module": self.MODULE,
                "session_id": resp.get("sessionId", session_id),
                "chat_id": resp.get("chatId", ""),
            }
        else:
            # 单文件检查
            url = file_url or (file_urls[0] if file_urls else "")
            payload = {"fileUrl": url}
            if session_id:
                payload["sessionId"] = session_id
            if checklist:
                payload["checklist"] = checklist

            resp = self.client._post_with_retry("/checkDueDiligenceFile", payload)

            # 检查错误状态，避免将失败误判为异步处理中
            status = resp.get("status", "")
            if status in ("error", "failed"):
                return {
                    "status": "error",
                    "module": self.MODULE,
                    "session_id": resp.get("sessionId", session_id),
                    "chat_id": resp.get("chatId", ""),
                    "content": "",
                    "error": resp.get("message", "Due diligence file check failed"),
                }

            # 单文件可能直接返回结果
            if resp.get("riskLevel"):
                content = json.dumps({
                    "riskLevel": resp.get("riskLevel", ""),
                    "issueCount": resp.get("issueCount", 0),
                    "summary": resp.get("summary", ""),
                    "fields": resp.get("fields", []),
                    "complianceMatrix": resp.get("complianceMatrix", []),
                    "redFlags": resp.get("redFlags", []),
                }, ensure_ascii=False)
                return {
                    "status": "complete",
                    "module": self.MODULE,
                    "session_id": resp.get("sessionId", session_id),
                    "chat_id": resp.get("chatId", ""),
                    "content": content,
                }

            return {
                "status": "started",
                "module": self.MODULE,
                "session_id": resp.get("sessionId", session_id),
                "chat_id": resp.get("chatId", ""),
            }

    def check(self, session_id: str, chat_id: str = "") -> dict:
        """轮询尽职调查结果。"""
        params = {"sessionId": session_id}
        if chat_id:
            params["chatId"] = chat_id

        resp = self.client._get_with_retry("/getDueDiligenceResult", params=params)

        status = resp.get("status", "")
        if status == "completed":
            result = resp.get("result", resp.get("data", {}))
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
                "error": resp.get("message", "Due diligence analysis failed"),
            }

        return {"status": "running", "module": self.MODULE,
                "session_id": session_id, "chat_id": chat_id, "content": ""}
