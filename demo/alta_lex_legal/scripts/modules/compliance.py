"""
合规审查模块 (Legal Compliance)
==============================
三步工作流合规审查：法条检索 -> 审查清单 -> 最终分析。
"""

import json
from typing import Optional
from core.client import BaseClient


class ComplianceModule:
    MODULE = "compliance"

    def __init__(self, client: BaseClient):
        self.client = client

    def start(
        self,
        file_urls: list,
        jurisdiction: str,
        domains: list,
        title: str = "",
        start_date: str = "",
        end_date: str = "",
        output_language: str = "zh",
        priority_sources: Optional[list] = None,
        entity_type: str = "",
        regulated_status: str = "",
        data_scope: str = "",
        business_regions: Optional[list] = None,
    ) -> dict:
        """启动合规审查任务。"""
        payload = {
            "fileUrls": file_urls,
            "jurisdiction": jurisdiction,
            "domains": domains,
        }
        if title:
            payload["title"] = title
        if start_date:
            payload["startDate"] = start_date
        if end_date:
            payload["endDate"] = end_date
        if output_language:
            payload["outputLanguage"] = output_language
        if priority_sources:
            payload["prioritySources"] = priority_sources
        if entity_type:
            payload["entityType"] = entity_type
        if regulated_status:
            payload["regulatedStatus"] = regulated_status
        if data_scope:
            payload["dataScope"] = data_scope
        if business_regions:
            payload["businessRegions"] = business_regions

        resp = self.client._post_with_retry(
            "/legal_compliance/startComplianceAnalysis", payload
        )

        return {
            "status": "started",
            "module": self.MODULE,
            "session_id": resp.get("sessionId", ""),
            "chat_id": resp.get("chatId", ""),
        }

    def check(self, session_id: str, chat_id: str) -> dict:
        """轮询合规审查结果，含进度信息。"""
        resp = self.client._get_with_retry(
            "/legal_compliance/getComplianceTaskResult",
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

        if status == "processing":
            progress = resp.get("progress", {})
            return {
                "status": "running",
                "module": self.MODULE,
                "session_id": session_id,
                "chat_id": chat_id,
                "content": "",
                "progress": {
                    "percentage": progress.get("progress_percentage", 0),
                    "phase": progress.get("phase_name", ""),
                    "message": progress.get("phase_message", ""),
                    "step": progress.get("current_step", 0),
                    "total_steps": progress.get("total_steps", 3),
                },
            }

        if status in ("error", "failed"):
            return {
                "status": "error",
                "module": self.MODULE,
                "session_id": session_id,
                "chat_id": chat_id,
                "content": "",
                "error": resp.get("message", "Compliance analysis failed"),
            }

        return {"status": "running", "module": self.MODULE,
                "session_id": session_id, "chat_id": chat_id, "content": ""}

    def export_excel(self, session_id: str) -> dict:
        """导出 Excel 报告。"""
        resp = self.client._post_with_retry(
            "/legal_compliance/export/excel", {"analysis_id": session_id}
        )
        return {
            "status": "complete",
            "module": self.MODULE,
            "session_id": session_id,
            "content": resp.get("url", ""),
        }
