import bpy
from typing import Tuple

def toggle_object_visibility(obj: bpy.types.Object, frame_range: Tuple[int, int], hide: bool):
    """
    Keys the visibility of an object to be hidden or shown for a specific frame range.
    It keys the frame before and after the range to ensure visibility returns to its
    previous state.

    Args:
        obj (bpy.types.Object): The object to keyframe.
        frame_range (Tuple[int, int]): The (start, end) frames for the visibility change.
        hide (bool): True to hide the object during the range, False to show it.
    """
    start_frame, end_frame = frame_range
    assert start_frame <= end_frame, "Start frame must be less than or equal to end frame."

    # Ensure animation data exists
    if not obj.animation_data:
        obj.animation_data_create()

    # Properties to keyframe
    visibility_props = ["hide_viewport", "hide_render"]

    for prop in visibility_props:
        # Frame before the range: Set to the opposite of the 'hide' state
        setattr(obj, prop, not hide)
        obj.keyframe_insert(data_path=prop, frame=start_frame - 1)

        # Start of the range: Set to the desired 'hide' state
        setattr(obj, prop, hide)
        obj.keyframe_insert(data_path=prop, frame=start_frame)

        # End of the range: Keep the desired 'hide' state
        obj.keyframe_insert(data_path=prop, frame=end_frame)

        # Frame after the range: Revert to the opposite state
        setattr(obj, prop, not hide)
        obj.keyframe_insert(data_path=prop, frame=end_frame + 1)

