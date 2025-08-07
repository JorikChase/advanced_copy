import bpy
import re
from typing import Optional, Dict, List, Tuple

def get_current_shot_info(context: bpy.types.Context) -> Optional[Dict[str, any]]:
    """
    Determines the current shot from timeline markers bound to cameras.
    Parses marker names like 'CAM-SC17-SH180-FLAT' to extract shot details.

    Args:
        context (bpy.types.Context): The current Blender context.

    Returns:
        Optional[Dict[str, any]]: A dictionary with shot info or None if not in a shot.
        The dictionary contains: {name, start, end, scene_str, shot_str}
    """
    current_frame = context.scene.frame_current
    # Filter for markers that are bound to a camera and sort them by frame
    markers = sorted([m for m in context.scene.timeline_markers if m.camera], key=lambda m: m.frame)

    if not markers:
        return None

    current_shot_marker = None
    shot_end_frame = context.scene.frame_end

    # Find which shot range the current frame falls into
    for i, marker in enumerate(markers):
        start_frame = marker.frame
        # Determine the end frame of the current shot
        if i + 1 < len(markers):
            end_frame = markers[i+1].frame - 1
        else:
            # Last marker goes to the end of the scene
            end_frame = context.scene.frame_end

        if start_frame <= current_frame <= end_frame:
            current_shot_marker = marker
            shot_end_frame = end_frame
            break

    if not current_shot_marker:
        return None

    # Use regex to parse the scene and shot numbers from the marker name
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
        "shot_str": shot_str
    }

def get_scene_frame_range(context: bpy.types.Context, scene_str: str) -> Optional[Tuple[int, int]]:
    """
    Calculates the full frame range for a given scene by finding the
    earliest start and latest end frame among all its associated shot markers.

    Args:
        context (bpy.types.Context): The current Blender context.
        scene_str (str): The scene identifier (e.g., "SC17").

    Returns:
        Optional[Tuple[int, int]]: A tuple of (start_frame, end_frame), or None.
    """
    scene_markers: List[bpy.types.TimelineMarker] = []
    # Find all markers belonging to the specified scene
    for marker in context.scene.timeline_markers:
        if marker.camera and f"-{scene_str.upper()}-" in marker.name.upper():
            scene_markers.append(marker)

    if not scene_markers:
        return None

    scene_markers.sort(key=lambda m: m.frame)
    all_markers = sorted([m for m in context.scene.timeline_markers if m.camera], key=lambda m: m.frame)

    start_frame = scene_markers[0].frame
    last_shot_marker = scene_markers[-1]
    end_frame = context.scene.frame_end # Default end frame

    try:
        last_marker_index = all_markers.index(last_shot_marker)
        # If this is not the last marker in the entire timeline, the scene ends before the next marker
        if last_marker_index + 1 < len(all_markers):
            end_frame = all_markers[last_marker_index + 1].frame - 1
    except ValueError:
        # This should not happen if logic is correct, but as a safeguard.
        pass

    return (start_frame, end_frame)

