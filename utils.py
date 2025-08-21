import bpy
import re

# --- Shot, Scene, and Timeline Helpers ---

def get_current_shot_info(context):
    """
    Determines the current shot from timeline markers bound to cameras.
    Parses marker names like 'CAM-SC17-SH180' to extract shot details.
    Caches the result per frame to avoid redundant calculations.
    """
    current_frame = context.scene.frame_current

    # Simple caching mechanism
    if hasattr(bpy.context.scene, "_advcopy_cache") and \
       bpy.context.scene._advcopy_cache.get("frame") == current_frame:
        return bpy.context.scene._advcopy_cache.get("shot_info")

    markers = sorted(
        [m for m in context.scene.timeline_markers if m.camera], key=lambda m: m.frame
    )
    if not markers:
        return None

    current_shot_marker = None
    shot_end_frame = context.scene.frame_end

    for i, marker in enumerate(markers):
        start_frame = marker.frame
        end_frame = markers[i + 1].frame - 1 if i + 1 < len(markers) else context.scene.frame_end
        if start_frame <= current_frame <= end_frame:
            current_shot_marker = marker
            shot_end_frame = end_frame
            break

    if not current_shot_marker:
        return None

    match = re.match(r"CAM-(SC\d+)-(SH\d+)", current_shot_marker.name, re.IGNORECASE)
    if not match:
        return None

    shot_info = {
        "name": current_shot_marker.name,
        "start": current_shot_marker.frame,
        "end": shot_end_frame,
        "scene_str": match.group(1).upper(),
        "shot_str": match.group(2).upper(),
    }

    # Store in cache
    bpy.context.scene._advcopy_cache = {"frame": current_frame, "shot_info": shot_info}
    return shot_info


def get_scene_frame_range(context, scene_str):
    """
    Calculates the full frame range for a given scene by finding the
    earliest start and latest end frame among all its associated shot markers.
    """
    scene_markers = [
        m for m in context.scene.timeline_markers
        if m.camera and f"-{scene_str.upper()}-" in m.name.upper()
    ]
    if not scene_markers:
        return None

    scene_markers.sort(key=lambda m: m.frame)
    all_markers = sorted([m for m in context.scene.timeline_markers if m.camera], key=lambda m: m.frame)

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


def get_current_env_name(context):
    """
    Determines the current environment name by parsing it from the top-level
    collection of the current scene. e.g., '+SC19-APOLLO_CRASH+' -> 'APOLLO_CRASH'.
    """
    shot_info = get_current_shot_info(context)
    if not shot_info:
        return None

    scene_coll = find_top_level_scene_collection_by_str(shot_info['scene_str'])
    if not scene_coll:
        return None

    # Match against '+SC<id>-<env_name>+'
    match = re.match(r"\+SC\d+-(.+)\+", scene_coll.name)
    if match:
        return match.group(1)
    return None

# --- Collection Management Helpers ---

def get_or_create_collection(parent_collection, child_name):
    """
    Gets a child collection by name. If it doesn't exist, it creates and links it.
    """
    if child_name in parent_collection.children:
        return parent_collection.children[child_name]
    else:
        new_coll = bpy.data.collections.new(name=child_name)
        parent_collection.children.link(new_coll)
        return new_coll

def find_all_scene_collections():
    """
    Finds all top-level scene collections, identified by `+SC##-<env_name>+`
    and having no collection parents.
    """
    # A top-level collection is one that is not a child of any other collection.
    # We can find these by checking which collections in the scene's master collection
    # are also present in the global bpy.data.collections.
    root_collections = {c.name for c in bpy.context.scene.collection.children}

    scene_colls = []
    for coll_name in root_collections:
        coll = bpy.data.collections.get(coll_name)
        if coll and coll.name.startswith("+SC") and coll.name.endswith("+"):
            scene_colls.append(coll)
    return scene_colls


def find_top_level_scene_collection_by_str(scene_str):
    """
    Finds a top-level scene collection that matches the scene string, e.g., "SC17".
    """
    all_scenes = find_all_scene_collections()
    for coll in all_scenes:
        if coll.name.startswith(f"+{scene_str}-"):
            return coll
    return None

# --- Object Helpers ---

def get_base_name(full_name):
    """Strips common suffixes like '-P', '-P-SCENE', etc., to get the asset's base name."""
    return re.split(r'[-.]P($|\-)', full_name)[0]

def link_and_unlink_from_others(obj, target_collection, other_collections):
    """Links an object to a target collection and unlinks it from all others."""
    # First, link to the new collection.
    if obj.name not in target_collection.objects:
        target_collection.objects.link(obj)
    # Then, unlink from all other collections it might be in.
    for coll in other_collections:
        if coll != target_collection and obj.name in coll.objects:
            coll.objects.unlink(obj)

