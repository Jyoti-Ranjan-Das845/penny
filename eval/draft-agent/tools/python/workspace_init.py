"""Create or find the draft workspace for one document.

``.draft/`` is anchored to the directory the agent was launched from,
read from ``OMNIGENT_RUNNER_WORKSPACE``. That anchor is fixed for the
life of a run, so every workspace and every registry lookup resolves to
the same place regardless of which document is being worked on.
"""

import csv
import os
from pathlib import Path

from omnigent_client import tool

REGISTRY_COLUMNS = ["workspace_id", "target_path", "stage"]
INITIAL_STAGE = "requirements"


def _anchor() -> Path:
    """Return the directory that holds ``.draft/``.

    :returns: The launch directory, resolved absolute.
    """
    root = os.environ.get("OMNIGENT_RUNNER_WORKSPACE") or os.getcwd()
    return Path(root).expanduser().resolve()


def _read_rows(registry: Path) -> list[dict[str, str]]:
    """Read existing registry rows.

    :param registry: Path to ``registry.csv``.
    :returns: One dict per row; empty when the file does not exist.
    """
    if not registry.is_file():
        return []
    with registry.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _next_id(rows: list[dict[str, str]]) -> str:
    """Assign the lowest unused workspace id.

    :param rows: Existing registry rows.
    :returns: An id of the form ``ws-01``.
    """
    used = set()
    for row in rows:
        value = (row.get("workspace_id") or "").strip()
        if value.startswith("ws-") and value[3:].isdigit():
            used.add(int(value[3:]))
    n = 1
    while n in used:
        n += 1
    return f"ws-{n:02d}"


@tool
def workspace_init(target_path: str | None = None, file_name: str | None = None) -> str:
    """Open the draft workspace for a document, creating it if needed.

    Call this once a document is ready to begin. An explicit target path is
    preserved. When no target path is supplied, the finished document defaults
    to ``.draft/<workspace_id>/<file_name>`` under the launch directory. In
    that case ``file_name`` must be a bare file name; it defaults to
    ``document.md``. Calls with the same explicit target are idempotent.

    :param target_path: Optional explicit finished-document path, e.g.
        ``"docs/router-hld.md"``. Relative paths resolve against the launch
        directory.
    :param file_name: Optional bare name for the workspace-default document,
        e.g. ``"router-hld.md"``. Ignored when ``target_path`` is supplied.
    :returns: Newline-separated ``key=value`` lines describing the
        workspace, or a line beginning ``error=`` on failure.
    """
    try:
        root = _anchor()
        draft_dir = root / ".draft"
        registry = draft_dir / "registry.csv"

        draft_status = "existing" if draft_dir.is_dir() else "created"
        draft_dir.mkdir(parents=True, exist_ok=True)

        explicit_target = bool(target_path and target_path.strip())
        target: str | None = None
        if explicit_target:
            resolved_target = Path(target_path.strip()).expanduser()
            if not resolved_target.is_absolute():
                resolved_target = root / resolved_target
            target = str(resolved_target.resolve(strict=False))

        rows = _read_rows(registry)
        existing = (
            next(
                (r for r in rows if (r.get("target_path") or "").strip() == target),
                None,
            )
            if target is not None
            else None
        )

        if existing is not None:
            workspace_id = (existing.get("workspace_id") or "").strip()
            stage = (existing.get("stage") or INITIAL_STAGE).strip()
            document_status = "existing"
        else:
            workspace_id = _next_id(rows)
            stage = INITIAL_STAGE
            document_status = "created"

        workspace = draft_dir / workspace_id
        workspace.mkdir(parents=True, exist_ok=True)

        if target is None:
            chosen_name = (file_name or "document.md").strip()
            candidate = Path(chosen_name).expanduser()
            if not chosen_name or candidate.is_absolute() or candidate.name != chosen_name:
                return "error=file_name must be a non-empty bare file name"
            target = str((workspace / candidate).resolve(strict=False))

        if existing is None:
            write_header = not registry.is_file()
            with registry.open("a", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=REGISTRY_COLUMNS)
                if write_header:
                    writer.writeheader()
                writer.writerow(
                    {
                        "workspace_id": workspace_id,
                        "target_path": target,
                        "stage": stage,
                    }
                )

        contents = sorted(p.name for p in workspace.iterdir() if p.is_file())

        return "\n".join(
            [
                f"document={document_status}",
                f"workspace_id={workspace_id}",
                f"workspace_path={workspace}",
                f"target_path={target}",
                f"registry_path={registry}",
                f"stage={stage}",
                f"workspace_files={', '.join(contents) if contents else 'none'}",
                f"draft_dir={draft_status}",
            ]
        )
    except OSError as exc:
        return f"error={exc}"
