import bpy
import re

# --- Shot, Scene, and Timeline Helpers ---


def get_current_shot_info(context):
    """
    Determines the current shot from timeline markers bound to cameras.
    Parses marker names like 'CAM-SC17-SH180-FLAT' to extract shot details.
    """
    current_frame = context.scene.frame_current
    markers = sorted(
        [m for m in context.scene.timeline_markers if m.camera], key=lambda m: m.frame
    )

    if not markers:
        return None

    current_shot_marker = None
    shot_end_frame = context.scene.frame_end

    for i, marker in enumerate(markers):
        start_frame = marker.frame
        if i + 1 < len(markers):
            end_frame = markers[i + 1].frame - 1
        else:
            end_frame = context.scene.frame_end

        if start_frame <= current_frame <= end_frame:
            current_shot_marker = marker
            shot_end_frame = end_frame
            break

    if not current_shot_marker:
        return None

    match = re.match(r"CAM-(SC\d+)-(SH\d+)", current_shot_marker.name, re.IGNORECASE)
    if not match:
        return None

    scene_str = match.group(1).upper()
    shot_str = match.group(2).upper()

    return {
        "name": current_shot_marker.name,
        "start": current_shot_marker.frame,
        "end": shot_end_frame,
        "scene_str": scene_str,
        "shot_str": shot_str,
    }


def get_scene_frame_range(context, scene_str):
    """
    Calculates the full frame range for a given scene by finding the
    earliest start and latest end frame among all its associated shot markers.
    """
    scene_markers = []
    for marker in context.scene.timeline_markers:
        if marker.camera and f"-{scene_str.upper()}-" in marker.name.upper():
            scene_markers.append(marker)

    if not scene_markers:
        return None

    scene_markers.sort(key=lambda m: m.frame)
    all_markers = sorted(
        [m for m in context.scene.timeline_markers if m.camera], key=lambda m: m.frame
    )

    start_frame = scene_markers[0].frame
    last_shot_marker = scene_markers[-1]
    end_frame = context.scene.frame_end

    try:
        last_marker_index = all_markers.index(last_shot_marker)
        if last_marker_index + 1 < len(all_markers):
            end_frame = all_markers[last_marker_index + 1].frame - 1
    except ValueError:
        pass

    return (start_frame, end_frame)


# --- Collection Management Helpers ---


def get_or_create_collection(parent_collection, child_name):
    """
    Gets a child collection by name from a parent. If it doesn't exist,
    it creates and links it.
    """
    if child_name in parent_collection.children:
        return parent_collection.children[child_name]
    else:
        new_coll = bpy.data.collections.new(name=child_name)
        parent_collection.children.link(new_coll)
        return new_coll


def find_all_scene_collections():
    """
    Finds all top-level scene collections in the entire .blend file data.
    A scene collection is identified by the naming convention `+SC##-...`
    and having no collection parents.
    """
    scene_colls = []
    nested_collections = set()
    for coll in bpy.data.collections:
        for child in coll.children:
            nested_collections.add(child.name)

    for coll in bpy.data.collections:
        if (
            coll.name.startswith("+SC")
            and coll.name.endswith("+")
            and coll.name not in nested_collections
        ):
            if all(sub not in coll.name for sub in ["-ART", "-MODEL", "-SHOT", "-VFX"]):
                scene_colls.append(coll)
    return scene_colls


def find_top_level_scene_collection_by_str(scene_str):
    """
    Finds a top-level scene collection from all .blend file data that matches the scene string, e.g., "SC17".
    """
    all_scenes = find_all_scene_collections()
    for coll in all_scenes:
        if coll.name.startswith(f"+{scene_str}-"):
            return coll
    return None


# --- Object Helpers ---


def toggle_object_visibility(obj, frame_range, hide):
    """
    Keys the visibility of an object to be on or off for a specific frame range.
    """
    start_frame, end_frame = frame_range
    if not obj.animation_data:
        obj.animation_data_create()

    for prop in ["hide_viewport", "hide_render"]:
        setattr(obj, prop, not hide)
        obj.keyframe_insert(data_path=prop, frame=start_frame - 1)
        setattr(obj, prop, hide)
        obj.keyframe_insert(data_path=prop, frame=start_frame)
        obj.keyframe_insert(data_path=prop, frame=end_frame)
        setattr(obj, prop, not hide)
        obj.keyframe_insert(data_path=prop, frame=end_frame + 1)


# --- Context Diagnosis & Collection Finders ---

