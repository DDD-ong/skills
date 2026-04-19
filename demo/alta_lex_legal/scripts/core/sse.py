"""
SSE (Server-Sent Events) 流解析器
=================================
解析 Alta Lex API 的 SSE 流式响应。
"""

import json
import os
import threading
import time
from typing import Generator, Optional

import requests

# SSE 结果文件目录
SSE_RESULTS_DIR = os.path.join(
    os.path.expanduser("~"), ".openclaw", "skills", "alta_lex_legal", ".sse_results"
)


class SSEEvent:
    """表示一个 SSE 数据事件。"""

    def __init__(self, message: str, is_finished: bool, raw: dict):
        self.message = message
        self.is_finished = is_finished
        self.raw = raw

    def __repr__(self):
        return f"SSEEvent(message={self.message!r}, is_finished={self.is_finished})"


def parse_sse_stream(resp: requests.Response) -> Generator[SSEEvent, None, None]:
    """
    解析 SSE 流。

    Alta Lex SSE 格式:
        `: init`          — 初始化信号 (忽略)
        `: heartbeat N`   — 心跳保活 (忽略)
        `data: {"message": "...", "is_finished": false}` — 数据事件
    """
    buffer = ""
    for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
        if not chunk:
            continue
        buffer += chunk
        while "\n\n" in buffer:
            event_text, buffer = buffer.split("\n\n", 1)
            for line in event_text.split("\n"):
                line = line.strip()
                if not line or line.startswith(":"):
                    continue
                if line.startswith("data:"):
                    payload = line[len("data:"):].strip()
                    if not payload or payload == "[DONE]":
                        continue
                    try:
                        obj = json.loads(payload)
                        yield SSEEvent(
                            message=obj.get("message", ""),
                            is_finished=obj.get("is_finished", False),
                            raw=obj,
                        )
                    except json.JSONDecodeError:
                        yield SSEEvent(message=payload, is_finished=False, raw={})
    # 处理缓冲区剩余数据
    if buffer.strip():
        for line in buffer.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith(":"):
                continue
            if line.startswith("data:"):
                payload = line[len("data:"):].strip()
                if not payload or payload == "[DONE]":
                    continue
                try:
                    obj = json.loads(payload)
                    yield SSEEvent(
                        message=obj.get("message", ""),
                        is_finished=obj.get("is_finished", False),
                        raw=obj,
                    )
                except json.JSONDecodeError:
                    yield SSEEvent(message=payload, is_finished=False, raw={})


def collect_sse_content(resp: requests.Response, timeout: int = 300) -> str:
    """
    消费 SSE 流并返回拼接后的完整内容。

    Args:
        resp: SSE 响应对象 (stream=True)
        timeout: 最大等待秒数 (默认 300 秒 / 5 分钟)。
                 超时后返回已收集到的内容（可能为空）。
    """
    parts = []
    start_time = time.monotonic()
    for event in parse_sse_stream(resp):
        parts.append(event.message)
        if event.is_finished:
            break
        if time.monotonic() - start_time > timeout:
            break
    return "".join(parts)


def _sse_result_path(session_id: str) -> str:
    """返回 SSE 结果文件路径。"""
    return os.path.join(SSE_RESULTS_DIR, f"{session_id}.json")


def write_sse_result(session_id: str, status: str, content: str = "",
                     error: str = ""):
    """写入 SSE 结果到本地文件。"""
    os.makedirs(SSE_RESULTS_DIR, exist_ok=True)
    data = {"status": status, "content": content, "error": error}
    path = _sse_result_path(session_id)
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False)


def read_sse_result(session_id: str) -> Optional[dict]:
    """
    读取本地 SSE 结果文件。

    Returns:
        {"status": "running|complete|error", "content": "...", "error": "..."}
        或 None (文件不存在)
    """
    path = _sse_result_path(session_id)
    try:
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def consume_sse_background(
    session: requests.Session,
    url: str,
    method: str = "GET",
    json_data: Optional[dict] = None,
    params: Optional[dict] = None,
    session_id: str = "",
):
    """
    在后台线程中消费 SSE 流，捕获内容并写入本地结果文件。

    Args:
        session: requests.Session 实例 (已含认证信息)
        url: 完整的 SSE 端点 URL
        method: HTTP 方法 (GET 或 POST)
        json_data: POST 请求体
        params: GET 查询参数
        session_id: 会话 ID，用于标识结果文件
    """
    if session_id:
        write_sse_result(session_id, "running")

    def _consume():
        parts = []
        try:
            if method.upper() == "POST":
                resp = session.post(
                    url, json=json_data or {}, stream=True, timeout=(10, 600),
                    headers={**session.headers, "Accept": "text/event-stream"},
                )
            else:
                resp = session.get(
                    url, params=params, stream=True, timeout=(10, 600),
                    headers={**session.headers, "Accept": "text/event-stream"},
                )
            resp.raise_for_status()
            for event in parse_sse_stream(resp):
                parts.append(event.message)
                if event.is_finished:
                    break
            content = "".join(parts)
            if session_id:
                if content:
                    write_sse_result(session_id, "complete", content)
                else:
                    write_sse_result(session_id, "running")
        except Exception as e:
            if session_id:
                content = "".join(parts)
                if content:
                    write_sse_result(session_id, "complete", content)
                else:
                    write_sse_result(session_id, "error", error=str(e))

    t = threading.Thread(target=_consume, daemon=False)
    t.start()
