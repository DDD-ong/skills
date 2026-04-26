"""
任务状态持久化存储
====================
管理 alta_lex_legal 技能的活跃任务状态，支持增删改查与自动清理。

存储路径: 动态获取 agent 的 workspace 目录，在其下创建 alta_lex_legal 子目录。
    优先级: 1) OPENCLAW_WORKSPACE 环境变量  2) 脚本位置推算（开发/测试环境兜底）
"""

import fcntl
import json
import os
import tempfile
import time
from typing import Optional

def _get_workspace_dir() -> str:
    """动态获取临时文件存储目录。优先级：
    1. OPENCLAW_WORKSPACE 环境变量（agent 的 workspace 路径）→ 在其下创建 alta_lex_legal 子目录
    2. 脚本位置推算（开发/测试环境兜底）
    """
    # 优先级1: agent workspace
    ws = os.environ.get("OPENCLAW_WORKSPACE", "")
    if ws and os.path.isdir(ws):
        skill_dir = os.path.join(ws, "alta_lex_legal")
        os.makedirs(skill_dir, exist_ok=True)
        return skill_dir
    # 优先级2: 脚本位置推算
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_active_tasks_file() -> str:
    return os.path.join(_get_workspace_dir(), ".active_tasks.json")


def _ensure_dir():
    """确保存储文件所在目录存在。"""
    cache_dir = os.path.dirname(_get_active_tasks_file())
    os.makedirs(cache_dir, exist_ok=True)


def _read_all_tasks() -> list:
    """读取任务列表（内部方法，不负责加锁）。"""
    try:
        if not os.path.exists(_get_active_tasks_file()):
            return []
        with open(_get_active_tasks_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("tasks"), list):
                return data["tasks"]
            return []
    except (OSError, ValueError):
        return []


def _write_all_tasks(tasks: list):
    """原子写入任务列表（内部方法，不负责加锁）。"""
    _ensure_dir()
    data = {"tasks": tasks}
    fd, tmp_path = tempfile.mkstemp(
        dir=os.path.dirname(_get_active_tasks_file()), suffix=".tmp"
    )
    os.close(fd)
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, _get_active_tasks_file())
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def load_tasks() -> list:
    """读取所有任务，文件不存在返回空列表。"""
    try:
        if not os.path.exists(_get_active_tasks_file()):
            return []
        with open(_get_active_tasks_file(), "r", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                data = json.load(f)
                if isinstance(data, dict) and isinstance(data.get("tasks"), list):
                    return data["tasks"]
                return []
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except (OSError, ValueError):
        return []


def save_task(module: str, session_id: str, chat_id: str = "", status: str = "started", query: str = "") -> None:
    """新增或更新任务（按 session_id 去重），如果 session_id 已存在则更新。"""
    try:
        _ensure_dir()
        with open(_get_active_tasks_file(), "a+", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.seek(0)
                try:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        data = {"tasks": []}
                except (ValueError, json.JSONDecodeError):
                    data = {"tasks": []}

                tasks = data.get("tasks", [])
                if not isinstance(tasks, list):
                    tasks = []

                now = time.time()
                existing = None
                for task in tasks:
                    if isinstance(task, dict) and task.get("session_id") == session_id:
                        existing = task
                        break

                if existing:
                    existing["module"] = module
                    existing["chat_id"] = chat_id
                    existing["status"] = status
                    existing["query"] = query
                    existing["updated_at"] = now
                else:
                    tasks.append({
                        "module": module,
                        "session_id": session_id,
                        "chat_id": chat_id,
                        "status": status,
                        "query": query,
                        "created_at": now,
                        "updated_at": now,
                    })

                data["tasks"] = tasks
                fd, tmp_path = tempfile.mkstemp(
                    dir=os.path.dirname(_get_active_tasks_file()), suffix=".tmp"
                )
                os.close(fd)
                try:
                    with open(tmp_path, "w", encoding="utf-8") as tf:
                        json.dump(data, tf, ensure_ascii=False, indent=2)
                    os.replace(tmp_path, _get_active_tasks_file())
                except Exception:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                    raise
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except Exception:
        pass  # 写操作失败不影响主流程


def update_task_status(session_id: str, status: str, content: str = "") -> None:
    """更新指定任务的状态和 updated_at。"""
    try:
        _ensure_dir()
        with open(_get_active_tasks_file(), "a+", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.seek(0)
                try:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        data = {"tasks": []}
                except (ValueError, json.JSONDecodeError):
                    data = {"tasks": []}

                tasks = data.get("tasks", [])
                if not isinstance(tasks, list):
                    tasks = []

                for task in tasks:
                    if isinstance(task, dict) and task.get("session_id") == session_id:
                        task["status"] = status
                        task["updated_at"] = time.time()
                        if content:
                            task["content"] = content
                        break

                data["tasks"] = tasks
                fd, tmp_path = tempfile.mkstemp(
                    dir=os.path.dirname(_get_active_tasks_file()), suffix=".tmp"
                )
                os.close(fd)
                try:
                    with open(tmp_path, "w", encoding="utf-8") as tf:
                        json.dump(data, tf, ensure_ascii=False, indent=2)
                    os.replace(tmp_path, _get_active_tasks_file())
                except Exception:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                    raise
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except Exception:
        pass  # 写操作失败不影响主流程


def get_task(session_id: str) -> Optional[dict]:
    """按 session_id 查询单个任务。"""
    try:
        if not os.path.exists(_get_active_tasks_file()):
            return None
        with open(_get_active_tasks_file(), "r", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                data = json.load(f)
                if isinstance(data, dict):
                    tasks = data.get("tasks", [])
                    if isinstance(tasks, list):
                        for task in tasks:
                            if isinstance(task, dict) and task.get("session_id") == session_id:
                                return task
                return None
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except (OSError, ValueError):
        return None


def remove_completed_tasks(max_age_hours: int = 24) -> None:
    """清理 status 为 complete/error 且 updated_at 超过 max_age_hours 的任务。"""
    try:
        _ensure_dir()
        with open(_get_active_tasks_file(), "a+", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.seek(0)
                try:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        data = {"tasks": []}
                except (ValueError, json.JSONDecodeError):
                    data = {"tasks": []}

                tasks = data.get("tasks", [])
                if not isinstance(tasks, list):
                    tasks = []

                cutoff = time.time() - max_age_hours * 3600
                remaining = []
                for task in tasks:
                    if not isinstance(task, dict):
                        continue
                    status = task.get("status", "")
                    updated_at = task.get("updated_at", 0)
                    if status in ("complete", "error") and updated_at < cutoff:
                        continue
                    remaining.append(task)

                data["tasks"] = remaining
                fd, tmp_path = tempfile.mkstemp(
                    dir=os.path.dirname(_get_active_tasks_file()), suffix=".tmp"
                )
                os.close(fd)
                try:
                    with open(tmp_path, "w", encoding="utf-8") as tf:
                        json.dump(data, tf, ensure_ascii=False, indent=2)
                    os.replace(tmp_path, _get_active_tasks_file())
                except Exception:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                    raise
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except Exception:
        pass  # 写操作失败不影响主流程