_parent_cache = {}


def find_parent_collection(child_coll, collections):
    """Helper to find the parent of a collection with caching."""
    child_name = child_coll.name
    if child_name in _parent_cache:
        return _parent_cache[child_name]
    for parent_coll in collections:
        if child_name in parent_coll.children:
            _parent_cache[child_name] = parent_coll
            return parent_coll
    _parent_cache[child_name] = None
    return None


def get_contextual_op_type(obj):
    """
    Auto-diagnoses if an object is in a MODEL or VFX context by checking its collections.
    Defaults to 'MODEL' if no context can be found.
    """
    _parent_cache.clear()
    all_colls = bpy.data.collections
    for coll in obj.users_collection:
        current_coll = coll
        for _ in range(32):  # Safety break for deep or recursive hierarchies
            if not current_coll:
                break
            name = current_coll.name.upper()
            if "VFX" in name:
                return "VFX"
            if "MODEL" in name or "ART" in name:
                return "MODEL"
            current_coll = find_parent_collection(current_coll, all_colls)
    return "MODEL"


def find_shot_collection(context, scene_str, shot_str, op_type):
    """
    Finds or creates the target collection for a specific shot (MODEL or VFX).
    """
    top_level_scene_coll = find_top_level_scene_collection_by_str(scene_str)
    if not top_level_scene_coll:
        print(
            f"AdvCopy Error: Could not find top-level scene collection for '{scene_str}'"
        )
        return None
    location_name = "-".join(top_level_scene_coll.name.strip("+").split("-")[1:])
    if not location_name:
        return None

    if op_type == "MODEL":
        art_coll = get_or_create_collection(
            top_level_scene_coll, f"+{scene_str}-{location_name}-ART+"
        )
        art_shot_coll = get_or_create_collection(
            art_coll, f"{scene_str}-{location_name}-ART-SHOT"
        )
        shot_art_coll = get_or_create_collection(
            art_shot_coll, f"{scene_str}-{shot_str}-ART"
        )
        return get_or_create_collection(shot_art_coll, f"MODEL-{scene_str}-{shot_str}")
    elif op_type == "VFX":
        vfx_coll = get_or_create_collection(
            top_level_scene_coll, f"+{scene_str}-{location_name}-VFX+"
        )
        vfx_shot_coll = get_or_create_collection(
            vfx_coll, f"{scene_str}-{location_name}-VFX-SHOT"
        )
        return get_or_create_collection(vfx_shot_coll, f"{scene_str}-{shot_str}-VFX")
    return None


def find_scene_collection(top_level_scene_coll, op_type):
    """
    Finds or creates the scene-level collection (MODEL or VFX).
    """
    if not top_level_scene_coll:
        return None
    try:
        parts = top_level_scene_coll.name.strip("+").split("-")
        scene_str, location_name = parts[0], "-".join(parts[1:])
    except IndexError:
        return None

    if op_type == "MODEL":
        art_coll = get_or_create_collection(
            top_level_scene_coll, f"+{scene_str}-{location_name}-ART+"
        )
        return get_or_create_collection(art_coll, f"{scene_str}-{location_name}-MODEL")
    elif op_type == "VFX":
        vfx_parent = get_or_create_collection(
            top_level_scene_coll, f"+{scene_str}-{location_name}-VFX+"
        )
        return get_or_create_collection(vfx_parent, f"{scene_str}-{location_name}-VFX")
    return None


def find_source_loc_collection(obj, op_type):
    """Finds the source `+LOC-.../LOC-...-[TYPE]` collection of an object."""
    suffix = f"-{op_type}"
    for coll in obj.users_collection:
        if coll.name.endswith(suffix) and coll.name.startswith("LOC-"):
            for parent_coll in bpy.data.collections:
                if coll.name in parent_coll.children and parent_coll.name.startswith(
                    "+LOC-"
                ):
                    return coll
    return None


def find_all_env_collections(op_type):
    """Finds all `+ENV-.../ENV-...-[TYPE]` collections."""
    suffix = f"-{op_type}"
    env_colls = []
    for parent_coll in bpy.data.collections:
        if parent_coll.name.startswith("+ENV-"):
            env_name = parent_coll.name.strip("+").replace("ENV-", "", 1)
            expected_coll_name = f"ENV-{env_name}{suffix}"
            if expected_coll_name in parent_coll.children:
                env_colls.append(parent_coll.children[expected_coll_name])
    return env_colls
