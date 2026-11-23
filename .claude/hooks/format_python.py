"""PostToolUse: format a Python file right after Claude edits or writes it.

Runs `ruff format` plus import sorting only (`--select I`). It deliberately does
not run the full `ruff check --fix`: that removes "unused" imports, and Claude
often adds an import in one edit and its first use in the next.

Never blocks: formatting failures are left for the Stop gate and pre-commit.
"""

import json
import os
import subprocess
import sys


def main() -> None:
    payload = json.load(sys.stdin)
    path = payload.get("tool_input", {}).get("file_path", "")
    if not path.endswith((".py", ".pyi")) or not os.path.isfile(path):
        return
    project = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    ruff = ["uv", "run", "--frozen", "--quiet", "ruff"]
    for args in (["format", path], ["check", "--select", "I", "--fix", "--quiet", path]):
        subprocess.run(ruff + args, cwd=project, capture_output=True)


if __name__ == "__main__":
    main()
