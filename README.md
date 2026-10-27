# Morph Gen

Morph Gen is a Blender add-on for manually creating, editing, reusing, and
exporting facial morphs on Blender meshes with shape keys.

## Install

1. Open **Edit > Preferences > Add-ons** in Blender.
2. Click **Install...**.
3. Select `morph_gen.zip`.
4. Enable the Morph Gen add-on.
5. Open a 3D Viewport and press **N**.
6. Open the **Morph Gen** tab.

## Select a model from the 3D View

Morph Gen does not require a folder scan when the model is already open:

1. Select the mesh object in the 3D View.
2. Ensure it has shape keys.
3. Click **Use Selected Mesh**.

The selected mesh is the active morph target. This keeps authoring predictable
when a scene contains body, eye, tongue, or occlusion meshes with separate
shape-key sets.

## Create sequential morph keys

1. Select the model with **Use Selected Mesh**.
2. Blender automatically creates its neutral `Basis` key when the first morph
   key is created. Do not select or replace this key.
3. Set existing morph sliders or edit the mesh to create the first deformation.
4. Enter a name and click **Create Morph Key**. The new key starts at `1.0` and
   captures the current visible mix relative to Blender's `Basis`.
5. Continue deforming the mesh while the new key is at `1.0`.
6. Enter another name and click **Create Morph Key** again.

Each created key uses the production range `0.0..1.0`: `0.0` returns to the
neutral Basis and `1.0` displays that key's captured deformation. Source keys
are reset after capture so the current key owns the visible result and the
next deformation can be authored cleanly.

Use **Remove Selected Morph** to remove a custom shape key from the primary
model. Save the character as an FBX when the morph is ready for export.

## Combine two existing morphs

Use **Combine Existing Morphs** to make a clean, named production morph:

1. Choose the source shape key for **Positive Key**.
2. Choose the source shape key for **Negative Key**.
3. Enter a name in **Combined Morph Name**.
4. Click **Create Named Combined Morph**.

Morph Gen creates one combined controller with a `-1.0..1.0` range:

- `+1.0` drives Positive Key to `1.0` and Negative Key to `0.0`.
- `0.0` drives both source keys to `0.0`, showing Basis.
- `-1.0` drives Positive Key to `0.0` and Negative Key to `1.0`.

The source keys remain native Blender shape keys. Morph Gen only displays the
generated combined controller in its own library.

Only generated combined keys are listed in Morph Gen's library. Original and
manually created keys remain available in Blender's native Shape Keys panel.

## Presets

- **Save Preset** writes current shape-key values to a JSON file.
- **Load Preset** restores values from a JSON file.
- **Reset Morphs** clears all morph values.
- **Randomize Morphs** creates a quick randomized starting point.
- **Sync Meshes** copies primary morph values to matching character meshes.

## Compatibility and limitations

- Blender 3.6 or newer is recommended.
- Shape-key names must match between meshes for synchronization.
- Morph sliders use the `0.0` to `1.0` influence range.
- Body proportions are not generated automatically by this add-on.
## Files

```text
morph_gen/
  __init__.py
  operators.py
  panels.py
  properties.py
```
