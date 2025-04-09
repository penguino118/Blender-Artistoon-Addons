# Blender Artistoon Addons
Blender addon that helps handle assets from the Artistoon engine. Designed to be used with [**GioGio's Bizarre Adventure (PS2)**](https://jojowiki.com/GioGio%27s_Bizarre_Adventure) files.

## Usage
Enable the addon under Blender's settings and then import any `.pzz` file located within `AFS_DATA.AFS`. The addon will create a new collection containing imported files within the `.pzz`, if found.

When exporting, make sure that the collection holding the imported `.pzz` files is selected in the Outliner, and then export over the original `.pzz` archive, or a copy of it. The addon does not create new .pzz files and instead writes the new data over existing entries, so that any data not imported from the original is preserved.

## To-do
- [ ]  Auto Modellista .bin I/O support
- [ ]  GioGio PS2 SDT data support (Shadow caster volumes, for characters)
- [ ]  GioGio PS2 HITS data support (Stage Collision meshes)
- [ ]  GioGio PS2 AAN support (Animation data)
- [ ]  GioGio PS2 TXB/TIM2 import...?
