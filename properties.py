import bpy
import os


def _fbx_items(self, context):
    items = []
    root = self.base_root
    if root and os.path.isdir(root):
        for dirpath, _dirs, files in os.walk(root):
            for f in sorted(files):
                if f.lower().endswith('.fbx'):
                    full = os.path.join(dirpath, f).replace('\\', '/')
                    items.append((full, f, full))
    if not items:
        items.append(('NONE', 'No FBX found', ''))
    return items


def _mesh_items(self, context):
    items = []
    try:
        from . import operators
        meshes = operators.get_meshes_with_shape_keys()
    except Exception:
        meshes = []
    for obj in meshes:
        items.append((obj.name, obj.name, ""))
    if not items:
        items.append(('NONE', 'No mesh', ''))
    return items


def _shape_key_items(self, context):
    items = []
    try:
        from . import operators
        m = operators.get_target_mesh()
        if m and m.data.shape_keys:
            for kb in m.data.shape_keys.key_blocks:
                if kb.name != 'Basis':
                    items.append((kb.name, kb.name, ""))
    except Exception:
        pass
    if not items:
        items.append(('NONE', 'No shape keys', ''))
    return items


def _version_items(self, context):
    text = bpy.data.texts.get("CC_Character_Versions")
    items = [('NONE', 'No saved versions', '')]
    if text:
        try:
            import json
            versions = json.loads(text.as_string())
            items = [(name, name, "") for name in versions]
        except (TypeError, ValueError):
            pass
    return items


class CCCharSettings(bpy.types.PropertyGroup):
    base_root: bpy.props.StringProperty(
        name="Base Root Folder",
        description="Folder to scan for CC base FBX files",
        subtype='DIR_PATH',
        default="C:/Users/Malik/Downloads/CC Character Base",
    )
    base_file: bpy.props.EnumProperty(
        name="Base File",
        description="Discovered CC base FBX file",
        items=_fbx_items,
    )
    target_mesh: bpy.props.EnumProperty(
        name="Target Mesh",
        description="Mesh whose shape keys drive the sliders",
        items=_mesh_items,
    )
    target_object: bpy.props.PointerProperty(
        name="Model",
        description="Mesh selected in the 3D View whose shape keys drive the sliders",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'MESH' and obj.data.shape_keys is not None,
    )
    filter_text: bpy.props.StringProperty(
        name="Filter Morphs",
        description="Filter morph slider names",
        default="",
    )
    loaded_collection: bpy.props.StringProperty(
        name="Loaded Collection",
        description="Name of the collection holding the current character",
        default="",
    )
    random_seed: bpy.props.IntProperty(
        name="Random Seed",
        default=0,
        min=0,
    )
    random_strength: bpy.props.FloatProperty(
        name="Random Strength",
        default=0.5,
        min=0.0,
        max=1.0,
    )
    face_match_strength: bpy.props.FloatProperty(
        name="Face Match Strength",
        default=2.0,
        min=0.0,
        max=5.0,
    )
    face_match_bake: bpy.props.BoolProperty(
        name="Create Reusable Face Morph",
        description="Bake the image match into a reusable shape key",
        default=True,
    )
    new_shape_key_name: bpy.props.StringProperty(
        name="New Shape Key Name",
        default="NewMorph",
    )
    shape_key_to_remove: bpy.props.EnumProperty(
        name="Shape Key",
        items=_shape_key_items,
    )
    version_name: bpy.props.StringProperty(
        name="Version Name",
        description="Name for the internal recovery checkpoint",
        default="Version 1",
    )
    saved_version: bpy.props.EnumProperty(
        name="Saved Version",
        description="Internal recovery checkpoint to restore",
        items=_version_items,
    )


_classes = (CCCharSettings,)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cc_char = bpy.props.PointerProperty(type=CCCharSettings)


def unregister():
    del bpy.types.Scene.cc_char
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
