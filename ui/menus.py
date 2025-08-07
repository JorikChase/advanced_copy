import bpy
from ..operators import (
    copy_to_current_shot,
    copy_to_current_scene,
    move_to_all_scenes,
    copy_to_env,
)

class ADVCOPY_MT_scene_menu(bpy.types.Menu):
    """Sub-menu for Scene-level operations."""
    bl_label = "Scene Operations"
    bl_idname = "OBJECT_MT_advcopy_scene_menu"

    def draw(self, context):
        layout = self.layout
        layout.operator(copy_to_current_scene.ADVCOPY_OT_copy_to_current_scene.bl_idname, icon='SCENE_DATA')
        layout.operator(move_to_all_scenes.ADVCOPY_OT_move_to_all_scenes.bl_idname, icon='COPY_ID')

def draw_main_menu(self, context):
    """Draws the main entry point for the addon in the Object Context Menu."""
    layout = self.layout
    layout.separator()
    # Main operators
    layout.operator(copy_to_current_shot.ADVCOPY_OT_copy_to_current_shot.bl_idname, icon='SEQUENCE')
    layout.operator(copy_to_env.ADVCOPY_OT_copy_to_env.bl_idname, icon='WORLD')
    # Sub-menu
    layout.menu(ADVCOPY_MT_scene_menu.bl_idname, icon='OUTLINER_COLLECTION')


