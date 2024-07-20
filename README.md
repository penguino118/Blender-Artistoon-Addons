# Blender Artistoon Addons
Blender addon that helps handle assets from the Artistoon engine. Designed to be used with [**GioGio's Bizarre Adventure (PS2)**](https://jojowiki.com/GioGio%27s_Bizarre_Adventure) files.</br>
Auto Modellista meshes should work well, too.

# Importers
## Model Importer (AMO)
### To-do
- [ ]  Managing two+ material lists (collection and meshes) is clunky, maybe use Blender’s internal materials for list
- [ ]  Figure out unknown attribute flags

## Armature Importer (AHI)
### To-do
- [ ]  Figure out unknown attribute flags
- [ ]  Reposition model meshes (if already imported) based on bones with translation flag

## Animation Importer (AAN)
### To-do
- [ ]  Support Camera animations
- [ ]  Add animation data types to empty collection for export usage
- [ ]  Read initial header correctly, varies per file a lot
- [ ]  Support Scale and Position key-frame sectors
- [ ]  Fix incorrect rotation from **SHORT** type animation data
- [ ]  Set frame range and loop start values when creating animation actions
- [ ]  Set FCurve 'Ease In' and 'Ease Out' to the animation values instead of Blender’s auto calculation

</br>

# Exporters
## Model Exporter (AMO)
### To-do
- [x]  Fix mesh normals operations for newer blender versions
- [x]  Auto split face corners with multiple UVs
- [x]  Find better solution for Triangle Strips

## Armature Exporter (AHI)
### To-do
- [ ]  Rotation is not always the same as source post export
    - Rotation is ocasionally missing for some bones on export, not sure why.
    - st0e0 (Chapter 10-1) is the main example, clouds don’t keep the same rotation on import/export
- [ ]  Support weird behavior from st0b0 (Pillar object bones)
