"""
freecad.BulletDesigner namespace package (Addon Academy Modern layout).

Workbench implementation code and resources paths; loaded when the addon
root is on sys.path (see package.xml workbench subdirectory).
"""

import os

__version__ = "1.0.0"
__author__ = "Bullet Designer Team"
__date__ = "2026-02-16"

_PKG = os.path.dirname(os.path.abspath(__file__))
# Parent of freecad/BulletDesigner is freecad/; its parent is addon install root
WB_ROOT = os.path.dirname(os.path.dirname(_PKG))
