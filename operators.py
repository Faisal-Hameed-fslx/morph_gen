import bpy
import json
import random
import os
import mathutils
import sys
from datetime import datetime

from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props import StringProperty

from . import properties


def _char_collection():
    scene = bpy.context.scene
    name = scene.morph_gen.loaded_collection
    if not name:
        return None
    return bpy.data.collections.get(name)


def _collect_collection_objects(coll):
    if coll is None:
        return []
    result = []
    for obj in coll.objects:
        result.append(obj)
    for child in coll.children:
        result += _collect_collection_objects(child)
    return result


def get_char_objects():
    return _collect_collection_objects(_char_collection())


def get_meshes_with_shape_keys():
    meshes = []
    for obj in get_char_objects():
        if obj.type == 'MESH' and obj.data.shape_keys is not None:
            meshes.append(obj)
    meshes.sort(key=lambda o: len(o.data.vertices), reverse=True)
    return meshes


def get_target_mesh():
    try:
        s = bpy.context.scene.morph_gen
        if s.target_object and s.target_object.type == 'MESH' and s.target_object.data.shape_keys:
            return s.target_object
        name = s.target_mesh
        if name and name != 'NONE':
            obj = bpy.data.objects.get(name)
            if obj is not None and obj.type == 'MESH' and obj.data.shape_keys is not None:
                return obj
    except Exception:
        pass
    meshes = get_meshes_with_shape_keys()
    return meshes[0] if meshes else None


def get_armature():
    for obj in get_char_objects():
        if obj.type == 'ARMATURE':
            return obj
    return None


def _set_slider_ranges():
    for obj in get_meshes_with_shape_keys():
        if obj.data.shape_keys is None:
            continue
        for kb in obj.data.shape_keys.key_blocks:
            if kb.name == 'Basis':
                continue
            try:
                kb.slider_min = -1.0
                kb.slider_max = 1.0
            except Exception:
                pass


def _sync_meshes_to_primary():
    meshes = get_meshes_with_shape_keys()
    if len(meshes) < 2:
        return
    primary = get_target_mesh()
    if primary is None or primary.data.shape_keys is None:
        return
    for obj in meshes:
        if obj == primary or obj.data.shape_keys is None:
            continue
        for kb in primary.data.shape_keys.key_blocks:
            if kb.name == 'Basis':
                continue
            other = obj.data.shape_keys.key_blocks.get(kb.name)
            if other is not None and other.value != kb.value:
                other.value = kb.value


def _bake_face_match(name):
    baked = 0
    for obj in get_meshes_with_shape_keys():
        keys = obj.data.shape_keys.key_blocks
        existing = keys.get(name)
        if existing is not None:
            existing.value = 0.0
            obj.shape_key_remove(existing)
        new_key = obj.shape_key_add(name=name, from_mix=True)
        new_key.slider_min = 0.0
        new_key.slider_max = 1.0
        for key in obj.data.shape_keys.key_blocks:
            if key != new_key and key.name != "Basis":
                key.value = 0.0
        new_key.value = 1.0
        baked += 1
    return baked


_syncing = False


def _depsgraph_handler(scene, depsgraph):
    global _syncing
    if _syncing:
        return
    _syncing = True
    try:
        _sync_meshes_to_primary()
    except Exception:
        pass
    finally:
        _syncing = False


def register_handlers():
    if _depsgraph_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_depsgraph_handler)


def unregister_handlers():
    if _depsgraph_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_depsgraph_handler)


# ---------- Operators ----------

_VERSION_TEXT = "Morph_Gen_Versions"


def _version_data():
    text = bpy.data.texts.get(_VERSION_TEXT)
    if text is None:
        return {}
    try:
        return json.loads(text.as_string())
    except (TypeError, ValueError):
        return {}


def _write_version_data(data):
    text = bpy.data.texts.get(_VERSION_TEXT)
    if text is None:
        text = bpy.data.texts.new(_VERSION_TEXT)
    text.clear()
    text.write(json.dumps(data, separators=(",", ":")))


