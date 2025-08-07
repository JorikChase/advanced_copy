import bpy
from ..core import shot_utils, collection_utils, object_utils

class ADVCOPY_OT_copy_to_current_scene(bpy.types.Operator):
    """Copies object to the current scene's collection, auto-detecting MODEL/VFX context and keying visibility"""
    bl_idname = "object.advcopy_copy_to_current_scene"
    bl_label = "Copy to Current Scene"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and shot_utils.get_current_shot_info(context) is not None

    def execute(self, context):
        original_obj = context.active_object
        shot_info = shot_utils.get_current_shot_info(context)
        assert shot_info is not None, "Could not determine current shot info"
        
        scene_str = shot_info['scene_str']
        op_type = collection_utils.get_contextual_op_type(original_obj)

        top_level_coll = collection_utils.find_top_level_scene_collection_by_str(scene_str)
        if not top_level_coll:
            self.report({'ERROR'}, f"Could not find top-level scene collection for '{scene_str}'.")
            return {'CANCELLED'}

        target_collection = collection_utils.find_scene_collection(top_level_coll, op_type)
        if not target_collection:
            self.report({'ERROR'}, f"Could not find or create the scene's {op_type} collection.")
            return {'CANCELLED'}

        frame_range = shot_utils.get_scene_frame_range(context, scene_str)
        if not frame_range:
            self.report({'WARNING'}, f"No markers for scene '{scene_str}'. Cannot toggle visibility.")
            # We can still proceed with the copy, just without visibility keying.
            # Or cancel if visibility is critical. Let's proceed.
            # return {'CANCELLED'}

        # Create and link the new object
        new_obj = original_obj.copy()
        if original_obj.data:
            new_obj.data = original_obj.data.copy()
        new_obj.animation_data_clear()
        new_obj.name = f"{original_obj.name}.{scene_str}"
        target_collection.objects.link(new_obj)

        if frame_range:
            object_utils.toggle_object_visibility(original_obj, frame_range, hide=True)
            object_utils.toggle_object_visibility(new_obj, frame_range, hide=False)

        self.report({'INFO'}, f"({op_type}) Copied '{original_obj.name}' to '{target_collection.name}'")
        return {'FINISHED'}

