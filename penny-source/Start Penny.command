#!/bin/zsh
# Local convenience launcher. Stop Omnigent yourself before running this file.
set -eu
cd -- /Users/Pradeep.Das/Spaces/code/misc/penny-writing
exec /Users/Pradeep.Das/Spaces/code/oss/omnigent/.venv/bin/python3 \
  scripts/start_penny.py --bundle /Users/Pradeep.Das/.omnigent/agents/penny
