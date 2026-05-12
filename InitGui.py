"""
FreeCAD Bullet Designer Workbench GUI initialization.

This module initializes the GUI components of the workbench,
including toolbars, menus, and commands.
"""

import FreeCAD as App
import FreeCADGui as Gui
import os


class BulletDesignerWorkbench(Gui.Workbench):
    """
    Bullet Designer workbench class.
    
    Provides parametric bullet and projectile design tools with
    ballistic calculations and material database.
    """
    
    def __init__(self):
        """Initialize workbench properties."""
        # Get workbench directory - handle case where __file__ might not be defined
        try:
            __dir__ = os.path.dirname(__file__)
        except NameError:
            # Fallback: use FreeCAD's Mod path
            import FreeCAD as App
            __dir__ = os.path.join(App.getUserAppDataDir(), "Mod", "BulletDesigner")
        
        self.__class__.Icon = os.path.join(
            __dir__, "Resources", "icons", "BulletDesigner.svg"
        )
        self.__class__.MenuText = "Bullet Designer"
        self.__class__.ToolTip = "Design parametric bullets and projectiles"
    
    def Initialize(self):
        """
        Initialize the workbench.
        This is called when the workbench is first activated.
        """
        App.Console.PrintLog("Initializing Bullet Designer workbench...\n")
        
        # Import commands (wrap in try-except to handle import errors gracefully)
        commands_loaded = []
        
        try:
            from bullet_designer.Commands import CreateBullet  # noqa: F401

            commands_loaded.append("CreateBullet")
            # Verify command was registered
            if Gui.Command.get("BulletDesigner_CreateBullet"):
                App.Console.PrintLog("  CreateBullet loaded and registered\n")
            else:
                App.Console.PrintWarning("  CreateBullet imported but not registered\n")
        except Exception as e:
            App.Console.PrintError(f"  Failed to import CreateBullet: {e}\n")
            import traceback
            App.Console.PrintError(traceback.format_exc())
        
        try:
            from bullet_designer.Commands import BallisticCalculator  # noqa: F401

            commands_loaded.append("BallisticCalculator")
            App.Console.PrintLog("  BallisticCalculator loaded\n")
        except Exception as e:
            App.Console.PrintError(f"  Failed to import BallisticCalculator: {e}\n")
            import traceback
            App.Console.PrintError(traceback.format_exc())
        
        try:
            from bullet_designer.Commands import TrajectoryCalculator  # noqa: F401

            commands_loaded.append("TrajectoryCalculator")
            App.Console.PrintLog("  TrajectoryCalculator loaded\n")
        except Exception as e:
            App.Console.PrintError(f"  Failed to import TrajectoryCalculator: {e}\n")
            import traceback
            App.Console.PrintError(traceback.format_exc())
        
        try:
            from bullet_designer.Commands import BulletLibrary  # noqa: F401

            commands_loaded.append("BulletLibrary")
            App.Console.PrintLog("  BulletLibrary loaded\n")
        except Exception as e:
            App.Console.PrintWarning(f"  Failed to import BulletLibrary: {e}\n")

        try:
            from bullet_designer.Commands import ExportTools  # noqa: F401

            commands_loaded.append("ExportTools")
            App.Console.PrintLog("  ExportTools loaded\n")
        except Exception as e:
            App.Console.PrintError(f"  Failed to import ExportTools: {e}\n")
            import traceback
            App.Console.PrintError(traceback.format_exc())
        
        # Import preferences page
        try:
            from bullet_designer.Gui import PreferencesPage  # noqa: F401

            App.Console.PrintLog("  PreferencesPage loaded\n")
        except Exception as e:
            App.Console.PrintWarning(f"  Failed to import PreferencesPage: {e}\n")
        
        # List of command names for toolbar
        # Commands register themselves when their modules are imported
        self.list = [
            "BulletDesigner_CreateBullet",
            "BulletDesigner_BallisticCalculator",
            "Separator",
            "BulletDesigner_ExportSTL",
            "BulletDesigner_ExportSTEP"
        ]
        
        # Create toolbar
        self.appendToolbar("Bullet Designer", self.list)
        
        # Create menu
        create_menu = [
            "BulletDesigner_CreateBullet"
        ]
        self.appendMenu(["Bullet Designer", "Create"], create_menu)
        
        library_menu = [
            "BulletDesigner_BulletLibrary"
        ]
        self.appendMenu(["Bullet Designer", "Library"], library_menu)
        
        analysis_menu = [
            "BulletDesigner_BallisticCalculator",
            "BulletDesigner_TrajectoryCalculator"
        ]
        self.appendMenu(["Bullet Designer", "Calculate"], analysis_menu)
        
        export_menu = [
            "BulletDesigner_ExportSTL",
            "BulletDesigner_ExportSTEP"
        ]
        self.appendMenu(["Bullet Designer", "Export"], export_menu)
        
        msg = (
            "Bullet Designer workbench initialized "
            f"({len(commands_loaded)} modules loaded)\n"
        )
        App.Console.PrintLog(msg)
    
    def Activated(self):
        """
        Executed when workbench is activated.
        """
        return
    
    def Deactivated(self):
        """
        Executed when workbench is deactivated.
        """
        return
    
    def ContextMenu(self, recipient):
        """
        Right-click context menu.
        
        Args:
            recipient: Context menu recipient ("View", "Tree", etc.)
        """
        if recipient == "View":
            self.appendContextMenu("Bullet Designer", self.list)
    
    def GetClassName(self):
        """Return the workbench class name."""
        return "Gui::PythonWorkbench"


# Register workbench
Gui.addWorkbench(BulletDesignerWorkbench())
