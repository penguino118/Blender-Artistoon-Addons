# Blender Artistoon Model Addons
Blender scripts to manage model files from the Artistoon engine. Only tested with [**GioGio's Bizarre Adventure (PS2)**](https://jojowiki.com/GioGio%27s_Bizarre_Adventure).<br>

## Model Importer (AMO)
### To-do
- Figure out unknown attribute flags
- Support Auto Modellista meshes...?

## Armature Importer (AHI)
### To-do
- Figure out unknown attribute flags

## Armature Exporter (AHI)
### To-do
- Rotation isn't always correct (?)
  - Rotation is ocasionally missing for some bones on export, not sure why.

## Model Exporter (AMO)
### To-do
- Separate textures from materials
- Find better solution for Triangle Strips
- Use material custom properties when available
- Export collision data sectors (`00110000`) when available
- Use per-object attributes from the import script when available