def _capture_version(context):
    scene = context.scene
    data = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "loaded_collection": scene.morph_gen.loaded_collection,
        "target_mesh": scene.morph_gen.target_mesh,
        "target_object": scene.morph_gen.target_object.name if scene.morph_gen.target_object else "",
        "settings": {
            "filter_text": scene.morph_gen.filter_text,
            "random_seed": scene.morph_gen.random_seed,
            "random_strength": scene.morph_gen.random_strength,
            "face_match_strength": scene.morph_gen.face_match_strength,
        },
        "objects": {},
    }
    for obj in bpy.data.objects:
        object_data = {
            "location": list(obj.location),
            "rotation": list(obj.rotation_euler),
            "scale": list(obj.scale),
            "hide_viewport": obj.hide_viewport,
            "hide_render": obj.hide_render,
        }
        if obj.type == "MESH" and obj.data.shape_keys:
            object_data["shape_keys"] = {
                key.name: key.value
                for key in obj.data.shape_keys.key_blocks
            }
        data["objects"][obj.name] = object_data
    return data


class MORPHGEN_OT_save_version(bpy.types.Operator):
    bl_idname = "morph_gen.save_version"
    bl_label = "Save Internal Version"
    bl_description = "Save a compact recovery checkpoint inside this blend file"

    def execute(self, context):
        name = context.scene.morph_gen.version_name.strip()
        if not name:
            self.report({'WARNING'}, "Enter a version name")
            return {'CANCELLED'}
        versions = _version_data()
        versions[name] = _capture_version(context)
        _write_version_data(versions)
        context.scene.morph_gen.saved_version = name
        self.report({'INFO'}, "Saved internal version: %s" % name)
        return {'FINISHED'}


class MORPHGEN_OT_restore_version(bpy.types.Operator):
    bl_idname = "morph_gen.restore_version"
    bl_label = "Restore Internal Version"
    bl_description = "Restore morph values and scene state from a saved checkpoint"

    def execute(self, context):
        name = context.scene.morph_gen.saved_version
        version = _version_data().get(name)
        if not version:
            self.report({'WARNING'}, "Select a saved version first")
            return {'CANCELLED'}
        for object_name, object_data in version.get("objects", {}).items():
            obj = bpy.data.objects.get(object_name)
            if obj is None:
                continue
            obj.location = object_data.get("location", obj.location)
            obj.rotation_euler = object_data.get("rotation", obj.rotation_euler)
            obj.scale = object_data.get("scale", obj.scale)
            obj.hide_viewport = object_data.get("hide_viewport", False)
            obj.hide_render = object_data.get("hide_render", False)
            if obj.type == "MESH" and obj.data.shape_keys:
                for key_name, value in object_data.get("shape_keys", {}).items():
                    key = obj.data.shape_keys.key_blocks.get(key_name)
                    if key:
                        key.value = value
        settings = version.get("settings", {})
        for key, value in settings.items():
            setattr(context.scene.morph_gen, key, value)
        _sync_meshes_to_primary()
        self.report({'INFO'}, "Restored internal version: %s" % name)
        return {'FINISHED'}


class MORPHGEN_OT_delete_version(bpy.types.Operator):
    bl_idname = "morph_gen.delete_version"
    bl_label = "Delete Internal Version"
    bl_description = "Delete the selected internal recovery checkpoint"

    def execute(self, context):
        name = context.scene.morph_gen.saved_version
        versions = _version_data()
        if name == 'NONE' or name not in versions:
            self.report({'WARNING'}, "Select a saved version first")
            return {'CANCELLED'}
        del versions[name]
        _write_version_data(versions)
        context.scene.morph_gen.saved_version = 'NONE'
        self.report({'INFO'}, "Deleted internal version: %s" % name)
        return {'FINISHED'}


class MORPHGEN_OT_pick_model(bpy.types.Operator):
    bl_idname = "morph_gen.pick_model"
    bl_label = "Pick Selected Model"
    bl_description = "Use the selected shape-key mesh from the 3D View"

    def execute(self, context):
        selected = context.selected_objects
        obj = context.view_layer.objects.active
        if obj not in selected or obj is None or obj.type != 'MESH':
            obj = next((item for item in selected if item.type == 'MESH'), None)
        if obj is None or obj.data.shape_keys is None:
            self.report({'WARNING'}, "Select a mesh with shape keys in the 3D View")
            return {'CANCELLED'}
        context.scene.morph_gen.target_object = obj
        collections = list(obj.users_collection)
        if collections:
            context.scene.morph_gen.loaded_collection = collections[0].name
        self.report({'INFO'}, "Using selected model: %s" % obj.name)
        return {'FINISHED'}


