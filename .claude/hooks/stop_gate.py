"""Stop hook: before Claude ends its turn, lint and test whatever it changed.

If `just lint` or `just test` fails, the turn is not allowed to end: the failing
output goes back to Claude as the reason, and it keeps working. This turns
"I think it's done" into "the checks pass".

- Skips when the working tree is clean, so plain question-and-answer turns cost nothing.
- Loop guard: when Claude is already continuing because of this hook
  (stop_hook_active), it lets the turn end and tells the user instead of
  blocking forever on something Claude cannot fix.
- Only fast checks belong here. Database checks (migration-check) stay in CI.
"""

import json
import os
import subprocess
import sys

CHECKS = (["just", "lint"], ["just", "test", "-q"])
MAX_OUTPUT = 4000  # characters of failing output sent back to Claude


def run(cmd: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def main() -> None:
    payload = json.load(sys.stdin)
    project = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    if not run(["git", "status", "--porcelain"], project).stdout.strip():
        return

    for cmd in CHECKS:
        result = run(cmd, project)
        if result.returncode == 0:
            continue
        output = (result.stdout + result.stderr)[-MAX_OUTPUT:]
        name = " ".join(cmd)
        if payload.get("stop_hook_active"):
            print(json.dumps({"systemMessage": f"Stop gate: `{name}` still fails; over to you."}))
            return
        reason = f"`{name}` failed. Fix it before finishing:\n\n{output}"
        print(json.dumps({"decision": "block", "reason": reason}))
        return


if __name__ == "__main__":
    main()
