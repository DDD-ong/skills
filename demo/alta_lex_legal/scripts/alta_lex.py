#!/usr/bin/env python3
"""
Alta Lex Legal AI - CLI 入口
============================
统一子命令路由，覆盖全部 11 个功能模块。
所有 start/check 命令输出单行 JSON，供 OpenClaw cron 解析。

用法:
    python3 alta_lex.py [认证参数] <模块> <动作> [模块参数]

示例:
    python3 alta_lex.py -u USER -p PASS draft start --industry Technology ...
    python3 alta_lex.py -u USER -p PASS draft check --session-id sess_xxx
"""

import argparse
import importlib
import json
import os
import sys

# 确保 scripts/ 目录在 Python 路径中
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from core.client import BaseClient, AltaLexError, SessionExpiredError
from core.task_store import save_task, update_task_status, remove_completed_tasks, load_tasks
from utils.output import json_output, error_exit


def _get_query_from_args(args) -> str:
    """根据模块和参数提取用户查询内容（用于任务持久化）。"""
    action = getattr(args, "action", "")
    if action != "start":
        return ""
    if hasattr(args, "query") and args.query:
        return args.query
    if hasattr(args, "title") and args.title:
        return args.title
    if hasattr(args, "request") and args.request:
        return args.request
    return ""


def create_client(args) -> BaseClient:
    """
    根据命令行参数创建并认证客户端。

    认证优先级:
    1. --session-id / ALTA_LEX_SESSION_ID  → 直接使用，不调 login
    2. -u/-p / ALTA_LEX_USERNAME+PASSWORD  → 智能认证 (缓存优先，失效才 login)
    """
    client = BaseClient(base_url=args.base_url)

    # 优先级 1: 直接传入 Session ID
    session_id = args.session_id or os.environ.get("ALTA_LEX_SESSION_ID")
    if session_id:
        client.set_auth(session_id)
        try:
            client._save_session_cache(session_id)
        except Exception:
            pass
        return client

    # 优先级 2: 用户名密码 → 智能认证 (缓存优先)
    username = args.username or os.environ.get("ALTA_LEX_USERNAME")
    password = args.password or os.environ.get("ALTA_LEX_PASSWORD")
    if username and password:
        try:
            client.authenticate(username, password)
            return client
        except AltaLexError as e:
            error_exit("auth", f"Authentication failed: {e}")
    else:
        error_exit("auth", "Missing credentials: use -u/-p, --session-id, or env vars")

    return client  # unreachable


# ── 子命令处理函数 ──────────────────────────────────────


def handle_draft(args, client):
    from modules.contract_draft import ContractDraftModule
    mod = ContractDraftModule(client)

    if args.action == "start":
        result = mod.start(
            industry=args.industry,
            position=args.position,
            scenario=args.scenario,
            contract_type=args.contract_type,
            governing_law=args.governing_law,
            language=args.language or "Chinese",
            template_url=args.template_url or "",
            customer_request=args.request or "",
            sync_sse=getattr(args, "wait", False),
        )
        return result
    elif args.action == "check":
        result = mod.check(session_id=args.sid)
        return result


def handle_review(args, client):
    from modules.contract_review import ContractReviewModule
    mod = ContractReviewModule(client)

    if args.action == "start":
        result = mod.start(
            file_url=args.file_url,
            review_type=args.review_type,
            industry=args.industry,
            position=args.position,
            scenario=args.scenario,
            contract_type=args.contract_type,
            governing_law=args.governing_law or "",
            language=args.language or "",
            customer_request=args.request or "",
        )
        return result
    elif args.action == "check":
        result = mod.check(filename=args.filename)
        return result


def handle_compare(args, client):
    from modules.contract_compare import ContractCompareModule
    mod = ContractCompareModule(client)

    if args.action == "start":
        result = mod.start(
            original_url=args.original_url,
            revised_url=args.revised_url,
            industry=args.industry or "",
            position=args.position or "",
            contract_type=args.contract_type or "",
            language=args.language or "Chinese",
            governing_law=args.governing_law or "",
            title=args.title or "",
            customer_request=args.request or "",
            sync_sse=getattr(args, "wait", False),
        )
        return result
    elif args.action == "check":
        result = mod.check(session_id=args.sid)
        return result


