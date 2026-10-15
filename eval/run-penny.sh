#!/bin/bash
E=$HOME/Downloads/Penny-Omnigent-Fallback-2026-09-18/eval
B=$HOME/Downloads/Penny-Omnigent-Fallback-2026-09-18/penny-claude
OMNI=$HOME/.local/bin/omnigent
cd $HOME/Downloads/Penny-Omnigent-Fallback-2026-09-18
for tid in "$@"; do
  L=$E/logs/penny-task-$tid.log
  : > "$L"
  PROMPT="$(cat $E/tasks/task-$tid.md)

---
Note: child dispatch results cannot reach this non-interactive session, so run
your own pass and deliver. Do not wait on a reader.
Deliver the finished artifact between these exact markers:
<<<ARTIFACT
...the artifact only...
ARTIFACT>>>
After the closing marker, one short line: which model wrote it, and anything you
could not verify."
  echo "=== penny task-$tid  $(date +%H:%M:%S) ==="
  $OMNI run "$B" --server local -p "$PROMPT" > "$L" 2>&1
  python3 - "$tid" "$E" <<'PY'
import re,sys,pathlib
tid,E=sys.argv[1],sys.argv[2]
log=pathlib.Path(f"{E}/logs/penny-task-{tid}.log").read_text()
ms=re.findall(r'<<<ARTIFACT\s*(.*?)\s*ARTIFACT>>>', log, re.S)
if ms:
    pathlib.Path(f"{E}/results-penny/task-{tid}.md").write_text(ms[-1]); print(f"  OK {len(ms[-1])} chars")
else:
    m=re.search(r'<<<ARTIFACT\s*(.*)', log, re.S)
    if m and len(m.group(1).strip())>100:
        body=re.split(r'ARTIFACT>>>',m.group(1))[0].strip()
        pathlib.Path(f"{E}/results-penny/task-{tid}.md").write_text(body); print(f"  PARTIAL {len(body)} chars")
    else: print("  FAILED")
PY
done
echo "PENNY RUN DONE"
