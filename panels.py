import bpy

from . import operators


def _target_mesh():
    return operators.get_target_mesh()


class CCCHAR_PT_main(bpy.types.Panel):
    bl_label = "CC Character"
    bl_idname = "CCCHAR_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CC Char"

    def draw(self, context):
        layout = self.layout
        s = context.scene.cc_char

        layout.prop(s, "target_object")
        layout.operator("cc_char.pick_model", icon='EYEDROPPER')
        row = layout.row(align=True)
        row.operator("cc_char.load_base", icon='FILEBROWSER')
        row.operator("cc_char.face_detect", icon='IMAGE')
        if not s.loaded_collection and not s.target_object:
            layout.label(text="Select a model with shape keys")
            return

        row = layout.row(align=True)
        row.operator("cc_char.reset", icon='LOOP_BACK')
        row.operator("cc_char.randomize", icon='MOD_NOISE')
        row.operator("cc_char.sync", icon='LINKED')

        layout.prop(s, "random_seed")
        layout.prop(s, "random_strength")
        layout.prop(s, "face_match_strength")
        layout.prop(s, "face_match_bake")

        row = layout.row(align=True)
        row.operator("cc_char.save_preset", icon='EXPORT')
        row.operator("cc_char.load_preset", icon='IMPORT')
        layout.operator("cc_char.export", icon='EXPORT')

        version_box = layout.box()
        version_box.label(text="Internal Recovery Versions")
        version_box.prop(s, "version_name")
        version_box.operator("cc_char.save_version", icon='FILE_TICK')
        version_box.prop(s, "saved_version")
        row = version_box.row(align=True)
        row.operator("cc_char.restore_version", icon='LOOP_BACK')
        row.operator("cc_char.delete_version", icon='TRASH')

        layout.prop(s, "filter_text", icon='VIEWZOOM')

        # Manual morph library
        sk_box = layout.box()
        sk_box.label(text="Manual Morph Library")
        sk_box.prop(s, "new_shape_key_name")
        sk_box.operator("cc_char.add_shape_key", text="Create Morph From Current", icon='ADD')
        sk_box.prop(s, "shape_key_to_remove")
        sk_box.operator("cc_char.remove_shape_key", text="Remove Selected Morph", icon='REMOVE')
        primary = _target_mesh()
        if primary is None or primary.data.shape_keys is None:
            layout.label(text="No shape keys found")
            return
        sk = primary.data.shape_keys

        groups = {}
        filt = s.filter_text.lower().strip()
        for kb in sk.key_blocks:
            if kb.name == 'Basis':
                continue
            if filt and filt not in kb.name.lower():
                continue
            group = kb.name.split('_')[0]
            groups.setdefault(group, []).append(kb.name)

        for group in sorted(groups):
            box = layout.box()
            box.label(text=group)
            for name in sorted(groups[group]):
                kb = sk.key_blocks[name]
                box.prop(kb, "value", text=name, slider=True)


_classes = (CCCHAR_PT_main,)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
