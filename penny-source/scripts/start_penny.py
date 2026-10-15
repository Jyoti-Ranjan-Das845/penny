#!/usr/bin/env python3
"""Start the finalized Penny after the user has fully stopped local Omnigent.

This helper never stops or restarts an existing server or host daemon.
"""

from __future__ import annotations

import argparse
from importlib.metadata import version
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

from manage import VERIFIED_RUNTIME, validate_bundle
from omnigent.host.local_server import local_server_status


def require_stopped() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "omnigent.cli", "host", "status", "--server", "", "--json"],
        check=True, capture_output=True, text=True, timeout=20,
    )
    status = json.loads(result.stdout)
    if not isinstance(status, dict) or not isinstance(status.get("daemons"), list):
        raise RuntimeError("Could not verify local host status; nothing was started")
    if status["daemons"]:
        raise RuntimeError("Fully stop local Omnigent first; a host daemon is still recorded")
    server = local_server_status()
    if server.running or server.pid is not None:
        raise RuntimeError("Fully stop local Omnigent first; a local server is still recorded")
    try:
        connection = socket.create_connection(("127.0.0.1", 6767), timeout=2)
    except ConnectionRefusedError:
        return
    except OSError as exc:
        raise RuntimeError("Could not verify that the local server is stopped") from exc
    else:
        connection.close()
        raise RuntimeError("Fully stop local Omnigent first; port 6767 is still in use")


def start_environment(bundle: Path, original: dict[str, str]) -> dict[str, str]:
    if not bundle.is_absolute() or bundle.name != "penny" or bundle.is_symlink():
        raise ValueError("Use an absolute, real bundle directory whose basename is penny")
    if version("omnigent") != VERIFIED_RUNTIME:
        raise RuntimeError("Use the verified Omnigent Python interpreter")
    validate_bundle(bundle)
    environment = original.copy()
    entries = [entry.strip() for entry in environment.get("OMNIGENT_BUILTIN_AGENT_DIRS", "").split(os.pathsep)
               if entry.strip()]
    # A second source with the same builtin name could undo the selected update.
    for entry in entries:
        source = Path(entry)
        name = source.stem if source.is_file() else source.name
        if name == "penny" and source.resolve() != bundle.resolve():
            raise ValueError("Another Penny source is already configured; resolve it before starting")
    if str(bundle) not in entries:
        entries.append(str(bundle))
    environment["OMNIGENT_BUILTIN_AGENT_DIRS"] = os.pathsep.join(entries)
    return environment


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    environment = start_environment(args.bundle, dict(os.environ))
    require_stopped()
    if args.check_only:
        print("Ready. No server was started and no live installation was changed.")
        return
    # Recheck immediately before launch; never deliberately reuse a running host.
    require_stopped()
    raise SystemExit(subprocess.call(
        [sys.executable, "-m", "omnigent.cli", "start", "--server", "", "--non-interactive"],
        env=environment,
    ))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Penny was not started: {error}", file=sys.stderr)
        raise SystemExit(1)
