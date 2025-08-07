import bpy
from typing import Optional, List, Dict, Set

# --- Cache for Parent Lookups ---
_parent_cache: Dict[str, Optional[bpy.types.Collection]] = {}

def get_or_create_collection(parent_collection: bpy.types.Collection, child_name: str) -> bpy.types.Collection:
    """
    Gets a child collection by name from a parent. If it doesn't exist,
    it creates and links it.

    Args:
        parent_collection (bpy.types.Collection): The collection to search within or add to.
        child_name (str): The name of the child collection to find or create.

    Returns:
        bpy.types.Collection: The existing or newly created child collection.
    """
    assert parent_collection is not None, "Parent collection cannot be None"
    assert child_name, "Child name cannot be empty"

    if child_name in parent_collection.children:
        return parent_collection.children[child_name]
    else:
        new_coll = bpy.data.collections.new(name=child_name)
        parent_collection.children.link(new_coll)
        return new_coll

def find_parent_collection(child_coll: bpy.types.Collection, collections: List[bpy.types.Collection]) -> Optional[bpy.types.Collection]:
    """
    Helper to find the parent of a collection with caching to improve performance
    on repeated lookups within a single operation.

    Args:
        child_coll (bpy.types.Collection): The collection whose parent is to be found.
        collections (List[bpy.types.Collection]): A list of all collections to search through.

    Returns:
        Optional[bpy.types.Collection]: The parent collection, or None if not found.
    """
    child_name = child_coll.name
    if child_name in _parent_cache:
        return _parent_cache[child_name]

    for parent_coll in collections:
        if child_name in parent_coll.children:
            _parent_cache[child_name] = parent_coll
            return parent_coll

    _parent_cache[child_name] = None
    return None

def get_contextual_op_type(obj: bpy.types.Object) -> str:
    """
    Auto-diagnoses if an object is in a MODEL or VFX context by checking its collection hierarchy.
    Defaults to 'MODEL' if no specific context can be determined.

    Args:
        obj (bpy.types.Object): The object to diagnose.

    Returns:
        str: 'VFX' or 'MODEL'.
    """
    _parent_cache.clear()  # Clear cache for each new diagnosis
    all_colls = list(bpy.data.collections) # Convert to list for faster iteration if needed

    for coll in obj.users_collection:
        current_coll: Optional[bpy.types.Collection] = coll
        # Safety break for deep or recursive hierarchies
        for _ in range(32):
            if not current_coll:
                break
            name = current_coll.name.upper()
            if 'VFX' in name:
                return 'VFX'
            if 'MODEL' in name or 'ART' in name:
                return 'MODEL'
            current_coll = find_parent_collection(current_coll, all_colls)
    return 'MODEL'

def find_all_scene_collections() -> List[bpy.types.Collection]:
    """
    Finds all top-level scene collections in the entire .blend file data.
    A scene collection is identified by the naming convention `+SC##-...`
    and having no collection parents.

    Returns:
        List[bpy.types.Collection]: A list of all found top-level scene collections.
    """
    scene_colls: List[bpy.types.Collection] = []
    # Using a set for faster lookups
    nested_collections: Set[str] = {child.name for coll in bpy.data.collections for child in coll.children}

    for coll in bpy.data.collections:
        # A top-level collection is not in the set of nested collections
        if coll.name not in nested_collections and coll.name.startswith("+SC") and coll.name.endswith("+"):
             # Additional check to avoid matching intermediate collections like +SC...-ART+
            if all(sub not in coll.name for sub in ['-ART', '-MODEL', '-SHOT', '-VFX']):
                scene_colls.append(coll)
    return scene_colls

def find_top_level_scene_collection_by_str(scene_str: str) -> Optional[bpy.types.Collection]:
    """
    Finds a top-level scene collection from all .blend file data that matches the scene string.

    Args:
        scene_str (str): The scene identifier to search for (e.g., "SC17").

    Returns:
        Optional[bpy.types.Collection]: The matching collection, or None.
    """
    assert scene_str, "Scene string cannot be empty"
    all_scenes = find_all_scene_collections()
    for coll in all_scenes:
        # Check if the collection name starts with "+SC##-"
        if coll.name.startswith(f"+{scene_str.upper()}-"):
            return coll
    return None

