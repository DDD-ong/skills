"""
脱敏处理模块 (Desensitization)
==============================
自动识别并脱敏文档中的敏感信息。
"""

from typing import Optional
from core.client import BaseClient


class DesensitizationModule:
    MODULE = "desensitize"

    def __init__(self, client: BaseClient):
        self.client = client

    def start(
        self,
        file_url: str,
        title: str = "",
        entity_types: Optional[list] = None,
    ) -> dict:
        """
        启动脱敏工作流。

        entity_types 可选: PERSON, ORGANIZATION, EMAIL, PHONE,
                          ID_NUMBER, ADDRESS, BANK_CARD, DATE
        """
        payload = {"fileUrl": file_url}
        if title:
            payload["title"] = title
        if entity_types:
            payload["entity_types"] = entity_types

        resp = self.client._post_with_retry("/runDesensitize", payload)

        return {
            "status": "started",
            "module": self.MODULE,
            "session_id": resp.get("sessionId", ""),
        }

    def check(self, session_id: str) -> dict:
        """轮询脱敏结果。"""
        resp = self.client._get_with_retry(
            "/getWorkflowDetail/desensitize",
            params={"sessionId": session_id},
        )

        status = resp.get("status", "")
        data = resp.get("data", {})

        if status == "completed" and data:
            result = data.get("result", {})
            preview_url = result.get("preview_url", "")
            desensitized_filename = result.get("desensitized_filename", "")
            return {
                "status": "complete",
                "module": self.MODULE,
                "session_id": session_id,
                "content": preview_url,
                "extra": {
                    "desensitized_filename": desensitized_filename,
                    "original_filename": result.get("original_filename", ""),
                    "spend_time": result.get("spend_time", 0),
                },
            }

        if status in ("error", "failed"):
            return {
                "status": "error",
                "module": self.MODULE,
                "session_id": session_id,
                "content": "",
                "error": resp.get("message", "Desensitization failed"),
            }

        return {"status": "running", "module": self.MODULE,
                "session_id": session_id, "content": ""}
