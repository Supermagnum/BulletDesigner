"""
DirModGui loader entry (FreeCAD expects this exact filename).

Workbench implementation lives in init_gui.py per Addon Academy naming;
see src/Gui/FreeCADGuiInit.py DirModGui.INIT_GUI_PY vs ExtModGui.
"""

import importlib

importlib.import_module("freecad.BulletDesigner.init_gui")
