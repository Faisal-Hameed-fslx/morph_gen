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
        model_box.label(
            text="%s | %d morphs" % (
                primary.name,
                max(0, len(primary.data.shape_keys.key_blocks) - 1),
            ),
            icon='CHECKMARK',
        )

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

        layout.prop(s, "filter_text", icon='VIEWZOOM')

        sk_box = layout.box()
        sk_box.label(text="Combined Morph Library", icon='SHAPEKEY_DATA')
        sk_box.label(text="Create source keys in Blender's Shape Keys panel", icon='INFO')
        combine = sk_box.box()
        combine.label(text="Combine Existing Morphs", icon='MODIFIER')
        combine.label(text="Output: 0 Basis | 1 Combined Deformation", icon='INFO')
        combine.prop(s, "combine_positive_key")
        combine.prop(s, "combine_negative_key")
        combine.prop(s, "combined_morph_name")
        combine.operator(
            "morph_gen.combine_shape_keys",
            text="Create Named Combined Morph",
            icon='ADD',
        )
        sk_box.prop(s, "shape_key_to_remove")
        sk_box.operator("morph_gen.remove_shape_key", text="Remove Selected Morph", icon='REMOVE')
        sk = primary.data.shape_keys

        groups = {}
        filt = s.filter_text.lower().strip()
        for kb in sk.key_blocks:
            if kb.name == 'Basis' or not operators.is_combined_key(primary, kb.name):
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
                row = box.row(align=True)
                row.label(text=name)
                row.prop(kb, "value", text="Influence", slider=True)

        controller_box = layout.box()
        controller_box.label(text="Combined Morphs", icon='DRIVER')
        for key, value in sorted(primary.items()):
            if key.startswith("morph_gen_combined_"):
                controller_box.prop(
                    primary,
                    '["%s"]' % key,
                    text=key[len("morph_gen_combined_"):].replace("_", " ").title(),
                    slider=True,
                )

class MORPHGEN_PT_properties(bpy.types.Panel):
    bl_label = "Morph Gen"
    bl_idname = "MORPHGEN_PT_properties"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "DATA"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        settings = getattr(scene, "morph_gen", None)
        if settings is None:
            layout.label(text="Morph Gen is not initialized")
            return
        layout.label(text="Open the 3D View sidebar (N) for the full studio")
        layout.prop(settings, "target_object", text="Active Mesh")
        layout.operator("morph_gen.pick_model", text="Use Selected Mesh", icon="EYEDROPPER")


_classes = (MORPHGEN_PT_main, MORPHGEN_PT_properties)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
