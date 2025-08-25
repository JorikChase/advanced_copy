import bpy
import re

# --- Shot, Scene, and Timeline Helpers ---


def get_current_shot_info(context):
    """
    Determines the current shot from timeline markers bound to cameras.
    Parses marker names like 'CAM-SC17-SH180' to extract shot details.
    """
    current_frame = context.scene.frame_current
    # Filter for markers that have a camera bound to them
    markers = sorted(
        [m for m in context.scene.timeline_markers if m.camera], key=lambda m: m.frame
    )

    if not markers:
        return None

    current_shot_marker = None
    shot_end_frame = context.scene.frame_end

    # Find which shot range the current frame is in
    for i, marker in enumerate(markers):
        start_frame = marker.frame
        # The end frame is one frame before the next marker, or the scene end
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

    # Parse the marker name using regex to get SC and SH identifiers
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
        # Find all markers belonging to the specified scene
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

    # Determine the end frame of the scene's very last shot
    try:
        last_marker_index = all_markers.index(last_shot_marker)
        if last_marker_index + 1 < len(all_markers):
            end_frame = all_markers[last_marker_index + 1].frame - 1
    except ValueError:
        # This shot is the last one in the timeline
        pass

    return (start_frame, end_frame)


# --- Collection Management Helpers ---


def get_env_name_from_scene_collection(scene_coll):
    """
    Extracts the environment/local name from a scene collection name.
    e.g., from '+SC17-APOLLO_CRASH+' it returns 'APOLLO_CRASH'.
    """
    if not scene_coll:
        return None
    try:
        # e.g., "+SC17-APOLLO_CRASH+" -> "SC17-APOLLO_CRASH"
        base_name = scene_coll.name.strip('+')
        # e.g., "SC17-APOLLO_CRASH" -> ["SC17", "APOLLO_CRASH"]
        parts = base_name.split('-', 1)
        if len(parts) > 1:
            return parts[1]
    except Exception:
        # In case of unexpected naming, return None
        return None
    return None


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
    A scene collection is identified by the naming convention `+SC##-<env_name>+`
    and having no collection parents.
    """
    scene_colls = []
    # Create a set of all collections that are children of another collection
    nested_collections = set()
    for coll in bpy.data.collections:
        for child in coll.children:
            nested_collections.add(child.name)

    # Find collections that match the pattern and are not in the nested set
    for coll in bpy.data.collections:
        if (
            coll.name.startswith("+SC")
            and coll.name.endswith("+")
            and coll.name not in nested_collections
        ):
            scene_colls.append(coll)
    return scene_colls


def find_top_level_scene_collection_by_str(scene_str):
    """
    Finds a top-level scene collection from all .blend file data that matches
    the scene string, e.g., "SC17".
    """
    all_scenes = find_all_scene_collections()
    for coll in all_scenes:
        # Match against `+SC17-...`
        if coll.name.startswith(f"+{scene_str}-"):
            return coll
    return None


# --- Object Helpers ---


def toggle_object_visibility(obj, frame_range, hide):
    """
    Keys the visibility of an object to be on or off for a specific frame range.
    This keys hide_viewport and hide_render properties.
    """
    start_frame, end_frame = frame_range
    if not obj.animation_data:
        obj.animation_data_create()

    # Set keyframes for visibility properties
    for prop in ["hide_viewport", "hide_render"]:
        # Frame before the range: visible
        setattr(obj, prop, not hide)
        obj.keyframe_insert(data_path=prop, frame=start_frame - 1)
        # First frame of the range: hidden
        setattr(obj, prop, hide)
        obj.keyframe_insert(data_path=prop, frame=start_frame)
        # Last frame of the range: hidden
        obj.keyframe_insert(data_path=prop, frame=end_frame)
        # Frame after the range: visible
        setattr(obj, prop, not hide)
        obj.keyframe_insert(data_path=prop, frame=end_frame + 1)


# --- Context Diagnosis & Collection Finders ---

_parent_cache = {}


def find_parent_collection(child_coll, collections):
    """Helper to find the parent of a collection with caching for performance."""
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
    Auto-diagnoses the operation type (MODEL, VFX, ACTOR, PROP) by checking the
    object's collection hierarchy, including parents and grandparents.
    Defaults to 'MODEL' if no specific context can be found.
    """
    _parent_cache.clear()  # Clear cache for each new diagnosis
    all_colls = bpy.data.collections
    for coll in obj.users_collection:
        current_coll = coll
        # Walk up the hierarchy to find a context keyword
        for _ in range(32):  # Safety break for deep or recursive hierarchies
            if not current_coll:
                break
            name = current_coll.name.upper()
            # Check for specific flags in order of precedence
            if "VFX" in name:
                return "VFX"
            if "MODEL" in name or "ART" in name:
                return "MODEL"
            if "PROP" in name:
                return "PROP"
            if "ACTOR" in name:
                return "ACTOR"
            # Find the parent of the current collection for the next iteration
            current_coll = find_parent_collection(current_coll, all_colls)
    return "MODEL"  # Default fallback