def handle_research(args, client):
    from modules.legal_research import LegalResearchModule
    mod = LegalResearchModule(client)

    if args.action == "start":
        file_urls = args.file_urls.split(",") if args.file_urls else None
        result = mod.start(
            query=args.query,
            research_type=args.research_type or "search",
            file_urls=file_urls,
            sync_sse=getattr(args, "wait", False),
        )
        return result
    elif args.action == "check":
        result = mod.check(session_id=args.sid)
        return result
    elif args.action == "followup":
        file_urls = args.file_urls.split(",") if args.file_urls else None
        result = mod.followup(
            session_id=args.sid,
            query=args.query,
            research_type=args.research_type or "search",
            file_urls=file_urls,
            sync_sse=getattr(args, "wait", False),
        )
        return result


def handle_ipo(args, client):
    from modules.ipo_support import IPOSupportModule
    mod = IPOSupportModule(client)

    if args.action == "start":
        result = mod.start(
            title=args.title or "",
            connected_person=args.connected_person or "",
            connect_transact_class=args.transact_class or "",
            transaction_classification=args.transaction_class or "",
            involves_guarantees=args.involves_guarantees,
            shareholder_approval=args.shareholder_approval,
            circular_requirements=args.circular_requirements,
            other_relevant_facts=args.other_facts or "",
            file_url=args.file_url or "",
            sync_sse=getattr(args, "wait", False),
        )
        return result
    elif args.action == "check":
        result = mod.check(session_id=args.sid)
        return result


def handle_negotiation(args, client):
    from modules.negotiation import NegotiationModule
    mod = NegotiationModule(client)

    if args.action == "start":
        result = mod.start(
            industry=args.industry,
            position=args.position,
            scenario=args.scenario,
            contract_type=args.contract_type,
            language=args.language or "Chinese",
            title=args.title or "",
            customer_request=args.request or "",
            file_url=args.file_url or "",
            sync_sse=getattr(args, "wait", False),
        )
        return result
    elif args.action == "check":
        result = mod.check(session_id=args.sid)
        return result


def handle_translation(args, client):
    from modules.translation import TranslationModule
    mod = TranslationModule(client)

    if args.action == "start":
        result = mod.start(
            file_url=args.file_url,
            source_language=args.source_lang or "English",
            target_language=args.target_lang or "Chinese",
            contract_type=args.contract_type or "",
            governing_law=args.governing_law or "",
            sync_sse=getattr(args, "wait", False),
        )
        return result
    elif args.action == "check":
        result = mod.check(session_id=args.sid)
        return result
    elif args.action == "quick":
        result = mod.quick_translate(
            query=args.query,
            source_language=args.source_lang or "English",
            target_language=args.target_lang or "Chinese",
            contract_type=args.contract_type or "",
            governing_law=args.governing_law or "",
        )
        return result


def handle_duediligence(args, client):
    from modules.due_diligence import DueDiligenceModule
    mod = DueDiligenceModule(client)

    if args.action == "checklist":
        result = mod.generate_checklist(
            document_type=args.document_type,
            position=args.position,
            industry=args.industry,
            jurisdiction=args.jurisdiction or "PRC",
            language=args.language or "Chinese",
            customer_request=args.request or "",
        )
        return result
    elif args.action == "start":
        file_urls = args.file_urls.split(",") if args.file_urls else None
        result = mod.start(
            file_url=args.file_url or "",
            file_urls=file_urls,
            session_id=args.sid or "",
            checklist=args.checklist or "",
        )
        return result
    elif args.action == "check":
        result = mod.check(
            session_id=args.sid,
            chat_id=args.chat_id or "",
        )
        return result


