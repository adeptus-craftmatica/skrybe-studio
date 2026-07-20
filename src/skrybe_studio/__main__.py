"""Enables `python -m skrybe_studio`."""

import sys

from skrybe_studio.app.main import main

if __name__ == "__main__":
    sys.exit(main())
