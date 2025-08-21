import bpy
from . import operators


class ADVCOPY_MT_main_menu(bpy.types.Menu):
    """The main menu for all Advanced Copy operations."""
    bl_label = "Advanced Copy"
    bl_idname = "OBJECT_MT_advcopy_main_menu"

    def draw(self, context):
        layout = self.layout

        # --- Group for operations starting from a LOCATION collection ---
        layout.label(text="From Location [A -> B]")
        layout.operator(operators.ADVCOPY_OT_copy_from_loc_to_current_env.bl_idname, icon="FORWARD")
        layout.operator(operators.ADVCOPY_OT_move_from_loc_to_all_envs.bl_idname, icon="COPY_ID")
        layout.separator()

        # --- Group for operations starting from an ENVIRONMENT collection ---
        layout.label(text="From Environment [B -> C]")
        layout.operator(operators.ADVCOPY_OT_copy_to_current_scene.bl_idname, icon="SCENE_DATA")
        layout.operator(operators.ADVCOPY_OT_move_to_all_scenes.bl_idname, icon="MOD_MULTIRES")
        layout.separator()

        # --- Group for operations starting from a SCENE collection ---
        layout.label(text="From Scene [C -> D]")
        layout.operator(operators.ADVCOPY_OT_copy_to_current_shot.bl_idname, icon="SEQUENCE")


def draw_main_menu(self, context):
    """
    The main drawing function to be appended to Blender's UI.
    This function adds the main menu to the object context menu.
    """
    layout = self.layout
    layout.separator()
    # We refer to our custom menu by its bl_idname string.
    layout.menu(ADVCOPY_MT_main_menu.bl_idname, icon="COPYDOWN")


# A tuple containing all menu classes in this file,
# to be imported by __init__.py for registration.
classes = (ADVCOPY_MT_main_menu,)