def toggle_object_visibility(obj, frame_range, hide):
    """
    Keys the visibility of an object (viewport and render) to be on or off
    for a specific frame range using stepped interpolation.
    """
    start_frame, end_frame = frame_range
    if not obj.animation_data:
        obj.animation_data_create()

    for prop in ["hide_viewport", "hide_render"]:
        # Ensure the property is not already keyed in a conflicting way
        if obj.animation_data.action and obj.animation_data.action.fcurves.find(prop):
            fcurve = obj.animation_data.action.fcurves.find(prop)
        else:
            fcurve = obj.animation_data.action.fcurves.new(data_path=prop)

        # Values: hide=True means value is 1. hide=False means value is 0.
        val_hidden = 1.0 if hide else 0.0
        val_visible = 0.0 if hide else 1.0

        # Add keyframes
        keys = [
            (start_frame - 1, val_visible),
            (start_frame, val_hidden),
            (end_frame, val_hidden),
            (end_frame + 1, val_visible)
        ]

        for frame, val in keys:
            fcurve.keyframe_points.insert(frame, val).interpolation = 'CONSTANT'
        fcurve.update()

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
    Diagnoses the operation type (MODEL, VFX, ACTOR, PROP) by checking the
    object's collection hierarchy. Defaults to 'MODEL'.
    """
    _parent_cache.clear()
    all_colls = bpy.data.collections
    for coll in obj.users_collection:
        current_coll = coll
        for _ in range(32): # Safety break
            if not current_coll: break
            name = current_coll.name.upper()
            if "VFX" in name: return "VFX"
            if "MODEL" in name or "ART" in name: return "MODEL"
            if "PROP" in name: return "PROP"
            if "ACTOR" in name: return "ACTOR"
            current_coll = find_parent_collection(current_coll, all_colls)
    return "MODEL"

# --- Context-Aware Poll Helpers ---

def is_in_collection_type(obj, prefix, midfix=""):
    """Generic helper to check if an object is in a collection matching a pattern."""
    for coll in obj.users_collection:
        if coll.name.startswith(prefix) and midfix in coll.name:
            return True
    return False

def is_in_loc_collection(obj):
    return is_in_collection_type(obj, "MODEL-LOC-") or \
           is_in_collection_type(obj, "VFX-LOC-")

def is_in_env_collection(obj):
    return is_in_collection_type(obj, "MODEL-ENV-") or \
           is_in_collection_type(obj, "VFX-ENV-")

def is_in_scene_collection(obj):
    # Matches patterns like 'MODEL-SC19-APOLLO_CRASH'
    return any(re.match(r"(MODEL|VFX|ACTOR|PROP)-SC\d+-", c.name) for c in obj.users_collection)

# --- Specific Collection Finders ---

def get_source_collection(obj, coll_type):
    """Finds the specific source collection of an object (e.g., 'LOC', 'ENV')."""
    for coll in obj.users_collection:
        if f"-{coll_type}-" in coll.name:
            return coll
    return None

def find_shot_collection(context, scene_str, shot_str, op_type):
    """Finds or creates the target collection for a specific shot."""
    top_level_scene_coll = find_top_level_scene_collection_by_str(scene_str)
    if not top_level_scene_coll: return None
    base_name = top_level_scene_coll.name.strip("+")

    if op_type == "MODEL":
        art_col = get_or_create_collection(top_level_scene_coll, f"+ART-{base_name}+")
        shot_art_col = get_or_create_collection(art_col, f"SHOT-ART-{base_name}")
        return get_or_create_collection(shot_art_col, f"MODEL-{scene_str}-{shot_str}")
    elif op_type == "VFX":
        vfx_col = get_or_create_collection(top_level_scene_coll, f"+VFX-{base_name}+")
        shot_vfx_col = get_or_create_collection(vfx_col, f"SHOT-VFX-{base_name}")
        return get_or_create_collection(shot_vfx_col, f"VFX-{scene_str}-{shot_str}")
    elif op_type in ["ACTOR", "PROP"]:
        ani_col = get_or_create_collection(top_level_scene_coll, f"+ANI-{base_name}+")
        shot_ani_col = get_or_create_collection(ani_col, f"SHOT-ANI-{base_name}")
        return get_or_create_collection(shot_ani_col, f"{op_type}-{scene_str}-{shot_str}")
    return None

def find_scene_collection(top_level_scene_coll, op_type):
    """Finds or creates the scene-level collection."""
    if not top_level_scene_coll: return None
    base_name = top_level_scene_coll.name.strip("+")

    if op_type == "MODEL":
        art_col = get_or_create_collection(top_level_scene_coll, f"+ART-{base_name}+")
        return get_or_create_collection(art_col, f"MODEL-{base_name}")
    elif op_type == "VFX":
        vfx_col = get_or_create_collection(top_level_scene_coll, f"+VFX-{base_name}+")
        return get_or_create_collection(vfx_col, f"VFX-{base_name}")
    elif op_type in ["ACTOR", "PROP"]:
        ani_col = get_or_create_collection(top_level_scene_coll, f"+ANI-{base_name}+")
        return get_or_create_collection(ani_col, f"{op_type}-{base_name}")
    return None

def find_env_collection(env_name, op_type):
    """Finds or creates a specific ENV collection by name."""
    parent_coll_name = f"+ENV-{env_name}+"
    child_coll_name = f"{op_type}-ENV-{env_name}"

    # Find the top-level +ENV-... collection
    parent_coll = bpy.data.collections.get(parent_coll_name)
    if not parent_coll:
        parent_coll = bpy.data.collections.new(name=parent_coll_name)
        bpy.context.scene.collection.children.link(parent_coll)

    return get_or_create_collection(parent_coll, child_coll_name)

def find_all_env_collections(op_type):
    """Finds all `[op_type]-ENV-...` collections inside their `+ENV-...` parents."""
    env_colls = []
    for coll in bpy.data.collections:
        # Correctly find child collections like 'MODEL-ENV-forest'
        # inside parents like '+ENV-forest+'.
        if coll.name.startswith(f"{op_type}-ENV-"):
            # Verify it has a correctly named parent
            parent = find_parent_collection(coll, bpy.data.collections)
            if parent and parent.name.startswith("+ENV-"):
                env_colls.append(coll)
    return env_colls
