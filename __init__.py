bl_info = {
    "name": "Advanced Copy V4",
    "author": "iori, krutart, Gemini",
    "version": (4, 0, 1),
    "blender": (4, 0, 0),
    "location": "View3D > Object Context Menu",
    "description": "Automatically performs MODEL or VFX copy/move operations based on object context and a structured collection hierarchy.",
    "warning": "",
    "doc_url": "https://github.com/krutartstudio/blender", 
    "category": "Object",
}

# This is a reload-safe way to handle f5 multi-file addons.
if "bpy" in locals():
    import importlib
    if "core" in locals():
        importlib.reload(core.collection_utils)
        importlib.reload(core.object_utils)
        importlib.reload(core.shot_utils)
    if "operators" in locals():
        importlib.reload(operators.copy_to_current_shot)
        importlib.reload(operators.copy_to_current_scene)
        importlib.reload(operators.move_to_all_scenes)
        importlib.reload(operators.copy_to_env)
    if "ui" in locals():
        importlib.reload(ui.menus)


import bpy
from . import core
from . import operators
from . import ui


# --- Registration ---

classes = (
    operators.copy_to_current_shot.ADVCOPY_OT_copy_to_current_shot,
    operators.copy_to_current_scene.ADVCOPY_OT_copy_to_current_scene,
    operators.move_to_all_scenes.ADVCOPY_OT_move_to_all_scenes,
    operators.copy_to_env.ADVCOPY_OT_copy_to_env,
    ui.menus.ADVCOPY_MT_scene_menu,
)

def register():
    """Registers all addon classes and adds the menu to the UI."""
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_object_context_menu.append(ui.menus.draw_main_menu)

def unregister():
    """Unregisters all addon classes and removes the menu."""
    bpy.types.VIEW3D_MT_object_context_menu.remove(ui.menus.draw_main_menu)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()

