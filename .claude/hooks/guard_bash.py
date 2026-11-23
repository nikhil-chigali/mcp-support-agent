"""PreToolUse guard for Bash: refuse commands that touch secrets, the holdout set,
or wipe a database.

File tools (Read, Edit, Grep, ...) are covered by permissions.deny in
.claude/settings.json. A shell command can reach the same files by other means
(cat, source, cp), so it is checked here. This is a guardrail against mistakes,
not a sandbox: a determined command can always be phrased to slip past a regex.

Input: the hook payload as JSON on stdin. Output: nothing to allow, or a JSON
"deny" decision whose reason is shown to Claude so it can change course.
Stdlib only, so any python3 on PATH can run it.
"""

import json
import re
import sys

# .env or .env.<anything>, as a path or word in the command; .env.example is fine.
ENV_FILE = re.compile(r"(?<![\w.-])\.env(?:\.(?!example\b)[\w.-]+)?(?![\w.-])")
# The holdout file itself (evals/tickets/holdout*), not every mention of the word.
HOLDOUT = re.compile(r"tickets/holdout|holdout[\w.-]*\.jsonl", re.IGNORECASE)

RULES = [
    (
        lambda cmd: ENV_FILE.search(cmd),
        ".env holds the user's real database credentials and must not be read, "
        "copied or printed. Use .env.example for the variable names.",
    ),
    (
        lambda cmd: HOLDOUT.search(cmd),
        "The holdout eval tickets must never be read or touched: they are the "
        "check against overfitting the prompt. Use evals/tickets/dev.jsonl.",
    ),
    (
        lambda cmd: re.search(r"\balembic\b.*\bdowngrade\b", cmd) and "store_test" not in cmd,
        "alembic downgrade drops data. It is only allowed against store_test "
        "(e.g. `just migration-check`). Ask the user to downgrade the dev database.",
    ),
    (
        lambda cmd: re.search(r"\bdocker\s+compose\b.*\bdown\b.*(\s-v\b|--volumes)", cmd),
        "`docker compose down -v` deletes the database volume. Ask the user to "
        "run `just reset-db` themselves.",
    ),
    (
        lambda cmd: re.search(r"\bjust\s+reset-db\b", cmd),
        "`just reset-db` wipes all local data. Ask the user to run it themselves.",
    ),
    (
        lambda cmd: re.search(r"\bdrop\s+(database|schema|table)\b", cmd, re.IGNORECASE),
        "DROP statements are not run by Claude. Write a migration, or ask the user.",
    ),
]


def main() -> None:
    payload = json.load(sys.stdin)
    command = payload.get("tool_input", {}).get("command", "")
    for matches, reason in RULES:
        if matches(command):
            decision = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Blocked by .claude/hooks/guard_bash.py: " + reason,
                }
            }
            print(json.dumps(decision))
            return


if __name__ == "__main__":
    main()
