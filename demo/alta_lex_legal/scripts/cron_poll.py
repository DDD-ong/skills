#!/usr/bin/env python3
"""
Alta Lex Legal AI — Background Polling Script
===============================================
独立轮询脚本，检查异步任务状态。

支持两种模式:
  1. 单次轮询 (one-shot): 检查一次，输出 JSON，退出
  2. 循环轮询 (background 模式): 按间隔重复检查，直到完成或超时

覆盖全部 11 个模块: draft, compare, research, ipo, negotiation, translation,
                    review, duediligence, compliance, desensitize, tabular

用法:
    # 单次轮询
    python3 cron_poll.py -u USER -p PASS research --session-id SID

    # 循环轮询 (推荐以 background:true 运行)
    python3 cron_poll.py -u USER -p PASS research --session-id SID \\
        --loop --interval 30 --max-attempts 30
"""

import argparse
import importlib
import os
import sys
import time

# 确保 scripts/ 目录在 Python 路径中
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from core.client import (
    AltaLexError,
    APIError,
    AuthenticationError,
    BaseClient,
    SessionExpiredError,
)
from core.task_store import update_task_status, remove_completed_tasks
from utils.output import error_exit, json_output

# ── 常量 ─────────────────────────────────────────────────

MODULE_REGISTRY = {
    "draft":         ("modules.contract_draft",    "ContractDraftModule"),
    "compare":       ("modules.contract_compare",  "ContractCompareModule"),
    "research":      ("modules.legal_research",    "LegalResearchModule"),
    "ipo":           ("modules.ipo_support",        "IPOSupportModule"),
    "negotiation":   ("modules.negotiation",        "NegotiationModule"),
    "translation":   ("modules.translation",        "TranslationModule"),
    "review":        ("modules.contract_review",    "ContractReviewModule"),
    "duediligence":  ("modules.due_diligence",      "DueDiligenceModule"),
    "compliance":    ("modules.compliance",          "ComplianceModule"),
    "desensitize":   ("modules.desensitization",     "DesensitizationModule"),
    "tabular":       ("modules.tabular",             "TabularModule"),
}

DEFAULT_INTERVALS = {
    "draft": 30,
    "compare": 30,
    "research": 30,
    "ipo": 30,
    "negotiation": 30,
    "translation": 30,
    "review": 30,
    "duediligence": 60,
    "compliance": 90,
    "desensitize": 20,
    "tabular": 60,
}


# ── 错误分类 ──────────────────────────────────────────────

def _is_retryable(exc: Exception) -> bool:
    """判断异常是否为可重试的瞬态错误。"""
    import requests.exceptions

    # 网络层瞬态错误
    if isinstance(exc, (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.ChunkedEncodingError,
    )):
        return True

    # 系统错误 B00001 可重试
    if isinstance(exc, APIError) and "B00001" in str(exc):
        return True

    # 认证/会话错误不可重试 (_get_with_retry 已尝试过 auto-relogin)
    if isinstance(exc, (AuthenticationError, SessionExpiredError)):
        return False

    # 信用不足 A04006 不可重试
    if isinstance(exc, APIError) and "A04006" in str(exc):
        return False

    # OSError 中的网络相关错误可重试
    if isinstance(exc, OSError) and getattr(exc, "errno", None) in (
        61,   # ECONNREFUSED
        54,   # ECONNRESET
        60,   # ETIMEDOUT
        51,   # ENETUNREACH
    ):
        return True

    return False


# ── 重试包装器 ────────────────────────────────────────────

def retry_poll(fn, max_retries: int = 2, delay: float = 3.0) -> dict:
    """
    带重试的轮询调用。

    仅对瞬态网络错误重试，永久错误（认证失败、信用不足等）立即抛出。

    Args:
        fn: 无参调用，返回 check() 结果 dict
        max_retries: 最大重试次数
        delay: 重试间隔（秒）

    Returns:
        module.check() 返回的结果 dict
    """
    last_exc = None
    for attempt in range(1 + max_retries):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if not _is_retryable(exc):
                raise
            if attempt < max_retries:
                time.sleep(delay)
    # 重试耗尽
    raise last_exc


