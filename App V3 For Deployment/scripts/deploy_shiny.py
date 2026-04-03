# deploy_shiny.py
# Publish the Shiny app to Posit Connect: python scripts/deploy_shiny.py

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
    parser = argparse.ArgumentParser(description="Deploy Shiny app to Posit Connect via rsconnect-python.")
    parser.add_argument(
        "-t",
        "--title",
        default=os.environ.get("DEPLOY_SHINY_TITLE", "Airspace Intelligence (Shiny)"),
        help="Content title on Connect (default from DEPLOY_SHINY_TITLE or built-in).",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip post-deploy HTTP verification (rsconnect --no-verify).",
    )
    parser.add_argument(
        "--new",
        action="store_true",
        help="Force a new deployment (rsconnect --new). Useful when the existing deployment has the wrong content mode.",
    )
    parser.add_argument(
        "--app-id",
        default=None,
        help="Existing Connect content GUID or numeric id to update (rsconnect -a). "
        "If omitted, uses CONNECT_SHINY_APP_ID from .env when not using --new.",
    )
    parser.add_argument(
        "-E",
        "--env",
        action="append",
        default=[],
        metavar="NAME[=VALUE]",
        help="Forward an environment variable to Connect (repeatable). Same as rsconnect -E.",
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
    mcp_base_url = (os.environ.get("MCP_BASE_URL") or "").strip().rstrip("/")
    if not server:
        print("Set CONNECT_SERVER (or POSIT_CONNECT_SERVER) in .env to your Connect base URL.", file=sys.stderr)
        return 1
    if not key:
        print("Set POSIT_CONNECT_PUBLISHER or CONNECT_API_KEY in .env for rsconnect.", file=sys.stderr)
        return 1

    root = repo_root()
    cmd: list[str] = [
        *rsconnect_cli_prefix(),
        "deploy",
        "shiny",
        "-s",
        server,
        "-k",
        key,
        "-e",
        "app.shiny_app:app",
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
    if mcp_base_url and not any((e or "").split("=", 1)[0] == "MCP_BASE_URL" for e in args.env):
        cmd.extend(["-E", f"MCP_BASE_URL={mcp_base_url}"])
    if args.no_verify:
        cmd.append("--no-verify")
    if args.python_version:
        cmd.extend(["--override-python-version", args.python_version])
    if args.new:
        cmd.append("--new")
    elif not args.new:
        app_id = (args.app_id or os.environ.get("CONNECT_SHINY_APP_ID") or "").strip()
        if app_id:
            cmd.extend(["--app-id", app_id])
    cmd.append(".")

    print("rsconnect deploy shiny (entry app.shiny_app:app) …")
    return subprocess.run(cmd, cwd=str(root)).returncode


if __name__ == "__main__":
    raise SystemExit(main())
