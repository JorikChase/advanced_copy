import bpy
from . import operators


class ADVCOPY_MT_scene_menu(bpy.types.Menu):
    bl_label = "Scene Operations"
    bl_idname = "OBJECT_MT_advcopy_scene_menu"

    def draw(self, context):
        layout = self.layout
        # We refer to operators by their bl_idname string, not the class itself.
        layout.operator(
            operators.ADVCOPY_OT__copy_to_current_scene.bl_idname, icon="SCENE_DATA"
        )
        layout.operator(
            operators.ADVCOPY_OT_move_to_all_scenes.bl_idname, icon="COPY_ID"
        )

class ADVCOPY_MT_env_menu(bpy.types.Menu):
    bl_label = "Enviro Operations"
    bl_idname = "OBJECT_MT_advcopy_env_menu"

    def draw(self, context):
        layout = self.layout
        layout.operator(
            operators.ADVCOPY_OT_move_to_all_envs.bl_idname, icon="COPY_ID"
        )
        layout.operator(
            operators.ADVCOPY_OT_copy_to_current_env.bl_idname, icon="WORLD_DATA"
        )


def draw_main_menu(self, context):
    """
    The main drawing function to be appended to Blender's UI.
    """
    layout = self.layout
    layout.separator()
    layout.operator(
        operators.ADVCOPY_OT_copy_to_current_shot.bl_idname, icon="SEQUENCE"
    )
    # We refer to our custom menus by their bl_idname string.
    layout.menu(ADVCOPY_MT_scene_menu.bl_idname, icon="OUTLINER_COLLECTION")
    layout.menu(ADVCOPY_MT_env_menu.bl_idname, icon="WORLD")


# A tuple containing all menu classes in this file,
# to be imported by __init__.py for registration.
classes = (
    ADVCOPY_MT_scene_menu,
    ADVCOPY_MT_env_menu,
)
