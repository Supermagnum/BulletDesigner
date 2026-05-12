"""
Create Bullet command for Bullet Designer workbench.

This command creates a new parametric bullet object and opens
the task panel for parameter editing.
"""

import os

import FreeCAD as App
import FreeCADGui as Gui

from bullet_designer import WB_ROOT
from bullet_designer.Gui.BulletTaskPanel import BulletTaskPanel
from bullet_designer.Objects.BulletFeature import makeBulletFeature


class CreateBulletCommand:
    """
    Command to create a new bullet object.
    """
    
    def __init__(self):
        """Initialize the command."""
        # Get icon path
        icon_path = os.path.join(WB_ROOT, "Resources", "icons", "CreateBullet.svg")
        # Fallback if icon doesn't exist
        if not os.path.exists(icon_path):
            icon_path = ""
        
        self.resources = {
            "Pixmap": icon_path,
            "MenuText": "Create Bullet",
            "ToolTip": "Create a new parametric bullet",
            "Accel": "B"
        }
    
    def GetResources(self):
        """
        Return command metadata.
        
        Returns:
            dict: Command resources including icon, menu text, tooltip, etc.
        """
        return self.resources
    
    def IsActive(self):
        """
        Determine if command should be enabled.
        
        Returns:
            bool: True if command should be active, False otherwise
        """
        return App.ActiveDocument is not None
    
    def Activated(self):
        """
        Execute the command.
        
        Creates a new parametric bullet object and opens the task panel
        for parameter editing.
        """
        doc = App.ActiveDocument
        if not doc:
            App.Console.PrintError("No active document\n")
            return
        
        # Use transaction for undo/redo support
        doc.openTransaction("Create Bullet")
        
        try:
            # Create new bullet object
            bullet = makeBulletFeature("Bullet")
            
            if bullet:
                # Note: For sketch attachment, manually create a PartDesign Body:
                #   1. Switch to PartDesign workbench
                #   2. Create a new Body (PartDesign menu -> Create Body)
                #   3. Select the bullet object
                #   4. In the Body's properties, set "Base Feature" to the bullet object
                #   5. Set the Body as active (double-click or right-click -> Toggle active body)
                # Then you can attach sketches to bullet faces without "make independent copy" dialog
                App.Console.PrintMessage("Bullet created successfully\n")
                App.Console.PrintMessage("  To attach sketches: Create a PartDesign Body and set bullet as BaseFeature\n")
                
                # Values are now set in makeBulletFeature(), so we can safely open the task panel
                # The task panel will load the correct values
                panel = BulletTaskPanel(bullet)
                Gui.Control.showDialog(panel)
                
                # Recompute after panel is shown to generate geometry
                # execute() will skip if values aren't set (Length check)
                bullet.recompute()
                
                # Commit transaction
                doc.commitTransaction()
                
                # Fit view
                if App.GuiUp:
                    Gui.SendMsgToActiveView("ViewFit")
                
                App.Console.PrintMessage("Bullet created successfully\n")
            else:
                doc.abortTransaction()
                App.Console.PrintError("Failed to create bullet object\n")
                
        except Exception as e:
            # Rollback on error
            doc.abortTransaction()
            App.Console.PrintError(f"Error creating bullet: {str(e)}\n")
            import traceback
            traceback.print_exc()


# Register command (only if Gui is available)
try:
    Gui.addCommand("BulletDesigner_CreateBullet", CreateBulletCommand())
except Exception as e:
    App.Console.PrintError(f"Failed to register CreateBullet command: {e}\n")
