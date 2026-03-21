#!/usr/bin/env python3
"""
Alta Lex Legal Analysis - Polling Orchestrator
===============================================
Background script for OpenClaw integration.

Workflow:
  1. Login to Alta Lex API
  2. Create analysis session
  3. Start SSE streaming and write incremental results to a session file
  4. The session file can be polled by OpenClaw at 30-second intervals

Session file format (JSON):
  {
    "status": "running" | "complete" | "error",
    "session_id": "...",
    "query": "...",
    "content": "accumulated text so far...",
    "error": null | "error message",
    "started_at": "ISO timestamp",
    "updated_at": "ISO timestamp",
    "finished_at": null | "ISO timestamp"
  }

Usage:
  python3 alta_lex_poll.py \
    --username USER --password PASS \
    --query "legal question" \
    --session-file /tmp/alta-lex-session-XXXXX.json \
    [--practice-area "Property Law"] \
    [--jurisdiction "Hong Kong"] \
    [--output-language "English"] \
    [--background "additional context"] \
    [--pro]
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

# Add the script directory to path so we can import the client
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alta_lex_client import (
    AltaLexClient,
    AltaLexError,
    AuthenticationError,
    SessionExpiredError,
    APIError,
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_session_file(path: str, data: dict):
    """Atomically write session state to JSON file."""
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def read_session_file(path: str) -> dict:
    """Read session state from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_analysis(args):
    session_state = {
        "status": "running",
        "session_id": None,
        "query": args.query,
        "content": "",
        "error": None,
        "started_at": now_iso(),
        "updated_at": now_iso(),
        "finished_at": None,
    }
    write_session_file(args.session_file, session_state)

    client = AltaLexClient(base_url=args.base_url)

    # Step 1: Login
    try:
        client.login(args.username, args.password)
        session_state["updated_at"] = now_iso()
        write_session_file(args.session_file, session_state)
    except AuthenticationError as e:
        session_state["status"] = "error"
        session_state["error"] = f"Authentication failed: {e}"
        session_state["finished_at"] = now_iso()
        write_session_file(args.session_file, session_state)
        return 1
    except AltaLexError as e:
        session_state["status"] = "error"
        session_state["error"] = f"Login error: {e}"
        session_state["finished_at"] = now_iso()
        write_session_file(args.session_file, session_state)
        return 1

    # Step 2: Create analysis session
    try:
        session_id = client.create_analysis_session(args.query)
        session_state["session_id"] = session_id
        session_state["updated_at"] = now_iso()
        write_session_file(args.session_file, session_state)
    except AltaLexError as e:
        session_state["status"] = "error"
        session_state["error"] = f"Failed to create session: {e}"
        session_state["finished_at"] = now_iso()
        write_session_file(args.session_file, session_state)
        return 1

    # Step 3: Stream SSE and write incremental results
    try:
        parts = []
        last_write_time = time.monotonic()

        for event in client.legal_analysis_sse(
            session_id=session_id,
            query=args.query,
            practice_area=args.practice_area,
            jurisdiction=args.jurisdiction,
            output_language=args.output_language,
            background=args.background,
            legal_research_pro=args.pro,
        ):
            parts.append(event.message)

            # Write to file at most every 5 seconds to reduce I/O
            elapsed = time.monotonic() - last_write_time
            if elapsed >= 5 or event.is_finished:
                session_state["content"] = "".join(parts)
                session_state["updated_at"] = now_iso()
                if event.is_finished:
                    session_state["status"] = "complete"
                    session_state["finished_at"] = now_iso()
                write_session_file(args.session_file, session_state)
                last_write_time = time.monotonic()

            if event.is_finished:
                break

        # Ensure final state is written
        if session_state["status"] != "complete":
            session_state["content"] = "".join(parts)
            session_state["status"] = "complete"
            session_state["updated_at"] = now_iso()
            session_state["finished_at"] = now_iso()
            write_session_file(args.session_file, session_state)

    except SessionExpiredError:
        # Try re-login once
        try:
            client.login(args.username, args.password)
            # Retry streaming with the same session
            parts_so_far = parts[:]
            for event in client.legal_analysis_sse(
                session_id=session_id,
                query=args.query,
                practice_area=args.practice_area,
                jurisdiction=args.jurisdiction,
                output_language=args.output_language,
                background=args.background,
                legal_research_pro=args.pro,
            ):
                parts_so_far.append(event.message)
                elapsed = time.monotonic() - last_write_time
                if elapsed >= 5 or event.is_finished:
                    session_state["content"] = "".join(parts_so_far)
                    session_state["updated_at"] = now_iso()
                    if event.is_finished:
                        session_state["status"] = "complete"
                        session_state["finished_at"] = now_iso()
                    write_session_file(args.session_file, session_state)
                    last_write_time = time.monotonic()
                if event.is_finished:
                    break
            if session_state["status"] != "complete":
                session_state["content"] = "".join(parts_so_far)
                session_state["status"] = "complete"
                session_state["updated_at"] = now_iso()
                session_state["finished_at"] = now_iso()
                write_session_file(args.session_file, session_state)
        except AltaLexError as e:
            session_state["status"] = "error"
            session_state["error"] = f"Session expired and re-login failed: {e}"
            session_state["finished_at"] = now_iso()
            write_session_file(args.session_file, session_state)
            return 1

    except AltaLexError as e:
        session_state["content"] = "".join(parts)
        session_state["status"] = "error"
        session_state["error"] = f"Analysis error: {e}"
        session_state["finished_at"] = now_iso()
        write_session_file(args.session_file, session_state)
        return 1

    return 0


def poll_status(args):
    """Poll a session file and print status."""
    if not os.path.exists(args.session_file):
        print(json.dumps({"status": "not_found", "error": "Session file does not exist"}))
        return 1

    state = read_session_file(args.session_file)
    print(json.dumps(state, ensure_ascii=False))
    return 0 if state.get("status") in ("complete", "running") else 1


def main():
    parser = argparse.ArgumentParser(
        description="Alta Lex Legal Analysis - Polling Orchestrator"
    )
    sub = parser.add_subparsers(dest="command", help="Command to run")

    # -- run command --
    run_parser = sub.add_parser("run", help="Start a legal analysis in background")
    run_parser.add_argument("--username", required=True, help="Alta Lex username")
    run_parser.add_argument("--password", required=True, help="Alta Lex password")
    run_parser.add_argument("--query", required=True, help="Legal question")
    run_parser.add_argument("--session-file", required=True, help="Path to session JSON file")
    run_parser.add_argument("--practice-area", default="Property Law", help="Legal practice area")
    run_parser.add_argument("--jurisdiction", default="Hong Kong", help="Jurisdiction")
    run_parser.add_argument("--output-language", default="English", help="Output language")
    run_parser.add_argument("--background", default="", help="Background context")
    run_parser.add_argument("--pro", action="store_true", help="Enable Legal Research Pro")
    run_parser.add_argument("--base-url", default=None, help="Override API base URL")

    # -- poll command --
    poll_parser = sub.add_parser("poll", help="Poll session file status")
    poll_parser.add_argument("--session-file", required=True, help="Path to session JSON file")

    args = parser.parse_args()

    if args.command == "run":
        sys.exit(run_analysis(args))
    elif args.command == "poll":
        sys.exit(poll_status(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
