#!/bin/bash
E=$HOME/Downloads/Penny-Omnigent-Fallback-2026-09-18/eval
OMNI=$HOME/.local/bin/omnigent
cd "$E"
for tid in "$@"; do
  L=$E/logs/draft-task-$tid.log
  : > "$L"
  PROMPT="$(cat $E/tasks/task-$tid.md)

---
Use the defaults for file name and location — go ahead, do not ask.
Name the output file task-$tid.md
Run your full workflow to completion and tell me the resolved output path."
  echo "=== draft task-$tid  $(date +%H:%M:%S) ==="
  $OMNI run "$E/draft-agent" --server local -p "$PROMPT" > "$L" 2>&1
  # draft-agent writes into .draft/<workspace>/ — find it
  F=$(find "$E/.draft" -name "task-$tid.md" -newermt '-2 hours' 2>/dev/null | head -1)
  if [ -n "$F" ]; then cp "$F" "$E/results-draft/task-$tid.md"; echo "  OK $(wc -c < "$F") chars  <- $F"
  else echo "  no artifact; log tail:"; tail -3 "$L" | sed 's/^/    /'; fi
done
echo "DRAFT RUN DONE"
