#!/usr/bin/env python3
"""Add Penny's inline label to the installed Omnigent 0.12.0 web bundle."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


OLD = b'var mKe={polly:`Multi-agent coding`,debby:`Multi-agent debate`}'
NEW = b'var mKe={polly:`Multi-agent coding`,debby:`Multi-agent debate`,penny:`Multi-agent writing`}'


def install(web_root: Path, backup_dir: Path) -> dict:
    html = (web_root / "index.html").read_text()
    entries = re.findall(r'src="(?:\./|/)?(assets/index-[^"/]+\.js)"', html)
    if len(entries) != 1:
        raise ValueError("Expected exactly one installed web entry point")
    target = web_root / entries[0]
    data = target.read_bytes()
    if data.count(NEW) == 1 and OLD not in data:
        return {"action": "already_installed", "asset": str(target)}
    if data.count(OLD) != 1 or NEW in data:
        raise ValueError("Installed picker mapping differs; no changes made")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / (target.name + ".original")
    if backup.exists():
        if backup.read_bytes() != data:
            raise ValueError("Existing backup differs; no changes made")
    else:
        shutil.copy2(target, backup)
    updated = data.replace(OLD, NEW, 1)
    target.write_bytes(updated)
    if target.read_bytes() != updated:
        raise RuntimeError("Picker asset write did not verify")
    report = {
        "action": "installed", "asset": str(target), "backup": str(backup),
        "before_sha256": hashlib.sha256(data).hexdigest(),
        "after_sha256": hashlib.sha256(updated).hexdigest(),
        "literal_replacements": 1, "label": "Multi-agent writing",
        "refresh": "Hard-refresh existing browser tabs to bypass cached immutable assets.",
    }
    (backup_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web-root", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(install(args.web_root, args.backup_dir), indent=2))


if __name__ == "__main__":
    main()
