"""Unified ``autoresearch`` command — the front door after installation.

Running ``autoresearch`` with no arguments prints what to do next, so a freshly
installed user isn't left guessing. Subcommands dispatch to the same entry
points exposed as ``autoresearch-init`` / ``-eval`` / ``-data``.
"""

from __future__ import annotations

import os
import sys

from autoresearch import __version__

_KNOWN_NAMES = {"autoresearch", "autoresearch-trading"}


def _prog() -> str:
    """The command name the user actually typed (so help echoes it back)."""
    name = os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else ""
    return name if name in _KNOWN_NAMES else "autoresearch"


def _help(prog: str) -> str:
    return f"""\
autoresearch-trading {__version__} — build LLM-driven autoresearch trading systems

Get started:
  {prog} init my-project      scaffold a runnable starter project
  cd my-project && python run.py     backtest on synthetic data (no setup)

Then edit, in order:  strategy.py  ->  provider.py  ->  config.py

Commands:
  init <name>      Scaffold a new project you own (strategy/provider/config/…)
  eval [mode]      Run the walk-forward evaluator + anti-overfit gates
                   (mode: research | promotion; default research)
  data             Generate a synthetic prices + universe dataset
  version          Print the installed version
  help             Show this message

Docs & source:   https://github.com/victorvini08/autoresearch-trading-india

⚠  Use at your own risk. Research software, no warranty, NOT financial advice;
   trading risks total loss of capital. Terms: DISCLAIMER.md in the repo.
"""


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    cmd = args[0] if args else "help"
    rest = args[1:]

    if cmd in ("help", "-h", "--help"):
        print(_help(_prog()))
        return 0
    if cmd in ("version", "-V", "--version"):
        print(__version__)
        return 0

    # Dispatch to the existing entry-point mains, which parse sys.argv.
    if cmd == "init":
        from autoresearch.scaffold import main as sub
        sys.argv = ["autoresearch-init", *rest]
    elif cmd == "eval":
        from autoresearch.research.prepare import main as sub
        sys.argv = ["autoresearch-eval", *rest]
    elif cmd == "data":
        from autoresearch.data.synthetic import main as sub
        sys.argv = ["autoresearch-data", *rest]
    else:
        print(f"{_prog()}: unknown command '{cmd}'\n")
        print(_help(_prog()))
        return 2

    return sub() or 0


if __name__ == "__main__":
    sys.exit(main())