def handle_compliance(args, client):
    from modules.compliance import ComplianceModule
    mod = ComplianceModule(client)

    if args.action == "start":
        file_urls = args.file_urls.split(",") if args.file_urls else []
        domains = args.domains.split(",") if args.domains else []
        priority_sources = args.priority_sources.split(",") if args.priority_sources else None
        business_regions = args.business_regions.split(",") if args.business_regions else None
        result = mod.start(
            file_urls=file_urls,
            jurisdiction=args.jurisdiction,
            domains=domains,
            title=args.title or "",
            output_language=args.output_language or "zh",
            priority_sources=priority_sources,
            entity_type=args.entity_type or "",
            regulated_status=args.regulated_status or "",
            data_scope=args.data_scope or "",
            business_regions=business_regions,
        )
        return result
    elif args.action == "check":
        result = mod.check(
            session_id=args.sid,
            chat_id=args.chat_id,
        )
        return result
    elif args.action == "export":
        result = mod.export_excel(session_id=args.sid)
        return result


def handle_desensitize(args, client):
    from modules.desensitization import DesensitizationModule
    mod = DesensitizationModule(client)

    if args.action == "start":
        entity_types = args.entity_types.split(",") if args.entity_types else None
        result = mod.start(
            file_url=args.file_url,
            title=args.title or "",
            entity_types=entity_types,
        )
        return result
    elif args.action == "check":
        result = mod.check(session_id=args.sid)
        return result


def handle_tabular(args, client):
    from modules.tabular import TabularModule
    mod = TabularModule(client)

    if args.action == "checklist":
        result = mod.generate_checklist(
            document_type=args.document_type,
            position=args.position,
            industry=args.industry,
            jurisdiction=args.jurisdiction or "PRC",
            language=args.language or "Chinese",
            customer_request=args.request or "",
        )
        return result
    elif args.action == "start":
        file_urls = args.file_urls.split(",") if args.file_urls else []
        checklist = None
        if args.checklist:
            try:
                checklist = json.loads(args.checklist)
            except json.JSONDecodeError:
                error_exit("tabular", "Invalid checklist JSON")
        result = mod.start(
            file_urls=file_urls,
            document_type=args.document_type or "",
            position=args.position or "",
            industry=args.industry or "",
            jurisdiction=args.jurisdiction or "PRC",
            language=args.language or "Chinese",
            title=args.title or "",
            customer_request=args.request or "",
            checklist=checklist,
        )
        return result
    elif args.action == "check":
        result = mod.check(
            session_id=args.sid,
            chat_id=args.chat_id,
        )
        return result


def handle_tasks(args, client):
    """任务管理子命令：列出活跃任务。"""
    if args.action == "list":
        tasks = load_tasks()
        print(json.dumps({"tasks": tasks}, ensure_ascii=False))
    return None


# ── argparse 构建 ─────────────────────────────────────


