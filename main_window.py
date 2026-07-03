#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legacy compatibility entry point.

Historically this project could be started with ``python main_window.py``.
The production startup path is now ``main.py`` because it owns network mode,
license checks, logging, periodic backups, and the Document Shell bootstrap.
Keep this file only as a thin wrapper so old shortcuts do not start a
divergent application path.
"""

from main import main


if __name__ == "__main__":
    main()
