"""
合同审查模块 (Contract Review)
==============================
上传合同文件进行 AI 审查，支持 Summary 和 Edit 两种模式。
"""

import os
from core.client import BaseClient


class ContractReviewModule:
    MODULE = "review"

    def __init__(self, client: BaseClient):
        self.client = client

    def start(
        self,
        file_url: str,
        review_type: str,
        industry: str,
        position: str,
        scenario: str,
        contract_type: str,
        governing_law: str = "",
        language: str = "",
        customer_request: str = "",
    ) -> dict:
        """
        提交合同审查任务。

        review_type: "1"=Summary, "2"=Edit
        """
        payload = {
            "fileUrl": file_url,
            "reviewType": review_type,
            "industry": industry,
            "position": position,
            "scenario": scenario,
            "contractType": contract_type,
        }
        if governing_law:
            payload["governingLaw"] = governing_law
        if language:
            payload["language"] = language
        if customer_request:
            payload["customerRequest"] = customer_request

        resp = self.client._post_with_retry("/common_review", payload)

        # 从 task_data URL 提取文件名
        task_data = resp.get("task_data", "")
        filename = os.path.basename(task_data) if task_data else os.path.basename(file_url)

        return {
            "status": "started",
            "module": self.MODULE,
            "session_id": "",
            "extra": {"filename": filename},
        }

    def check(self, filename: str) -> dict:
        """轮询审查结果。"""
        resp = self.client._post_with_retry("/getReviewAnswer", {
            "type": "contract_review",
            "filename": filename,
        })

        status = resp.get("status", "")
        if status == "completed":
            content = resp.get("processing_result", "")
            edit_doc = resp.get("edit_document", "")
            review_type = resp.get("review_type", "1")
            result = {
                "status": "complete",
                "module": self.MODULE,
                "session_id": "",
                "content": content,
            }
            if edit_doc:
                result["extra"] = {
                    "edit_document": edit_doc,
                    "review_type": review_type,
                    "preview_url": resp.get("url", ""),
                }
            return result

        return {"status": "running", "module": self.MODULE,
                "session_id": "", "content": ""}

    def list_files(self) -> list:
        """获取文件列表。"""
        resp = self.client._post_with_retry("/listFiles", {"type": "contract_review"})
        if isinstance(resp, list):
            return resp
        return resp.get("data", [])

    def delete_file(self, filename: str) -> dict:
        """删除文件。"""
        return self.client._post_with_retry("/deleteFile", {"filename": filename})