def find_shot_collection(scene_str: str, shot_str: str, op_type: str) -> Optional[bpy.types.Collection]:
    """
    Finds or creates the target collection for a specific shot (MODEL or VFX).
    Structure: `+SC.../+-ART/SHOT/.../MODEL-...` or `+SC.../+-VFX/SHOT/...-VFX`

    Args:
        scene_str (str): The scene identifier (e.g., "SC17").
        shot_str (str): The shot identifier (e.g., "SH180").
        op_type (str): The operation type, 'MODEL' or 'VFX'.

    Returns:
        Optional[bpy.types.Collection]: The target collection, or None if creation fails.
    """
    top_level_scene_coll = find_top_level_scene_collection_by_str(scene_str)
    if not top_level_scene_coll:
        print(f"AdvCopy Error: Could not find top-level scene collection for '{scene_str}'")
        return None

    # Extract location name, e.g., "LOCA" from "+SC17-LOCA+"
    location_name = '-'.join(top_level_scene_coll.name.strip('+').split('-')[1:])
    if not location_name:
        print(f"AdvCopy Error: Could not parse location from '{top_level_scene_coll.name}'")
        return None

    if op_type == 'MODEL':
        art_coll = get_or_create_collection(top_level_scene_coll, f"+{scene_str}-{location_name}-ART+")
        art_shot_coll = get_or_create_collection(art_coll, f"{scene_str}-{location_name}-ART-SHOT")
        shot_art_coll = get_or_create_collection(art_shot_coll, f"{scene_str}-{shot_str}-ART")
        return get_or_create_collection(shot_art_coll, f"MODEL-{scene_str}-{shot_str}")
    elif op_type == 'VFX':
        vfx_coll = get_or_create_collection(top_level_scene_coll, f"+{scene_str}-{location_name}-VFX+")
        vfx_shot_coll = get_or_create_collection(vfx_coll, f"{scene_str}-{location_name}-VFX-SHOT")
        return get_or_create_collection(vfx_shot_coll, f"{scene_str}-{shot_str}-VFX")

    return None

def find_scene_collection(top_level_scene_coll: bpy.types.Collection, op_type: str) -> Optional[bpy.types.Collection]:
    """
    Finds or creates the scene-level collection (MODEL or VFX).
    Structure: `+SC.../+-ART/MODEL...` or `+SC.../+-VFX/VFX...`

    Args:
        top_level_scene_coll (bpy.types.Collection): The top-level collection for the scene.
        op_type (str): The operation type, 'MODEL' or 'VFX'.

    Returns:
        Optional[bpy.types.Collection]: The target collection, or None on failure.
    """
    if not top_level_scene_coll: return None
    try:
        parts = top_level_scene_coll.name.strip('+').split('-')
        scene_str, location_name = parts[0], '-'.join(parts[1:])
    except IndexError:
        print(f"AdvCopy Error: Could not parse scene/location from '{top_level_scene_coll.name}'")
        return None

    if op_type == 'MODEL':
        art_coll = get_or_create_collection(top_level_scene_coll, f"+{scene_str}-{location_name}-ART+")
        return get_or_create_collection(art_coll, f"{scene_str}-{location_name}-MODEL")
    elif op_type == 'VFX':
        vfx_parent = get_or_create_collection(top_level_scene_coll, f"+{scene_str}-{location_name}-VFX+")
        return get_or_create_collection(vfx_parent, f"{scene_str}-{location_name}-VFX")

    return None

def find_source_loc_collection(obj: bpy.types.Object, op_type: str) -> Optional[bpy.types.Collection]:
    """
    Finds the source `+LOC-.../LOC-...-[TYPE]` collection of an object.

    Args:
        obj (bpy.types.Object): The object to check.
        op_type (str): The type to look for, 'MODEL' or 'VFX'.

    Returns:
        Optional[bpy.types.Collection]: The found source collection, or None.
    """
    suffix = f"-{op_type}"
    for coll in obj.users_collection:
        if coll.name.startswith("LOC-") and coll.name.endswith(suffix):
            # Verify it has a valid top-level LOC parent
            for p_coll in bpy.data.collections:
                if p_coll.name.startswith("+LOC-") and coll.name in p_coll.children:
                    return coll
    return None

def find_all_env_collections(op_type: str) -> List[bpy.types.Collection]:
    """
    Finds all `+ENV-.../ENV-...-[TYPE]` collections.

    Args:
        op_type (str): The type to look for, 'MODEL' or 'VFX'.

    Returns:
        List[bpy.types.Collection]: A list of matching ENV collections.
    """
    suffix = f"-{op_type}"
    env_colls: List[bpy.types.Collection] = []
    for parent_coll in bpy.data.collections:
        if parent_coll.name.startswith("+ENV-"):
            # e.g., from "+ENV-FOREST+", get "FOREST"
            env_name = parent_coll.name.strip('+-').replace('ENV-', '', 1)
            expected_coll_name = f"ENV-{env_name}{suffix}"
            if expected_coll_name in parent_coll.children:
                env_colls.append(parent_coll.children[expected_coll_name])
    return env_colls

