"""
SSE (Server-Sent Events) 流解析器
=================================
解析 Alta Lex API 的 SSE 流式响应。
"""

import json
import threading
from typing import Generator, Optional

import requests


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


def collect_sse_content(resp: requests.Response) -> str:
    """消费 SSE 流并返回拼接后的完整内容。"""
    parts = []
    for event in parse_sse_stream(resp):
        parts.append(event.message)
        if event.is_finished:
            break
    return "".join(parts)


def consume_sse_background(
    session: requests.Session,
    url: str,
    method: str = "GET",
    json_data: Optional[dict] = None,
    params: Optional[dict] = None,
):
    """
    在后台线程中消费 SSE 流，保持连接以确保服务端持续生成。

    Args:
        session: requests.Session 实例 (已含认证信息)
        url: 完整的 SSE 端点 URL
        method: HTTP 方法 (GET 或 POST)
        json_data: POST 请求体
        params: GET 查询参数
    """
    def _consume():
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
            for _ in resp.iter_content(chunk_size=4096):
                pass
        except Exception:
            pass

    t = threading.Thread(target=_consume, daemon=True)
    t.start()
