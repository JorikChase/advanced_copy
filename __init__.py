bl_info = {
    "name": "Advanced Copy V4",
    "author": "iori, krutart, Gemini",
    "version": (4, 0, 1),
    "blender": (4, 0, 0),
    "location": "View3D > Object Context Menu",
    "description": "Automatically performs MODEL or VFX copy/move operations based on object context and a structured collection hierarchy.",
    "warning": "Ensure the folder containing these files is named 'advanced_copy'",
    "doc_url": "",
    "category": "Object",
}

import bpy

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
    import importlib

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