class MORPHGEN_OT_load_base(bpy.types.Operator, ImportHelper):
    bl_idname = "morph_gen.load_base"
    bl_label = "Load Base Mesh"
    bl_description = "Import a base mesh and set up morph sliders"
    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})

    def execute(self, context):
        try:
            bpy.ops.import_scene.fbx(filepath=self.filepath)
        except Exception as e:
            self.report({'ERROR'}, "FBX import failed: %s" % e)
            return {'CANCELLED'}

        imported = list(context.selected_objects)
        if not imported:
            self.report({'WARNING'}, "No objects imported")
            return {'CANCELLED'}

        coll = bpy.data.collections.new("Morph_Character")
        context.scene.collection.children.link(coll)
        for obj in imported:
            for c in list(obj.users_collection):
                try:
                    c.objects.unlink(obj)
                except Exception:
                    pass
            coll.objects.link(obj)

        context.scene.morph_gen.loaded_collection = coll.name
        _set_slider_ranges()
        self.report({'INFO'}, "Loaded %d objects" % len(imported))
        return {'FINISHED'}


class MORPHGEN_OT_reset(bpy.types.Operator):
    bl_idname = "morph_gen.reset"
    bl_label = "Reset Morphs"
    bl_description = "Reset all morph sliders to zero"

    def execute(self, context):
        for obj in get_meshes_with_shape_keys():
            if obj.data.shape_keys is None:
                continue
            for kb in obj.data.shape_keys.key_blocks:
                if kb.name != 'Basis':
                    kb.value = 0.0
        return {'FINISHED'}


class MORPHGEN_OT_randomize(bpy.types.Operator):
    bl_idname = "morph_gen.randomize"
    bl_label = "Randomize Morphs"
    bl_description = "Randomize morph sliders"

    def execute(self, context):
        s = context.scene.morph_gen
        random.seed(s.random_seed)
        strength = s.random_strength
        primary = get_target_mesh()
        if primary is None or primary.data.shape_keys is None:
            return {'CANCELLED'}
        for kb in primary.data.shape_keys.key_blocks:
            if kb.name == 'Basis':
                continue
            kb.value = random.uniform(0.0, strength)
        _sync_meshes_to_primary()
        s.random_seed += 1
        return {'FINISHED'}


class MORPHGEN_OT_sync(bpy.types.Operator):
    bl_idname = "morph_gen.sync"
    bl_label = "Sync Meshes"
    bl_description = "Copy morph values from the body mesh to all other meshes"

    def execute(self, context):
        _sync_meshes_to_primary()
        return {'FINISHED'}


class MORPHGEN_OT_save_preset(bpy.types.Operator, ExportHelper):
    bl_idname = "morph_gen.save_preset"
    bl_label = "Save Preset"
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    def execute(self, context):
        data = {}
        for obj in get_meshes_with_shape_keys():
            data[obj.name] = {}
            if obj.data.shape_keys is None:
                continue
            for kb in obj.data.shape_keys.key_blocks:
                if kb.name != 'Basis':
                    data[obj.name][kb.name] = kb.value
        try:
            with open(self.filepath, 'w') as f:
                json.dump(data, f, indent=2)
            self.report({'INFO'}, "Preset saved")
        except Exception as e:
            self.report({'ERROR'}, "Save failed: %s" % e)
            return {'CANCELLED'}
        return {'FINISHED'}


class MORPHGEN_OT_load_preset(bpy.types.Operator, ImportHelper):
    bl_idname = "morph_gen.load_preset"
    bl_label = "Load Preset"
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    def execute(self, context):
        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)
        except Exception as e:
            self.report({'ERROR'}, "Load failed: %s" % e)
            return {'CANCELLED'}
        for obj_name, keys in data.items():
            obj = bpy.data.objects.get(obj_name)
            if obj is None or obj.data.shape_keys is None:
                continue
            for kb_name, val in keys.items():
                kb = obj.data.shape_keys.key_blocks.get(kb_name)
                if kb is not None:
                    kb.value = val
        _sync_meshes_to_primary()
        return {'FINISHED'}


