"""SARMS — check a repository's architecture from a Git URL.

NORMAL WORKFLOW
  uv run sarms auto <git-url> --tests "python -m pytest -q"
  uv run sarms auto <git-url> --tests "python -m pytest -q" --apply
  uv run sarms auto <git-url> --tests "python -m pytest -q" --apply --push

RESET ONE REPOSITORY
  uv run sarms clean <git-url> --yes

The default is a dry run. ``--apply`` enables verified fixes on the ``sarms/fixes``
branch; ``--push`` also pushes that branch to the repository's origin.

ADVANCED COMMANDS
  run, mine, certify-ledger, status, compile, check, replay, ledger, draft, learn,
  adopt, certify, verify-rules

Results are stored automatically under data/<repository>/rms.
"""
from __future__ import annotations

import importlib
import sys

# command -> module whose main() runs it (and the arguments put in front of the user's).
# Modules are imported only when their command runs, so `sarms --help` stays instant.
COMMANDS: dict[str, tuple[str, list[str]]] = {
    # the product (sarms.product)
    "auto": ("sarms.product", ["run"]),
    "run": ("sarms.product", ["run"]),
    "mine": ("sarms.product", ["mine"]),
    "certify-ledger": ("sarms.product", ["certify-ledger"]),
    "status": ("sarms.product", ["status"]),
    "clean": ("sarms.product", ["clean"]),
    # one stage at a time
    "compile": ("sarms.rules.compile", []),
    "check": ("sarms.differ.diff", []),
    "replay": ("sarms.differ.replay", []),
    "ledger": ("sarms.ledger.build", []),
    "draft": ("sarms.synthesize.draft", []),
    "learn": ("sarms.rules.evidence", []),
    "adopt": ("sarms.synthesize.adopt", []),
    "certify": ("sarms.rules.certify", ["certify"]),
    "verify-rules": ("sarms.rules.certify", ["verify"]),
}


def main() -> None:
    for stream in (sys.stdout, sys.stderr):  # a character the console's code page lacks prints as "?", never crashes
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help") or argv[0] not in COMMANDS:
        print(__doc__)
        sys.exit(0 if argv and argv[0] in ("-h", "--help") else 2)
    modname, pre = COMMANDS[argv[0]]
    mod = importlib.import_module(modname)
    sys.argv = [f"sarms {argv[0]}", *pre, *argv[1:]]
    mod.main()