# ── 模块加载 ──────────────────────────────────────────────

def _get_module(module_name: str, client: BaseClient):
    """根据模块名懒加载并实例化模块类。"""
    if module_name not in MODULE_REGISTRY:
        supported = ", ".join(sorted(MODULE_REGISTRY.keys()))
        error_exit("poll", f"Unknown module: {module_name}. Supported: {supported}")

    module_path, class_name = MODULE_REGISTRY[module_name]
    mod = importlib.import_module(module_path)
    cls = getattr(mod, class_name)
    return cls(client)


# ── 认证 ──────────────────────────────────────────────────

def _create_client(args) -> BaseClient:
    """
    创建并认证客户端。

    认证优先级:
    1. --auth-session-id / ALTA_LEX_SESSION_ID  → 直接使用
    2. -u/-p / ALTA_LEX_USERNAME+PASSWORD        → 智能认证（缓存优先）
    """
    client = BaseClient(base_url=args.base_url)

    # 优先级 1: 直接传入 Session ID
    auth_sid = args.auth_session_id or os.environ.get("ALTA_LEX_SESSION_ID")
    if auth_sid:
        client.set_auth(auth_sid)
        return client

    # 优先级 2: 用户名密码
    username = args.username or os.environ.get("ALTA_LEX_USERNAME")
    password = args.password or os.environ.get("ALTA_LEX_PASSWORD")
    if username and password:
        try:
            client.authenticate(username, password)
            return client
        except AltaLexError as e:
            error_exit("auth", f"Authentication failed: {e}")
    else:
        error_exit("auth", "Missing credentials: use -u/-p, --auth-session-id, or env vars")

    return client  # unreachable


# ── check 参数分发 ─────────────────────────────────────────

def _build_check_kwargs(module_name: str, session_id: str,
                        chat_id: str, filename: str) -> dict:
    """根据模块类型构建 check() 调用参数。"""
    if module_name == "review":
        return {"filename": filename}
    elif module_name in ("compliance", "duediligence", "tabular"):
        return {"session_id": session_id, "chat_id": chat_id}
    else:
        return {"session_id": session_id}


# ── 单次轮询 ──────────────────────────────────────────────

def single_poll(module, module_name: str, check_kwargs: dict,
                max_retries: int, delay: float) -> dict:
    """执行单次轮询并返回结果。"""
    result = retry_poll(
        lambda: module.check(**check_kwargs),
        max_retries=max_retries,
        delay=delay,
    )
    try:
        update_task_status(
            session_id=result.get("session_id", ""),
            status=result.get("status", ""),
        )
    except Exception:
        pass
    return result


# ── 循环轮询 ──────────────────────────────────────────────

def loop_poll(module, module_name: str, check_kwargs: dict,
              interval: int, max_attempts: int,
              max_retries: int, delay: float):
    """循环轮询直到完成、出错或超时。"""
    sid = check_kwargs.get("session_id", check_kwargs.get("filename", ""))
    for attempt in range(1, max_attempts + 1):
        try:
            result = retry_poll(
                lambda: module.check(**check_kwargs),
                max_retries=max_retries,
                delay=delay,
            )
        except AltaLexError as e:
            json_output(
                status="error", module=module_name,
                session_id=sid, error=str(e),
            )
            sys.exit(1)
        except Exception as e:
            json_output(
                status="error", module=module_name,
                session_id=sid, error=f"Unexpected error: {e}",
            )
            sys.exit(1)

        status = result.get("status", "running")

        try:
            update_task_status(
                session_id=result.get("session_id", ""),
                status=status,
            )
        except Exception:
            pass

        json_output(
            status=status, module=module_name,
            session_id=sid,
            content=result.get("content", ""),
            error=result.get("error", ""),
            progress=result.get("progress"),
            extra=result.get("extra"),
        )

        if status == "complete":
            sys.exit(0)
        if status == "error":
            sys.exit(1)

        if attempt < max_attempts:
            time.sleep(interval)

    # 超时
    total_time = interval * max_attempts
    json_output(
        status="error", module=module_name,
        session_id=sid,
        error=f"Polling timeout: {max_attempts} attempts over ~{total_time}s",
    )
    sys.exit(1)


