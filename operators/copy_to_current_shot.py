import bpy
from ..core import shot_utils, collection_utils, object_utils

class ADVCOPY_OT_copy_to_current_shot(bpy.types.Operator):
    """Copies object to the collection for the current shot, auto-detecting MODEL/VFX context and keying visibility"""
    bl_idname = "object.advcopy_copy_to_current_shot"
    bl_label = "Copy to Current Shot"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Operator can only run if there is an active object and we are in a defined shot
        return context.active_object is not None and shot_utils.get_current_shot_info(context) is not None

    def execute(self, context):
        shot_info = shot_utils.get_current_shot_info(context)
        # This poll should prevent shot_info from being None, but we assert for safety
        assert shot_info is not None, "Could not determine current shot info"

        original_obj = context.active_object
        op_type = collection_utils.get_contextual_op_type(original_obj)

        target_collection = collection_utils.find_shot_collection(
            shot_info['scene_str'], shot_info['shot_str'], op_type
        )
        if not target_collection:
            self.report({'ERROR'}, f"Could not find or create target {op_type} shot collection.")
            return {'CANCELLED'}

        # Create a full copy of the object and its data
        new_obj = original_obj.copy()
        if original_obj.data:
            new_obj.data = original_obj.data.copy()
        new_obj.animation_data_clear() # Clear existing animation
        new_obj.name = f"{original_obj.name}.{shot_info['scene_str']}.{shot_info['shot_str']}"

        # Link the new object to the target collection
        target_collection.objects.link(new_obj)

        # Keyframe visibility
        frame_range = (shot_info['start'], shot_info['end'])
        object_utils.toggle_object_visibility(original_obj, frame_range, hide=True)
        object_utils.toggle_object_visibility(new_obj, frame_range, hide=False)

        self.report({'INFO'}, f"({op_type}) Copied '{original_obj.name}' to shot '{shot_info['name']}'")
        return {'FINISHED'}