class MORPHGEN_OT_export(bpy.types.Operator, ExportHelper):
    bl_idname = "morph_gen.export"
    bl_label = "Export Character (FBX)"
    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})

    def execute(self, context):
        objs = get_char_objects()
        if not objs:
            self.report({'WARNING'}, "No character loaded")
            return {'CANCELLED'}
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objs:
            try:
                obj.select_set(True)
            except Exception:
                pass
        try:
            bpy.ops.export_scene.fbx(
                filepath=self.filepath,
                use_selection=True,
                add_leaf_bones=False,
            )
            self.report({'INFO'}, "Exported")
        except Exception as e:
            self.report({'ERROR'}, "Export failed: %s" % e)
            return {'CANCELLED'}
        return {'FINISHED'}
class MORPHGEN_OT_add_shape_key(bpy.types.Operator):
    bl_idname = "morph_gen.add_shape_key"
    bl_label = "Add Shape Key (from current)"
    bl_description = "Create a new shape key from the current deformed mesh"

    def execute(self, context):
        s = context.scene.morph_gen
        name = s.new_shape_key_name.strip() or "NewMorph"
        primary = get_target_mesh()
        if primary is None or primary.data.shape_keys is None:
            self.report({'WARNING'}, "No target mesh")
            return {'CANCELLED'}
        if primary.data.shape_keys.key_blocks.get('Basis') is None:
            primary.shape_key_add(name='Basis', from_mix=False)
        new_key = primary.shape_key_add(name=name, from_mix=True)
        new_key.value = 0.0
        for obj in get_meshes_with_shape_keys():
            if obj == primary or obj.data.shape_keys is None:
                continue
            other = obj.data.shape_keys.key_blocks.get(name)
            if other is not None:
                other.value = 0.0
        _sync_meshes_to_primary()
        self.report({'INFO'}, "Added shape key: %s" % name)
        return {'FINISHED'}


class MORPHGEN_OT_remove_shape_key(bpy.types.Operator):
    bl_idname = "morph_gen.remove_shape_key"
    bl_label = "Remove Shape Key"
    bl_description = "Remove the selected shape key from target mesh"

    def execute(self, context):
        s = context.scene.morph_gen
        name = s.shape_key_to_remove
        if not name or name == 'NONE':
            self.report({'WARNING'}, "No shape key selected")
            return {'CANCELLED'}
        primary = get_target_mesh()
        if primary is None or primary.data.shape_keys is None:
            return {'CANCELLED'}
        kb = primary.data.shape_keys.key_blocks.get(name)
        if kb is None:
            self.report({'WARNING'}, "Shape key not found")
            return {'CANCELLED'}
        primary.shape_key_remove(kb)
        self.report({'INFO'}, "Removed: %s" % name)
        return {'FINISHED'}

class MORPHGEN_OT_load_selected(bpy.types.Operator):
    bl_idname = "morph_gen.load_selected"
    bl_label = "Load Selected Base"
    bl_description = "Load the base FBX chosen in the dropdown (auto-discovered from folder)"

    def execute(self, context):
        s = context.scene.morph_gen
        path = s.base_file
        if not path or path == 'NONE':
            items = properties._fbx_items(s, context)
            if items and items[0][0] != 'NONE':
                path = items[0][0]
            else:
                self.report({'WARNING'}, "No FBX found in folder")
                return {'CANCELLED'}
        try:
            bpy.ops.import_scene.fbx(filepath=path)
        except Exception as e:
            self.report({'ERROR'}, "FBX import failed: %s" % e)
            return {'CANCELLED'}

        imported = list(context.selected_objects)
        if not imported:
            self.report({'WARNING'}, "No objects imported")
            return {'CANCELLED'}

        coll = bpy.data.collections.new("Morph_Character")
        context.scene.collection.children.link(coll)
        for obj in imported:
            for c in list(obj.users_collection):
                try:
                    c.objects.unlink(obj)
                except Exception:
                    pass
            coll.objects.link(obj)

        context.scene.morph_gen.loaded_collection = coll.name
        _set_slider_ranges()
        self.report({'INFO'}, "Loaded %d objects from %s" % (len(imported), path))
        return {'FINISHED'}


class MORPHGEN_OT_load_first_found(bpy.types.Operator):
    bl_idname = "morph_gen.load_first_found"
    bl_label = "Auto-Find && Load First"
    bl_description = "Scan the folder and load the first base mesh found"

    def execute(self, context):
        s = context.scene.morph_gen
        items = properties._fbx_items(s, context)
        if not items or items[0][0] == 'NONE':
            self.report({'WARNING'}, "No FBX found in folder")
            return {'CANCELLED'}
        s.base_file = items[0][0]
        return bpy.ops.morph_gen.load_selected()


