import bpy
from ..core import collection_utils

class ADVCOPY_OT_copy_to_env(bpy.types.Operator):
    """Copies an object from a LOC collection to all corresponding ENV collections, auto-detecting MODEL/VFX context"""
    bl_idname = "object.advcopy_copy_to_env"
    bl_label = "Copy from LOC to All Enviros"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj:
            return False

        # Check if the object is in a valid source collection
        source_model = collection_utils.find_source_loc_collection(obj, 'MODEL')
        source_vfx = collection_utils.find_source_loc_collection(obj, 'VFX')
        if not (source_model or source_vfx):
            return False

        # Determine op_type and check if any target ENV collections exist
        op_type = 'MODEL' if source_model else 'VFX'
        return len(collection_utils.find_all_env_collections(op_type)) > 0

    def execute(self, context):
        original_obj = context.active_object

        # Determine the operation type and source collection
        source_coll = collection_utils.find_source_loc_collection(original_obj, 'MODEL')
        op_type = 'MODEL'
        if not source_coll:
            source_coll = collection_utils.find_source_loc_collection(original_obj, 'VFX')
            op_type = 'VFX'

        if not source_coll:
            self.report({'ERROR'}, "Source object not in a valid LOC-MODEL or LOC-VFX collection.")
            return {'CANCELLED'}

        target_env_colls = collection_utils.find_all_env_collections(op_type)
        if not target_env_colls:
            self.report({'WARNING'}, f"No target ENV-{op_type} collections were found.")
            return {'CANCELLED'}

        copies_made = 0
        for env_coll in target_env_colls:
            new_obj = original_obj.copy()
            if original_obj.data:
                new_obj.data = original_obj.data.copy()
            
            # Generate a descriptive name for the copy
            try:
                env_name = env_coll.name.replace(f"-{op_type}", "").replace("ENV-", "")
                new_obj.name = f"{original_obj.name}.{env_name}"
            except Exception:
                new_obj.name = f"{original_obj.name}.ENV_COPY"

            env_coll.objects.link(new_obj)
            copies_made += 1

        if copies_made > 0:
            # Unlink the original object from its source collection, effectively moving it
            source_coll.objects.unlink(original_obj)
            # A check to see if the object has any other users, if not, remove it.
            if original_obj.users == 0:
                bpy.data.objects.remove(original_obj, do_unlink=True)
            self.report({'INFO'}, f"({op_type}) Copied '{original_obj.name}' to {copies_made} ENV collection(s) and removed from source.")
        else:
            self.report({'ERROR'}, "Failed to create any copies. Original object was not moved.")
            return {'CANCELLED'}
            
        return {'FINISHED'}