def build_parser():
    parser = argparse.ArgumentParser(
        description="Alta Lex Legal AI - Unified CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # 全局认证参数
    parser.add_argument("-u", "--username", default=None)
    parser.add_argument("-p", "--password", default=None)
    parser.add_argument("--session-id", default=None, dest="session_id")
    parser.add_argument("--base-url", default=None)

    # --wait 模式 (start + 自动轮询)
    wait_group = parser.add_argument_group("wait mode")
    wait_group.add_argument(
        "--wait", action="store_true",
        help="After start, automatically poll until complete/error/timeout",
    )
    wait_group.add_argument(
        "--wait-interval", type=int, default=None,
        help="Poll interval in seconds (default: per-module)",
    )
    wait_group.add_argument(
        "--wait-max-attempts", type=int, default=30,
        help="Max poll attempts in wait mode (default: 30)",
    )

    subparsers = parser.add_subparsers(dest="module", help="功能模块")

    # ── 公共参数函数 ──
    def add_common_params(p):
        p.add_argument("--industry", default="")
        p.add_argument("--position", default="")
        p.add_argument("--scenario", default="")
        p.add_argument("--contract-type", default="", dest="contract_type")
        p.add_argument("--governing-law", default="", dest="governing_law")
        p.add_argument("--language", default="")
        p.add_argument("--request", default="", help="自定义需求描述")

    def add_check_params(p):
        p.add_argument("--session-id", required=True, dest="sid")
        p.add_argument("--chat-id", default="", dest="chat_id")

    # ── draft ──
    draft = subparsers.add_parser("draft", help="合同起草")
    draft_sub = draft.add_subparsers(dest="action")

    draft_start = draft_sub.add_parser("start")
    add_common_params(draft_start)
    draft_start.add_argument("--template-url", default="", dest="template_url")

    draft_check = draft_sub.add_parser("check")
    draft_check.add_argument("--session-id", required=True, dest="sid")

    # ── review ──
    review = subparsers.add_parser("review", help="合同审查")
    review_sub = review.add_subparsers(dest="action")

    review_start = review_sub.add_parser("start")
    add_common_params(review_start)
    review_start.add_argument("--file-url", required=True, dest="file_url")
    review_start.add_argument("--review-type", required=True, dest="review_type",
                              help="1=Summary, 2=Edit")

    review_check = review_sub.add_parser("check")
    review_check.add_argument("--filename", required=True)

    # ── compare ──
    compare = subparsers.add_parser("compare", help="合同比对")
    compare_sub = compare.add_subparsers(dest="action")

    compare_start = compare_sub.add_parser("start")
    add_common_params(compare_start)
    compare_start.add_argument("--original-url", required=True, dest="original_url")
    compare_start.add_argument("--revised-url", required=True, dest="revised_url")
    compare_start.add_argument("--title", default="")

    compare_check = compare_sub.add_parser("check")
    compare_check.add_argument("--session-id", required=True, dest="sid")

    # ── research ──
    research = subparsers.add_parser("research", help="法律研究")
    research_sub = research.add_subparsers(dest="action")

    research_start = research_sub.add_parser("start")
    research_start.add_argument("-q", "--query", required=True)
    research_start.add_argument("--research-type", default="search", dest="research_type")
    research_start.add_argument("--file-urls", default="", dest="file_urls")

    research_check = research_sub.add_parser("check")
    research_check.add_argument("--session-id", required=True, dest="sid")

    research_followup = research_sub.add_parser("followup")
    research_followup.add_argument("--session-id", required=True, dest="sid")
    research_followup.add_argument("-q", "--query", required=True)
    research_followup.add_argument("--research-type", default="search", dest="research_type")
    research_followup.add_argument("--file-urls", default="", dest="file_urls")

    # ── ipo ──
    ipo = subparsers.add_parser("ipo", help="IPO 支持")
    ipo_sub = ipo.add_subparsers(dest="action")

    ipo_start = ipo_sub.add_parser("start")
    ipo_start.add_argument("--title", default="")
    ipo_start.add_argument("--connected-person", default="", dest="connected_person")
    ipo_start.add_argument("--transact-class", default="", dest="transact_class")
    ipo_start.add_argument("--transaction-class", default="", dest="transaction_class")
    ipo_start.add_argument("--involves-guarantees", action="store_true", dest="involves_guarantees")
    ipo_start.add_argument("--shareholder-approval", action="store_true", dest="shareholder_approval")
    ipo_start.add_argument("--circular-requirements", action="store_true", dest="circular_requirements")
    ipo_start.add_argument("--other-facts", default="", dest="other_facts")
    ipo_start.add_argument("--file-url", default="", dest="file_url")

    ipo_check = ipo_sub.add_parser("check")
    ipo_check.add_argument("--session-id", required=True, dest="sid")

    # ── negotiation ──
    neg = subparsers.add_parser("negotiation", help="谈判策略")
    neg_sub = neg.add_subparsers(dest="action")

    neg_start = neg_sub.add_parser("start")
    add_common_params(neg_start)
    neg_start.add_argument("--title", default="")
    neg_start.add_argument("--file-url", default="", dest="file_url")

    neg_check = neg_sub.add_parser("check")
    neg_check.add_argument("--session-id", required=True, dest="sid")

    # ── translation ──
    trans = subparsers.add_parser("translation", help="文档翻译")
    trans_sub = trans.add_subparsers(dest="action")

    trans_start = trans_sub.add_parser("start")
    trans_start.add_argument("--file-url", required=True, dest="file_url")
    trans_start.add_argument("--source-lang", default="English", dest="source_lang")
    trans_start.add_argument("--target-lang", default="Chinese", dest="target_lang")
    trans_start.add_argument("--contract-type", default="", dest="contract_type")
    trans_start.add_argument("--governing-law", default="", dest="governing_law")

    trans_check = trans_sub.add_parser("check")
    trans_check.add_argument("--session-id", required=True, dest="sid")

    trans_quick = trans_sub.add_parser("quick")
    trans_quick.add_argument("-q", "--query", required=True)
    trans_quick.add_argument("--source-lang", default="English", dest="source_lang")
    trans_quick.add_argument("--target-lang", default="Chinese", dest="target_lang")
    trans_quick.add_argument("--contract-type", default="", dest="contract_type")
    trans_quick.add_argument("--governing-law", default="", dest="governing_law")

    # ── duediligence ──
    dd = subparsers.add_parser("duediligence", help="尽职调查")
    dd_sub = dd.add_subparsers(dest="action")

    dd_cl = dd_sub.add_parser("checklist")
    dd_cl.add_argument("--document-type", required=True, dest="document_type")
    dd_cl.add_argument("--position", required=True)
    dd_cl.add_argument("--industry", required=True)
    dd_cl.add_argument("--jurisdiction", default="PRC")
    dd_cl.add_argument("--language", default="Chinese")
    dd_cl.add_argument("--request", default="")

    dd_start = dd_sub.add_parser("start")
    dd_start.add_argument("--file-url", default="", dest="file_url")
    dd_start.add_argument("--file-urls", default="", dest="file_urls")
    dd_start.add_argument("--session-id", default="", dest="sid")
    dd_start.add_argument("--checklist", default="")

    dd_check = dd_sub.add_parser("check")
    dd_check.add_argument("--session-id", required=True, dest="sid")
    dd_check.add_argument("--chat-id", default="", dest="chat_id")

    # ── compliance ──
    comp = subparsers.add_parser("compliance", help="合规审查")
    comp_sub = comp.add_subparsers(dest="action")

    comp_start = comp_sub.add_parser("start")
    comp_start.add_argument("--file-urls", required=True, dest="file_urls")
    comp_start.add_argument("--jurisdiction", required=True)
    comp_start.add_argument("--domains", required=True)
    comp_start.add_argument("--title", default="")
    comp_start.add_argument("--output-language", default="zh", dest="output_language")
    comp_start.add_argument("--priority-sources", default="", dest="priority_sources")
    comp_start.add_argument("--entity-type", default="", dest="entity_type")
    comp_start.add_argument("--regulated-status", default="", dest="regulated_status")
    comp_start.add_argument("--data-scope", default="", dest="data_scope")
    comp_start.add_argument("--business-regions", default="", dest="business_regions")

    comp_check = comp_sub.add_parser("check")
    comp_check.add_argument("--session-id", required=True, dest="sid")
    comp_check.add_argument("--chat-id", required=True, dest="chat_id")

    comp_export = comp_sub.add_parser("export")
    comp_export.add_argument("--session-id", required=True, dest="sid")

    # ── desensitize ──
    desen = subparsers.add_parser("desensitize", help="脱敏处理")
    desen_sub = desen.add_subparsers(dest="action")

    desen_start = desen_sub.add_parser("start")
    desen_start.add_argument("--file-url", required=True, dest="file_url")
    desen_start.add_argument("--title", default="")
    desen_start.add_argument("--entity-types", default="", dest="entity_types",
                             help="逗号分隔: PERSON,ORGANIZATION,EMAIL,PHONE,ID_NUMBER,ADDRESS,BANK_CARD,DATE")

    desen_check = desen_sub.add_parser("check")
    desen_check.add_argument("--session-id", required=True, dest="sid")

    # ── tabular ──
    tab = subparsers.add_parser("tabular", help="表格处理")
    tab_sub = tab.add_subparsers(dest="action")

    tab_cl = tab_sub.add_parser("checklist")
    tab_cl.add_argument("--document-type", required=True, dest="document_type")
    tab_cl.add_argument("--position", required=True)
    tab_cl.add_argument("--industry", required=True)
    tab_cl.add_argument("--jurisdiction", default="PRC")
    tab_cl.add_argument("--language", default="Chinese")
    tab_cl.add_argument("--request", default="")

    tab_start = tab_sub.add_parser("start")
    tab_start.add_argument("--file-urls", required=True, dest="file_urls")
    tab_start.add_argument("--document-type", default="", dest="document_type")
    tab_start.add_argument("--position", default="")
    tab_start.add_argument("--industry", default="")
    tab_start.add_argument("--jurisdiction", default="PRC")
    tab_start.add_argument("--language", default="Chinese")
    tab_start.add_argument("--title", default="")
    tab_start.add_argument("--request", default="")
    tab_start.add_argument("--checklist", default="", help="JSON 格式检查清单")

    tab_check = tab_sub.add_parser("check")
    tab_check.add_argument("--session-id", required=True, dest="sid")
    tab_check.add_argument("--chat-id", required=True, dest="chat_id")

    # ── tasks ──
    tasks_parser = subparsers.add_parser("tasks", help="任务管理")
    tasks_sub = tasks_parser.add_subparsers(dest="action")
    tasks_list = tasks_sub.add_parser("list", help="列出活跃任务")

    return parser


# ── 路由表 ────────────────────────────────────────────

HANDLERS = {
    "draft": handle_draft,
    "review": handle_review,
    "compare": handle_compare,
    "research": handle_research,
    "ipo": handle_ipo,
    "negotiation": handle_negotiation,
    "translation": handle_translation,
    "duediligence": handle_duediligence,
    "compliance": handle_compliance,
    "desensitize": handle_desensitize,
    "tabular": handle_tabular,
    "tasks": handle_tasks,
}


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.module:
        parser.print_help()
        sys.exit(1)

    if not getattr(args, "action", None):
        parser.parse_args([args.module, "-h"])
        sys.exit(1)

    handler = HANDLERS.get(args.module)
    if not handler:
        error_exit(args.module, f"Unknown module: {args.module}")

    try:
        # tasks 模块为本地任务管理，不需要认证
        if args.module == "tasks":
            result = handler(args, None)
            if result:
                json_output(**result)
            return

        client = create_client(args)
        result = handler(args, client)

        # task_store 持久化
        action = getattr(args, "action", "")
        if action == "start" and result:
            try:
                save_task(
                    module=result.get("module", ""),
                    session_id=result.get("session_id", ""),
                    chat_id=result.get("chat_id", ""),
                    status=result.get("status", "started"),
                    query=_get_query_from_args(args),
                )
            except Exception:
                pass
        elif action == "check" and result:
            try:
                status = result.get("status", "")
                if status in ("complete", "error"):
                    update_task_status(
                        session_id=result.get("session_id", ""),
                        status=status,
                    )
            except Exception:
                pass

        # 集中输出
        if result:
            json_output(**result)

        # --wait: start 后自动轮询直到完成
        if (
            getattr(args, "wait", False)
            and getattr(args, "action", "") == "start"
            and result
            and result.get("status") == "started"
        ):
            from cron_poll import (
                DEFAULT_INTERVALS,
                MODULE_REGISTRY,
                _build_check_kwargs,
                loop_poll,
            )

            module_name = args.module
            session_id = result.get("session_id", "")
            chat_id = result.get("chat_id", "")
            extra = result.get("extra") or {}
            filename = extra.get("filename", "")

            # 加载模块实例 (复用已认证 client)
            mod_path, cls_name = MODULE_REGISTRY[module_name]
            mod = importlib.import_module(mod_path)
            poll_module = getattr(mod, cls_name)(client)

            check_kwargs = _build_check_kwargs(
                module_name, session_id, chat_id, filename
            )
            interval = (
                args.wait_interval
                or DEFAULT_INTERVALS.get(module_name, 30)
            )

            loop_poll(
                poll_module, module_name, check_kwargs,
                interval=interval,
                max_attempts=args.wait_max_attempts,
                max_retries=2,
                delay=3.0,
            )

    except AltaLexError as e:
        error_exit(args.module or "unknown", str(e))
    except Exception as e:
        error_exit(args.module or "unknown", f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