def find_shot_collection(context, scene_str, shot_str, op_type):
    """
    Finds or creates the target collection for a specific shot (MODEL, VFX, ACTOR, or PROP)
    based on the new, correct hierarchy from the layout_suite addon.
    """
    top_level_scene_coll = find_top_level_scene_collection_by_str(scene_str)
    if not top_level_scene_coll:
        print(
            f"AdvCopy Error: Could not find top-level scene collection for '{scene_str}'"
        )
        return None

    # e.g., "SC17-APOLLO_CRASH" from "+SC17-APOLLO_CRASH+"
    base_name = top_level_scene_coll.name.strip("+")

    if op_type == "MODEL":
        # Path: +ART-SC... -> SHOT-ART-... -> MODEL-SC##-SH###
        art_col = get_or_create_collection(top_level_scene_coll, f"+ART-{base_name}+")
        shot_art_col = get_or_create_collection(art_col, f"SHOT-ART-{base_name}")
        return get_or_create_collection(shot_art_col, f"MODEL-{scene_str}-{shot_str}")

    elif op_type == "VFX":
        # Path: +VFX-SC... -> SHOT-VFX-... -> VFX-SC##-SH###
        vfx_col = get_or_create_collection(top_level_scene_coll, f"+VFX-{base_name}+")
        shot_vfx_col = get_or_create_collection(vfx_col, f"SHOT-VFX-{base_name}")
        return get_or_create_collection(shot_vfx_col, f"VFX-{scene_str}-{shot_str}")

    elif op_type in ["ACTOR", "PROP"]:
        # Path: +ANI-SC... -> SHOT-ANI-... -> [ACTOR/PROP]-SC##-SH###
        ani_col = get_or_create_collection(top_level_scene_coll, f"+ANI-{base_name}+")
        shot_ani_col = get_or_create_collection(ani_col, f"SHOT-ANI-{base_name}")
        return get_or_create_collection(
            shot_ani_col, f"{op_type}-{scene_str}-{shot_str}"
        )

    return None


def find_scene_collection(top_level_scene_coll, op_type):
    """
    Finds or creates the scene-level collection (MODEL, VFX, ACTOR, or PROP)
    based on the new, correct hierarchy from the layout_suite addon.
    """
    if not top_level_scene_coll:
        return None

    # e.g., "SC17-APOLLO_CRASH" from "+SC17-APOLLO_CRASH+"
    base_name = top_level_scene_coll.name.strip("+")

    if op_type == "MODEL":
        # Path: +ART-SC... -> MODEL-SC##-<env_name>
        art_col = get_or_create_collection(top_level_scene_coll, f"+ART-{base_name}+")
        return get_or_create_collection(art_col, f"MODEL-{base_name}")

    elif op_type == "VFX":
        # Path: +VFX-SC... -> VFX-SC##-<env_name>
        vfx_col = get_or_create_collection(top_level_scene_coll, f"+VFX-{base_name}+")
        return get_or_create_collection(vfx_col, f"VFX-{base_name}")

    elif op_type in ["ACTOR", "PROP"]:
        # Path: +ANI-SC... -> [ACTOR/PROP]-SC##-<env_name>
        ani_col = get_or_create_collection(top_level_scene_coll, f"+ANI-{base_name}+")
        return get_or_create_collection(ani_col, f"{op_type}-{base_name}")

    return None


def find_source_loc_collection(obj, op_type):
    """Finds the source `LOC-...-[TYPE]` collection of an object."""
    suffix = f"-{op_type}"
    for coll in obj.users_collection:
        # Check if the collection name matches the LOC pattern
        if coll.name.endswith(suffix) and coll.name.startswith("LOC-"):
            # Verify its parent is the main `+LOC-...` collection
            for parent_coll in bpy.data.collections:
                if coll.name in parent_coll.children and parent_coll.name.startswith(
                    "+LOC-"
                ):
                    return coll
    return None


def find_all_env_collections(op_type):
    """Finds all `...-ENV-...-[TYPE]` collections inside their `+ENV-...` parents."""
    env_colls = []
    for parent_coll in bpy.data.collections:
        if parent_coll.name.startswith("+ENV-"):
            # e.g., parent is "+ENV-APOLLO_CRASH+"
            base_name = parent_coll.name.strip('+') # "ENV-APOLLO_CRASH"
            expected_coll_name = f"{op_type}-{base_name}" # "MODEL-ENV-APOLLO_CRASH"
            if expected_coll_name in parent_coll.children:
                env_colls.append(parent_coll.children[expected_coll_name])
    return env_colls


def find_env_collection_by_name(env_name, op_type):
    """Finds a specific `...-ENV-[NAME]` collection by the environment name."""
    parent_coll_name = f"+ENV-{env_name}+"
    if parent_coll_name not in bpy.data.collections:
        return None

    parent_coll = bpy.data.collections[parent_coll_name]
    base_name = parent_coll.name.strip('+')

    expected_coll_name = f"{op_type}-{base_name}"

    if expected_coll_name in parent_coll.children:
        return parent_coll.children[expected_coll_name]

    return None
