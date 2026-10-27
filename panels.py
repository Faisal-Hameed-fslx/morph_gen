import bpy

from . import operators


def _target_mesh():
    return operators.get_target_mesh()


class MORPHGEN_PT_main(bpy.types.Panel):
    bl_label = "Morph Gen | Shape Key Studio"
    bl_idname = "MORPHGEN_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Morph Gen"

    def draw(self, context):
        layout = self.layout
        s = context.scene.morph_gen

        model_box = layout.box()
        model_box.label(text="Active Model", icon='MESH_DATA')
        model_box.prop(s, "target_object", text="Mesh")
        model_box.operator("morph_gen.pick_model", text="Use Selected Mesh", icon='EYEDROPPER')
        primary = _target_mesh()
        if primary is None or primary.data.shape_keys is None:
            model_box.label(text="Select a mesh with shape keys", icon='INFO')
            return

        actions = layout.box()
        actions.label(text="Shape Key Actions", icon='MODIFIER')
        row = actions.row(align=True)
        row.operator("morph_gen.reset", text="Reset", icon='LOOP_BACK')
        row.operator("morph_gen.sync", text="Synchronize", icon='LINKED')
        actions.operator("morph_gen.randomize", text="Generate Random Variation", icon='MOD_NOISE')

        random_box = actions.box()
        random_box.prop(s, "random_seed")
        random_box.prop(s, "random_strength")

        presets = layout.box()
        presets.label(text="Presets & Export", icon='FILE')
        row = presets.row(align=True)
        row.operator("morph_gen.save_preset", text="Save Preset", icon='EXPORT')
        row.operator("morph_gen.load_preset", text="Load Preset", icon='IMPORT')
        presets.operator("morph_gen.export", text="Export FBX", icon='EXPORT')

        version_box = layout.box()
        version_box.label(text="Scene Checkpoints", icon='FILE_TICK')
        version_box.prop(s, "version_name")
        version_box.operator("morph_gen.save_version", icon='FILE_TICK')
        version_box.prop(s, "saved_version")
        row = version_box.row(align=True)
        row.operator("morph_gen.restore_version", icon='LOOP_BACK')
        row.operator("morph_gen.delete_version", icon='TRASH')

        layout.prop(s, "filter_text", icon='VIEWZOOM')

        sk_box = layout.box()
        sk_box.label(text="Morph Library", icon='SHAPEKEY_DATA')
        sk_box.prop(s, "new_shape_key_name")
        sk_box.operator("morph_gen.add_shape_key", text="Create Morph From Current", icon='ADD')
        sk_box.prop(s, "shape_key_to_remove")
        sk_box.operator("morph_gen.remove_shape_key", text="Remove Selected Morph", icon='REMOVE')
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


_classes = (MORPHGEN_PT_main,)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
