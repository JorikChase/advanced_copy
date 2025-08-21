# __init__.py
"""
toggle visibility on or off when playhead in the current section (scenes or shots based on collection and camera markers)
name the copied object with a unique name according to the new collection where it is placed

Moving from location A to all enviro collections [A -> B]
Copy from location A to single current enviro collection [A -> B]
Move from enviro B to all scene collections [B -> C]
Copy from enviro B to single current scene collection [B -> C]
Copy from scene C to current shot collection D


MODEL-SC19-SH200+LOC-<loc_name>+
 MODEL-LOC-<loc_name>
  <asset_name>-P                      [<-here A]

+ENV-<env_name>+
 MODEL-ENV-<env_name>
  <asset_name>-P-<env_name>          [<-here B]

+SC<id>-<env_name>+
 +ART-SC19-APOLLO_CRASH+
  MODEL-SC19-APOLLO_CRASH
   <asset_name>-P-SC<id>-<env_name>  [<-here C]
  SHOT-ART-SC19-APOLLO_CRASH
   MODEL-SC19-SH200
    <asset_name>-P-SC<id>-SH<id>     [<-here D]
"""

bl_info = {
    "name": "Advanced Copy V4.1",
    "author": "iori, krutart, Gemini",
    "version": (4, 1, 0),
    "blender": (4, 5, 0),
    "location": "View3D > Object Context Menu",
    "description": "Automatically performs MODEL, VFX, ACTOR or PROP copy/move operations based on object context and a structured collection hierarchy.",
    "warning": "Ensure the folder containing these files is named 'advanced_copy'",
    "doc_url": "",
    "category": "Object",
}

import bpy
import importlib

# The 'from . import' syntax is crucial for Blender to correctly
# handle multi-file addons.
from . import utils
from . import operators
from . import ui

# A list to hold all classes that need to be registered.
# We gather them from the other modules.
classes = (
    *operators.classes,
    *ui.classes,
)


def register():
    """
    Registers all addon classes and adds the menu to the UI.
    """
    # Reload the submodules when re-registering. This is important for development.
    importlib.reload(utils)
    importlib.reload(operators)
    importlib.reload(ui)

    for cls in classes:
        bpy.utils.register_class(cls)

    # Add the main menu drawing function to the object context menu.
    bpy.types.VIEW3D_MT_object_context_menu.append(ui.draw_main_menu)


def unregister():
    """
    Unregisters all addon classes and removes the menu from the UI.
    """
    # Remove the menu drawing function.
    bpy.types.VIEW3D_MT_object_context_menu.remove(ui.draw_main_menu)

    # Unregister classes in reverse order.
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
