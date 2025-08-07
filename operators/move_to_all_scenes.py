import bpy
from ..core import collection_utils

class ADVCOPY_OT_move_to_all_scenes(bpy.types.Operator):
    """Creates a unique copy in every scene's collection and removes the original, auto-detecting MODEL/VFX context"""
    bl_idname = "object.advcopy_move_to_all_scenes"
    bl_label = "Move Unique Copies to Each Scene"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and len(collection_utils.find_all_scene_collections()) > 0

    def execute(self, context):
        original_obj = context.active_object
        op_type = collection_utils.get_contextual_op_type(original_obj)
        scene_collections = collection_utils.find_all_scene_collections()

        if not scene_collections:
            self.report({'WARNING'}, "No top-level scene collections (+SC##-...) found.")
            return {'CANCELLED'}

        copies_made = 0
        for scene_coll in scene_collections:
            target_coll = collection_utils.find_scene_collection(scene_coll, op_type)
            if not target_coll:
                self.report({'WARNING'}, f"Skipping '{scene_coll.name}', no {op_type} collection found/created.")
                continue

            # Create a unique copy for this scene
            new_obj = original_obj.copy()
            if original_obj.data:
                new_obj.data = original_obj.data.copy()
            
            try:
                scene_str = scene_coll.name.strip('+').split('-')[0]
                new_obj.name = f"{original_obj.name}.{scene_str}"
            except IndexError:
                new_obj.name = f"{original_obj.name}.SCENE_COPY"

            target_coll.objects.link(new_obj)
            copies_made += 1

        if copies_made > 0:
            # Remove the original object after all copies are made
            bpy.data.objects.remove(original_obj, do_unlink=True)
            self.report({'INFO'}, f"({op_type}) Moved '{original_obj.name}' into {copies_made} scene(s).")
        else:
            self.report({'ERROR'}, "Failed to create any copies. Original object was not removed.")
            return {'CANCELLED'}
            
        return {'FINISHED'}

