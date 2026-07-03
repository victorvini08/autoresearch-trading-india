"""Enables ``python -m autoresearch`` as an alias for the ``autoresearch`` CLI."""

import sys

from autoresearch.cli import main

if __name__ == "__main__":
    sys.exit(main())
