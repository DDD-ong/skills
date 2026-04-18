"""
JSON 输出工具
=============
为 OpenClaw cron 集成提供标准化 JSON 输出。
"""

import json
import sys
from typing import Optional


def json_output(
    status: str,
    module: str,
    session_id: str = "",
    chat_id: str = "",
    content: str = "",
    error: str = "",
    extra: Optional[dict] = None,
    progress: Optional[dict] = None,
):
    """
    输出标准化 JSON 到 stdout，供 OpenClaw cron 解析。

    status: started | running | complete | error
    """
    result = {
        "status": status,
        "module": module,
        "session_id": session_id,
        "chat_id": chat_id,
        "content": content,
        "error": error,
    }
    if progress is not None:
        result["progress"] = progress
    if extra is not None:
        result["extra"] = extra
    print(json.dumps(result, ensure_ascii=False), flush=True)


def error_exit(module: str, error_msg: str, session_id: str = ""):
    """输出错误 JSON 并退出。"""
    json_output(status="error", module=module, session_id=session_id, error=error_msg)
    sys.exit(1)
