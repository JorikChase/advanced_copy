# operators.py
import bpy
from . import utils


class ADVCOPY_OT_copy_to_current_shot(bpy.types.Operator):
    """Copies object to the collection for the current shot, auto-detecting MODEL/VFX/ACTOR/PROP context"""

    bl_idname = "object.advcopy_copy_to_current_shot"
    bl_label = "Copy to Current Shot"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return (
            context.active_object is not None
            and utils.get_current_shot_info(context) is not None
        )

    def execute(self, context):
        shot_info = utils.get_current_shot_info(context)
        original_obj = context.active_object
        op_type = utils.get_contextual_op_type(original_obj)

        target_collection = utils.find_shot_collection(
            context, shot_info["scene_str"], shot_info["shot_str"], op_type
        )
        if not target_collection:
            self.report({"ERROR"}, f"Could not find target {op_type} shot collection.")
            return {"CANCELLED"}

        new_obj = original_obj.copy()
        if original_obj.data:
            new_obj.data = original_obj.data.copy()
        new_obj.animation_data_clear()

        # Use the new helper function to generate the unique name
        new_obj.name = utils.generate_new_name(original_obj, target_collection)

        target_collection.objects.link(new_obj)

        frame_range = (shot_info["start"], shot_info["end"])
        utils.toggle_object_visibility(original_obj, frame_range, hide=True)
        utils.toggle_object_visibility(new_obj, frame_range, hide=False)

        self.report(
            {"INFO"},
            f"({op_type}) Copied '{original_obj.name}' to shot '{shot_info['name']}'",
        )
        return {"FINISHED"}


class ADVCOPY_OT_copy_to_current_scene(bpy.types.Operator):
    """Copies object to the current scene's collection, auto-detecting MODEL/VFX/ACTOR/PROP context"""

    bl_idname = "object.advcopy_copy_to_current_scene"
    bl_label = "Copy to Current Scene"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return (
            context.active_object is not None
            and utils.get_current_shot_info(context) is not None
        )

    def execute(self, context):
        original_obj = context.active_object
        shot_info = utils.get_current_shot_info(context)
        scene_str = shot_info["scene_str"]
        op_type = utils.get_contextual_op_type(original_obj)

        top_level_coll = utils.find_top_level_scene_collection_by_str(scene_str)
        if not top_level_coll:
            self.report(
                {"ERROR"},
                f"Could not find top-level scene collection for '{scene_str}'.",
            )
            return {"CANCELLED"}

        target_collection = utils.find_scene_collection(top_level_coll, op_type)
        if not target_collection:
            self.report({"ERROR"}, f"Could not find the scene's {op_type} collection.")
            return {"CANCELLED"}

        frame_range = utils.get_scene_frame_range(context, scene_str)
        if not frame_range:
            self.report(
                {"WARNING"},
                f"No markers for scene '{scene_str}'. Cannot toggle visibility.",
            )
            return {"CANCELLED"}

        new_obj = original_obj.copy()
        if original_obj.data:
            new_obj.data = original_obj.data.copy()
        new_obj.animation_data_clear()

        # Use the new helper function to generate the unique name
        new_obj.name = utils.generate_new_name(original_obj, target_collection)
        target_collection.objects.link(new_obj)

        utils.toggle_object_visibility(original_obj, frame_range, hide=True)
        utils.toggle_object_visibility(new_obj, frame_range, hide=False)

        self.report(
            {"INFO"},
            f"({op_type}) Copied '{original_obj.name}' to '{target_collection.name}'",
        )
        return {"FINISHED"}


class ADVCOPY_OT_move_to_all_scenes(bpy.types.Operator):
    """Creates a copy in every scene's collection and removes original, auto-detecting context"""

    bl_idname = "object.advcopy_move_to_all_scenes"
    bl_label = "Move Unique Copies to Each Scene"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return (
            context.active_object is not None
            and len(utils.find_all_scene_collections()) > 0
        )

    def execute(self, context):
        original_obj = context.active_object
        op_type = utils.get_contextual_op_type(original_obj)
        scene_collections = utils.find_all_scene_collections()
        if not scene_collections:
            self.report(
                {"WARNING"}, "No top-level scene collections (+SC##-...) found."
            )
            return {"CANCELLED"}

        copies_made = 0
        for scene_coll in scene_collections:
            target_coll = utils.find_scene_collection(scene_coll, op_type)
            if not target_coll:
                self.report(
                    {"WARNING"},
                    f"Skipping '{scene_coll.name}', no {op_type} collection.",
                )
                continue

            new_obj = original_obj.copy()
            if original_obj.data:
                new_obj.data = original_obj.data.copy()
            # Use the new helper function to generate the unique name
            new_obj.name = utils.generate_new_name(original_obj, target_coll)
            target_coll.objects.link(new_obj)
            copies_made += 1

        if copies_made > 0:
            bpy.data.objects.remove(original_obj, do_unlink=True)
            self.report(
                {"INFO"},
                f"({op_type}) Moved '{original_obj.name}' into {copies_made} scene(s).",
            )
        else:
            self.report({"ERROR"}, "Failed to create any copies. Original not removed.")
            return {"CANCELLED"}
        return {"FINISHED"}


class ADVCOPY_OT_copy_to_env(bpy.types.Operator):
    """Copies object from a LOC collection to all ENV collections, auto-detecting MODEL/VFX"""

    bl_idname = "object.advcopy_copy_to_env"
    bl_label = "Copy to All Enviros"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj:
            return False

        source_model = utils.find_source_loc_collection(obj, "MODEL")
        source_vfx = utils.find_source_loc_collection(obj, "VFX")

        if not (source_model or source_vfx):
            return False

        op_type = "MODEL" if source_model else "VFX"
        return len(utils.find_all_env_collections(op_type)) > 0

    def execute(self, context):
        original_obj = context.active_object

        source_model_coll = utils.find_source_loc_collection(original_obj, "MODEL")
        source_vfx_coll = utils.find_source_loc_collection(original_obj, "VFX")

        if source_model_coll:
            op_type = "MODEL"
            source_coll = source_model_coll
        elif source_vfx_coll:
            op_type = "VFX"
            source_coll = source_vfx_coll
        else:
            self.report(
                {"ERROR"},
                "Source object not in a valid LOC-MODEL or LOC-VFX collection.",
            )
            return {"CANCELLED"}

        target_env_colls = utils.find_all_env_collections(op_type)
        if not target_env_colls:
            self.report({"WARNING"}, f"No ENV-{op_type} collections found.")
            return {"CANCELLED"}

        copies_made = 0
        for env_coll in target_env_colls:
            new_obj = original_obj.copy()
            if original_obj.data:
                new_obj.data = original_obj.data.copy()
            # Use the new helper function to generate the unique name
            new_obj.name = utils.generate_new_name(original_obj, env_coll)

            env_coll.objects.link(new_obj)
            copies_made += 1

        if copies_made > 0:
            # Unlink the original object instead of removing it from all collections
            source_coll.objects.unlink(original_obj)
            self.report(
                {"INFO"},
                f"({op_type}) Copied '{original_obj.name}' to {copies_made} ENV collection(s).",
            )
        else:
            self.report({"ERROR"}, "Failed to create any copies. Original not moved.")
            return {"CANCELLED"}
        return {"FINISHED"}


# A tuple containing all operator classes in this file,
# to be imported by __init__.py for registration.
classes = (
    ADVCOPY_OT_copy_to_current_shot,
    ADVCOPY_OT_copy_to_current_scene,
    ADVCOPY_OT_move_to_all_scenes,
    ADVCOPY_OT_copy_to_env,
)
