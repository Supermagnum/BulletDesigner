"""
BulletDesigner workbench Python package.

All workbench modules live here so generic names such as Commands or Utils
never collide with other addons on sys.path or with stdlib-ish top-level names.
"""

import os

_PATH = os.path.dirname(os.path.abspath(__file__))
# Parent of bullet_designer/ is the addon workbench root (InitGui.py lives there)
WB_ROOT = os.path.dirname(_PATH)