class MORPHGEN_OT_face_detect(bpy.types.Operator, ImportHelper):
    bl_idname = "morph_gen.face_detect"
    bl_label = "Match Front Image"
    bl_description = "Detect a front-facing image and apply matching facial morphs"
    filename_ext = ".jpg"
    filter_glob: StringProperty(default="*.jpg;*.png;*.jpeg", options={'HIDDEN'})

    def execute(self, context):
        path = self.filepath
        if not path or not os.path.isfile(path):
            self.report({'ERROR'}, "Image file does not exist")
            return {'CANCELLED'}
        primary = get_target_mesh()
        if primary is None or primary.data.shape_keys is None:
            self.report({'WARNING'}, "Load or select a base mesh with shape keys first")
            return {'CANCELLED'}

        import subprocess
        import tempfile
        candidates = [
            r"C:\Users\Malik\AppData\Local\Programs\Python\Python313\python.exe",
            sys.executable if os.path.basename(sys.executable).lower().startswith("python") else None,
        ]
        syspy = next((candidate for candidate in candidates if candidate and os.path.isfile(candidate)), None)
        if syspy is None:
            self.report({'ERROR'}, "Python 3 with MediaPipe could not be found")
            return {'CANCELLED'}

        script = '''
import cv2, json, sys
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
path = sys.argv[1]
model = sys.argv[2]
img = cv2.imread(path)
if img is None:
    print(json.dumps({"error":"read"})); sys.exit()
h,w = img.shape[:2]
base_opts = mp_python.BaseOptions(model_asset_path=model)
opts = vision.FaceLandmarkerOptions(base_options=base_opts, output_face_blendshapes=True, output_facial_transformation_matrixes=False, num_faces=1)
landmarker = vision.FaceLandmarker.create_from_options(opts)
mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
res = landmarker.detect(mp_image)
if not res.face_landmarks:
    print(json.dumps({"error":"noface"})); sys.exit()
lm = res.face_landmarks[0]
def pt(i): return (lm[i].x*w, lm[i].y*h)
left_eye=pt(33); right_eye=pt(263)
eye_dist=((left_eye[0]-right_eye[0])**2+(left_eye[1]-right_eye[1])**2)**0.5
nose_l=pt(129); nose_r=pt(358)
nose_width=abs(nose_l[0]-nose_r[0])
jaw_l=pt(234); jaw_r=pt(454)
jaw_width=abs(jaw_l[0]-jaw_r[0])
mouth_l=pt(61); mouth_r=pt(291)
mouth_width=abs(mouth_l[0]-mouth_r[0])
top=pt(10); bottom=pt(152)
face_height=abs(top[1]-bottom[1])
blendshapes = {}
if res.face_blendshapes:
    blendshapes = {
        category.category_name: category.score
        for category in res.face_blendshapes[0]
    }
print(json.dumps({"eye_dist":eye_dist,"nose_width":nose_width,"jaw_width":jaw_width,"mouth_width":mouth_width,"face_height":face_height,"blendshapes":blendshapes}))
'''
        model_candidates = [
            os.path.join(os.path.dirname(__file__), "face_landmarker.task"),
            r"C:\Users\Malik\Downloads\face_landmarker.task",
        ]
        model_path = next((candidate for candidate in model_candidates if os.path.isfile(candidate)), None)
        if model_path is None:
            self.report({'ERROR'}, "face_landmarker.task was not found beside the add-on or in Downloads")
            return {'CANCELLED'}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script)
            script_path = f.name
        try:
            out = subprocess.run([syspy, script_path, path, model_path], capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            self.report({'ERROR'}, "Face detection timed out after 120 seconds")
            return {'CANCELLED'}
        except OSError as error:
            self.report({'ERROR'}, "Could not start face detection: %s" % error)
            return {'CANCELLED'}
        finally:
            os.remove(script_path)
        if out.returncode != 0:
            details = (out.stderr.strip() or out.stdout.strip() or "unknown error").splitlines()
            self.report({'ERROR'}, "Face detection failed: %s" % details[-1][:240])
            return {'CANCELLED'}
        try:
            data = json.loads(out.stdout.strip().splitlines()[-1])
        except Exception:
            self.report({'ERROR'}, "Bad output: %s" % out.stdout[:200])
            return {'CANCELLED'}
        if "error" in data:
            self.report({'WARNING'}, "No face detected" if data["error"]=="noface" else "Could not read image")
            return {'CANCELLED'}

        aliases = (
            (("browdown",), ("browdown", "brow_down", "browlower")),
            (("browinnerup", "browouterup"), ("browup", "brow_up", "browraise")),
            (("eyeblink",), ("blink", "eyeblink", "eye_blink")),
            (("eyesquint",), ("squint", "eyesquint", "eye_squint")),
            (("eyewide",), ("eyewide", "eye_wide", "wideeye")),
            (("jawopen",), ("jawopen", "jaw_open", "mouthopen", "mouth_open")),
            (("jawleft",), ("jawleft", "jaw_left")),
            (("jawright",), ("jawright", "jaw_right")),
            (("mouthsmile", "mouthdimple"), ("mouthsmile", "mouth_smile", "smile")),
            (("mouthfrown",), ("mouthfrown", "mouth_frown", "frown")),
            (("mouthpucker", "mouthfunnel"), ("mouthpucker", "mouth_pucker", "pucker")),
            (("nosesneer",), ("nosesneer", "nose_sneer", "sneer")),
        )
        shape_keys = [kb for kb in primary.data.shape_keys.key_blocks if kb.name != 'Basis']
        blendshapes = data.get("blendshapes", {})
        applied = 0
        strength = max(2.0, context.scene.morph_gen.face_match_strength)
        for key_block in shape_keys:
            key_block.value = 0.0
        for key_block in shape_keys:
            key_name = ''.join(char.lower() for char in key_block.name if char.isalnum() or char == '_')
            scores = []
            for blend_name, score in blendshapes.items():
                normalized_blend_name = ''.join(
                    char.lower() for char in blend_name if char.isalnum()
                )
                for blend_tokens, key_tokens in aliases:
                    if any(token in normalized_blend_name for token in blend_tokens):
                        if any(token in key_name for token in key_tokens):
                            scores.append(score)
                        break
            if scores:
                score = max(scores)
                if "blink" not in key_name and "squint" not in key_name and "wide" not in key_name:
                    score = score if score >= 0.35 else 0.0
                if "pucker" in key_name or "funnel" in key_name:
                    score = 0.0
                key_block.value = min(1.0, max(0.0, score * strength))
                applied += 1
        _sync_meshes_to_primary()

        name = os.path.basename(path)
        if name in bpy.data.images:
            imgdata = bpy.data.images[name]
        else:
            imgdata = bpy.data.images.load(path)
        if name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = 'IMAGE'
        empty.data = imgdata
        empty.location = (0, -2, 1)
        empty.rotation_euler = (1.5708, 0, 0)
        bpy.context.scene.collection.objects.link(empty)
        baked = 0
        if applied and context.scene.morph_gen.face_match_bake:
            morph_name = "FaceMatch_%s" % os.path.splitext(name)[0][:40]
            baked = _bake_face_match(morph_name)
        if applied == 0:
            self.report({'WARNING'}, "Face detected, but no matching facial shape keys were found")
        elif baked:
            self.report({'INFO'}, "Created reusable %s morph on %d meshes" % (morph_name, baked))
        else:
            self.report({'INFO'}, "Matched face image to %d facial morphs" % applied)
        return {'FINISHED'}


_classes = (
    MORPHGEN_OT_save_version,
    MORPHGEN_OT_restore_version,
    MORPHGEN_OT_delete_version,
    MORPHGEN_OT_pick_model,
    MORPHGEN_OT_load_base,
    MORPHGEN_OT_reset,
    MORPHGEN_OT_randomize,
    MORPHGEN_OT_sync,
    MORPHGEN_OT_save_preset,
    MORPHGEN_OT_load_preset,
    MORPHGEN_OT_export,
    MORPHGEN_OT_load_selected,
    MORPHGEN_OT_load_first_found,
    MORPHGEN_OT_face_detect,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)

_classes = _classes + (MORPHGEN_OT_add_shape_key, MORPHGEN_OT_remove_shape_key)