# ── 参数解析 ──────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Alta Lex Legal AI — Cron Polling Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # 认证参数
    auth = parser.add_argument_group("authentication")
    auth.add_argument("-u", "--username", help="Alta Lex username")
    auth.add_argument("-p", "--password", help="Alta Lex password")
    auth.add_argument(
        "--auth-session-id",
        help="Direct auth session ID (skips login)",
    )
    auth.add_argument(
        "--base-url",
        default=os.environ.get("ALTA_LEX_BASE_URL"),
        help="API base URL (default: env ALTA_LEX_BASE_URL)",
    )

    # 模块与任务
    parser.add_argument(
        "module",
        choices=sorted(MODULE_REGISTRY.keys()),
        help="Module to poll",
    )
    parser.add_argument(
        "--session-id",
        help="Task session ID to poll (required for most modules)",
    )
    parser.add_argument(
        "--chat-id",
        help="Chat ID (required for compliance/duediligence/tabular)",
    )
    parser.add_argument(
        "--filename",
        help="Filename to poll (required for review module)",
    )

    # 循环模式
    loop_group = parser.add_argument_group("loop mode")
    loop_group.add_argument(
        "--loop", action="store_true",
        help="Enable loop polling mode (background:true)",
    )
    loop_group.add_argument(
        "--interval", type=int, default=None,
        help="Poll interval in seconds (default: per-module)",
    )
    loop_group.add_argument(
        "--max-attempts", type=int, default=30,
        help="Max poll attempts in loop mode (default: 30)",
    )

    # 重试配置
    retry = parser.add_argument_group("retry")
    retry.add_argument(
        "--retries", type=int, default=2,
        help="Max retries per poll on transient errors (default: 2)",
    )
    retry.add_argument(
        "--retry-delay", type=float, default=3.0,
        help="Delay between retries in seconds (default: 3.0)",
    )

    return parser


# ── 入口 ──────────────────────────────────────────────────

def main():
    # 启动时清理过期任务
    try:
        remove_completed_tasks()
    except Exception:
        pass

    parser = build_parser()
    args = parser.parse_args()

    module_name = args.module

    # ── 输入验证 ──
    if module_name == "review":
        if not args.filename:
            parser.error("review module requires --filename")
    elif module_name in ("compliance", "duediligence", "tabular"):
        if not args.session_id:
            parser.error(f"{module_name} module requires --session-id")
        if not args.chat_id:
            parser.error(f"{module_name} module requires --chat-id")
    else:
        if not args.session_id:
            parser.error(f"{module_name} module requires --session-id")

    check_kwargs = _build_check_kwargs(
        module_name, args.session_id or "",
        args.chat_id or "", args.filename or "",
    )

    try:
        client = _create_client(args)
        module = _get_module(module_name, client)

        if args.loop:
            interval = args.interval or DEFAULT_INTERVALS.get(module_name, 30)
            loop_poll(
                module, module_name, check_kwargs,
                interval=interval,
                max_attempts=args.max_attempts,
                max_retries=args.retries,
                delay=args.retry_delay,
            )
        else:
            result = single_poll(
                module, module_name, check_kwargs,
                max_retries=args.retries,
                delay=args.retry_delay,
            )
            sid = check_kwargs.get("session_id", check_kwargs.get("filename", ""))
            status = result.get("status", "running")
            json_output(
                status=status, module=module_name,
                session_id=sid,
                content=result.get("content", ""),
                error=result.get("error", ""),
                progress=result.get("progress"),
                extra=result.get("extra"),
            )
            sys.exit(1 if status == "error" else 0)

    except AltaLexError as e:
        error_exit(module_name, str(e))
    except Exception as e:
        error_exit(module_name, f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
