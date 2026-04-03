# deploy_mcp_http_bridge.py
# Publish the FastAPI HTTP tool bridge (POST /tools/call) used when MCP_BASE_URL is set.
# Run from repo root: python scripts/deploy_mcp_http_bridge.py

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

from _connect_env import (
    connect_api_key,
    connect_server_url,
    ensure_config_loaded,
    repo_root,
    rsconnect_cli_prefix,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deploy MCP HTTP bridge (mcp_server.http_bridge:app) to Posit Connect.",
    )
    parser.add_argument(
        "-t",
        "--title",
        default=os.environ.get("DEPLOY_MCP_TITLE", "Airspace Intelligence (MCP HTTP bridge)"),
        help="Content title on Connect.",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip post-deploy HTTP verification.",
    )
    parser.add_argument(
        "-E",
        "--env",
        action="append",
        default=[],
        metavar="NAME[=VALUE]",
        help="Forward an environment variable to Connect (repeatable).",
    )
    parser.add_argument(
        "--app-id",
        default=None,
        help="Optional: existing Connect content app ID to update (rsconnect -a/--app-id).",
    )
    parser.add_argument(
        "--python-version",
        default=None,
        help="Optional: override the Connect Python version (recommended to use .python-version instead).",
    )
    args = parser.parse_args(argv)

    ensure_config_loaded()
    server = connect_server_url()
    key = connect_api_key()
    if not server:
        print("Set CONNECT_SERVER (or POSIT_CONNECT_SERVER) in .env.", file=sys.stderr)
        return 1
    if not key:
        print("Set POSIT_CONNECT_PUBLISHER or CONNECT_API_KEY in .env.", file=sys.stderr)
        return 1

    root = repo_root()
    # Put options before the directory; use "." with cwd=root so -x globs cannot pick up sibling repo folders.
    cmd: list[str] = [
        *rsconnect_cli_prefix(),
        "deploy",
        "fastapi",
        "-s",
        server,
        "-k",
        key,
        "-e",
        "mcp_server.http_bridge:app",
        "-t",
        args.title,
        "-x",
        "screenshots",
        "-x",
        "__pycache__",
        "-x",
        ".pytest_cache",
        "-x",
        "scripts",
    ]
    for e in args.env:
        cmd.extend(["-E", e])
    if args.no_verify:
        cmd.append("--no-verify")
    if args.python_version:
        cmd.extend(["--override-python-version", args.python_version])
    if args.app_id:
        cmd.extend(["--app-id", args.app_id])
    cmd.append(".")

    print("rsconnect deploy fastapi (entry mcp_server.http_bridge:app) …")
    return subprocess.run(cmd, cwd=str(root)).returncode


if __name__ == "__main__":
    raise SystemExit(main())
