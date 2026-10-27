# Morph Gen

Morph Gen is a Blender add-on for manually creating, editing, reusing, and
exporting facial morphs on Blender meshes with shape keys.

## Install

1. Open **Edit > Preferences > Add-ons** in Blender.
2. Click **Install...**.
3. Select `cc_char_gen.zip`.
4. Enable the Morph Gen add-on.
5. Open a 3D Viewport and press **N**.
6. Open the **Morph Gen** tab.

## Select a model from the 3D View

Morph Gen does not require a folder scan when the model is already open:

1. Select the mesh object in the 3D View.
2. Ensure it has shape keys.
3. Click **Pick Selected Model**.

The add-on uses the selected mesh as the primary morph model and synchronizes
matching shape-key values to other meshes in the same character collection.

## Create a reusable manual morph

1. Select the model with **Pick Selected Model**.
2. Adjust the visible morph sliders.
3. Enter a name in **New Shape Key Name**, such as `SoftEyes`.
4. Click **Create Morph From Current**.
5. The new shape key appears as a reusable slider starting at `0.0`.
6. Set its value between `0.0` and `1.0` to use the morph.

Use **Remove Selected Morph** to remove a custom shape key from the primary
model. Save the character as an FBX when the morph is ready for export.

## Presets

- **Save Preset** writes current shape-key values to a JSON file.
- **Load Preset** restores values from a JSON file.
- **Reset Morphs** clears all morph values.
- **Randomize Morphs** creates a quick randomized starting point.
- **Sync Meshes** copies primary morph values to matching character meshes.

## Image face matching

**Match Face From Image** uses MediaPipe facial blendshapes to drive compatible
expression shape keys. It can match expressions such as blinking, squinting,
smiling, and jaw opening.

Required files:

- Python 3
- `mediapipe`
- `opencv-python`
- `face_landmarker.task`

The model file is searched for beside the add-on and at:

```text
C:\Users\Malik\Downloads\face_landmarker.task
```

Image matching is an expression helper, not full identity reconstruction. The
result depends on the facial shape keys available on the selected mesh and may
not reproduce exact face width, nose shape, jaw structure, or eye spacing from
one image.

## Optional FBX loading

You can load a model through the add-on using:

- **Load Selected Base**
- **Auto-Find && Load First**
- **Load Model (FBX)**

For an already-open model, prefer **Pick Selected Model**.

## Compatibility and limitations

- Blender 3.6 or newer is recommended.
- Shape-key names must match between meshes for synchronization.
- Morph sliders are normally used in the `0.0` to `1.0` range.
- Negative values may be available for some shape keys.
- Body proportions are not generated automatically by this add-on.
## Files

```text
cc_char_gen/
  __init__.py
  operators.py
  panels.py
  properties.py
```
